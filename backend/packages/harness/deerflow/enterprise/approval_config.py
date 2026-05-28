"""Configuration models for Human-in-Loop approval workflow."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ApprovalNotificationsConfig(BaseModel):
    """Configuration for approval notifications.

    Attributes:
        webhook_url: Webhook URL for approval notifications
        channels: List of notification channels (webhook, email, slack)
    """

    webhook_url: str | None = Field(default=None)
    channels: list[str] = Field(default_factory=lambda: ["webhook"])


class ApprovalConfig(BaseModel):
    """Top-level approval workflow configuration.

    Attributes:
        enabled: Whether approval workflow is enabled
        default_timeout_hours: Default timeout for approval requests
        storage_path: Path for storing suspended execution states
        notifications: Notification configuration
    """

    enabled: bool = Field(default=False)
    default_timeout_hours: int = Field(default=24, ge=1)
    storage_path: str = Field(default=".deer-flow/approvals")
    notifications: ApprovalNotificationsConfig = Field(
        default_factory=ApprovalNotificationsConfig
    )
