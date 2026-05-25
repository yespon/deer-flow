"""RBAC configuration schema."""

from pydantic import BaseModel, Field


class RBACConfig(BaseModel):
    """RBAC configuration."""

    enabled: bool = Field(default=False, description="Enable RBAC")
    model_config: str = Field(default="", description="Custom Casbin model")
    policy_file: str | None = Field(default=None, description="Policy CSV file path")
