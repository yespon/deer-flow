"""Brand and Compliance configuration models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BrandConfig(BaseModel):
    """Configuration for brand compliance.

    Example:
        ```yaml
        brand:
          enabled: true
          brand_name: "Acme Corp"
          forbidden_words:
            - "competitor"
            - "badword"
          required_disclaimers:
            - "Terms and conditions apply"
          tone_guidelines: "Professional and friendly"
        ```
    """

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=False, description="Enable brand compliance checking")
    brand_name: str = Field(default="", description="Official brand name")
    forbidden_words: list[str] = Field(
        default_factory=list,
        description="List of forbidden words/phrases",
    )
    required_disclaimers: list[str] = Field(
        default_factory=list,
        description="Disclaimers required in marketing content",
    )
    tone_guidelines: str | None = Field(
        default=None,
        description="Description of acceptable tone and style",
    )
    visual_standards: dict[str, Any] = Field(
        default_factory=dict,
        description="Visual content requirements",
    )


class ComplianceRuleConfig(BaseModel):
    """Configuration for a single compliance rule."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(description="Rule identifier")
    rule_type: str = Field(description="Type of rule: sensitive_words, regex, etc.")
    severity: str = Field(default="high", description="Violation severity: block, high, medium, low")
    words: list[str] = Field(default_factory=list, description="Words to check (for sensitive_words type)")
    pattern: str | None = Field(default=None, description="Regex pattern (for regex type)")


class ComplianceConfig(BaseModel):
    """Configuration for content compliance filtering.

    Example:
        ```yaml
        compliance:
          enabled: true
          sensitive_words:
            - "secret"
            - "confidential"
          policy_rules:
            - name: pii_detection
              rule_type: sensitive_words
              severity: block
              words:
                - "ssn"
                - "password"
          auto_review: true
        ```
    """

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=False, description="Enable compliance filtering")
    sensitive_words: list[str] = Field(
        default_factory=list,
        description="Global list of sensitive words to check",
    )
    policy_rules: list[ComplianceRuleConfig] = Field(
        default_factory=list,
        description="Configured compliance policy rules",
    )
    auto_review: bool = Field(
        default=True,
        description="Automatically review media content",
    )
