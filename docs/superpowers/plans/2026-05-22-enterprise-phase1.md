# DeerFlow Enterprise Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the infrastructure layer for DeerFlow Enterprise, including multi-tenancy, RBAC, data isolation, and audit logging.

**Architecture:** Build upon DeerFlow's existing user context system (`user_context.py`) to extend tenant-aware operations. Follow the existing middleware pattern for request-level isolation, and create new config modules following the `*_config.py` convention. The audit system will extend the existing `sandbox_audit_middleware.py` pattern.

**Tech Stack:** Python 3.12+, FastAPI, Casbin (RBAC), PostgreSQL (RLS), contextvars, Ed25519 signatures

**Timeline:** 6 weeks (4 slices)

---

## Phase 1: Infrastructure Layer Overview

```
Phase 1: Infrastructure Layer (6 weeks)
├── Slice 1.1: TenantContext Thread Storage (1.5 weeks)
│   ├── Tenant model and context
│   ├── TenantContextVar implementation
│   └── TenantIdentificationMiddleware
├── Slice 1.2: Data Isolation Boundaries (1.5 weeks)
│   ├── Namespace management
│   ├── PostgreSQL RLS policies
│   └── Vector store namespace isolation
├── Slice 1.3: RBAC Role Model (1.5 weeks)
│   ├── Casbin integration
│   ├── Policy models
│   └── RBACMiddleware
└── Slice 1.4: Audit Event System (1.5 weeks)
    ├── AuditEvent model
    ├── Ed25519 signing
    └── ImmutableAuditLog storage
```

---

## File Structure

### New Files

| File | Responsibility |
|------|----------------|
| `backend/packages/harness/deerflow/enterprise/__init__.py` | Enterprise module exports |
| `backend/packages/harness/deerflow/enterprise/tenancy.py` | TenantContext, tenant resolution |
| `backend/packages/harness/deerflow/enterprise/tenant_config.py` | Tenant config schema |
| `backend/packages/harness/deerflow/enterprise/isolation.py` | Namespace management |
| `backend/packages/harness/deerflow/enterprise/rbac.py` | RBAC core, Casbin wrapper |
| `backend/packages/harness/deerflow/enterprise/rbac_config.py` | RBAC configuration |
| `backend/packages/harness/deerflow/enterprise/audit.py` | AuditEvent, signing, storage |
| `backend/packages/harness/deerflow/enterprise/audit_config.py` | Audit configuration |
| `backend/packages/harness/deerflow/agents/middlewares/tenant_middleware.py` | Tenant identification middleware |
| `backend/packages/harness/deerflow/agents/middlewares/rbac_middleware.py` | Permission check middleware |
| `backend/tests/enterprise/test_tenancy.py` | Tenancy unit tests |
| `backend/tests/enterprise/test_isolation.py` | Isolation tests |
| `backend/tests/enterprise/test_rbac.py` | RBAC tests |
| `backend/tests/enterprise/test_audit.py` | Audit system tests |

### Modified Files

| File | Changes |
|------|---------|
| `backend/packages/harness/deerflow/config/app_config.py` | Add tenant, rbac, audit config sections |
| `backend/packages/harness/deerflow/runtime/user_context.py` | Add tenant context integration |
| `config.example.yaml` | Add enterprise configuration section |

---

## Slice 1.1: TenantContext Thread Storage

**Files:**
- Create: `backend/packages/harness/deerflow/enterprise/__init__.py`
- Create: `backend/packages/harness/deerflow/enterprise/tenancy.py`
- Create: `backend/packages/harness/deerflow/enterprise/tenant_config.py`
- Create: `backend/packages/harness/deerflow/agents/middlewares/tenant_middleware.py`
- Create: `backend/tests/enterprise/test_tenancy.py`
- Modify: `backend/packages/harness/deerflow/config/app_config.py` (add tenant config)

---

### Task 1.1.1: Create Enterprise Module Structure

**Files:**
- Create: `backend/packages/harness/deerflow/enterprise/__init__.py`

- [ ] **Step 1: Write the enterprise module init**

```python
"""DeerFlow Enterprise - Multi-tenancy, RBAC, and Audit infrastructure."""

from deerflow.enterprise.tenancy import (
    get_current_tenant,
    set_current_tenant,
    reset_current_tenant,
    require_current_tenant,
    tenant_context,
    Tenant,
)
from deerflow.enterprise.isolation import (
    TenantNamespace,
    get_tenant_prefix,
)
from deerflow.enterprise.rbac import (
    check_permission,
    require_permission,
)
from deerflow.enterprise.audit import (
    AuditEvent,
    ImmutableAuditLog,
)

__all__ = [
    # Tenancy
    "get_current_tenant",
    "set_current_tenant",
    "reset_current_tenant",
    "require_current_tenant",
    "tenant_context",
    "Tenant",
    # Isolation
    "TenantNamespace",
    "get_tenant_prefix",
    # RBAC
    "check_permission",
    "require_permission",
    # Audit
    "AuditEvent",
    "ImmutableAuditLog",
]
```

- [ ] **Step 2: Create the enterprise directory**

```bash
mkdir -p backend/packages/harness/deerflow/enterprise
touch backend/packages/harness/deerflow/enterprise/__init__.py
```

- [ ] **Step 3: Commit**

```bash
git add backend/packages/harness/deerflow/enterprise/__init__.py
git commit -m "feat(enterprise): create enterprise module structure"
```

---

### Task 1.1.2: Implement Tenant Model and Context

