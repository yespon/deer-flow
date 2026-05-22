"""Tests for DeerFlow Enterprise tenancy module."""

from contextvars import copy_context

import pytest

from deerflow.enterprise.tenancy import (
    AUTO,
    Tenant,
    get_current_tenant,
    require_current_tenant,
    reset_current_tenant,
    resolve_tenant_id,
    set_current_tenant,
    tenant_context,
)


class TestTenant:
    """Test Tenant dataclass."""

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

    def test_tenant_defaults(self):
        tenant = Tenant(id="tenant_abc", name="Test")
        assert tenant.plan == "pro"
        assert tenant.isolation_mode == "relaxed"

    def test_tenant_namespace_prefix(self):
        tenant = Tenant(id="tenant_abc", name="Test")
        assert tenant.namespace_prefix == "tenant_abc"

    def test_tenant_str(self):
        tenant = Tenant(id="tenant_123", name="Test Corp")
        assert str(tenant) == "Tenant(tenant_123, Test Corp)"

    def test_tenant_frozen(self):
        tenant = Tenant(id="tenant_123", name="Test")
        with pytest.raises(AttributeError):
            tenant.id = "new_id"


class TestTenantContext:
    """Test tenant context management."""

    def test_get_current_tenant_returns_none_when_unset(self):
        # Ensure context is clear (each test runs in isolated context)
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
        with pytest.raises(RuntimeError, match="operation requires tenant context"):
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
    """Test tenant_context context manager."""

    def test_tenant_context_sets_and_resets(self):
        # Run in isolated context to avoid interference
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

    def test_tenant_context_with_string_and_params(self):
        with tenant_context(
            "tenant_custom",
            name="Custom Tenant",
            plan="enterprise",
            isolation_mode="strict",
        ) as tenant:
            assert tenant.id == "tenant_custom"
            assert tenant.name == "Custom Tenant"
            assert tenant.plan == "enterprise"
            assert tenant.isolation_mode == "strict"


class TestResolveTenantId:
    """Test resolve_tenant_id helper."""

    def test_resolve_with_auto_raises_when_unset(self):
        with pytest.raises(RuntimeError, match="tenant_id=AUTO"):
            resolve_tenant_id(AUTO)

    def test_resolve_with_auto_returns_tenant_id_when_set(self):
        tenant = Tenant(id="tenant_123", name="Test")
        token = set_current_tenant(tenant)
        try:
            result = resolve_tenant_id(AUTO)
            assert result == "tenant_123"
        finally:
            reset_current_tenant(token)

    def test_resolve_with_explicit_string(self):
        result = resolve_tenant_id("tenant_explicit")
        assert result == "tenant_explicit"

    def test_resolve_with_none(self):
        result = resolve_tenant_id(None)
        assert result is None
