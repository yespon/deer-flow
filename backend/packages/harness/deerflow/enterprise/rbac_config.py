"""RBAC configuration schema."""

from pydantic import BaseModel, Field


class RBACConfig(BaseModel):
    """RBAC configuration."""

    enabled: bool = Field(default=False, description="Enable RBAC")
    casbin_model: str = Field(default="", description="Custom Casbin model config")
    policy_file: str | None = Field(default=None, description="Policy CSV file path")