**Files:**
- Create: `backend/packages/harness/deerflow/enterprise/tenancy.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/enterprise/test_tenancy.py
from contextvars import copy_context

import pytest

from deerflow.enterprise.tenancy import (
    Tenant,
    get_current_tenant,
    set_current_tenant,
    reset_current_tenant,
    require_current_tenant,
    tenant_context,
)


class TestTenant:
    def test_tenant_creation(self):
        tenant = Tenant(
            id="tenant_123",
            name="Acme Corp",
            plan="enterprise",
            isolation_mode="strict",
        )
        assert tenant.id == "tenant_123"
        assert tenant.name == "Acme Corp"
        assert tenant.plan == "enterprise"
        assert tenant.isolation_mode == "strict"

    def test_tenant_namespace_prefix(self):
        tenant = Tenant(id="tenant_abc", name="Test")
        assert tenant.namespace_prefix == "tenant_abc"


class TestTenantContext:
    def test_get_current_tenant_returns_none_when_unset(self):
        # Clear any existing context
        assert get_current_tenant() is None

    def test_set_and_get_current_tenant(self):
        tenant = Tenant(id="tenant_123", name="Test")
        token = set_current_tenant(tenant)
        try:
            assert get_current_tenant() == tenant
        finally:
            reset_current_tenant(token)

    def test_reset_current_tenant_restores_previous(self):
        tenant1 = Tenant(id="tenant_1", name="First")
        tenant2 = Tenant(id="tenant_2", name="Second")

        token1 = set_current_tenant(tenant1)
        try:
            token2 = set_current_tenant(tenant2)
            try:
                assert get_current_tenant() == tenant2
            finally:
                reset_current_tenant(token2)
            assert get_current_tenant() == tenant1
        finally:
            reset_current_tenant(token1)

    def test_require_current_tenant_raises_when_unset(self):
        # Ensure context is clear
        with pytest.raises(RuntimeError, match="no tenant context"):
            require_current_tenant()

    def test_require_current_tenant_returns_tenant_when_set(self):
        tenant = Tenant(id="tenant_123", name="Test")
        token = set_current_tenant(tenant)
        try:
            result = require_current_tenant()
            assert result == tenant
        finally:
            reset_current_tenant(token)


class TestTenantContextManager:
    def test_tenant_context_sets_and_resets(self):
        # Run in isolated context
        ctx = copy_context()

        def test_fn():
            assert get_current_tenant() is None

            with tenant_context("tenant_456"):
                assert get_current_tenant().id == "tenant_456"

            assert get_current_tenant() is None

        ctx.run(test_fn)

    def test_tenant_context_with_tenant_object(self):
        tenant = Tenant(id="tenant_789", name="Test Corp")

        with tenant_context(tenant):
            current = get_current_tenant()
            assert current.id == "tenant_789"
            assert current.name == "Test Corp"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/enterprise/test_tenancy.py -v
```
Expected: ImportError or ModuleNotFoundError

- [ ] **Step 3: Implement Tenant dataclass**

```python
# backend/packages/harness/deerflow/enterprise/tenancy.py
"""Tenant context management for multi-tenancy.

This module provides tenant-scoped context similar to user_context.py,
enabling data isolation across multiple enterprise tenants.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Final, Generator, Literal


@dataclass(frozen=True, slots=True)
class Tenant:
    """Represents a single tenant (enterprise customer).

    Attributes:
        id: Unique tenant identifier (e.g., "tenant_123abc")
        name: Human-readable tenant name
        plan: Subscription tier ("free", "pro", "enterprise")
        isolation_mode: Data isolation strategy ("strict" or "relaxed")
    """

    id: str
    name: str
    plan: Literal["free", "pro", "enterprise"] = "pro"
    isolation_mode: Literal["strict", "relaxed"] = "relaxed"

    @property
    def namespace_prefix(self) -> str:
        """Return the prefix used for namespacing tenant resources."""
        return self.id

    def __str__(self) -> str:
        return f"Tenant({self.id}, {self.name})"


# ContextVar for storing current tenant in async tasks
_current_tenant: Final[ContextVar[Tenant | None]] = ContextVar(
    "deerflow_current_tenant",
    default=None,
)


def set_current_tenant(tenant: Tenant) -> Token[Tenant | None]:
    """Set the current tenant for this async task.

    Returns a reset token that should be passed to reset_current_tenant
    in a finally block to restore the previous context.

    Example:
        token = set_current_tenant(tenant)
        try:
            # ... do work with tenant context
        finally:
            reset_current_tenant(token)
    """
    return _current_tenant.set(tenant)


def reset_current_tenant(token: Token[Tenant | None]) -> None:
    """Restore the context to the state captured by token."""
    _current_tenant.reset(token)


def get_current_tenant() -> Tenant | None:
    """Return the current tenant, or None if unset.

    Safe to call in any context. Used by code paths that can proceed
    without a tenant (e.g., system operations, public endpoints).
    """
    return _current_tenant.get()


def require_current_tenant() -> Tenant:
    """Return the current tenant, or raise RuntimeError.

    Used by repository code that must not be called outside a
    tenant-authenticated context.
    """
    tenant = _current_tenant.get()
    if tenant is None:
        raise RuntimeError("operation requires tenant context but none is set")
    return tenant


@contextmanager
def tenant_context(
    tenant: Tenant | str,
    name: str = "",
    plan: Literal["free", "pro", "enterprise"] = "pro",
    isolation_mode: Literal["strict", "relaxed"] = "relaxed",
) -> Generator[Tenant, None, None]:
    """Context manager for temporarily setting the current tenant.

    Args:
        tenant: Either a Tenant object or a tenant ID string
        name: Tenant name (used only if tenant is a string)
        plan: Subscription tier (used only if tenant is a string)
        isolation_mode: Isolation strategy (used only if tenant is a string)

    Example:
        with tenant_context("tenant_123", name="Acme Corp"):
            # All operations within this block have tenant context
            do_work()
    """
    if isinstance(tenant, str):
        tenant = Tenant(
            id=tenant,
            name=name or tenant,
            plan=plan,
            isolation_mode=isolation_mode,
        )

    token = set_current_tenant(tenant)
    try:
        yield tenant
    finally:
        reset_current_tenant(token)


# Sentinel for auto-resolution (similar to user_context.py)
class _AutoSentinel:
    """Marker meaning 'resolve tenant_id from contextvar'."""

    _instance: _AutoSentinel | None = None

    def __new__(cls) -> _AutoSentinel:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "<AUTO>"


AUTO: Final[_AutoSentinel] = _AutoSentinel()


def resolve_tenant_id(
    value: str | None | _AutoSentinel,
    *,
    method_name: str = "operation",
) -> str | None:
    """Resolve tenant_id parameter using AUTO sentinel pattern.

    Three-state semantics:
    - AUTO (default): read from contextvar; raise if no tenant context
    - Explicit str: use provided value
    - None: no tenant filter (for system operations)
    """
    if isinstance(value, _AutoSentinel):
        tenant = _current_tenant.get()
        if tenant is None:
            raise RuntimeError(
                f"{method_name} called with tenant_id=AUTO but no tenant context is set; "
                "pass an explicit tenant_id or use tenant_context()"
            )
        return tenant.id
    return value
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/enterprise/test_tenancy.py -v
```
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/packages/harness/deerflow/enterprise/tenancy.py
mkdir -p backend/tests/enterprise
mv backend/tests/enterprise/test_tenancy.py backend/tests/enterprise/test_tenancy.py 2>/dev/null || true
git add backend/tests/enterprise/test_tenancy.py
git commit -m "feat(enterprise): implement TenantContext with ContextVar"
```

---

### Task 1.1.3: Implement Tenant Configuration

**Files:**
- Create: `backend/packages/harness/deerflow/enterprise/tenant_config.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/enterprise/test_tenant_config.py
import pytest
from pydantic import ValidationError

