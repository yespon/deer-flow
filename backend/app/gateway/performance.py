"""
Performance optimization utilities for DeerFlow Gateway.

Provides connection pooling, caching layers, and request optimization.
"""

from __future__ import annotations

import functools
import hashlib
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ConnectionPool:
    """HTTP connection pool with retry strategy."""

    _pools: dict[str, requests.Session] = {}

    @classmethod
    def get_session(
        cls,
        name: str,
        pool_connections: int = 10,
        pool_maxsize: int = 10,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> requests.Session:
        """Get or create a connection pool session.

        Args:
            name: Pool identifier
            pool_connections: Number of connection pools to cache
            pool_maxsize: Maximum connections per pool
            max_retries: Maximum retry attempts
            backoff_factor: Backoff factor for retries

        Returns:
            Configured requests Session
        """
        if name not in cls._pools:
            session = requests.Session()

            # Configure retry strategy
            retry_strategy = Retry(
                total=max_retries,
                backoff_factor=backoff_factor,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS"],
            )

            # Configure connection pool
            adapter = HTTPAdapter(
                pool_connections=pool_connections,
                pool_maxsize=pool_maxsize,
                max_retries=retry_strategy,
            )

            session.mount("http://", adapter)
            session.mount("https://", adapter)

            cls._pools[name] = session
            logger.debug(f"Created connection pool: {name}")

        return cls._pools[name]

    @classmethod
    def close_all(cls) -> None:
        """Close all connection pools."""
        for name, session in cls._pools.items():
            session.close()
            logger.debug(f"Closed connection pool: {name}")
        cls._pools.clear()


class SimpleCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, default_ttl: int = 300):
        """Initialize cache.

        Args:
            default_ttl: Default TTL in seconds
        """
        self._cache: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        """Get value from cache if not expired."""
        if key not in self._cache:
            return None

        value, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache with TTL."""
        expiry = time.time() + (ttl or self._default_ttl)
        self._cache[key] = (value, expiry)

    def delete(self, key: str) -> None:
        """Delete key from cache."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count removed."""
        now = time.time()
        expired = [k for k, (_, exp) in self._cache.items() if now > exp]
        for key in expired:
            del self._cache[key]
        return len(expired)


# Global cache instances
_health_cache = SimpleCache(default_ttl=5)  # 5 second TTL for health checks
_model_cache = SimpleCache(default_ttl=60)  # 60 second TTL for model configs


def cached(cache: SimpleCache, ttl: int | None = None):
    """Decorator to cache function results.

    Args:
        cache: Cache instance to use
        ttl: Optional TTL override
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Create cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            key = hashlib.sha256("|".join(key_parts).encode()).hexdigest()

            # Try cache first
            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value

            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result

        return wrapper

    return decorator


class RequestBatcher:
    """Batch multiple requests into single operations."""

    def __init__(self, batch_size: int = 100, flush_interval: float = 0.1):
        """Initialize batcher.

        Args:
            batch_size: Maximum batch size before auto-flush
            flush_interval: Maximum time between flushes (seconds)
        """
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._buffer: list[Any] = []
        self._last_flush = time.time()

    def add(self, item: Any) -> bool:
        """Add item to batch. Returns True if batch was flushed."""
        self._buffer.append(item)

        # Check if we should flush
        should_flush = len(self._buffer) >= self.batch_size or time.time() - self._last_flush >= self.flush_interval

        if should_flush:
            self.flush()
            return True

        return False

    def flush(self) -> list[Any]:
        """Flush current batch and return items."""
        items = self._buffer.copy()
        self._buffer.clear()
        self._last_flush = time.time()
        return items

    def __len__(self) -> int:
        """Return current batch size."""
        return len(self._buffer)


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, burst: int):
        """Initialize rate limiter.

        Args:
            rate: Tokens per second
            burst: Maximum burst size
        """
        self.rate = rate
        self.burst = burst
        self._tokens = burst
        self._last_update = time.time()

    def _update_tokens(self) -> None:
        """Update available tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_update = now

    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens. Returns True if successful."""
        self._update_tokens()

        if self._tokens >= tokens:
            self._tokens -= tokens
            return True

        return False

    def wait_time(self, tokens: int = 1) -> float:
        """Calculate wait time for tokens to be available."""
        self._update_tokens()

        if self._tokens >= tokens:
            return 0.0

        needed = tokens - self._tokens
        return needed / self.rate


def optimize_json_response(data: dict) -> dict:
    """Optimize JSON response by removing None values and empty lists.

    Args:
        data: Original response data

    Returns:
        Optimized response data
    """
    if isinstance(data, dict):
        return {k: optimize_json_response(v) for k, v in data.items() if v is not None and v != [] and v != {}}
    elif isinstance(data, list):
        return [optimize_json_response(item) for item in data]
    return data


# Export cache instances for use in other modules
__all__ = [
    "ConnectionPool",
    "SimpleCache",
    "cached",
    "RequestBatcher",
    "RateLimiter",
    "optimize_json_response",
    "_health_cache",
    "_model_cache",
]
