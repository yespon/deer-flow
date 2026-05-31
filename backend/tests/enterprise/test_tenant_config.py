"""Tests for DeerFlow Enterprise tenant configuration."""

import pytest
from pydantic import ValidationError

from deerflow.enterprise.tenant_config import TenancyConfig, TenantConfig


class TestTenantConfig:
    """Test TenantConfig model."""

    def test_default_tenant_config(self):
        config = TenantConfig()
        assert config.id == "default"
        assert config.name == "Default Tenant"
        assert config.plan == "pro"
        assert config.isolation_mode == "relaxed"
        assert config.max_agents == 10
        assert config.max_storage_gb == 100

    def test_tenant_config_with_values(self):
        config = TenantConfig(
            id="tenant_123",
            name="Acme Corp",
            plan="enterprise",
            isolation_mode="strict",
            max_agents=50,
            max_storage_gb=500,
        )
        assert config.id == "tenant_123"
        assert config.name == "Acme Corp"
        assert config.plan == "enterprise"
        assert config.isolation_mode == "strict"
        assert config.max_agents == 50
        assert config.max_storage_gb == 500

    def test_invalid_isolation_mode(self):
        with pytest.raises(ValidationError):
            TenantConfig(isolation_mode="invalid")

    def test_invalid_plan(self):
        with pytest.raises(ValidationError):
            TenantConfig(plan="premium")

    def test_empty_id_raises(self):
        with pytest.raises(ValidationError):
            TenantConfig(id="")

    def test_id_with_spaces_raises(self):
        with pytest.raises(ValidationError):
            TenantConfig(id="tenant with spaces")


class TestTenancyConfig:
    """Test TenancyConfig model."""

    def test_default_tenancy_config(self):
        config = TenancyConfig()
        assert config.enabled is False
        assert config.default_isolation_mode == "relaxed"
        assert len(config.tenants) == 1
        assert config.tenants[0].id == "default"
        assert config.header_name == "X-Tenant-ID"

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
        assert default.name == "Default"

    def test_default_tenant_fallback_to_first(self):
        config = TenancyConfig(
            tenants=[
                TenantConfig(id="first", name="First"),
            ]
        )
        default = config.default_tenant
        assert default.id == "first"