from deerflow.enterprise.tenant_config import TenantConfig, TenancyConfig


class TestTenantConfig:
    def test_default_tenant_config(self):
        config = TenantConfig()
        assert config.id == "default"
        assert config.name == "Default Tenant"
        assert config.plan == "pro"
        assert config.isolation_mode == "relaxed"

    def test_tenant_config_with_values(self):
        config = TenantConfig(
            id="tenant_123",
            name="Acme Corp",
            plan="enterprise",
            isolation_mode="strict",
        )
        assert config.id == "tenant_123"
        assert config.isolation_mode == "strict"

    def test_invalid_isolation_mode(self):
        with pytest.raises(ValidationError):
            TenantConfig(isolation_mode="invalid")

    def test_invalid_plan(self):
        with pytest.raises(ValidationError):
            TenantConfig(plan="premium")


class TestTenancyConfig:
    def test_default_tenancy_config(self):
        config = TenancyConfig()
        assert config.enabled is False
        assert config.default_isolation_mode == "relaxed"
        assert len(config.tenants) == 1
        assert config.tenants[0].id == "default"

    def test_tenancy_enabled(self):
        config = TenancyConfig(enabled=True)
        assert config.enabled is True

    def test_get_tenant_by_id(self):
        config = TenancyConfig(
            tenants=[
                TenantConfig(id="tenant_a", name="A"),
                TenantConfig(id="tenant_b", name="B"),
            ]
        )
        tenant = config.get_tenant("tenant_a")
        assert tenant is not None
        assert tenant.name == "A"

    def test_get_tenant_not_found(self):
        config = TenancyConfig()
        assert config.get_tenant("nonexistent") is None

    def test_default_tenant(self):
        config = TenancyConfig(
            tenants=[
                TenantConfig(id="tenant_a", name="A"),
                TenantConfig(id="default", name="Default"),
            ]
        )
        default = config.default_tenant
        assert default.id == "default"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/enterprise/test_tenant_config.py -v
```
Expected: ModuleNotFoundError

- [ ] **Step 3: Implement TenantConfig**

```python
# backend/packages/harness/deerflow/enterprise/tenant_config.py
"""Configuration schema for multi-tenancy."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TenantConfig(BaseModel):
    """Configuration for a single tenant.

    This is the static configuration loaded from config.yaml.
    Dynamic tenant management would use a database instead.
    """

    id: str = Field(default="default", description="Unique tenant identifier")
    name: str = Field(default="Default Tenant", description="Human-readable name")
    plan: Literal["free", "pro", "enterprise"] = Field(
        default="pro",
        description="Subscription tier",
    )
    isolation_mode: Literal["strict", "relaxed"] = Field(
        default="relaxed",
        description="Data isolation strategy",
    )
    # Additional tenant-specific settings
    max_agents: int = Field(default=10, description="Max concurrent agents")
    max_storage_gb: int = Field(default=100, description="Max storage in GB")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v:
            raise ValueError("tenant id cannot be empty")
        if " " in v:
            raise ValueError("tenant id cannot contain spaces")
        return v


class TenancyConfig(BaseModel):
    """Top-level multi-tenancy configuration."""

    enabled: bool = Field(
        default=False,
        description="Enable multi-tenancy features",
    )
    default_isolation_mode: Literal["strict", "relaxed"] = Field(
        default="relaxed",
        description="Default isolation for new tenants",
    )
    tenants: list[TenantConfig] = Field(
        default_factory=lambda: [TenantConfig()],
        description="List of configured tenants",
    )
    # Tenant resolution settings
    header_name: str = Field(
        default="X-Tenant-ID",
        description="HTTP header for tenant identification",
    )
    domain_pattern: str | None = Field(
        default=None,
        description="Pattern to extract tenant from domain (e.g., '{tenant}.deerflow.com')",
    )

    def get_tenant(self, tenant_id: str) -> TenantConfig | None:
        """Find tenant config by ID."""
        for tenant in self.tenants:
            if tenant.id == tenant_id:
                return tenant
        return None

    @property
    def default_tenant(self) -> TenantConfig:
        """Return the default tenant configuration."""
        for tenant in self.tenants:
            if tenant.id == "default":
                return tenant
        return self.tenants[0]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/enterprise/test_tenant_config.py -v
```
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/packages/harness/deerflow/enterprise/tenant_config.py
mkdir -p backend/tests/enterprise
git add backend/tests/enterprise/test_tenant_config.py
git commit -m "feat(enterprise): add TenantConfig with validation"
```

---

### Task 1.1.4: Implement TenantIdentificationMiddleware

**Files:**
- Create: `backend/packages/harness/deerflow/agents/middlewares/tenant_middleware.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/enterprise/test_tenant_middleware.py
from unittest.mock import Mock, patch

import pytest

from deerflow.enterprise.tenancy import get_current_tenant
from deerflow.enterprise.tenant_config import TenancyConfig
from deerflow.agents.middlewares.tenant_middleware import (
    TenantIdentificationMiddleware,
    TenantResolver,
)


class TestTenantResolver:
    def test_resolve_from_header(self):
        config = TenancyConfig(
            tenants=[{"id": "tenant_a", "name": "A"}],
            header_name="X-Tenant-ID",
        )
        resolver = TenantResolver(config)

        request = Mock()
        request.headers = {"X-Tenant-ID": "tenant_a"}

        tenant = resolver.resolve(request)
        assert tenant is not None
        assert tenant.id == "tenant_a"

    def test_resolve_missing_header_returns_default(self):
        config = TenancyConfig(tenants=[{"id": "default", "name": "Default"}])
        resolver = TenantResolver(config)

        request = Mock()
        request.headers = {}

        tenant = resolver.resolve(request)
        assert tenant.id == "default"

    def test_resolve_unknown_tenant_raises(self):
        config = TenancyConfig()
        resolver = TenantResolver(config)

        request = Mock()
        request.headers = {"X-Tenant-ID": "unknown"}

        with pytest.raises(ValueError, match="Unknown tenant"):
            resolver.resolve(request)


class TestTenantIdentificationMiddleware:
    def test_middleware_sets_tenant_context(self):
        config = TenancyConfig(
            enabled=True,
            tenants=[{"id": "test_tenant", "name": "Test"}],
        )

        middleware = TenantIdentificationMiddleware(config)

        # Mock request
        request = Mock()
        request.headers = {"X-Tenant-ID": "test_tenant"}

        # Mock next middleware
        next_middleware = Mock(return_value="result")

        # Execute
        result = middleware(request, next_middleware)

        assert result == "result"
        assert get_current_tenant().id == "test_tenant"

    def test_middleware_disabled_skips_resolution(self):
        config = TenancyConfig(enabled=False)
        middleware = TenantIdentificationMiddleware(config)

        request = Mock()
        request.headers = {"X-Tenant-ID": "test"}

        next_middleware = Mock(return_value="result")
        result = middleware(request, next_middleware)

        assert result == "result"
        assert get_current_tenant() is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/enterprise/test_tenant_middleware.py -v
```
Expected: ModuleNotFoundError

- [ ] **Step 3: Implement TenantIdentificationMiddleware**

```python
# backend/packages/harness/deerflow/agents/middlewares/tenant_middleware.py
"""Middleware for identifying and setting tenant context.

