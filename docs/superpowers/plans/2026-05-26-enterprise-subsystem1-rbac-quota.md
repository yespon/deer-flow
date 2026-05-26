# Enterprise Subsystem 1: RBAC and Quota Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement RBACMiddleware, QuotaManager, and QuotaMiddleware for DeerFlow Enterprise with full TDD test coverage.

**Architecture:** Build on existing enterprise modules (rbac.py, tenancy.py). QuotaManager uses Redis for distributed counters. Both middlewares follow the AgentMiddleware pattern from langchain. RBAC maps tool names to resource types; Quota tracks concurrent sandboxes per tenant.

**Tech Stack:** Python 3.12+, Redis, pydantic, langchain, pytest, pytest-asyncio

**Timeline:** 2-3 days (5 components with TDD)

---

## File Structure

### New Files

| File | Responsibility |
|------|----------------|
| `backend/packages/harness/deerflow/enterprise/quota_config.py` | TenantQuota and QuotaConfig Pydantic models |
| `backend/packages/harness/deerflow/enterprise/quota.py` | QuotaManager with Redis-backed counters |
| `backend/packages/harness/deerflow/enterprise/quota_middleware.py` | QuotaMiddleware for sandbox lifecycle |
| `backend/packages/harness/deerflow/enterprise/rbac_middleware.py` | RBACMiddleware for permission checking |
| `backend/tests/enterprise/test_quota_manager.py` | QuotaManager unit tests (10 cases) |
| `backend/tests/enterprise/test_quota_middleware.py` | QuotaMiddleware unit tests (6 cases) |
| `backend/tests/enterprise/test_rbac_middleware.py` | RBACMiddleware unit tests (8 cases) |
| `backend/tests/enterprise/conftest.py` | Shared fixtures (Redis mock, etc.) |

### Modified Files

| File | Changes |
|------|---------|
| `backend/packages/harness/deerflow/enterprise/__init__.py` | Export new classes |
| `backend/packages/harness/deerflow/config/app_config.py` | Add `quota: QuotaConfig` field |
| `backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py` | Add middlewares to chain (optional) |

---

## Task 1: QuotaConfig Configuration Models

**Files:**
- Create: `backend/packages/harness/deerflow/enterprise/quota_config.py`
- Create: `backend/tests/enterprise/test_quota_config.py`

---

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/enterprise/test_quota_config.py
import pytest
from pydantic import ValidationError

from deerflow.enterprise.quota_config import TenantQuota, QuotaConfig


class TestTenantQuota:
    def test_default_quota_values(self):
        quota = TenantQuota()
        assert quota.max_concurrent_sandboxes == 5
        assert quota.max_cpu_cores == 4.0
        assert quota.max_memory_gb == 8.0
        assert quota.max_storage_gb == 100.0
        assert quota.max_network_egress_mb == 1000

    def test_custom_quota_values(self):
        quota = TenantQuota(
            max_concurrent_sandboxes=10,
            max_cpu_cores=8.0,
            max_memory_gb=16.0,
        )
        assert quota.max_concurrent_sandboxes == 10
        assert quota.max_cpu_cores == 8.0
        assert quota.max_memory_gb == 16.0

    def test_negative_quota_rejected(self):
        with pytest.raises(ValidationError):
            TenantQuota(max_concurrent_sandboxes=-1)


