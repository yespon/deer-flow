"""Performance optimizations for DeerFlow Enterprise.

Includes:
- Quota cache with TTL for reduced Redis calls
- Audit log batching for improved throughput
- Knowledge base query caching
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class CachedValue(Generic[T]):
    """Cached value with timestamp."""

    value: T
    timestamp: float


class TTLCache:
    """Simple TTL cache for quota and other frequently accessed data.

    Example:
        ```python
        cache = TTLCache(ttl_seconds=60)
        cache.set("tenant_abc:concurrent", 5)
        value = cache.get("tenant_abc:concurrent")  # Returns 5 if within TTL
        ```
    """

    def __init__(self, ttl_seconds: float = 60.0) -> None:
        self.ttl = ttl_seconds
        self._cache: dict[str, CachedValue[Any]] = {}

    def get(self, key: str) -> Any | None:
        """Get value if within TTL."""
        cached = self._cache.get(key)
        if cached is None:
            return None

        if time.time() - cached.timestamp > self.ttl:
            del self._cache[key]
            return None

        return cached.value

    def set(self, key: str, value: Any) -> None:
        """Set value with current timestamp."""
        self._cache[key] = CachedValue(value=value, timestamp=time.time())

    def delete(self, key: str) -> None:
        """Delete key from cache."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed."""
        now = time.time()
        expired = [
            k for k, v in self._cache.items()
            if now - v.timestamp > self.ttl
        ]
        for k in expired:
            del self._cache[k]
        return len(expired)


@dataclass
class AuditBatchConfig:
    """Configuration for audit log batching."""

    max_batch_size: int = 100
    max_wait_seconds: float = 5.0
    max_queue_size: int = 10000


class BatchedAuditLog:
    """Batched audit log for improved throughput.

    Buffers audit events and flushes them in batches to reduce
    storage overhead and improve performance.

    Example:
        ```python
        audit = BatchedAuditLog(
            storage=ImmutableAuditLog(),
            config=AuditBatchConfig(max_batch_size=50),
        )

        await audit.log(event_type, details)  # Buffered
        await audit.flush()  # Flush to storage
        ```
    """

    def __init__(
        self,
        storage: Any,
        config: AuditBatchConfig | None = None,
    ) -> None:
        self.storage = storage
        self.config = config or AuditBatchConfig()
        self._queue: deque = deque()
        self._last_flush = time.time()
        self._total_buffered = 0

    async def log(
        self,
        event_type: Any,
        details: dict[str, Any],
    ) -> None:
        """Buffer event for batch logging."""
        event = {
            "event_type": event_type,
            "details": details,
            "timestamp": time.time(),
        }

        # Add to queue
        self._queue.append(event)
        self._total_buffered += 1

        # Check if flush needed
        await self._maybe_flush()

    async def _maybe_flush(self) -> None:
        """Flush if batch size or time threshold reached."""
        should_flush = (
            len(self._queue) >= self.config.max_batch_size
            or time.time() - self._last_flush >= self.config.max_wait_seconds
        )

        if should_flush and self._queue:
            await self.flush()

    async def flush(self) -> int:
        """Flush all buffered events to storage.

        Returns:
            Number of events flushed
        """
        if not self._queue:
            return 0

        events = list(self._queue)
        self._queue.clear()

        # Write batch to storage
        for event in events:
            await self.storage.log(
                event["event_type"],
                event["details"],
            )

        self._last_flush = time.time()
        return len(events)

    @property
    def pending_count(self) -> int:
        """Number of events pending flush."""
        return len(self._queue)