This middleware runs early in the request chain to establish tenant context
for all downstream operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from deerflow.enterprise.tenancy import (
    Tenant,
    get_current_tenant,
    reset_current_tenant,
    set_current_tenant,
)
from deerflow.enterprise.tenant_config import TenancyConfig

if TYPE_CHECKING:
    from deerflow.agents.thread_state import ThreadState


class TenantResolver:
    """Resolves tenant from incoming requests."""

    def __init__(self, config: TenancyConfig) -> None:
        self.config = config

    def resolve(self, request: Any) -> Tenant:
        """Extract tenant from request and return Tenant object.

        Resolution order:
        1. Custom header (X-Tenant-ID)
        2. Domain-based resolution
        3. Default tenant
        """
        # Try header resolution
        tenant_id = self._resolve_from_header(request)
        if tenant_id:
            tenant_config = self.config.get_tenant(tenant_id)
            if tenant_config is None:
                raise ValueError(f"Unknown tenant: {tenant_id}")
            return Tenant(
                id=tenant_config.id,
                name=tenant_config.name,
                plan=tenant_config.plan,
                isolation_mode=tenant_config.isolation_mode,
            )

        # Return default tenant
        default = self.config.default_tenant
        return Tenant(
            id=default.id,
            name=default.name,
            plan=default.plan,
            isolation_mode=default.isolation_mode,
        )

    def _resolve_from_header(self, request: Any) -> str | None:
        """Extract tenant ID from custom header."""
        headers = getattr(request, "headers", {}) or {}
        tenant_id = headers.get(self.config.header_name)
        return tenant_id


class TenantIdentificationMiddleware:
    """Middleware that establishes tenant context for requests.

    This middleware should run after authentication but before any
tenant-aware operations.
    """

    def __init__(self, config: TenancyConfig) -> None:
        self.config = config
        self.resolver = TenantResolver(config)

    def __call__(
        self,
        request: Any,
        next_middleware: Callable[[Any], Any],
    ) -> Any:
        """Process request with tenant context."""
        if not self.config.enabled:
            # Multi-tenancy disabled - skip resolution
            return next_middleware(request)

        # Resolve tenant
        tenant = self.resolver.resolve(request)

        # Set context and proceed
        token = set_current_tenant(tenant)
        try:
            # Attach tenant to request for convenience
            request.tenant = tenant
            return next_middleware(request)
        finally:
            reset_current_tenant(token)

    async def __acall__(
        self,
        request: Any,
        next_middleware: Callable[[Any], Any],
    ) -> Any:
        """Async version of middleware call."""
        if not self.config.enabled:
            return await next_middleware(request)

        tenant = self.resolver.resolve(request)
        token = set_current_tenant(tenant)
        try:
            request.tenant = tenant
            return await next_middleware(request)
        finally:
            reset_current_tenant(token)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/enterprise/test_tenant_middleware.py -v
```
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/packages/harness/deerflow/agents/middlewares/tenant_middleware.py
mkdir -p backend/tests/enterprise
git add backend/tests/enterprise/test_tenant_middleware.py
git commit -m "feat(enterprise): add TenantIdentificationMiddleware"
```

---

## Slice 1.2: Data Isolation Boundaries

**Files:**
- Create: `backend/packages/harness/deerflow/enterprise/isolation.py`
- Create: `backend/tests/enterprise/test_isolation.py`

---

### Task 1.2.1: Implement Namespace Management

**Files:**
- Create: `backend/packages/harness/deerflow/enterprise/isolation.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/enterprise/test_isolation.py
import pytest

from deerflow.enterprise.isolation import (
    TenantNamespace,
    get_tenant_prefix,
    namespaced_path,
    namespaced_table,
)
from deerflow.enterprise.tenancy import Tenant


class TestTenantNamespace:
    def test_namespace_creation(self):
        tenant = Tenant(id="tenant_123", name="Test")
        ns = TenantNamespace(tenant)

        assert ns.tenant_id == "tenant_123"
        assert ns.prefix == "tenant_123"

    def test_apply_to_table_name(self):
        tenant = Tenant(id="tenant_abc", name="Test")
        ns = TenantNamespace(tenant)

        result = ns.apply_to_table("threads")
        assert result == "tenant_abc_threads"

    def test_apply_to_path(self):
        tenant = Tenant(id="tenant_xyz", name="Test")
        ns = TenantNamespace(tenant)

        result = ns.apply_to_path("/data/uploads")
        assert result == "/data/tenant_xyz/uploads"

    def test_apply_to_collection_name(self):
        tenant = Tenant(id="tenant_vec", name="Test")
        ns = TenantNamespace(tenant)

        result = ns.apply_to_collection("memories")
        assert result == "tenant_vec_memories"


class TestNamespaceHelpers:
    def test_get_tenant_prefix_with_tenant(self):
        tenant = Tenant(id="tenant_123", name="Test")
        assert get_tenant_prefix(tenant) == "tenant_123"

    def test_get_tenant_prefix_with_string(self):
        assert get_tenant_prefix("tenant_456") == "tenant_456"

    def test_namespaced_table(self):
        result = namespaced_table("tenant_789", "agents")
        assert result == "tenant_789_agents"

    def test_namespaced_path(self):
        result = namespaced_path("tenant_aaa", "/workspace")
        assert result == "/workspace/tenant_aaa"

    def test_namespaced_collection(self):
        result = namespaced_collection("tenant_bbb", "vectors")
        assert result == "tenant_bbb_vectors"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/enterprise/test_isolation.py -v
```
Expected: ImportError

