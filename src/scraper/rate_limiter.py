"""Rate limiting utilities for respectful web scraping."""

import time
import logging
import threading
from abc import ABC, abstractmethod
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from collections import deque, defaultdict
from enum import Enum


logger = logging.getLogger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    EXPONENTIAL_BACKOFF = "exponential_backoff"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    
    requests_per_second: float = 1.0
    requests_per_minute: int = 60
    requests_per_hour: int = 3600
    burst_allowance: int = 5
    backoff_factor: float = 2.0
    max_backoff_seconds: float = 300.0
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    
    def __post_init__(self):
        """Validate configuration."""
        if self.requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        if self.burst_allowance < 1:
            raise ValueError("burst_allowance must be at least 1")
        if self.backoff_factor < 1:
            raise ValueError("backoff_factor must be at least 1")


class BaseRateLimiter(ABC):
    """Abstract base class for rate limiters."""
    
    def __init__(self, config: RateLimitConfig):
        """Initialize rate limiter.
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config
        self._lock = threading.Lock()
        self.stats = {
            'requests_made': 0,
            'requests_blocked': 0,
            'total_wait_time': 0.0,
            'last_request_time': 0.0
        }
    
    @abstractmethod
    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire permission to make a request.
        
        Args:
            timeout: Maximum time to wait for permission
            
        Returns:
            True if permission granted, False if timeout
        """
        pass
    
    @abstractmethod
    def can_proceed(self) -> bool:
        """Check if request can proceed without waiting.
        
        Returns:
            True if request can proceed immediately
        """
        pass
    
    def wait_if_needed(self, timeout: Optional[float] = None) -> bool:
        """Wait if needed before proceeding.
        
        Args:
            timeout: Maximum time to wait
            
        Returns:
            True if can proceed, False if timeout
        """
        return self.acquire(timeout)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        with self._lock:
            return self.stats.copy()
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        with self._lock:
            self.stats = {
                'requests_made': 0,
                'requests_blocked': 0,
                'total_wait_time': 0.0,
                'last_request_time': 0.0
            }


class TokenBucketRateLimiter(BaseRateLimiter):
    """Token bucket rate limiter implementation."""
    
    def __init__(self, config: RateLimitConfig):
        """Initialize token bucket rate limiter."""
        super().__init__(config)
        self.capacity = config.burst_allowance
        self.tokens = self.capacity
        self.fill_rate = config.requests_per_second
        self.last_refill = time.time()
    
    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire a token from the bucket."""
        start_time = time.time()
        deadline = start_time + timeout if timeout else None
        
        while True:
            with self._lock:
                self._refill_bucket()
                
                if self.tokens >= 1:
                    self.tokens -= 1
                    self.stats['requests_made'] += 1
                    self.stats['last_request_time'] = time.time()
                    return True
                
                if deadline and time.time() >= deadline:
                    self.stats['requests_blocked'] += 1
                    return False
                
                # Calculate wait time for next token
                wait_time = min(1.0 / self.fill_rate, 1.0)
                self.stats['total_wait_time'] += wait_time
            
            time.sleep(wait_time)
    
    def can_proceed(self) -> bool:
        """Check if can proceed without waiting."""
        with self._lock:
            self._refill_bucket()
            return self.tokens >= 1
    
    def _refill_bucket(self) -> None:
        """Refill tokens in the bucket."""
        now = time.time()
        time_elapsed = now - self.last_refill
        
        tokens_to_add = time_elapsed * self.fill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now


class SlidingWindowRateLimiter(BaseRateLimiter):
    """Sliding window rate limiter implementation."""
    
    def __init__(self, config: RateLimitConfig):
        """Initialize sliding window rate limiter."""
        super().__init__(config)
        self.window_size = 60.0  # 1 minute window
        self.max_requests = config.requests_per_minute
        self.request_times = deque()
    
    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire permission using sliding window."""
        start_time = time.time()
        deadline = start_time + timeout if timeout else None
        
        while True:
            with self._lock:
                now = time.time()
                self._cleanup_old_requests(now)
                
                if len(self.request_times) < self.max_requests:
                    self.request_times.append(now)
                    self.stats['requests_made'] += 1
                    self.stats['last_request_time'] = now
                    return True
                
                if deadline and now >= deadline:
                    self.stats['requests_blocked'] += 1
                    return False
                
                # Wait until oldest request falls outside window
                oldest_request = self.request_times[0]
                wait_time = max(0.1, oldest_request + self.window_size - now)
                self.stats['total_wait_time'] += wait_time
            
            time.sleep(min(wait_time, 1.0))
    
    def can_proceed(self) -> bool:
        """Check if can proceed without waiting."""
        with self._lock:
            self._cleanup_old_requests(time.time())
            return len(self.request_times) < self.max_requests
    
    def _cleanup_old_requests(self, current_time: float) -> None:
        """Remove requests outside the sliding window."""
        cutoff_time = current_time - self.window_size
        while self.request_times and self.request_times[0] <= cutoff_time:
            self.request_times.popleft()


