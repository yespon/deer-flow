"""Tests for DeerFlow Enterprise tenant middleware."""

from unittest.mock import Mock

import pytest

from deerflow.agents.middlewares.tenant_middleware import (
    TenantIdentificationMiddleware,
    TenantResolver,
)
from deerflow.enterprise.tenant_config import TenancyConfig


class TestTenantResolver:
    """Test TenantResolver."""

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
    """Test TenantIdentificationMiddleware."""

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
        # Note: Context is reset after middleware, so we check it was set during execution
        assert hasattr(request, "tenant")
        assert request.tenant.id == "test_tenant"

    def test_middleware_disabled_skips_resolution(self):
        config = TenancyConfig(enabled=False)
        middleware = TenantIdentificationMiddleware(config)

        request = Mock(spec=["headers"])
        request.headers = {"X-Tenant-ID": "test"}

        next_middleware = Mock(return_value="result")
        result = middleware(request, next_middleware)

        assert result == "result"
        assert not hasattr(request, "tenant")
