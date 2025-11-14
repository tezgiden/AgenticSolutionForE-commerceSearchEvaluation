"""
Intelligent caching system for LLM Search Result Evaluation.

Provides multiple caching strategies to reduce expensive LLM calls and improve
response times while maintaining result quality.
"""

import hashlib
import json
import pickle
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List, Union, Tuple
from pathlib import Path
import os

from config import LLMConfig
from logging_config import get_logger, LoggerMixin


@dataclass
class CacheEntry:
    """Represents a cached item with metadata."""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def access(self) -> None:
        """Record an access to this cache entry."""
        self.access_count += 1
        self.last_accessed = datetime.now()


class CacheStore(ABC):
    """Abstract base class for cache storage backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[CacheEntry]:
        """Retrieve an entry from the cache."""
        pass
    
    @abstractmethod
    def put(self, entry: CacheEntry) -> None:
        """Store an entry in the cache."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete an entry from the cache."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all entries from the cache."""
        pass
    
    @abstractmethod
    def keys(self) -> List[str]:
        """Get all cache keys."""
        pass
    
    @abstractmethod
    def size(self) -> int:
        """Get the number of entries in the cache."""
        pass


class InMemoryCacheStore(CacheStore, LoggerMixin):
    """In-memory cache store with LRU eviction."""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.store: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []  # For LRU tracking
        self._lock = threading.RLock()
        self.current_memory_usage = 0
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Retrieve and mark as accessed."""
        with self._lock:
            entry = self.store.get(key)
            if entry is None:
                return None
            
            if entry.is_expired():
                self.delete(key)
                return None
            
            # Update access tracking
            entry.access()
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            
            self.logger.debug(f"Cache hit for key: {key}")
            return entry
    
    def put(self, entry: CacheEntry) -> None:
        """Store entry with eviction if necessary."""
        with self._lock:
            # Calculate entry size
            entry.size_bytes = self._calculate_size(entry.value)
            
            # Check if we need to evict
            while self._should_evict(entry.size_bytes):
                self._evict_lru()
            
            # Store the entry
            if entry.key in self.store:
                old_entry = self.store[entry.key]
                self.current_memory_usage -= old_entry.size_bytes
                if entry.key in self.access_order:
                    self.access_order.remove(entry.key)
            
            self.store[entry.key] = entry
            self.access_order.append(entry.key)
            self.current_memory_usage += entry.size_bytes
            
            self.logger.debug(f"Cached entry for key: {entry.key} (size: {entry.size_bytes} bytes)")
    
    def delete(self, key: str) -> bool:
        """Remove entry from cache."""
        with self._lock:
            entry = self.store.pop(key, None)
            if entry is None:
                return False
            
            if key in self.access_order:
                self.access_order.remove(key)
            
            self.current_memory_usage -= entry.size_bytes
            self.logger.debug(f"Deleted cache entry: {key}")
            return True
    
    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self.store.clear()
            self.access_order.clear()
            self.current_memory_usage = 0
            self.logger.info("Cache cleared")
    
    def keys(self) -> List[str]:
        """Get all cache keys."""
        with self._lock:
            return list(self.store.keys())
    
    def size(self) -> int:
        """Get number of entries."""
        with self._lock:
            return len(self.store)
    
    def _should_evict(self, new_entry_size: int) -> bool:
        """Check if eviction is needed."""
        return (len(self.store) >= self.max_size or 
                self.current_memory_usage + new_entry_size > self.max_memory_bytes)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self.access_order:
            return
        
        lru_key = self.access_order[0]
        self.delete(lru_key)
        self.logger.debug(f"Evicted LRU entry: {lru_key}")
    
    def _calculate_size(self, value: Any) -> int:
        """Estimate size of a value in bytes."""
        try:
            return len(pickle.dumps(value))
        except:
            # Fallback estimation
            return len(str(value).encode('utf-8'))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_accesses = sum(entry.access_count for entry in self.store.values())
            return {
                'entries': len(self.store),
                'max_size': self.max_size,
                'memory_usage_bytes': self.current_memory_usage,
                'max_memory_bytes': self.max_memory_bytes,
                'memory_usage_percent': (self.current_memory_usage / self.max_memory_bytes) * 100,
                'total_accesses': total_accesses,
                'avg_accesses_per_entry': total_accesses / len(self.store) if self.store else 0
            }