class QuotaCacheManager:
    """Cached quota manager to reduce Redis calls.

    Caches quota values with short TTL to reduce load on
    Redis while maintaining accuracy.

    Example:
        ```python
        manager = QuotaCacheManager(
            quota_manager=QuotaManager(),
            ttl_seconds=30,
        )

        # First call hits Redis
        usage = await manager.get_usage("tenant_abc")

        # Second call uses cache
        usage = await manager.get_usage("tenant_abc")
        ```
    """

    def __init__(
        self,
        quota_manager: Any,
        ttl_seconds: float = 30.0,
    ) -> None:
        self.quota = quota_manager
        self.cache = TTLCache(ttl_seconds=ttl_seconds)

    async def get_quota(self, tenant_id: str) -> Any:
        """Get tenant quota (cached)."""
        cache_key = f"quota:{tenant_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        quota = await self.quota.get_quota(tenant_id)
        self.cache.set(cache_key, quota)
        return quota

    async def get_usage(self, tenant_id: str) -> Any:
        """Get current usage (not cached, always fresh)."""
        return await self.quota.get_usage(tenant_id)

    async def check_before_acquire(self, tenant_id: str) -> None:
        """Check quota before acquiring resource."""
        # Get fresh usage for accuracy
        await self.quota.check_before_acquire(tenant_id)

    def invalidate(self, tenant_id: str) -> None:
        """Invalidate cached quota for tenant."""
        self.cache.delete(f"quota:{tenant_id}")


class KBQueryCache:
    """Cache for knowledge base queries.

    Caches query results to reduce vector store calls for
    frequently asked questions.

    Example:
        ```python
        cache = KBQueryCache(ttl_seconds=300)

        # First query hits vector store
        results = await cache.get_or_query(
            kb=knowledge_base,
            query="refund policy",
            tenant_id="tenant_abc",
        )

        # Second query uses cache
        results = await cache.get_or_query(...)
        ```
    """

    def __init__(self, ttl_seconds: float = 300.0) -> None:
        self.cache = TTLCache(ttl_seconds=ttl_seconds)

    def _make_key(
        self,
        query: str,
        tenant_id: str,
        top_k: int,
    ) -> str:
        """Create cache key from query parameters."""
        # Normalize query for consistent caching
        normalized = query.lower().strip()
        return f"kb:{tenant_id}:{normalized}:{top_k}"

    async def get_or_query(
        self,
        kb: Any,
        query: str,
        tenant_id: str,
        top_k: int = 5,
    ) -> list[Any]:
        """Get from cache or query knowledge base."""
        cache_key = self._make_key(query, tenant_id, top_k)

        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # Query knowledge base
        results = await kb.search(
            query=query,
            tenant_id=tenant_id,
            top_k=top_k,
        )

        # Cache results
        self.cache.set(cache_key, results)
        return results

    def invalidate_tenant(self, tenant_id: str) -> None:
        """Invalidate all cached queries for tenant."""
        prefix = f"kb:{tenant_id}:"
        keys_to_delete = [
            k for k in self.cache._cache.keys()
            if k.startswith(prefix)
        ]
        for k in keys_to_delete:
            self.cache.delete(k)


# Performance monitoring metrics
@dataclass
class PerformanceMetrics:
    """Performance metrics collector."""

    quota_cache_hits: int = 0
    quota_cache_misses: int = 0
    kb_cache_hits: int = 0
    kb_cache_misses: int = 0
    audit_batch_size: int = 0

    def record_quota_cache_hit(self) -> None:
        self.quota_cache_hits += 1

    def record_quota_cache_miss(self) -> None:
        self.quota_cache_misses += 1

    def record_kb_cache_hit(self) -> None:
        self.kb_cache_hits += 1

    def record_kb_cache_miss(self) -> None:
        self.kb_cache_misses += 1

    @property
    def quota_cache_hit_rate(self) -> float:
        total = self.quota_cache_hits + self.quota_cache_misses
        if total == 0:
            return 0.0
        return self.quota_cache_hits / total

    @property
    def kb_cache_hit_rate(self) -> float:
        total = self.kb_cache_hits + self.kb_cache_misses
        if total == 0:
            return 0.0
        return self.kb_cache_hits / total