- [ ] **Step 3: Implement Namespace Management**

```python
# backend/packages/harness/deerflow/enterprise/isolation.py
"""Data isolation utilities for multi-tenancy.

Provides namespace management for tables, files, and collections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deerflow.enterprise.tenancy import Tenant


class TenantNamespace:
    """Manages resource namespacing for a tenant.

    This class provides methods to generate tenant-scoped names for:
    - Database tables (strict mode): tenant_{id}_{table}
    - File paths: /base/tenant_{id}/...
    - Vector collections: tenant_{id}_{collection}
    """

    def __init__(self, tenant: Tenant | str) -> None:
        if isinstance(tenant, str):
            self._tenant_id = tenant
        else:
            self._tenant_id = tenant.id

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    @property
    def prefix(self) -> str:
        """Return the namespace prefix for this tenant."""
        return self._tenant_id

    def apply_to_table(self, table_name: str) -> str:
        """Generate tenant-scoped table name.

        Example: tenant_123_threads
        """
        return f"{self._tenant_id}_{table_name}"

    def apply_to_path(self, base_path: str, *segments: str) -> str:
        """Generate tenant-scoped file path.

        Example: /data/tenant_123/uploads
        """
        import os

        # Insert tenant prefix after base path
        path = os.path.join(base_path, self._tenant_id, *segments)
        return path

    def apply_to_collection(self, collection_name: str) -> str:
        """Generate tenant-scoped collection name for vector stores.

        Example: tenant_123_memories
        """
        return f"{self._tenant_id}_{collection_name}"

    def apply_to_key(self, key: str) -> str:
        """Generate tenant-scoped key for caches and stores.

        Example: tenant_123:session:abc123
        """
        return f"{self._tenant_id}:{key}"


def get_tenant_prefix(tenant: Tenant | str) -> str:
    """Get namespace prefix from tenant or tenant_id."""
    if isinstance(tenant, str):
        return tenant
    return tenant.id


def namespaced_table(tenant_id: str, table_name: str) -> str:
    """Generate tenant-scoped table name."""
    return f"{tenant_id}_{table_name}"


def namespaced_path(tenant_id: str, base_path: str, *segments: str) -> str:
    """Generate tenant-scoped file path."""
    import os

    return os.path.join(base_path, tenant_id, *segments)


def namespaced_collection(tenant_id: str, collection_name: str) -> str:
    """Generate tenant-scoped collection name."""
    return f"{tenant_id}_{collection_name}"


def namespaced_key(tenant_id: str, key: str) -> str:
    """Generate tenant-scoped key."""
    return f"{tenant_id}:{key}"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/enterprise/test_isolation.py -v
```
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/packages/harness/deerflow/enterprise/isolation.py
mkdir -p backend/tests/enterprise
git add backend/tests/enterprise/test_isolation.py
git commit -m "feat(enterprise): implement TenantNamespace for data isolation"
```

---

## Slice 1.3: RBAC Role Model

**Files:**
- Create: `backend/packages/harness/deerflow/enterprise/rbac.py`
- Create: `backend/packages/harness/deerflow/enterprise/rbac_config.py`
- Create: `backend/packages/harness/deerflow/agents/middlewares/rbac_middleware.py`
- Create: `backend/tests/enterprise/test_rbac.py`

---

### Task 1.3.1: Implement RBAC Core with Casbin

**Files:**
- Create: `backend/packages/harness/deerflow/enterprise/rbac.py`

- [ ] **Step 1: Add Casbin dependency**

```bash
cd backend/packages/harness
uv add casbin
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/enterprise/test_rbac.py
import pytest

from deerflow.enterprise.rbac import (
    RBACEngine,
    Role,
    check_permission,
    require_permission,
)


class TestRole:
    def test_role_enum(self):
        assert Role.TENANT_ADMIN.value == "tenant_admin"
        assert Role.PROJECT_MANAGER.value == "project_manager"
        assert Role.DEVELOPER.value == "developer"
        assert Role.OPERATOR.value == "operator"
        assert Role.EXTERNAL.value == "external"


class TestRBACEngine:
    def test_engine_initialization(self):
        engine = RBACEngine()
        assert engine.enforcer is not None

    def test_add_role_for_user(self):
        engine = RBACEngine()
        engine.add_role_for_user("user_123", "tenant_admin", "tenant_abc")

        assert engine.enforcer.has_role_for_user("user_123", "tenant_admin", "tenant_abc")

    def test_check_permission_allowed(self):
        engine = RBACEngine()
        engine.add_role_for_user("user_123", "developer", "tenant_abc")
        engine.add_policy("developer", "tenant_abc", "agent", "read")

        assert engine.check_permission("user_123", "tenant_abc", "agent", "read")

    def test_check_permission_denied(self):
        engine = RBACEngine()
        engine.add_role_for_user("user_123", "operator", "tenant_abc")
        # No policy granted for delete

        assert not engine.check_permission("user_123", "tenant_abc", "agent", "delete")

    def test_delete_policy(self):
        engine = RBACEngine()
        engine.add_role_for_user("user_123", "developer", "tenant_abc")
        engine.add_policy("developer", "tenant_abc", "agent", "delete")
        assert engine.check_permission("user_123", "tenant_abc", "agent", "delete")

        engine.remove_policy("developer", "tenant_abc", "agent", "delete")
        assert not engine.check_permission("user_123", "tenant_abc", "agent", "delete")


class TestPermissionHelpers:
    def test_check_permission_global_engine(self):
        # These rely on the global engine instance
        # In tests, we'd need to mock or initialize it
        pass

    def test_require_permission_raises(self):
        # Test that require_permission raises when denied
        pass
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/enterprise/test_rbac.py -v
```
Expected: ImportError

- [ ] **Step 4: Implement RBAC Core**

```python
# backend/packages/harness/deerflow/enterprise/rbac.py
"""Role-Based Access Control (RBAC) implementation using Casbin.

This module provides permission checking for enterprise multi-tenant scenarios.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

import casbin
from casbin.persist.adapters import StringAdapter

if TYPE_CHECKING:
    from deerflow.enterprise.tenancy import Tenant


class Role(str, Enum):
    """Standard RBAC roles for DeerFlow Enterprise.

    Hierarchy (high to low):
    - TENANT_ADMIN: Full tenant access
    - PROJECT_MANAGER: Project-level management
    - DEVELOPER: Create and modify agents
    - OPERATOR: Run agents and view results
    - EXTERNAL: Limited external access
    """

    TENANT_ADMIN = "tenant_admin"
    PROJECT_MANAGER = "project_manager"
    DEVELOPER = "developer"
    OPERATOR = "operator"
    EXTERNAL = "external"


# Default Casbin model configuration
DEFAULT_CASBIN_MODEL = """
[request_definition]
r = sub, dom, obj, act