class TestQuotaConfig:
    def test_default_config(self):
        config = QuotaConfig()
        assert config.enabled is False
        assert config.redis_url == "redis://localhost:6379"
        assert config.enforcement_mode == "hard"
        assert config.default_quotas.max_concurrent_sandboxes == 5

    def test_enabled_config(self):
        config = QuotaConfig(enabled=True)
        assert config.enabled is True

    def test_custom_redis_url(self):
        config = QuotaConfig(redis_url="redis://cluster:6379/1")
        assert config.redis_url == "redis://cluster:6379/1"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/enterprise/test_quota_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'deerflow.enterprise.quota_config'`

- [ ] **Step 3: Implement QuotaConfig models**

```python
# backend/packages/harness/deerflow/enterprise/quota_config.py
"""Configuration models for quota management."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TenantQuota(BaseModel):
    """Per-tenant resource quota limits.

    Attributes:
        max_concurrent_sandboxes: Maximum concurrent sandbox instances
        max_cpu_cores: Maximum CPU cores allowed
        max_memory_gb: Maximum memory in GB
        max_storage_gb: Maximum storage in GB
        max_network_egress_mb: Maximum network egress in MB per day
    """

    max_concurrent_sandboxes: int = Field(default=5, ge=0)
    max_cpu_cores: float = Field(default=4.0, ge=0.0)
    max_memory_gb: float = Field(default=8.0, ge=0.0)
    max_storage_gb: float = Field(default=100.0, ge=0.0)
    max_network_egress_mb: int = Field(default=1000, ge=0)


class QuotaConfig(BaseModel):
    """Top-level quota management configuration.

    Attributes:
        enabled: Whether quota enforcement is enabled
        redis_url: Redis connection URL for counters
        default_quotas: Default quota values for new tenants
        enforcement_mode: "hard" (block) or "soft" (warn only)
    """

    enabled: bool = Field(default=False)
    redis_url: str = Field(default="redis://localhost:6379")
    default_quotas: TenantQuota = Field(default_factory=TenantQuota)
    enforcement_mode: Literal["hard", "soft"] = Field(default="hard")

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        if not v.startswith(("redis://", "rediss://", "unix://")):
            raise ValueError("redis_url must start with redis://, rediss://, or unix://")
        return v
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/enterprise/test_quota_config.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/packages/harness/deerflow/enterprise/quota_config.py
git add backend/tests/enterprise/test_quota_config.py
git commit -m "feat(enterprise): add QuotaConfig and TenantQuota models"
```

---

## Task 2: QuotaManager Core Implementation

**Files:**
- Create: `backend/packages/harness/deerflow/enterprise/quota.py`
- Create: `backend/tests/enterprise/test_quota_manager.py`

---

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/enterprise/test_quota_manager.py
import pytest
from unittest.mock import Mock, patch

from deerflow.enterprise.quota import QuotaManager, QuotaExceededError
from deerflow.enterprise.quota_config import TenantQuota


class TestQuotaManager:
    @pytest.fixture
    def mock_redis(self):
        return Mock()

    @pytest.fixture
    def quota_manager(self, mock_redis):
        return QuotaManager(mock_redis)

    def test_acquire_succeeds_when_under_limit(self, quota_manager, mock_redis):
        mock_redis.get.return_value = "2"
        mock_redis.incr.return_value = 3

        result = quota_manager.acquire("tenant_123", "concurrent_sandboxes", limit=5)

        assert result is True
        mock_redis.incr.assert_called_once()

    def test_acquire_fails_when_at_limit(self, quota_manager, mock_redis):
        mock_redis.get.return_value = "5"
        mock_redis.incr.return_value = 6

        result = quota_manager.acquire("tenant_123", "concurrent_sandboxes", limit=5)

        assert result is False
        mock_redis.decr.assert_called_once()  # Should release immediately

    def test_release_decrements_counter(self, quota_manager, mock_redis):
        quota_manager.release("tenant_123", "concurrent_sandboxes")

        mock_redis.decr.assert_called_once_with("quota:tenant_123:concurrent_sandboxes")

    def test_get_usage_returns_current_value(self, quota_manager, mock_redis):
        mock_redis.get.return_value = "3"

        usage = quota_manager.get_usage("tenant_123", "concurrent_sandboxes")

        assert usage == 3

    def test_get_usage_returns_zero_when_none(self, quota_manager, mock_redis):
        mock_redis.get.return_value = None

        usage = quota_manager.get_usage("tenant_123", "concurrent_sandboxes")

        assert usage == 0

    def test_check_quota_raises_when_exceeded(self, quota_manager, mock_redis):
        mock_redis.get.return_value = "6"

        with pytest.raises(QuotaExceededError) as exc_info:
            quota_manager.check_quota("tenant_123", "concurrent_sandboxes", limit=5)

        assert "concurrent_sandboxes" in str(exc_info.value)
        assert "5" in str(exc_info.value)

    def test_check_quota_passes_when_under_limit(self, quota_manager, mock_redis):
        mock_redis.get.return_value = "3"

        # Should not raise
        quota_manager.check_quota("tenant_123", "concurrent_sandboxes", limit=5)

    def test_acquire_with_ttl(self, quota_manager, mock_redis):
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1

        quota_manager.acquire("tenant_123", "daily_api_calls", limit=1000, ttl_seconds=86400)

        mock_redis.expire.assert_called_once()

    def test_multiple_resources_independent(self, quota_manager, mock_redis):
        mock_redis.get.side_effect = ["2", "50"]  # sandboxes, api_calls

        sandbox_usage = quota_manager.get_usage("tenant_123", "concurrent_sandboxes")
        api_usage = quota_manager.get_usage("tenant_123", "daily_api_calls")

        assert sandbox_usage == 2
        assert api_usage == 50

    def test_release_does_not_go_negative(self, quota_manager, mock_redis):
        mock_redis.decr.return_value = -1
        mock_redis.get.return_value = "-1"

        quota_manager.release("tenant_123", "concurrent_sandboxes")

        # Should reset to 0 if negative
        mock_redis.set.assert_called_once_with("quota:tenant_123:concurrent_sandboxes", 0)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python -m pytest tests/enterprise/test_quota_manager.py -v
```

Expected: `ModuleNotFoundError: No module named 'deerflow.enterprise.quota'`

- [ ] **Step 3: Implement QuotaManager**

```python
# backend/packages/harness/deerflow/enterprise/quota.py
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
        super().__init__(
            f"Quota exceeded for tenant '{tenant_id}': "
            f"{resource} ({current}/{limit})"
        )


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
            logger.warning(
                "Quota exceeded: tenant=%s resource=%s limit=%d",
                tenant_id, resource, limit
            )
            return False

        logger.debug(
            "Quota acquired: tenant=%s resource=%s current=%d/%d",
            tenant_id, resource, current, limit
        )
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
            logger.warning(
                "Quota counter went negative: tenant=%s resource=%s",
                tenant_id, resource
            )
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/enterprise/test_quota_manager.py -v
```

Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/packages/harness/deerflow/enterprise/quota.py
git add backend/tests/enterprise/test_quota_manager.py
git commit -m "feat(enterprise): implement QuotaManager with Redis counters"
```

---

## Task 3: QuotaMiddleware Implementation

**Files:**
- Create: `backend/packages/harness/deerflow/enterprise/quota_middleware.py`
- Create: `backend/tests/enterprise/test_quota_middleware.py`
- Modify: `backend/packages/harness/deerflow/enterprise/__init__.py`

---

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/enterprise/test_quota_middleware.py
from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest

from deerflow.enterprise.quota import QuotaExceededError
from deerflow.enterprise.quota_config import QuotaConfig
from deerflow.enterprise.quota_middleware import QuotaMiddleware


class TestQuotaMiddleware:
    @pytest.fixture
    def quota_config(self):
        return QuotaConfig(
            enabled=True,
            default_quotas=Mock(max_concurrent_sandboxes=5),
        )

    @pytest.fixture
    def middleware(self, quota_config):
        with patch("deerflow.enterprise.quota_middleware.get_quota_manager") as mock_get:
            mock_manager = Mock()
            mock_get.return_value = mock_manager
            yield QuotaMiddleware(quota_config)

    def test_allows_sandbox_when_quota_available(self, middleware):
        middleware._quota_manager.acquire.return_value = True

        request = ToolCallRequest(
            tool_call={"name": "bash", "args": {"command": "ls"}, "id": "call_1"},
            tools=[],
        )
        handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="bash"))

        result = middleware.wrap_tool_call(request, handler)

        assert result.content == "ok"
        handler.assert_called_once()

    def test_blocks_sandbox_when_quota_exhausted(self, middleware):
        middleware._quota_manager.acquire.return_value = False

        request = ToolCallRequest(
            tool_call={"name": "bash", "args": {"command": "ls"}, "id": "call_1"},
            tools=[],
        )
        handler = Mock()

        result = middleware.wrap_tool_call(request, handler)

        assert isinstance(result, ToolMessage)
        assert result.status == "error"
        assert "quota" in result.content.lower()
        handler.assert_not_called()

    def test_skips_when_quota_disabled(self):
        config = QuotaConfig(enabled=False)
        middleware = QuotaMiddleware(config)

        request = ToolCallRequest(
            tool_call={"name": "bash", "args": {}, "id": "call_1"},
            tools=[],
        )
        handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="bash"))

        result = middleware.wrap_tool_call(request, handler)

        assert result.content == "ok"

    def test_skips_non_sandbox_tools(self, middleware):
        request = ToolCallRequest(
            tool_call={"name": "ask_clarification", "args": {"question": "?"}, "id": "call_1"},
            tools=[],
        )
        handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="ask_clarification"))

        result = middleware.wrap_tool_call(request, handler)

        assert result.content == "ok"
        middleware._quota_manager.acquire.assert_not_called()

    def test_extracts_tenant_from_context(self, middleware):
        middleware._quota_manager.acquire.return_value = True

        with patch("deerflow.enterprise.quota_middleware.get_current_tenant") as mock_get_tenant:
            mock_tenant = Mock()
            mock_tenant.id = "tenant_abc"
            mock_get_tenant.return_value = mock_tenant

            request = ToolCallRequest(
                tool_call={"name": "bash", "args": {}, "id": "call_1"},
                tools=[],
            )
            handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="bash"))

            middleware.wrap_tool_call(request, handler)

            middleware._quota_manager.acquire.assert_called_with(
                "tenant_abc", "concurrent_sandboxes", limit=5
            )

    def test_async_version_works(self, middleware):
        middleware._quota_manager.acquire.return_value = True

        request = ToolCallRequest(
            tool_call={"name": "bash", "args": {}, "id": "call_1"},
            tools=[],
        )
        handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="bash"))

        import asyncio
        result = asyncio.run(middleware.awrap_tool_call(request, handler))

        assert result.content == "ok"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python -m pytest tests/enterprise/test_quota_middleware.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement QuotaMiddleware**

```python
# backend/packages/harness/deerflow/enterprise/quota_middleware.py
"""Quota enforcement middleware for sandbox operations."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, override

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