class ExponentialBackoffRateLimiter(BaseRateLimiter):
    """Exponential backoff rate limiter for handling errors."""
    
    def __init__(self, config: RateLimitConfig):
        """Initialize exponential backoff rate limiter."""
        super().__init__(config)
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.current_backoff = 0.0
    
    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire permission with exponential backoff."""
        with self._lock:
            now = time.time()
            
            if self.current_backoff > 0:
                time_since_failure = now - self.last_failure_time
                if time_since_failure < self.current_backoff:
                    remaining_wait = self.current_backoff - time_since_failure
                    
                    if timeout and remaining_wait > timeout:
                        self.stats['requests_blocked'] += 1
                        return False
                    
                    self.stats['total_wait_time'] += remaining_wait
                    time.sleep(remaining_wait)
            
            self.stats['requests_made'] += 1
            self.stats['last_request_time'] = time.time()
            return True
    
    def can_proceed(self) -> bool:
        """Check if can proceed without waiting."""
        with self._lock:
            if self.current_backoff == 0:
                return True
            
            time_since_failure = time.time() - self.last_failure_time
            return time_since_failure >= self.current_backoff
    
    def record_failure(self) -> None:
        """Record a failure and increase backoff."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            # Calculate exponential backoff
            backoff_seconds = min(
                self.config.backoff_factor ** self.failure_count,
                self.config.max_backoff_seconds
            )
            self.current_backoff = backoff_seconds
            
            logger.warning(
                f"Failure #{self.failure_count} recorded. "
                f"Backing off for {backoff_seconds:.2f} seconds"
            )
    
    def record_success(self) -> None:
        """Record a success and reset backoff."""
        with self._lock:
            if self.failure_count > 0:
                logger.info(f"Success after {self.failure_count} failures. Resetting backoff.")
            
            self.failure_count = 0
            self.current_backoff = 0.0


class AdaptiveRateLimiter(BaseRateLimiter):
    """Adaptive rate limiter that adjusts based on response times."""
    
    def __init__(self, config: RateLimitConfig):
        """Initialize adaptive rate limiter."""
        super().__init__(config)
        self.response_times = deque(maxlen=50)  # Keep last 50 response times
        self.current_rate = config.requests_per_second
        self.min_rate = 0.1
        self.max_rate = config.requests_per_second * 2
        self.adjustment_factor = 0.1
        self.target_response_time = 2.0  # Target 2 second response time
    
    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire with adaptive rate adjustment."""
        with self._lock:
            wait_time = 1.0 / self.current_rate
            
            if timeout and wait_time > timeout:
                self.stats['requests_blocked'] += 1
                return False
            
            self.stats['total_wait_time'] += wait_time
            self.stats['requests_made'] += 1
            self.stats['last_request_time'] = time.time()
        
        time.sleep(wait_time)
        return True
    
    def can_proceed(self) -> bool:
        """Check if can proceed without waiting."""
        # Adaptive limiter always allows but with delay
        return True
    
    def record_response_time(self, response_time: float) -> None:
        """Record response time and adjust rate.
        
        Args:
            response_time: Response time in seconds
        """
        with self._lock:
            self.response_times.append(response_time)
            
            if len(self.response_times) >= 10:  # Need some data to adjust
                avg_response_time = sum(self.response_times) / len(self.response_times)
                
                if avg_response_time > self.target_response_time:
                    # Slow down
                    new_rate = self.current_rate * (1 - self.adjustment_factor)
                    self.current_rate = max(self.min_rate, new_rate)
                    logger.debug(f"Slowing down rate to {self.current_rate:.2f} req/s")
                    
                elif avg_response_time < self.target_response_time * 0.5:
                    # Speed up
                    new_rate = self.current_rate * (1 + self.adjustment_factor)
                    self.current_rate = min(self.max_rate, new_rate)
                    logger.debug(f"Speeding up rate to {self.current_rate:.2f} req/s")


class DomainBasedRateLimiter:
    """Rate limiter that manages limits per domain."""
    
    def __init__(self, default_config: RateLimitConfig):
        """Initialize domain-based rate limiter.
        
        Args:
            default_config: Default configuration for all domains
        """
        self.default_config = default_config
        self.domain_limiters: Dict[str, BaseRateLimiter] = {}
        self.domain_configs: Dict[str, RateLimitConfig] = {}
        self._lock = threading.Lock()
    
    def set_domain_config(self, domain: str, config: RateLimitConfig) -> None:
        """Set specific configuration for a domain.
        
        Args:
            domain: Domain name
            config: Rate limiting configuration for the domain
        """
        with self._lock:
            self.domain_configs[domain] = config
            # Remove existing limiter to recreate with new config
            if domain in self.domain_limiters:
                del self.domain_limiters[domain]
    
    def get_limiter_for_domain(self, domain: str) -> BaseRateLimiter:
        """Get rate limiter for a specific domain.
        
        Args:
            domain: Domain name
            
        Returns:
            Rate limiter for the domain
        """
        with self._lock:
            if domain not in self.domain_limiters:
                config = self.domain_configs.get(domain, self.default_config)
                self.domain_limiters[domain] = self._create_limiter(config)
            
            return self.domain_limiters[domain]
    
    def acquire_for_url(self, url: str, timeout: Optional[float] = None) -> bool:
        """Acquire permission for a specific URL.
        
        Args:
            url: Target URL
            timeout: Maximum time to wait
            
        Returns:
            True if permission granted
        """
        domain = self._extract_domain(url)
        limiter = self.get_limiter_for_domain(domain)
        return limiter.acquire(timeout)
    
    def can_proceed_for_url(self, url: str) -> bool:
        """Check if can proceed for a specific URL.
        
        Args:
            url: Target URL
            
        Returns:
            True if can proceed immediately
        """
        domain = self._extract_domain(url)
        limiter = self.get_limiter_for_domain(domain)
        return limiter.can_proceed()
    
    def get_domain_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all domains.
        
        Returns:
            Dictionary mapping domains to their statistics
        """
        with self._lock:
            return {
                domain: limiter.get_stats()
                for domain, limiter in self.domain_limiters.items()
            }
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return "unknown"
    
    def _create_limiter(self, config: RateLimitConfig) -> BaseRateLimiter:
        """Create rate limiter based on strategy."""
        if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return TokenBucketRateLimiter(config)
        elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return SlidingWindowRateLimiter(config)
        elif config.strategy == RateLimitStrategy.EXPONENTIAL_BACKOFF:
            return ExponentialBackoffRateLimiter(config)
        else:
            # Default to token bucket
            return TokenBucketRateLimiter(config)