[policy_definition]
p = sub, dom, obj, act

[role_definition]
g = _, _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub, r.dom) && r.dom == p.dom && r.obj == p.obj && r.act == p.act
"""


class RBACEngine:
    """Casbin-based RBAC engine for DeerFlow Enterprise.

    Supports multi-tenant policies using domain (tenant) separation.
    """

    def __init__(self, model_conf: str | None = None) -> None:
        """Initialize RBAC engine.

        Args:
            model_conf: Custom Casbin model configuration, or None for default
        """
        model = model_conf or DEFAULT_CASBIN_MODEL
        adapter = StringAdapter("")

        self.enforcer = casbin.Enforcer(
            casbin.Model(),
            adapter,
        )
        self.enforcer.load_model_from_text(model)

    def add_role_for_user(
        self,
        user_id: str,
        role: Role | str,
        tenant_id: str,
    ) -> bool:
        """Assign a role to a user within a tenant."""
        return self.enforcer.add_grouping_policy(user_id, str(role), tenant_id)

    def remove_role_for_user(
        self,
        user_id: str,
        role: Role | str,
        tenant_id: str,
    ) -> bool:
        """Remove a role from a user within a tenant."""
        return self.enforcer.remove_grouping_policy(user_id, str(role), tenant_id)

    def add_policy(
        self,
        role: Role | str,
        tenant_id: str,
        resource: str,
        action: str,
    ) -> bool:
        """Add a permission policy for a role."""
        return self.enforcer.add_policy(str(role), tenant_id, resource, action)

    def remove_policy(
        self,
        role: Role | str,
        tenant_id: str,
        resource: str,
        action: str,
    ) -> bool:
        """Remove a permission policy."""
        return self.enforcer.remove_policy(str(role), tenant_id, resource, action)

    def check_permission(
        self,
        user_id: str,
        tenant_id: str,
        resource: str,
        action: str,
    ) -> bool:
        """Check if user has permission for resource/action in tenant."""
        return self.enforcer.enforce(user_id, tenant_id, resource, action)

    def get_user_roles(self, user_id: str, tenant_id: str) -> list[str]:
        """Get all roles assigned to a user in a tenant."""
        return self.enforcer.get_roles_for_user_in_domain(user_id, tenant_id)

    def load_policies_from_csv(self, csv_path: str) -> None:
        """Load policies from CSV file."""
        # For production, use database adapter
        pass


# Global engine instance (initialized on first use)
_global_engine: RBACEngine | None = None


def get_rbac_engine() -> RBACEngine:
    """Get or create global RBAC engine."""
    global _global_engine
    if _global_engine is None:
        _global_engine = RBACEngine()
    return _global_engine


def check_permission(
    user_id: str,
    tenant_id: str,
    resource: str,
    action: str,
) -> bool:
    """Check if user has permission (uses global engine)."""
    engine = get_rbac_engine()
    return engine.check_permission(user_id, tenant_id, resource, action)


def require_permission(
    user_id: str,
    tenant_id: str,
    resource: str,
    action: str,
) -> None:
    """Check permission and raise PermissionError if denied."""
    if not check_permission(user_id, tenant_id, resource, action):
        raise PermissionError(
            f"User {user_id} does not have {action} permission on {resource} "
            f"in tenant {tenant_id}"
        )


def initialize_default_policies(engine: RBACEngine | None = None) -> None:
    """Initialize default role policies.

    This should be called during application startup.
    """
    e = engine or get_rbac_engine()

    # TENANT_ADMIN: Full access
    for action in ["create", "read", "update", "delete", "execute", "admin"]:
        for resource in ["agent", "thread", "sandbox", "skill", "memory", "audit_log"]:
            e.add_policy(Role.TENANT_ADMIN, "*", resource, action)

    # PROJECT_MANAGER: Project management
    e.add_policy(Role.PROJECT_MANAGER, "*", "agent", "create")
    e.add_policy(Role.PROJECT_MANAGER, "*", "agent", "read")
    e.add_policy(Role.PROJECT_MANAGER, "*", "agent", "update")
    e.add_policy(Role.PROJECT_MANAGER, "*", "thread", "read")
    e.add_policy(Role.PROJECT_MANAGER, "*", "sandbox", "read")

    # DEVELOPER: Agent development
    e.add_policy(Role.DEVELOPER, "*", "agent", "create")
    e.add_policy(Role.DEVELOPER, "*", "agent", "read")
    e.add_policy(Role.DEVELOPER, "*", "agent", "update")
    e.add_policy(Role.DEVELOPER, "*", "thread", "read")
    e.add_policy(Role.DEVELOPER, "*", "thread", "execute")

    # OPERATOR: Run and monitor
    e.add_policy(Role.OPERATOR, "*", "agent", "read")
    e.add_policy(Role.OPERATOR, "*", "agent", "execute")
    e.add_policy(Role.OPERATOR, "*", "thread", "read")
    e.add_policy(Role.OPERATOR, "*", "sandbox", "read")

    # EXTERNAL: Minimal access
    e.add_policy(Role.EXTERNAL, "*", "agent", "read")
    e.add_policy(Role.EXTERNAL, "*", "thread", "read")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/enterprise/test_rbac.py -v
```
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/packages/harness/deerflow/enterprise/rbac.py
mkdir -p backend/tests/enterprise
git add backend/tests/enterprise/test_rbac.py
git commit -m "feat(enterprise): implement RBAC with Casbin integration"
```

---

## Slice 1.4: Audit Event System

**Files:**
- Create: `backend/packages/harness/deerflow/enterprise/audit.py`
- Create: `backend/packages/harness/deerflow/enterprise/audit_config.py`
- Create: `backend/tests/enterprise/test_audit.py`

---

### Task 1.4.1: Implement AuditEvent and Signing

**Files:**
- Create: `backend/packages/harness/deerflow/enterprise/audit.py`

- [ ] **Step 1: Add cryptography dependency**

```bash
cd backend/packages/harness
uv add cryptography
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/enterprise/test_audit.py
import json
from datetime import datetime

import pytest

from deerflow.enterprise.audit import (
    AuditEvent,
    AuditEventType,
    AuditSigner,
    ImmutableAuditLog,
)


class TestAuditEventType:
    def test_event_types(self):
        assert AuditEventType.SANDBOX_ACQUIRED.value == "sandbox.acquired"
        assert AuditEventType.COMMAND_EXECUTED.value == "command.executed"


class TestAuditEvent:
    def test_event_creation(self):
        event = AuditEvent(
            event_type=AuditEventType.SANDBOX_ACQUIRED,
            tenant_id="tenant_123",
            thread_id="thread_456",
            sandbox_id="sandbox_789",
            payload={"cpu_limit": 2},
        )

        assert event.event_type == AuditEventType.SANDBOX_ACQUIRED
        assert event.tenant_id == "tenant_123"
        assert event.previous_hash == ""
        assert event.signature == ""

    def test_event_to_dict(self):
        event = AuditEvent(
            event_type=AuditEventType.COMMAND_EXECUTED,
            tenant_id="tenant_123",
            thread_id="thread_456",
            sandbox_id="sandbox_789",
            payload={"command": "ls -la"},
        )

        data = event.to_dict()
        assert data["event_type"] == "command.executed"
        assert data["tenant_id"] == "tenant_123"
        assert "timestamp" in data


class TestAuditSigner:
    def test_sign_and_verify(self):
        signer = AuditSigner.generate()

        message = b"test message"
        signature = signer.sign(message)

        assert signer.verify(message, signature)

    def test_verify_invalid_signature(self):
        signer = AuditSigner.generate()

        message = b"test message"
        signature = signer.sign(message)

        assert not signer.verify(b"different message", signature)


class TestImmutableAuditLog:
    @pytest.fixture
    def signer(self):
        return AuditSigner.generate()

    @pytest.fixture
    def audit_log(self, tmp_path, signer):
        log_path = tmp_path / "audit.log"
        return ImmutableAuditLog(str(log_path), signer)

    async def test_append_event(self, audit_log):
        event = AuditEvent(
            event_type=AuditEventType.SANDBOX_ACQUIRED,
            tenant_id="tenant_123",
            thread_id="thread_456",
            sandbox_id="sandbox_789",
            payload={},
        )

        await audit_log.append(event)

        assert event.signature != ""
        assert event.event_id != ""

    async def test_chain_hash_integrity(self, audit_log):
        event1 = AuditEvent(
            event_type=AuditEventType.SANDBOX_ACQUIRED,
            tenant_id="tenant_123",
            thread_id="thread_1",
            sandbox_id="sandbox_1",
            payload={},
        )
        await audit_log.append(event1)

        event2 = AuditEvent(
            event_type=AuditEventType.COMMAND_EXECUTED,
            tenant_id="tenant_123",
            thread_id="thread_1",
            sandbox_id="sandbox_1",
            payload={"cmd": "ls"},
        )
        await audit_log.append(event2)

        assert event2.previous_hash == event1.hash

    async def test_verify_chain(self, audit_log):
        for i in range(3):
            event = AuditEvent(
                event_type=AuditEventType.COMMAND_EXECUTED,
                tenant_id="tenant_123",
                thread_id="thread_1",
                sandbox_id="sandbox_1",
                payload={"index": i},
            )
            await audit_log.append(event)

        assert await audit_log.verify_chain()
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/enterprise/test_audit.py -v
```
Expected: ImportError

- [ ] **Step 4: Implement Audit System**

```python
# backend/packages/harness/deerflow/enterprise/audit.py
"""Immutable audit logging with cryptographic signatures.