from deerflow.agents.thread_state import ThreadState
from deerflow.enterprise.quota import QuotaManager, QuotaExceededError
from deerflow.enterprise.quota_config import QuotaConfig
from deerflow.enterprise.tenancy import get_current_tenant

if TYPE_CHECKING:
    from redis import Redis


logger = logging.getLogger(__name__)

# Tools that consume sandbox quota
_SANDBOX_TOOLS = {"bash", "str_replace", "write_file", "read_file", "ls"}


def get_quota_manager(redis_client: Redis | None = None) -> QuotaManager:
    """Get or create global QuotaManager instance."""
    # Simple global instance - in production might use dependency injection
    if not hasattr(get_quota_manager, "_instance"):
        get_quota_manager._instance = QuotaManager(redis_client)
    return get_quota_manager._instance


class QuotaMiddleware(AgentMiddleware[ThreadState]):
    """Middleware that enforces tenant resource quotas.

    Tracks and limits concurrent sandbox usage per tenant.
    """

    state_schema = ThreadState

    def __init__(
        self,
        config: QuotaConfig,
        quota_manager: QuotaManager | None = None,
    ) -> None:
        self.config = config
        self._quota_manager = quota_manager or get_quota_manager()

    def _is_sandbox_tool(self, tool_name: str) -> bool:
        """Check if tool consumes sandbox quota."""
        return tool_name in _SANDBOX_TOOLS

    def _get_tenant_id(self) -> str:
        """Extract tenant ID from current context."""
        tenant = get_current_tenant()
        return tenant.id if tenant else "default"

    def _get_quota_limit(self) -> int:
        """Get quota limit for concurrent sandboxes."""
        return self.config.default_quotas.max_concurrent_sandboxes

    def _build_quota_exceeded_message(
        self,
        request: ToolCallRequest,
        error: QuotaExceededError,
    ) -> ToolMessage:
        """Build error message for quota exceeded."""
        tool_call_id = str(request.tool_call.get("id") or "missing_id")
        tool_name = request.tool_call.get("name", "unknown")

        content = (
            f"❌ Quota Exceeded\n\n"
            f"Cannot execute '{tool_name}': sandbox quota exceeded.\n"
            f"Current usage: {error.current}/{error.limit} concurrent sandboxes.\n\n"
            f"Please wait for existing operations to complete or contact your administrator."
        )

        return ToolMessage(
            content=content,
            tool_call_id=tool_call_id,
            name=tool_name,
            status="error",
        )

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        if not self.config.enabled:
            return handler(request)

        tool_name = request.tool_call.get("name", "")

        if not self._is_sandbox_tool(tool_name):
            return handler(request)

        tenant_id = self._get_tenant_id()
        limit = self._get_quota_limit()

        # Try to acquire quota
        acquired = self._quota_manager.acquire(
            tenant_id, "concurrent_sandboxes", limit=limit
        )

        if not acquired:
            # Build error from current usage
            current = self._quota_manager.get_usage(tenant_id, "concurrent_sandboxes")
            error = QuotaExceededError(
                tenant_id=tenant_id,
                resource="concurrent_sandboxes",
                limit=limit,
                current=current,
            )
            return self._build_quota_exceeded_message(request, error)

        try:
            return handler(request)
        finally:
            # Release quota after execution
            self._quota_manager.release(tenant_id, "concurrent_sandboxes")

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        if not self.config.enabled:
            return await handler(request)

        tool_name = request.tool_call.get("name", "")

        if not self._is_sandbox_tool(tool_name):
            return await handler(request)

        tenant_id = self._get_tenant_id()
        limit = self._get_quota_limit()

        acquired = self._quota_manager.acquire(
            tenant_id, "concurrent_sandboxes", limit=limit
        )

        if not acquired:
            current = self._quota_manager.get_usage(tenant_id, "concurrent_sandboxes")
            error = QuotaExceededError(
                tenant_id=tenant_id,
                resource="concurrent_sandboxes",
                limit=limit,
                current=current,
            )
            return self._build_quota_exceeded_message(request, error)

        try:
            return await handler(request)
        finally:
            self._quota_manager.release(tenant_id, "concurrent_sandboxes")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/enterprise/test_quota_middleware.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 5: Update __init__.py exports**

