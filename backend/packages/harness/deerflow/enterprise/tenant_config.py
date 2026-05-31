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