class FileCacheStore(CacheStore, LoggerMixin):
    """File-based cache store for persistence."""
    
    def __init__(self, cache_dir: str, max_files: int = 10000):
        self.cache_dir = Path(cache_dir)
        self.max_files = max_files
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        
        # Create index file for metadata
        self.index_file = self.cache_dir / "cache_index.json"
        self.index: Dict[str, Dict[str, Any]] = self._load_index()
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Load entry from file."""
        with self._lock:
            if key not in self.index:
                return None
            
            file_path = self.cache_dir / f"{self._safe_filename(key)}.pkl"
            if not file_path.exists():
                # Clean up stale index entry
                del self.index[key]
                self._save_index()
                return None
            
            try:
                with open(file_path, 'rb') as f:
                    entry = pickle.load(f)
                
                if entry.is_expired():
                    self.delete(key)
                    return None
                
                entry.access()
                self.index[key]['last_accessed'] = entry.last_accessed.isoformat()
                self.index[key]['access_count'] = entry.access_count
                self._save_index()
                
                self.logger.debug(f"File cache hit for key: {key}")
                return entry
                
            except Exception as e:
                self.logger.error(f"Error loading cache entry {key}: {e}")
                self.delete(key)
                return None
    
    def put(self, entry: CacheEntry) -> None:
        """Save entry to file."""
        with self._lock:
            # Check if we need to evict
            while len(self.index) >= self.max_files:
                self._evict_oldest()
            
            file_path = self.cache_dir / f"{self._safe_filename(entry.key)}.pkl"
            
            try:
                with open(file_path, 'wb') as f:
                    pickle.dump(entry, f)
                
                # Update index
                self.index[entry.key] = {
                    'created_at': entry.created_at.isoformat(),
                    'expires_at': entry.expires_at.isoformat() if entry.expires_at else None,
                    'last_accessed': entry.last_accessed.isoformat(),
                    'access_count': entry.access_count,
                    'size_bytes': entry.size_bytes,
                    'file_path': str(file_path)
                }
                self._save_index()
                
                self.logger.debug(f"Saved cache entry to file: {entry.key}")
                
            except Exception as e:
                self.logger.error(f"Error saving cache entry {entry.key}: {e}")
    
    def delete(self, key: str) -> bool:
        """Delete entry file and index entry."""
        with self._lock:
            if key not in self.index:
                return False
            
            file_path = self.cache_dir / f"{self._safe_filename(key)}.pkl"
            
            try:
                if file_path.exists():
                    file_path.unlink()
                del self.index[key]
                self._save_index()
                self.logger.debug(f"Deleted file cache entry: {key}")
                return True
            except Exception as e:
                self.logger.error(f"Error deleting cache entry {key}: {e}")
                return False
    
    def clear(self) -> None:
        """Clear all cache files."""
        with self._lock:
            try:
                for file_path in self.cache_dir.glob("*.pkl"):
                    file_path.unlink()
                self.index.clear()
                self._save_index()
                self.logger.info("File cache cleared")
            except Exception as e:
                self.logger.error(f"Error clearing file cache: {e}")
    
    def keys(self) -> List[str]:
        """Get all cache keys."""
        with self._lock:
            return list(self.index.keys())
    
    def size(self) -> int:
        """Get number of entries."""
        with self._lock:
            return len(self.index)
    
    def _safe_filename(self, key: str) -> str:
        """Convert cache key to safe filename."""
        return hashlib.md5(key.encode()).hexdigest()
    
    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Load cache index from file."""
        if not self.index_file.exists():
            return {}
        
        try:
            with open(self.index_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading cache index: {e}")
            return {}
    
    def _save_index(self) -> None:
        """Save cache index to file."""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving cache index: {e}")
    
    def _evict_oldest(self) -> None:
        """Evict oldest entry by creation time."""
        if not self.index:
            return
        
        oldest_key = min(self.index.keys(), 
                        key=lambda k: self.index[k]['created_at'])
        self.delete(oldest_key)
        self.logger.debug(f"Evicted oldest file cache entry: {oldest_key}")


class CacheKeyGenerator:
    """Generates consistent cache keys for different types of data."""
    
    @staticmethod
    def evaluation_key(query: str, results: List[Dict[str, str]], 
                      search_type: str, model: str) -> str:
        """Generate cache key for evaluation requests."""
        # Create a deterministic hash of the evaluation inputs
        data = {
            'query': query.lower().strip(),
            'search_type': search_type,
            'model': model,
            'results_hash': CacheKeyGenerator._hash_results(results)
        }
        
        return CacheKeyGenerator._generate_hash(data)
    
    @staticmethod
    def prompt_key(search_type: str, query: str, results_count: int) -> str:
        """Generate cache key for prompts."""
        data = {
            'type': 'prompt',
            'search_type': search_type,
            'query': query.lower().strip(),
            'results_count': results_count
        }
        
        return CacheKeyGenerator._generate_hash(data)
    
    @staticmethod
    def llm_response_key(model: str, prompt: str) -> str:
        """Generate cache key for LLM responses."""
        data = {
            'type': 'llm_response',
            'model': model,
            'prompt_hash': hashlib.md5(prompt.encode()).hexdigest()
        }
        
        return CacheKeyGenerator._generate_hash(data)
    
    @staticmethod
    def _hash_results(results: List[Dict[str, str]]) -> str:
        """Create a hash of search results."""
        # Sort results and create consistent representation
        sorted_results = sorted(results, key=lambda x: x.get('part_number', ''))
        relevant_fields = []
        
        for result in sorted_results:
            # Only include fields that affect evaluation
            relevant = {
                'title': result.get('title', ''),
                'part_number': result.get('part_number', ''),
                'vendor_part_number': result.get('vendor_part_number', ''),
                'quantity': result.get('quantity', ''),
                'price': result.get('price', '')
            }
            relevant_fields.append(relevant)
        
        return hashlib.md5(json.dumps(relevant_fields, sort_keys=True).encode()).hexdigest()
    
    @staticmethod
    def _generate_hash(data: Dict[str, Any]) -> str:
        """Generate a hash from dictionary data."""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]  # Use first 16 chars