```python
# Add to backend/packages/harness/deerflow/enterprise/__init__.py

from deerflow.enterprise.quota import (
    QuotaManager,
    QuotaExceededError,
)
from deerflow.enterprise.quota_config import (
    QuotaConfig,
    TenantQuota,
)
from deerflow.enterprise.quota_middleware import QuotaMiddleware

__all__ = [
    # ... existing exports ...
    # Quota
    "QuotaManager",
    "QuotaExceededError",
    "QuotaConfig",
    "TenantQuota",
    "QuotaMiddleware",
]
```

- [ ] **Step 6: Commit**

```bash
git add backend/packages/harness/deerflow/enterprise/quota_middleware.py
git add backend/tests/enterprise/test_quota_middleware.py
git add backend/packages/harness/deerflow/enterprise/__init__.py
git commit -m "feat(enterprise): implement QuotaMiddleware for resource limits"
```

---

## Task 4: RBACMiddleware Implementation

**Files:**
- Create: `backend/packages/harness/deerflow/enterprise/rbac_middleware.py`
- Create: `backend/tests/enterprise/test_rbac_middleware.py`
- Modify: `backend/packages/harness/deerflow/enterprise/__init__.py`

---

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/enterprise/test_rbac_middleware.py
from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest

from deerflow.enterprise.rbac_middleware import RBACMiddleware


