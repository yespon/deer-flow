"""Audit configuration schema."""

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