Provides tamper-evident audit trails for enterprise compliance.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class AuditEventType(str, Enum):
    """Standard audit event types."""

    # Sandbox events
    SANDBOX_ACQUIRED = "sandbox.acquired"
    SANDBOX_RELEASED = "sandbox.released"
    COMMAND_EXECUTED = "command.executed"
    FILE_READ = "file.read"
    FILE_WRITTEN = "file.written"
    NETWORK_REQUEST = "network.request"
    RESOURCE_LIMIT = "resource.limit_exceeded"

    # Auth events
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    PERMISSION_DENIED = "permission.denied"

    # Agent events
    AGENT_CREATED = "agent.created"
    AGENT_EXECUTED = "agent.executed"
    SUBAGENT_SPAWNED = "subagent.spawned"


@dataclass
class AuditEvent:
    """A single audit event with cryptographic chain support.

    Attributes:
        event_id: Unique event UUID
        event_type: Type of event
        tenant_id: Tenant identifier
        thread_id: Thread/session identifier
        sandbox_id: Sandbox identifier (if applicable)
        timestamp: Event timestamp (auto-generated)
        payload: Event-specific data
        previous_hash: Hash of previous event (for chain integrity)
        signature: Ed25519 signature of this event
    """

    event_type: AuditEventType
    tenant_id: str
    thread_id: str
    sandbox_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    previous_hash: str = ""
    signature: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def to_signing_bytes(self) -> bytes:
        """Get bytes representation for signing (excludes signature)."""
        data = self.to_dict()
        data.pop("signature", None)
        return json.dumps(data, sort_keys=True).encode()

    @property
    def hash(self) -> str:
        """Calculate hash of this event."""
        return hashlib.sha256(self.to_signing_bytes()).hexdigest()


class AuditSigner:
    """Ed25519 signer for audit events."""

    def __init__(self, private_key: ed25519.Ed25519PrivateKey | None = None) -> None:
        self._private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()

    @classmethod
    def generate(cls) -> AuditSigner:
        """Generate a new signer with random keys."""
        return cls()

    @classmethod
    def from_private_key(cls, key_bytes: bytes) -> AuditSigner:
        """Load signer from private key bytes."""
        private_key = serialization.load_der_private_key(key_bytes, password=None)
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise ValueError("Invalid key type")
        return cls(private_key)

    @property
    def public_key_bytes(self) -> bytes:
        """Get public key for verification."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def sign(self, message: bytes) -> bytes:
        """Sign a message."""
        return self._private_key.sign(message)

    def verify(self, message: bytes, signature: bytes) -> bool:
        """Verify a signature."""
        try:
            self._public_key.verify(signature, message)
            return True
        except Exception:
            return False

    def sign_event(self, event: AuditEvent) -> None:
        """Sign an audit event in place."""
        message = event.to_signing_bytes()
        signature = self.sign(message)
        event.signature = signature.hex()

    def verify_event(self, event: AuditEvent) -> bool:
        """Verify an event's signature."""
        if not event.signature:
            return False
        message = event.to_signing_bytes()
        try:
            signature = bytes.fromhex(event.signature)
            return self.verify(message, signature)
        except Exception:
            return False