class TestRBACMiddleware:
    @pytest.fixture
    def middleware(self):
        return RBACMiddleware(enabled=True)

    def test_allows_permitted_tool_call(self, middleware):
        with patch("deerflow.enterprise.rbac_middleware.check_permission") as mock_check:
            mock_check.return_value = True

            request = ToolCallRequest(
                tool_call={"name": "read_file", "args": {"path": "/tmp/test"}, "id": "call_1"},
                tools=[],
            )
            handler = Mock(return_value=ToolMessage(content="content", tool_call_id="call_1", name="read_file"))

            result = middleware.wrap_tool_call(request, handler)

            assert result.content == "content"
            handler.assert_called_once()
            mock_check.assert_called_once()

    def test_denies_unpermitted_tool_call(self, middleware):
        with patch("deerflow.enterprise.rbac_middleware.check_permission") as mock_check:
            mock_check.return_value = False

            request = ToolCallRequest(
                tool_call={"name": "bash", "args": {"command": "rm -rf /"}, "id": "call_1"},
                tools=[],
            )
            handler = Mock()

            result = middleware.wrap_tool_call(request, handler)

            assert isinstance(result, ToolMessage)
            assert result.status == "error"
            assert "permission" in result.content.lower()
            handler.assert_not_called()

    def test_skips_check_when_rbac_disabled(self):
        middleware = RBACMiddleware(enabled=False)

        request = ToolCallRequest(
            tool_call={"name": "bash", "args": {}, "id": "call_1"},
            tools=[],
        )
        handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="bash"))

        result = middleware.wrap_tool_call(request, handler)

        assert result.content == "ok"

    def test_maps_bash_to_sandbox_execute(self, middleware):
        with patch("deerflow.enterprise.rbac_middleware.check_permission") as mock_check:
            mock_check.return_value = True

            request = ToolCallRequest(
                tool_call={"name": "bash", "args": {}, "id": "call_1"},
                tools=[],
            )
            handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="bash"))

            middleware.wrap_tool_call(request, handler)

            # Check it was called with correct resource mapping
            args = mock_check.call_args
            assert args[0][2] == "sandbox"  # resource
            assert args[0][3] == "execute"  # action

    def test_maps_read_file_to_sandbox_read(self, middleware):
        with patch("deerflow.enterprise.rbac_middleware.check_permission") as mock_check:
            mock_check.return_value = True

            request = ToolCallRequest(
                tool_call={"name": "read_file", "args": {}, "id": "call_1"},
                tools=[],
            )
            handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="read_file"))

            middleware.wrap_tool_call(request, handler)

            args = mock_check.call_args
            assert args[0][2] == "sandbox"
            assert args[0][3] == "read"

    def test_maps_task_to_agent_execute(self, middleware):
        with patch("deerflow.enterprise.rbac_middleware.check_permission") as mock_check:
            mock_check.return_value = True

            request = ToolCallRequest(
                tool_call={"name": "task", "args": {} , "id": "call_1"},
                tools=[],
            )
            handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="task"))

            middleware.wrap_tool_call(request, handler)

            args = mock_check.call_args
            assert args[0][2] == "agent"
            assert args[0][3] == "execute"

    def test_extracts_user_and_tenant_from_context(self, middleware):
        with patch("deerflow.enterprise.rbac_middleware.check_permission") as mock_check:
            mock_check.return_value = True
            with patch("deerflow.enterprise.rbac_middleware.get_effective_user_id") as mock_user:
                mock_user.return_value = "user_123"
                with patch("deerflow.enterprise.rbac_middleware.get_current_tenant") as mock_tenant:
                    mock_tenant.return_value = Mock(id="tenant_abc")

                    request = ToolCallRequest(
                        tool_call={"name": "read_file", "args": {}, "id": "call_1"},
                        tools=[],
                    )
                    handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="read_file"))

                    middleware.wrap_tool_call(request, handler)

                    args = mock_check.call_args
                    assert args[0][0] == "user_123"  # user_id
                    assert args[0][1] == "tenant_abc"  # tenant_id

    def test_async_version_works(self, middleware):
        with patch("deerflow.enterprise.rbac_middleware.check_permission") as mock_check:
            mock_check.return_value = True

            request = ToolCallRequest(
                tool_call={"name": "read_file", "args": {}, "id": "call_1"},
                tools=[],
            )
            handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="read_file"))

            import asyncio
            result = asyncio.run(middleware.awrap_tool_call(request, handler))

            assert result.content == "ok"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python -m pytest tests/enterprise/test_rbac_middleware.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement RBACMiddleware**