class RateLimitedSession:
    """Session wrapper that applies rate limiting to requests."""
    
    def __init__(self, rate_limiter: BaseRateLimiter):
        """Initialize rate limited session.
        
        Args:
            rate_limiter: Rate limiter to use
        """
        self.rate_limiter = rate_limiter
        self.response_times = []
    
    def make_request(self, request_func: Callable, *args, **kwargs) -> Any:
        """Make a rate-limited request.
        
        Args:
            request_func: Function to call for the request
            *args: Arguments for request function
            **kwargs: Keyword arguments for request function
            
        Returns:
            Result of request function
        """
        # Wait for permission
        if not self.rate_limiter.acquire(timeout=30):
            raise TimeoutError("Rate limiter timeout")
        
        # Record start time
        start_time = time.time()
        
        try:
            # Make the request
            result = request_func(*args, **kwargs)
            
            # Record success if using exponential backoff
            if isinstance(self.rate_limiter, ExponentialBackoffRateLimiter):
                self.rate_limiter.record_success()
            
            # Record response time if using adaptive limiter
            response_time = time.time() - start_time
            self.response_times.append(response_time)
            
            if isinstance(self.rate_limiter, AdaptiveRateLimiter):
                self.rate_limiter.record_response_time(response_time)
            
            return result
            
        except Exception as e:
            # Record failure if using exponential backoff
            if isinstance(self.rate_limiter, ExponentialBackoffRateLimiter):
                self.rate_limiter.record_failure()
            
            raise
    
    def get_average_response_time(self) -> float:
        """Get average response time."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)


# Decorator for rate limiting functions
def rate_limited(rate_limiter: BaseRateLimiter, timeout: Optional[float] = None):
    """Decorator to rate limit function calls.
    
    Args:
        rate_limiter: Rate limiter to use
        timeout: Maximum time to wait for permission
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not rate_limiter.acquire(timeout):
                raise TimeoutError(f"Rate limit timeout for {func.__name__}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Context manager for rate limiting
class RateLimitContext:
    """Context manager for rate limiting operations."""
    
    def __init__(self, rate_limiter: BaseRateLimiter, timeout: Optional[float] = None):
        """Initialize rate limit context.
        
        Args:
            rate_limiter: Rate limiter to use
            timeout: Maximum time to wait for permission
        """
        self.rate_limiter = rate_limiter
        self.timeout = timeout
    
    def __enter__(self):
        """Enter context and acquire permission."""
        if not self.rate_limiter.acquire(self.timeout):
            raise TimeoutError("Rate limit timeout")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        # Record failure if exception occurred and using exponential backoff
        if exc_type and isinstance(self.rate_limiter, ExponentialBackoffRateLimiter):
            self.rate_limiter.record_failure()
        elif not exc_type and isinstance(self.rate_limiter, ExponentialBackoffRateLimiter):
            self.rate_limiter.record_success()