class CacheManager(LoggerMixin):
    """Main cache management system with intelligent caching strategies."""
    
    def __init__(self, store: CacheStore, default_ttl: int = 3600):
        self.store = store
        self.default_ttl = default_ttl
        self.hit_count = 0
        self.miss_count = 0
        self._lock = threading.RLock()
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self._cleanup_thread.start()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        entry = self.store.get(key)
        
        with self._lock:
            if entry is None:
                self.miss_count += 1
                self.logger.debug(f"Cache miss for key: {key}")
                return None
            
            self.hit_count += 1
            self.logger.debug(f"Cache hit for key: {key}")
            return entry.value
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None, 
           tags: Optional[Dict[str, str]] = None) -> None:
        """Store value in cache."""
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None
        
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at,
            tags=tags or {}
        )
        
        self.store.put(entry)
        self.logger.debug(f"Stored value in cache: {key} (TTL: {ttl}s)")
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        return self.store.delete(key)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self.store.clear()
            self.hit_count = 0
            self.miss_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self.hit_count + self.miss_count
            hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
            
            stats = {
                'hit_count': self.hit_count,
                'miss_count': self.miss_count,
                'total_requests': total_requests,
                'hit_rate_percent': hit_rate,
                'entries': self.store.size()
            }
            
            # Add store-specific stats if available
            if hasattr(self.store, 'get_stats'):
                stats.update(self.store.get_stats())
            
            return stats
    
    def _periodic_cleanup(self) -> None:
        """Periodically clean up expired entries."""
        while True:
            try:
                time.sleep(300)  # Clean up every 5 minutes
                self._cleanup_expired()
            except Exception as e:
                self.logger.error(f"Error in cache cleanup: {e}")
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        expired_keys = []
        
        for key in self.store.keys():
            entry = self.store.get(key)
            if entry and entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            self.store.delete(key)
        
        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")


class EvaluationCache(LoggerMixin):
    """Specialized cache for evaluation results."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.evaluation_ttl = 7200  # 2 hours
    
    def get_evaluation(self, query: str, results: List[Dict[str, str]], 
                      search_type: str, model: str) -> Optional[Dict[str, Any]]:
        """Get cached evaluation result."""
        key = CacheKeyGenerator.evaluation_key(query, results, search_type, model)
        
        cached_result = self.cache_manager.get(key)
        if cached_result:
            self.logger.info(f"Using cached evaluation for query: {query}")
            return cached_result
        
        return None
    
    def cache_evaluation(self, query: str, results: List[Dict[str, str]], 
                        search_type: str, model: str, evaluation_result: Dict[str, Any]) -> None:
        """Cache evaluation result."""
        key = CacheKeyGenerator.evaluation_key(query, results, search_type, model)
        
        tags = {
            'type': 'evaluation',
            'search_type': search_type,
            'model': model,
            'query_hash': hashlib.md5(query.encode()).hexdigest()[:8]
        }
        
        self.cache_manager.put(key, evaluation_result, self.evaluation_ttl, tags)
        self.logger.info(f"Cached evaluation result for query: {query}")


class LLMResponseCache(LoggerMixin):
    """Specialized cache for LLM responses."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.response_ttl = 86400  # 24 hours
    
    def get_response(self, model: str, prompt: str) -> Optional[str]:
        """Get cached LLM response."""
        key = CacheKeyGenerator.llm_response_key(model, prompt)
        
        cached_response = self.cache_manager.get(key)
        if cached_response:
            self.logger.info(f"Using cached LLM response for model: {model}")
            return cached_response
        
        return None
    
    def cache_response(self, model: str, prompt: str, response: str) -> None:
        """Cache LLM response."""
        key = CacheKeyGenerator.llm_response_key(model, prompt)
        
        tags = {
            'type': 'llm_response',
            'model': model,
            'prompt_length': str(len(prompt)),
            'response_length': str(len(response))
        }
        
        self.cache_manager.put(key, response, self.response_ttl, tags)
        self.logger.info(f"Cached LLM response for model: {model}")