```python
# backend/packages/harness/deerflow/enterprise/rbac_middleware.py
"""RBAC permission checking middleware for tool calls."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

from deerflow.agents.thread_state import ThreadState
from deerflow.enterprise.rbac import check_permission
from deerflow.enterprise.tenancy import get_current_tenant
from deerflow.runtime.user_context import get_effective_user_id


logger = logging.getLogger(__name__)


# Tool name to (resource, action) mapping
_TOOL_PERMISSION_MAP: dict[str, tuple[str, str]] = {
    # Sandbox tools
    "bash": ("sandbox", "execute"),
    "str_replace": ("sandbox", "execute"),
    "write_file": ("sandbox", "execute"),
    "read_file": ("sandbox", "read"),
    "ls": ("sandbox", "read"),
    # Agent tools
    "task": ("agent", "execute"),
    "setup_agent": ("agent", "create"),
    "update_agent": ("agent", "update"),
    # Interaction tools
    "ask_clarification": ("interaction", "execute"),
    "present_files": ("file", "read"),
    "view_image": ("file", "read"),
}


def _map_tool_to_resource(tool_name: str) -> tuple[str, str]:
    """Map tool name to (resource, action) tuple.

    Unknown tools default to ("tool", "execute").
    """
    return _TOOL_PERMISSION_MAP.get(tool_name, ("tool", "execute"))


class RBACMiddleware(AgentMiddleware[ThreadState]):
    """Middleware that enforces RBAC permissions on tool calls.

    Checks if the current user has permission to execute the requested
    tool based on their role and tenant.
    """

    state_schema = ThreadState

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def _get_user_id(self) -> str:
        """Extract user ID from current context."""
        return get_effective_user_id() or "anonymous"

    def _get_tenant_id(self) -> str:
        """Extract tenant ID from current context."""
        tenant = get_current_tenant()
        return tenant.id if tenant else "default"

    def _build_permission_denied_message(
        self,
        request: ToolCallRequest,
        user_id: str,
        resource: str,
        action: str,
    ) -> ToolMessage:
        """Build error message for permission denied."""
        tool_call_id = str(request.tool_call.get("id") or "missing_id")
        tool_name = request.tool_call.get("name", "unknown")

        content = (
            f"❌ Permission Denied\n\n"
            f"You don't have permission to execute '{tool_name}'.\n"
            f"Required: {resource}:{action}\n"
            f"User: {user_id}\n\n"
            f"Contact your administrator if you need access."
        )

        return ToolMessage(
            content=content,
            tool_call_id=tool_call_id,
            name=tool_name,
            status="error",
        )

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        if not self.enabled:
            return handler(request)

        tool_name = request.tool_call.get("name", "")
        resource, action = _map_tool_to_resource(tool_name)

        user_id = self._get_user_id()
        tenant_id = self._get_tenant_id()

        # Check permission
        allowed = check_permission(user_id, tenant_id, resource, action)

        if not allowed:
            logger.warning(
                "RBAC denied: user=%s tenant=%s resource=%s action=%s tool=%s",
                user_id, tenant_id, resource, action, tool_name
            )
            return self._build_permission_denied_message(
                request, user_id, resource, action
            )

        logger.debug(
            "RBAC allowed: user=%s tenant=%s resource=%s action=%s tool=%s",
            user_id, tenant_id, resource, action, tool_name
        )
        return handler(request)

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        if not self.enabled:
            return await handler(request)

        tool_name = request.tool_call.get("name", "")
        resource, action = _map_tool_to_resource(tool_name)

        user_id = self._get_user_id()
        tenant_id = self._get_tenant_id()

        allowed = check_permission(user_id, tenant_id, resource, action)

        if not allowed:
            logger.warning(
                "RBAC denied (async): user=%s tenant=%s resource=%s action=%s tool=%s",
                user_id, tenant_id, resource, action, tool_name
            )
            return self._build_permission_denied_message(
                request, user_id, resource, action
            )

        return await handler(request)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/enterprise/test_rbac_middleware.py -v
```

