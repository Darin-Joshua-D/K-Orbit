"""
Query caching system for improved database performance.
Implements intelligent caching with TTL, cache invalidation, and memory management.
"""

import time
import hashlib
import json
from typing import Any, Dict, Optional, List, Set
from dataclasses import dataclass
from enum import Enum
import structlog
import asyncio
from functools import wraps

logger = structlog.get_logger()


class CacheStrategy(Enum):
    """Cache strategy types."""
    WRITE_THROUGH = "write_through"  # Update cache when data changes
    WRITE_BEHIND = "write_behind"    # Async cache updates
    READ_THROUGH = "read_through"    # Load on cache miss
    CACHE_ASIDE = "cache_aside"      # Manual cache management


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    data: Any
    created_at: float
    last_accessed: float
    access_count: int
    ttl: float
    tags: Set[str]


class QueryCache:
    """
    Intelligent query cache with TTL, invalidation, and memory management.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "invalidations": 0
        }
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Background task to clean up expired cache entries."""
        while True:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cache cleanup error", error=str(e))
    
    async def _cleanup_expired(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self._cache.items():
            if current_time - entry.created_at > entry.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
            self._stats["evictions"] += 1
        
        if expired_keys:
            logger.debug("Cleaned up expired cache entries", count=len(expired_keys))
    
    def _evict_lru(self):
        """Evict least recently used entries when cache is full."""
        if len(self._cache) < self._max_size:
            return
        
        # Sort by last accessed time and remove oldest
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        # Remove oldest 10% of entries
        evict_count = max(1, int(self._max_size * 0.1))
        for i in range(evict_count):
            if i < len(sorted_entries):
                key = sorted_entries[i][0]
                del self._cache[key]
                self._stats["evictions"] += 1
    
    def _generate_cache_key(self, query: str, params: tuple = ()) -> str:
        """Generate a unique cache key for a query."""
        key_data = f"{query}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, query: str, params: tuple = ()) -> Optional[Any]:
        """
        Get cached query result.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Cached data or None if not found
        """
        cache_key = self._generate_cache_key(query, params)
        current_time = time.time()
        
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            
            # Check if entry is expired
            if current_time - entry.created_at > entry.ttl:
                del self._cache[cache_key]
                self._stats["evictions"] += 1
                self._stats["misses"] += 1
                return None
            
            # Update access metadata
            entry.last_accessed = current_time
            entry.access_count += 1
            
            self._stats["hits"] += 1
            logger.debug("Cache hit", key=cache_key[:8])
            return entry.data
        
        self._stats["misses"] += 1
        return None
    
    async def set(self, query: str, data: Any, params: tuple = (), 
                  ttl: Optional[int] = None, tags: Optional[Set[str]] = None):
        """
        Store query result in cache.
        
        Args:
            query: SQL query
            data: Query result to cache
            params: Query parameters
            ttl: Time to live in seconds
            tags: Cache tags for invalidation
        """
        cache_key = self._generate_cache_key(query, params)
        current_time = time.time()
        
        # Evict old entries if cache is full
        self._evict_lru()
        
        entry = CacheEntry(
            data=data,
            created_at=current_time,
            last_accessed=current_time,
            access_count=1,
            ttl=ttl or self._default_ttl,
            tags=tags or set()
        )
        
        self._cache[cache_key] = entry
        logger.debug("Cache set", key=cache_key[:8], size=len(self._cache))
    
    async def invalidate_by_tags(self, tags: Set[str]):
        """
        Invalidate cache entries by tags.
        
        Args:
            tags: Tags to invalidate
        """
        invalidated_keys = []
        
        for key, entry in list(self._cache.items()):
            if entry.tags & tags:  # If any tag matches
                del self._cache[key]
                invalidated_keys.append(key)
        
        self._stats["invalidations"] += len(invalidated_keys)
        
        if invalidated_keys:
            logger.info("Cache invalidated by tags", 
                       tags=list(tags), 
                       count=len(invalidated_keys))
    
    async def invalidate_by_pattern(self, pattern: str):
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: SQL pattern to match against cached queries
        """
        invalidated_keys = []
        
        for key in list(self._cache.keys()):
            # This is a simplified pattern matching
            # In production, you might want more sophisticated matching
            if pattern.lower() in key.lower():
                del self._cache[key]
                invalidated_keys.append(key)
        
        self._stats["invalidations"] += len(invalidated_keys)
        
        if invalidated_keys:
            logger.info("Cache invalidated by pattern",
                       pattern=pattern,
                       count=len(invalidated_keys))
    
    async def clear(self):
        """Clear all cache entries."""
        cleared_count = len(self._cache)
        self._cache.clear()
        self._stats["evictions"] += cleared_count
        logger.info("Cache cleared", count=cleared_count)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hit_rate": hit_rate,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "evictions": self._stats["evictions"],
            "invalidations": self._stats["invalidations"],
            "memory_usage": self._estimate_memory_usage()
        }
    
    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage of cache in bytes."""
        # Rough estimation - in production you might want more accurate measurement
        total_size = 0
        for entry in self._cache.values():
            total_size += len(str(entry.data).encode('utf-8'))
        return total_size
    
    async def shutdown(self):
        """Shutdown cache and cleanup tasks."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        await self.clear()
        logger.info("Query cache shutdown complete")


def cache_query(ttl: int = 300, tags: Optional[Set[str]] = None):
    """
    Decorator for caching query results.
    
    Args:
        ttl: Time to live in seconds
        tags: Cache tags for invalidation
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = await get_query_cache()
            
            # Generate cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl=ttl, tags=tags)
            
            return result
        return wrapper
    return decorator


# Global cache instance
_query_cache: Optional[QueryCache] = None


async def get_query_cache() -> QueryCache:
    """Get the global query cache instance."""
    global _query_cache
    
    if _query_cache is None:
        _query_cache = QueryCache()
    
    return _query_cache


async def init_cache():
    """Initialize the global cache."""
    await get_query_cache()


async def cleanup_cache():
    """Cleanup cache resources."""
    global _query_cache
    if _query_cache:
        await _query_cache.shutdown()
        _query_cache = None 