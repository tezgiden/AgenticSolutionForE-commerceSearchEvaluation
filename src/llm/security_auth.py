"""
Security and authentication components for LLM Search Result Evaluation System.

Provides authentication, authorization, API key management, rate limiting,
and security monitoring capabilities.
"""

import hashlib
import hmac
import secrets
import time
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict, deque
import os

from .config import LLMConfig
from .logging_config import get_logger, LoggerMixin
from .exceptions import LLMEvaluatorError


class AuthenticationError(LLMEvaluatorError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(LLMEvaluatorError):
    """Raised when authorization fails."""
    pass


class RateLimitError(LLMEvaluatorError):
    """Raised when rate limit is exceeded."""
    pass


class SecurityRole(Enum):
    """User roles for authorization."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    API_CLIENT = "api_client"


@dataclass
class User:
    """User information for authentication and authorization."""
    id: str
    username: str
    email: str
    roles: List[SecurityRole]
    api_keys: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    login_count: int = 0
    
    def has_role(self, role: SecurityRole) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        role_permissions = {
            SecurityRole.ADMIN: ["*"],  # All permissions
            SecurityRole.USER: ["evaluate", "view_results", "view_metrics"],
            SecurityRole.VIEWER: ["view_results", "view_metrics"],
            SecurityRole.API_CLIENT: ["evaluate"]
        }
        
        for role in self.roles:
            permissions = role_permissions.get(role, [])
            if "*" in permissions or permission in permissions:
                return True
        
        return False


@dataclass
class APIKey:
    """API key information."""
    key_id: str
    key_hash: str
    user_id: str
    name: str
    permissions: List[str]
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    usage_count: int = 0
    rate_limit: Optional[int] = None  # Requests per minute
    
    def can_access(self, permission: str) -> bool:
        """Check if API key has permission."""
        return "*" in self.permissions or permission in self.permissions


class Authenticator(ABC):
    """Abstract base class for authentication providers."""
    
    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> Optional[User]:
        """Authenticate user with credentials."""
        pass
    
    @abstractmethod
    def validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """Validate API key."""
        pass


class InMemoryAuthenticator(Authenticator, LoggerMixin):
    """In-memory authenticator for development and testing."""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.api_keys: Dict[str, APIKey] = {}
        self.password_hashes: Dict[str, str] = {}
        self._lock = threading.RLock()
        
        # Create default admin user
        self._create_default_users()
    
    def _create_default_users(self):
        """Create default users for development."""
        admin_user = User(
            id="admin",
            username="admin",
            email="admin@example.com",
            roles=[SecurityRole.ADMIN]
        )
        
        # Default password: "admin123"
        admin_password_hash = self._hash_password("admin123")
        
        with self._lock:
            self.users["admin"] = admin_user
            self.password_hashes["admin"] = admin_password_hash
        
        self.logger.info("Created default admin user (username: admin, password: admin123)")
    
    def authenticate(self, credentials: Dict[str, Any]) -> Optional[User]:
        """Authenticate user with username/password."""
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            return None
        
        with self._lock:
            user = self.users.get(username)
            if not user or not user.is_active:
                return None
            
            stored_hash = self.password_hashes.get(username)
            if not stored_hash:
                return None
            
            if self._verify_password(password, stored_hash):
                user.last_login = datetime.now()
                user.login_count += 1
                self.logger.info(f"User authenticated: {username}")
                return user
        
        return None
    
    def validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """Validate API key."""
        key_hash = self._hash_api_key(api_key)
        
        with self._lock:
            for key_obj in self.api_keys.values():
                if key_obj.key_hash == key_hash and key_obj.is_active:
                    key_obj.last_used = datetime.now()
                    key_obj.usage_count += 1
                    return key_obj
        
        return None
    
    def create_user(self, username: str, email: str, password: str, 
                   roles: List[SecurityRole]) -> User:
        """Create a new user."""
        user_id = secrets.token_urlsafe(16)
        password_hash = self._hash_password(password)
        
        user = User(
            id=user_id,
            username=username,
            email=email,
            roles=roles
        )
        
        with self._lock:
            self.users[username] = user
            self.password_hashes[username] = password_hash
        
        self.logger.info(f"Created user: {username}")
        return user
    
    def create_api_key(self, user_id: str, name: str, 
                      permissions: List[str], rate_limit: Optional[int] = None) -> Tuple[str, APIKey]:
        """Create a new API key."""
        api_key = f"llm_eval_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_api_key(api_key)
        key_id = secrets.token_urlsafe(16)
        
        api_key_obj = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            name=name,
            permissions=permissions,
            rate_limit=rate_limit
        )
        
        with self._lock:
            self.api_keys[key_id] = api_key_obj
        
        self.logger.info(f"Created API key: {name} for user {user_id}")
        return api_key, api_key_obj
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        with self._lock:
            if key_id in self.api_keys:
                self.api_keys[key_id].is_active = False
                self.logger.info(f"Revoked API key: {key_id}")
                return True
        
        return False
    
    def _hash_password(self, password: str) -> str:
        """Hash password using PBKDF2."""
        salt = secrets.token_bytes(32)
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return salt.hex() + key.hex()
    
    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash."""
        try:
            salt = bytes.fromhex(stored_hash[:64])
            stored_key = stored_hash[64:]
            new_key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
            return hmac.compare_digest(stored_key, new_key.hex())
        except:
            return False
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()


class JWTAuthenticator(Authenticator, LoggerMixin):
    """JWT-based authenticator."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.users: Dict[str, User] = {}
        self.api_keys: Dict[str, APIKey] = {}
        self._lock = threading.RLock()
    
    def authenticate(self, credentials: Dict[str, Any]) -> Optional[User]:
        """Authenticate using JWT token."""
        token = credentials.get("token")
        if not token:
            return None
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("user_id")
            
            with self._lock:
                user = self.users.get(user_id)
                if user and user.is_active:
                    # Check token expiration
                    exp = payload.get("exp")
                    if exp and datetime.fromtimestamp(exp) > datetime.now():
                        user.last_login = datetime.now()
                        return user
        
        except jwt.InvalidTokenError as e:
            self.logger.warning(f"Invalid JWT token: {e}")
        
        return None
    
    def validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """Validate API key (same as in-memory)."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        with self._lock:
            for key_obj in self.api_keys.values():
                if key_obj.key_hash == key_hash and key_obj.is_active:
                    key_obj.last_used = datetime.now()
                    key_obj.usage_count += 1
                    return key_obj
        
        return None
    
    def create_token(self, user: User, expires_in: int = 3600) -> str:
        """Create JWT token for user."""
        payload = {
            "user_id": user.id,
            "username": user.username,
            "roles": [role.value for role in user.roles],
            "iat": datetime.now(),
            "exp": datetime.now() + timedelta(seconds=expires_in)
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)


class RateLimiter(LoggerMixin):
    """Rate limiting implementation with multiple strategies."""
    
    def __init__(self, default_limit: int = 100, window_seconds: int = 60):
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.request_counts: Dict[str, deque] = defaultdict(deque)
        self.custom_limits: Dict[str, int] = {}
        self._lock = threading.RLock()
    
    def is_allowed(self, identifier: str, limit: Optional[int] = None) -> bool:
        """Check if request is allowed based on rate limit."""
        current_time = time.time()
        limit = limit or self.custom_limits.get(identifier, self.default_limit)
        
        with self._lock:
            # Clean old requests outside the window
            requests = self.request_counts[identifier]
            cutoff_time = current_time - self.window_seconds
            
            while requests and requests[0] < cutoff_time:
                requests.popleft()
            
            # Check if limit is exceeded
            if len(requests) >= limit:
                self.logger.warning(f"Rate limit exceeded for {identifier}: {len(requests)}/{limit}")
                return False
            
            # Add current request
            requests.append(current_time)
            return True
    
    def set_custom_limit(self, identifier: str, limit: int) -> None:
        """Set custom rate limit for specific identifier."""
        with self._lock:
            self.custom_limits[identifier] = limit
    
    def get_remaining_requests(self, identifier: str) -> int:
        """Get remaining requests in current window."""
        current_time = time.time()
        limit = self.custom_limits.get(identifier, self.default_limit)
        
        with self._lock:
            requests = self.request_counts[identifier]
            cutoff_time = current_time - self.window_seconds
            
            # Count valid requests
            valid_requests = sum(1 for req_time in requests if req_time >= cutoff_time)
            return max(0, limit - valid_requests)
    
    def reset_user_limit(self, identifier: str) -> None:
        """Reset rate limit for specific identifier."""
        with self._lock:
            if identifier in self.request_counts:
                self.request_counts[identifier].clear()


class SecurityManager(LoggerMixin):
    """Central security management system."""
    
    def __init__(self, authenticator: Authenticator, rate_limiter: RateLimiter = None):
        self.authenticator = authenticator
        self.rate_limiter = rate_limiter or RateLimiter()
        self.security_events: List[Dict[str, Any]] = []
        self.blocked_ips: set = set()
        self.suspicious_activity: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.RLock()
    
    def authenticate_request(self, credentials: Dict[str, Any], 
                           client_ip: str = None) -> Optional[User]:
        """Authenticate a request with security checks."""
        # Check if IP is blocked
        if client_ip and client_ip in self.blocked_ips:
            self._log_security_event("blocked_ip_attempt", {"ip": client_ip})
            raise AuthenticationError("Access denied")
        
        # Attempt authentication
        user = self.authenticator.authenticate(credentials)
        
        if user:
            self._log_security_event("successful_auth", {
                "user_id": user.id,
                "username": user.username,
                "client_ip": client_ip
            })
        else:
            self._log_security_event("failed_auth", {
                "credentials": {k: "***" if k == "password" else v for k, v in credentials.items()},
                "client_ip": client_ip
            })
            
            # Track failed attempts
            if client_ip:
                self._track_suspicious_activity(client_ip)
        
        return user
    
    def validate_api_request(self, api_key: str, permission: str, 
                           client_ip: str = None) -> Optional[APIKey]:
        """Validate API request with rate limiting and security checks."""
        # Check if IP is blocked
        if client_ip and client_ip in self.blocked_ips:
            self._log_security_event("blocked_ip_api_attempt", {"ip": client_ip})
            raise AuthenticationError("Access denied")
        
        # Validate API key
        key_obj = self.authenticator.validate_api_key(api_key)
        if not key_obj:
            self._log_security_event("invalid_api_key", {
                "key_prefix": api_key[:10] + "...",
                "client_ip": client_ip
            })
            raise AuthenticationError("Invalid API key")
        
        # Check permissions
        if not key_obj.can_access(permission):
            self._log_security_event("insufficient_permissions", {
                "key_id": key_obj.key_id,
                "permission": permission,
                "client_ip": client_ip
            })
            raise AuthorizationError(f"Insufficient permissions for {permission}")
        
        # Check rate limit
        rate_limit = key_obj.rate_limit
        identifier = f"api_key_{key_obj.key_id}"
        
        if not self.rate_limiter.is_allowed(identifier, rate_limit):
            self._log_security_event("rate_limit_exceeded", {
                "key_id": key_obj.key_id,
                "client_ip": client_ip
            })
            raise RateLimitError("Rate limit exceeded")
        
        self._log_security_event("successful_api_auth", {
            "key_id": key_obj.key_id,
            "permission": permission,
            "client_ip": client_ip
        })
        
        return key_obj
    
    def check_permission(self, user: User, permission: str) -> bool:
        """Check if user has required permission."""
        has_permission = user.has_permission(permission)
        
        if not has_permission:
            self._log_security_event("permission_denied", {
                "user_id": user.id,
                "permission": permission
            })
        
        return has_permission
    
    def block_ip(self, ip_address: str, reason: str = "Security violation") -> None:
        """Block an IP address."""
        with self._lock:
            self.blocked_ips.add(ip_address)
        
        self._log_security_event("ip_blocked", {
            "ip": ip_address,
            "reason": reason
        })
    
    def unblock_ip(self, ip_address: str) -> None:
        """Unblock an IP address."""
        with self._lock:
            self.blocked_ips.discard(ip_address)
        
        self._log_security_event("ip_unblocked", {"ip": ip_address})
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security summary and statistics."""
        with self._lock:
            recent_events = [
                event for event in self.security_events
                if event["timestamp"] > time.time() - 3600  # Last hour
            ]
            
            event_counts = defaultdict(int)
            for event in recent_events:
                event_counts[event["event_type"]] += 1
            
            return {
                "total_events_last_hour": len(recent_events),
                "event_breakdown": dict(event_counts),
                "blocked_ips": list(self.blocked_ips),
                "suspicious_ips": [
                    ip for ip, attempts in self.suspicious_activity.items()
                    if len(attempts) >= 5
                ]
            }
    
    def _track_suspicious_activity(self, identifier: str) -> None:
        """Track suspicious activity for automatic blocking."""
        current_time = time.time()
        
        with self._lock:
            attempts = self.suspicious_activity[identifier]
            
            # Clean old attempts (last 5 minutes)
            cutoff_time = current_time - 300
            attempts[:] = [t for t in attempts if t > cutoff_time]
            
            # Add current attempt
            attempts.append(current_time)
            
            # Auto-block if too many attempts
            if len(attempts) >= 10:  # 10 failed attempts in 5 minutes
                self.block_ip(identifier, "Too many failed authentication attempts")
    
    def _log_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log security event."""
        event = {
            "timestamp": time.time(),
            "event_type": event_type,
            "details": details
        }
        
        with self._lock:
            self.security_events.append(event)
            
            # Keep only last 1000 events
            if len(self.security_events) > 1000:
                self.security_events = self.security_events[-1000:]
        
        self.logger.info(f"Security event: {event_type}", extra=details)


def create_security_manager(config: LLMConfig) -> SecurityManager:
    """Create security manager based on configuration."""
    auth_type = os.getenv('AUTH_TYPE', 'memory').lower()
    
    if auth_type == 'jwt':
        secret_key = os.getenv('JWT_SECRET_KEY')
        if not secret_key:
            secret_key = secrets.token_urlsafe(32)
            logger = get_logger('llm_evaluator.security')
            logger.warning("No JWT_SECRET_KEY provided, using generated key (not suitable for production)")
        
        authenticator = JWTAuthenticator(secret_key)
    else:
        authenticator = InMemoryAuthenticator()
    
    # Configure rate limiter
    default_rate_limit = int(os.getenv('DEFAULT_RATE_LIMIT', '100'))
    rate_window = int(os.getenv('RATE_LIMIT_WINDOW', '60'))
    rate_limiter = RateLimiter(default_rate_limit, rate_window)
    
    return SecurityManager(authenticator, rate_limiter)


# Decorators for security
def require_authentication(permission: str = None):
    """Decorator to require authentication for functions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # This would integrate with the actual request context
            # Implementation depends on the web framework used
            
            # For now, just a placeholder
            user = kwargs.get('current_user')
            if not user:
                raise AuthenticationError("Authentication required")
            
            if permission and not user.has_permission(permission):
                raise AuthorizationError(f"Permission required: {permission}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_api_key(permission: str):
    """Decorator to require API key authentication."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # This would integrate with the actual request context
            api_key = kwargs.get('api_key')
            if not api_key:
                raise AuthenticationError("API key required")
            
            # Validate API key (implementation depends on context)
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def rate_limit(requests_per_minute: int = 60):
    """Decorator to apply rate limiting."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # This would integrate with the actual request context
            # Implementation depends on the web framework used
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Security context manager
class SecurityContext:
    """Security context for tracking user and permissions."""
    
    def __init__(self, user: Optional[User] = None, api_key: Optional[APIKey] = None,
                 client_ip: Optional[str] = None):
        self.user = user
        self.api_key = api_key
        self.client_ip = client_ip
        self.session_id = secrets.token_urlsafe(16)
    
    def has_permission(self, permission: str) -> bool:
        """Check if context has required permission."""
        if self.user:
            return self.user.has_permission(permission)
        elif self.api_key:
            return self.api_key.can_access(permission)
        return False
    
    def get_identifier(self) -> str:
        """Get unique identifier for this context."""
        if self.user:
            return f"user_{self.user.id}"
        elif self.api_key:
            return f"api_key_{self.api_key.key_id}"
        elif self.client_ip:
            return f"ip_{self.client_ip}"
        return "anonymous"


# Global security manager instance
_security_manager: Optional[SecurityManager] = None
_security_lock = threading.Lock()


def get_security_manager() -> SecurityManager:
    """Get global security manager instance."""
    global _security_manager
    
    if _security_manager is None:
        with _security_lock:
            if _security_manager is None:
                from config import LLMConfig
                config = LLMConfig.from_environment()
                _security_manager = create_security_manager(config)
    
    return _security_manager


def security_enabled() -> bool:
    """Check if security is enabled."""
    return os.getenv('ENABLE_SECURITY', 'true').lower() == 'true'