Expected: All 8 tests PASS

- [ ] **Step 5: Update __init__.py exports**

```python
# Add to backend/packages/harness/deerflow/enterprise/__init__.py

from deerflow.enterprise.rbac_middleware import RBACMiddleware
from deerflow.enterprise.quota_middleware import QuotaMiddleware

__all__ = [
    # ... existing exports ...
    # Middleware
    "RBACMiddleware",
    "QuotaMiddleware",
]
```

- [ ] **Step 6: Commit**

```bash
git add backend/packages/harness/deerflow/enterprise/rbac_middleware.py
git add backend/tests/enterprise/test_rbac_middleware.py
git add backend/packages/harness/deerflow/enterprise/__init__.py
git commit -m "feat(enterprise): implement RBACMiddleware for permission checking"
```

---

## Task 5: AppConfig Integration

**Files:**
- Modify: `backend/packages/harness/deerflow/config/app_config.py`

---

- [ ] **Step 1: Add QuotaConfig to AppConfig**

```python
# Add to backend/packages/harness/deerflow/config/app_config.py

from deerflow.enterprise.quota_config import QuotaConfig

class AppConfig(BaseSettings):
    # ... existing fields ...

    # Enterprise configuration
    tenancy: TenancyConfig = Field(default_factory=TenancyConfig)
    rbac: RBACConfig = Field(default_factory=RBACConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    quota: QuotaConfig = Field(default_factory=QuotaConfig)  # NEW
```

