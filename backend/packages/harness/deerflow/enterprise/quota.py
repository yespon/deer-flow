"""Quota management with Redis-backed distributed counters."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis import Redis


logger = logging.getLogger(__name__)


class QuotaExceededError(Exception):
    """Raised when a tenant exceeds their resource quota."""

    def __init__(
        self,
        tenant_id: str,
        resource: str,
        limit: int,
        current: int,
    ) -> None:
        self.tenant_id = tenant_id
        self.resource = resource
        self.limit = limit
        self.current = current
        super().__init__(f"Quota exceeded for tenant '{tenant_id}': {resource} ({current}/{limit})")


class QuotaManager:
    """Manages per-tenant resource quotas using Redis counters.

    This class provides atomic operations for tracking resource usage
    across distributed instances.

    Redis Key Schema:
        quota:{tenant_id}:{resource}  # Counter value

    Example:
        >>> manager = QuotaManager(redis_client)
        >>> if manager.acquire("tenant_123", "concurrent_sandboxes", limit=5):
        ...     try:
        ...         # Use resource
        ...     finally:
        ...         manager.release("tenant_123", "concurrent_sandboxes")
    """

    def __init__(self, redis_client: Redis | None = None) -> None:
        """Initialize QuotaManager.

        Args:
            redis_client: Redis client for counters. If None, operations
                will fail gracefully (no quota enforcement).
        """
        self._redis = redis_client

    def _key(self, tenant_id: str, resource: str) -> str:
        """Generate Redis key for tenant resource."""
        return f"quota:{tenant_id}:{resource}"

    def acquire(
        self,
        tenant_id: str,
        resource: str,
        limit: int,
        ttl_seconds: int | None = None,
    ) -> bool:
        """Attempt to acquire quota for a resource.

        Args:
            tenant_id: The tenant identifier
            resource: Resource type (e.g., "concurrent_sandboxes")
            limit: Maximum allowed for this resource
            ttl_seconds: Optional TTL for the counter key

        Returns:
            True if quota acquired, False if limit would be exceeded
        """
        if self._redis is None:
            return True

        key = self._key(tenant_id, resource)

        # Atomically increment and check
        current = self._redis.incr(key)

        if ttl_seconds and current == 1:
            # Set expiration on first acquisition
            self._redis.expire(key, ttl_seconds)

        if current > limit:
            # Over limit, decrement and reject
            self._redis.decr(key)
            logger.warning("Quota exceeded: tenant=%s resource=%s limit=%d", tenant_id, resource, limit)
            return False

        logger.debug("Quota acquired: tenant=%s resource=%s current=%d/%d", tenant_id, resource, current, limit)
        return True

    def release(
        self,
        tenant_id: str,
        resource: str,
    ) -> None:
        """Release quota for a resource.

        Args:
            tenant_id: The tenant identifier
            resource: Resource type
        """
        if self._redis is None:
            return

        key = self._key(tenant_id, resource)
        new_value = self._redis.decr(key)

        if new_value < 0:
            # Prevent negative counters
            logger.warning("Quota counter went negative: tenant=%s resource=%s", tenant_id, resource)
            self._redis.set(key, 0)

    def get_usage(self, tenant_id: str, resource: str) -> int:
        """Get current usage for a tenant resource.

        Args:
            tenant_id: The tenant identifier
            resource: Resource type

        Returns:
            Current usage count (0 if not tracked)
        """
        if self._redis is None:
            return 0

        key = self._key(tenant_id, resource)
        value = self._redis.get(key)

        if value is None:
            return 0

        try:
            return int(value)
        except (ValueError, TypeError):
            logger.error("Invalid quota counter value: %s", value)
            return 0

    def check_quota(
        self,
        tenant_id: str,
        resource: str,
        limit: int,
    ) -> None:
        """Check if quota is exceeded without acquiring.

        Args:
            tenant_id: The tenant identifier
            resource: Resource type
            limit: Maximum allowed

        Raises:
            QuotaExceededError: If quota is exceeded
        """
        current = self.get_usage(tenant_id, resource)

        if current >= limit:
            raise QuotaExceededError(
                tenant_id=tenant_id,
                resource=resource,
                limit=limit,
                current=current,
            )

    def reset(self, tenant_id: str, resource: str) -> None:
        """Reset counter for a tenant resource (admin use).

        Args:
            tenant_id: The tenant identifier
            resource: Resource type
        """
        if self._redis is None:
            return

        key = self._key(tenant_id, resource)
        self._redis.delete(key)