def create_cache_manager(config: LLMConfig) -> CacheManager:
    """Create cache manager based on configuration."""
    cache_type = os.getenv('CACHE_TYPE', 'memory').lower()
    
    if cache_type == 'file':
        cache_dir = os.getenv('CACHE_DIR', os.path.join(config.debug_dir, 'cache'))
        store = FileCacheStore(cache_dir)
    elif cache_type == 'memory':
        max_size = int(os.getenv('CACHE_MAX_SIZE', '1000'))
        max_memory_mb = int(os.getenv('CACHE_MAX_MEMORY_MB', '100'))
        store = InMemoryCacheStore(max_size, max_memory_mb)
    else:
        # Default to in-memory
        store = InMemoryCacheStore()
    
    default_ttl = int(os.getenv('CACHE_DEFAULT_TTL', '3600'))
    return CacheManager(store, default_ttl)


# Global cache instances
_cache_manager: Optional[CacheManager] = None
_evaluation_cache: Optional[EvaluationCache] = None
_llm_response_cache: Optional[LLMResponseCache] = None
_cache_lock = threading.Lock()


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    
    if _cache_manager is None:
        with _cache_lock:
            if _cache_manager is None:
                from config import LLMConfig
                config = LLMConfig.from_environment()
                _cache_manager = create_cache_manager(config)
    
    return _cache_manager


def get_evaluation_cache() -> EvaluationCache:
    """Get global evaluation cache instance."""
    global _evaluation_cache
    
    if _evaluation_cache is None:
        with _cache_lock:
            if _evaluation_cache is None:
                _evaluation_cache = EvaluationCache(get_cache_manager())
    
    return _evaluation_cache


def get_llm_response_cache() -> LLMResponseCache:
    """Get global LLM response cache instance."""
    global _llm_response_cache
    
    if _llm_response_cache is None:
        with _cache_lock:
            if _llm_response_cache is None:
                _llm_response_cache = LLMResponseCache(get_cache_manager())
    
    return _llm_response_cache


def cache_enabled() -> bool:
    """Check if caching is enabled."""
    return os.getenv('ENABLE_CACHING', 'true').lower() == 'true'


# Decorator for automatic caching
def cached(ttl: Optional[int] = None, cache_type: str = 'general'):
    """Decorator for automatic function result caching."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not cache_enabled():
                return func(*args, **kwargs)
            
            # Generate cache key from function name and arguments
            key_data = {
                'function': f"{func.__module__}.{func.__name__}",
                'args': str(args),
                'kwargs': str(sorted(kwargs.items()))
            }
            cache_key = CacheKeyGenerator._generate_hash(key_data)
            
            # Try to get from cache
            cache_manager = get_cache_manager()
            cached_result = cache_manager.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            
            tags = {
                'type': cache_type,
                'function': func.__name__
            }
            
            cache_manager.put(cache_key, result, ttl, tags)
            return result
        
        return wrapper
    return decorator


# Context manager for cache operations
class CacheContext:
    """Context manager for cache operations with automatic cleanup."""
    
    def __init__(self, cache_manager: CacheManager, tags: Optional[Dict[str, str]] = None):
        self.cache_manager = cache_manager
        self.tags = tags or {}
        self.keys_created = []
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store value and track for cleanup."""
        self.cache_manager.put(key, value, ttl, self.tags)
        self.keys_created.append(key)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return self.cache_manager.get(key)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Optionally clean up created keys on exception
        if exc_type is not None:
            for key in self.keys_created:
                self.cache_manager.delete(key)