class ImmutableAuditLog:
    """Append-only audit log with chain verification.

    Events are chained using hashes: each event contains the hash of
    the previous event, creating a tamper-evident chain.
    """

    def __init__(
        self,
        log_path: str,
        signer: AuditSigner | None = None,
    ) -> None:
        self.log_path = Path(log_path)
        self.signer = signer or AuditSigner.generate()
        self._last_hash: str = ""
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Ensure log file exists."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    async def append(self, event: AuditEvent) -> None:
        """Append an event to the log.

        Signs the event and maintains chain integrity.
        """
        # Link to previous event
        event.previous_hash = self._last_hash

        # Sign the event
        self.signer.sign_event(event)

        # Append to file
        line = json.dumps(event.to_dict()) + "\n"
        with open(self.log_path, "a") as f:
            f.write(line)

        # Update last hash
        self._last_hash = event.hash

    async def read_all(self) -> list[AuditEvent]:
        """Read all events from log."""
        events = []
        if not self.log_path.exists():
            return events

        with open(self.log_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                event = AuditEvent(
                    event_type=AuditEventType(data["event_type"]),
                    tenant_id=data["tenant_id"],
                    thread_id=data["thread_id"],
                    sandbox_id=data.get("sandbox_id", ""),
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    payload=data.get("payload", {}),
                    event_id=data["event_id"],
                    previous_hash=data.get("previous_hash", ""),
                    signature=data.get("signature", ""),
                )
                events.append(event)

        return events

    async def verify_chain(self) -> bool:
        """Verify the integrity of the entire chain.

        Checks:
        1. Each event's signature
        2. Hash chain continuity
        """
        events = await self.read_all()

        previous_hash = ""
        for event in events:
            # Verify signature
            if not self.signer.verify_event(event):
                return False

            # Verify chain continuity
            if event.previous_hash != previous_hash:
                return False

            # Verify hash matches
            if event.hash != hashlib.sha256(
                event.to_signing_bytes()
            ).hexdigest():
                return False

            previous_hash = event.hash

        return True

    def get_events_for_tenant(
        self,
        tenant_id: str,
        event_type: AuditEventType | None = None,
    ) -> list[AuditEvent]:
        """Filter events by tenant and optionally by type."""
        # For production, use indexed database queries
        pass
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/enterprise/test_audit.py -v
```
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/packages/harness/deerflow/enterprise/audit.py
mkdir -p backend/tests/enterprise
git add backend/tests/enterprise/test_audit.py
git commit -m "feat(enterprise): implement immutable audit log with Ed25519 signatures"
```

---

## Integration Tasks

### Task 1.5.1: Add Enterprise Config to AppConfig

**Files:**
- Modify: `backend/packages/harness/deerflow/config/app_config.py`

- [ ] **Step 1: Add enterprise imports and config fields**

```python
# Add to backend/packages/harness/deerflow/config/app_config.py

from deerflow.enterprise.tenant_config import TenancyConfig
from deerflow.enterprise.rbac_config import RBACConfig
from deerflow.enterprise.audit_config import AuditConfig

# Add to AppConfig class:
class AppConfig(BaseSettings):
    # ... existing fields ...

    # Enterprise configuration
    tenancy: TenancyConfig = Field(default_factory=TenancyConfig)
    rbac: RBACConfig = Field(default_factory=RBACConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
```

- [ ] **Step 2: Create RBAC Config**

```python
# backend/packages/harness/deerflow/enterprise/rbac_config.py
from pydantic import BaseModel, Field


class RBACConfig(BaseModel):
    """RBAC configuration."""

    enabled: bool = Field(default=False, description="Enable RBAC")
    model_config: str = Field(default="", description="Custom Casbin model")
    policy_file: str | None = Field(default=None, description="Policy CSV file path")
```

- [ ] **Step 3: Create Audit Config**

```python
# backend/packages/harness/deerflow/enterprise/audit_config.py
from pydantic import BaseModel, Field


class AuditConfig(BaseModel):
    """Audit logging configuration."""

    enabled: bool = Field(default=False, description="Enable audit logging")
    log_path: str = Field(
        default=".deer-flow/audit.log",
        description="Audit log file path",
    )
    private_key_path: str | None = Field(
        default=None,
        description="Path to Ed25519 private key (generated if not exists)",
    )
    include_payload: bool = Field(
        default=True,
        description="Include event payload in logs",
    )
```

- [ ] **Step 4: Update config.example.yaml**

```yaml
# Add to config.example.yaml

# Enterprise configuration
enterprise:
  tenancy:
    enabled: false
    default_isolation_mode: relaxed
    tenants:
      - id: default
        name: Default Tenant
        plan: pro
        isolation_mode: relaxed
    header_name: X-Tenant-ID

  rbac:
    enabled: false
    policy_file: null

  audit:
    enabled: false
    log_path: .deer-flow/audit.log
    include_payload: true
```

- [ ] **Step 5: Commit**

```bash
git add backend/packages/harness/deerflow/config/app_config.py
git add backend/packages/harness/deerflow/enterprise/rbac_config.py
git add backend/packages/harness/deerflow/enterprise/audit_config.py
git add config.example.yaml
git commit -m "feat(enterprise): integrate enterprise config into AppConfig"
```

---

## Slice 1.1-1.4 Acceptance Criteria

- [ ] All new modules have >80% test coverage
- [ ] TenantContext correctly isolates tenant data across async boundaries
- [ ] Namespace functions generate correct tenant-scoped names
- [ ] RBAC correctly enforces role permissions
- [ ] Audit events are signed and chain verification passes
- [ ] Configuration validates correctly
- [ ] No regressions in existing tests: `make test` passes

---

## Spec Coverage Checklist

| Spec Requirement | Implementation Task | Status |
|------------------|---------------------|--------|
| TenantContext thread storage | Task 1.1.2 | ✅ |
| Tenant identification middleware | Task 1.1.4 | ✅ |
| Namespace management | Task 1.2.1 | ✅ |
| PostgreSQL RLS policies | (Phase 2 - persistence layer) | ⏳ |
| RBAC role model | Task 1.3.1 | ✅ |
| RBAC middleware | Task 1.3.2 | ⏳ |
| Audit event system | Task 1.4.1 | ✅ |
| Ed25519 signing | Task 1.4.1 | ✅ |
| Config integration | Task 1.5.1 | ✅ |

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-22-enterprise-phase1.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach would you like to use for implementing this plan?