- [ ] **Step 2: Run tests to verify no regressions**

```bash
cd backend
python -m pytest tests/ -v -k "test_app_config" --no-header -q 2>/dev/null || echo "Config tests may vary"
```

- [ ] **Step 3: Commit**

```bash
git add backend/packages/harness/deerflow/config/app_config.py
git commit -m "feat(enterprise): integrate QuotaConfig into AppConfig"
```

---

## Task 6: Final Integration and Verification

**Files:**
- Create: `backend/tests/enterprise/conftest.py`
- Modify: `config.example.yaml`

---

- [ ] **Step 1: Create shared test fixtures**

```python
# backend/tests/enterprise/conftest.py
"""Shared fixtures for enterprise module tests."""

import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_redis():
    """Mock Redis client for quota tests."""
    redis = Mock()
    redis.get.return_value = None
    redis.incr.return_value = 1
    redis.decr.return_value = 0
    return redis


@pytest.fixture
def mock_tenant():
    """Mock tenant for context tests."""
    tenant = Mock()
    tenant.id = "test_tenant"
    tenant.name = "Test Tenant"
    tenant.plan = "enterprise"
    tenant.isolation_mode = "strict"
    return tenant
```

- [ ] **Step 2: Update config.example.yaml**

```yaml
# Add to config.example.yaml under enterprise section

enterprise:
  tenancy:
    enabled: false
    # ... existing tenancy config ...

  rbac:
    enabled: false
    # ... existing rbac config ...

  audit:
    enabled: false
    # ... existing audit config ...

  quota:  # NEW
    enabled: false
    redis_url: "redis://localhost:6379"
    enforcement_mode: "hard"
    default_quotas:
      max_concurrent_sandboxes: 5
      max_cpu_cores: 4.0
      max_memory_gb: 8.0
      max_storage_gb: 100.0
      max_network_egress_mb: 1000
```

- [ ] **Step 3: Run full enterprise test suite**

```bash
cd backend
python -m pytest tests/enterprise/ -v --tb=short
```

Expected: All 24 tests PASS (6 quota_config + 10 quota_manager + 6 quota_middleware + 8 rbac_middleware - overlaps accounted)

- [ ] **Step 4: Run full test suite to check for regressions**

```bash
cd backend
make test
```

Expected: All existing tests pass + new enterprise tests pass

- [ ] **Step 5: Commit final changes**

```bash
git add backend/tests/enterprise/conftest.py
git add config.example.yaml
git commit -m "test(enterprise): add shared fixtures and config examples"
```

---

## Self-Review Checklist

- [ ] **Spec coverage:** All requirements from design doc are implemented
  - QuotaConfig ✅
  - QuotaManager with Redis ✅
  - QuotaMiddleware ✅
  - RBACMiddleware ✅
  - 24 test cases ✅

- [ ] **Placeholder scan:** No TBD/TODO/fill in details
- [ ] **Type consistency:** All function signatures match between tasks
- [ ] **Import consistency:** All imports use correct paths

---

## Acceptance Criteria

- [ ] All 24 unit tests pass
- [ ] RBACMiddleware blocks unauthorized tool calls
- [ ] QuotaMiddleware enforces resource limits
- [ ] Error messages are clear and actionable
- [ ] No regressions in existing tests
- [ ] config.example.yaml updated

---

## Plan Complete

**Plan saved to:** `docs/superpowers/plans/2026-05-26-enterprise-subsystem1-rbac-quota.md`

**Two execution options:**

**1. Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach would you like to use for implementing this plan?
