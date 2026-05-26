"""Quota configuration models for enterprise multi-tenancy."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TenantQuota(BaseModel):
    """Resource quota limits for a single tenant."""

    max_concurrent_sandboxes: int = Field(
        default=5,
        ge=0,
        description="Maximum number of concurrent sandboxes allowed",
    )
    max_cpu_cores: float = Field(
        default=4.0,
        ge=0.0,
        description="Maximum CPU cores allowed",
    )
    max_memory_gb: float = Field(
        default=8.0,
        ge=0.0,
        description="Maximum memory in GB allowed",
    )
    max_storage_gb: float = Field(
        default=100.0,
        ge=0.0,
        description="Maximum storage in GB allowed",
    )
    max_network_egress_mb: int = Field(
        default=1000,
        ge=0,
        description="Maximum network egress in MB allowed",
    )


class QuotaConfig(BaseModel):
    """Top-level quota configuration."""

    enabled: bool = Field(
        default=False,
        description="Enable quota management features",
    )
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis URL for quota state storage",
    )
    default_quotas: TenantQuota = Field(
        default_factory=TenantQuota,
        description="Default quotas for new tenants",
    )
    enforcement_mode: Literal["hard", "soft"] = Field(
        default="hard",
        description="Quota enforcement mode: hard (strict) or soft (warning)",
    )

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate that redis_url starts with a valid Redis scheme."""
        valid_schemes = ("redis://", "rediss://", "unix://")
        if not v.startswith(valid_schemes):
            raise ValueError(
                f"redis_url must start with one of {valid_schemes}"
            )
        return v
