"""Compliance Filter for enterprise content compliance.

Provides content filtering capabilities including:
- Sensitive word detection
- Policy rule enforcement
- Content type-specific checks
- Optional content sanitization
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class ContentType(Enum):
    """Types of content that can be filtered."""

    TEXT = "text"
    CODE = "code"
    MARKDOWN = "markdown"
    HTML = "html"


@dataclass
class Violation:
    """A compliance violation.

    Attributes:
        rule: Name of the rule that was violated
        severity: Violation severity (block, high, medium, low)
        message: Human-readable description
        details: Additional context about the violation
    """

    rule: str
    severity: str  # block, high, medium, low
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class FilterResult:
    """Result of content filtering.

    Attributes:
        blocked: True if content should be blocked
        violations: List of detected violations
        sanitized_content: Optional cleaned version of content
    """

    blocked: bool
    violations: list[Violation]
    sanitized_content: str | None = None


class PolicyRule(ABC):
    """Abstract base class for compliance policy rules."""

    def __init__(self, name: str, severity: str = "high") -> None:
        self.name = name
        self.severity = severity

    @abstractmethod
    async def check(self, content: str, content_type: ContentType) -> Violation | None:
        """Check content against this rule.

        Args:
            content: Content to check
            content_type: Type of content

        Returns:
            Violation if rule is violated, None otherwise
        """
        ...


class SensitiveWordRule(PolicyRule):
    """Rule that checks for sensitive words."""

    def __init__(
        self,
        name: str,
        words: list[str],
        severity: str = "high",
    ) -> None:
        super().__init__(name, severity)
        self.words = [w.lower() for w in words]

    async def check(self, content: str, content_type: ContentType) -> Violation | None:
        """Check for sensitive words in content."""
        content_lower = content.lower()

        for word in self.words:
            # Use word boundary matching
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, content_lower):
                return Violation(
                    rule=self.name,
                    severity=self.severity,
                    message=f"Content contains sensitive word: '{word}'",
                    details={"matched_word": word},
                )

        return None


class ComplianceRule(Protocol):
    """Protocol for compliance rules."""

    name: str
    severity: str

    async def check(self, content: str, content_type: ContentType) -> Violation | None:
        """Check content against this rule."""
        ...


class ComplianceFilter:
    """Filter for enterprise content compliance.

    Checks content against sensitive word lists and policy rules,
    optionally providing sanitized versions.

    Example:
        ```python
        filter = ComplianceFilter(
            sensitive_words=["secret", "confidential"],
            policy_rules=[
                SensitiveWordRule("pii", ["ssn", "password"], severity="block"),
            ],
        )

        result = await filter.filter_output(
            "My password is 12345",
            ContentType.TEXT,
        )

        if result.blocked:
            print("Content blocked due to violations")
            for v in result.violations:
                print(f"  - {v.message}")
        ```
    """

    def __init__(
        self,
        sensitive_words: list[str] | None = None,
        policy_rules: list[PolicyRule] | None = None,
        auto_review: bool = True,
    ) -> None:
        self.sensitive_words = [w.lower() for w in (sensitive_words or [])]
        self.policy_rules = policy_rules or []
        self.auto_review = auto_review

    async def filter_output(
        self,
        content: str,
        content_type: ContentType,
    ) -> FilterResult:
        """Filter content for compliance violations.

        Args:
            content: Content to filter
            content_type: Type of content

        Returns:
            FilterResult with block status and any violations
        """
        violations: list[Violation] = []

        # Check sensitive words
        violations.extend(await self._check_sensitive_words(content))

        # Check policy rules
        for rule in self.policy_rules:
            violation = await rule.check(content, content_type)
            if violation:
                violations.append(violation)

        # Media review (placeholder for multi-modal content)
        if self.auto_review and self._has_media(content):
            media_violations = await self._review_media(content, content_type)
            violations.extend(media_violations)

        # Block if any violations have block severity
        blocked = any(v.severity == "block" for v in violations)

        # Generate sanitized version if violations found
        sanitized = None
        if violations and not blocked:
            sanitized = self._sanitize_content(content, violations)

        return FilterResult(
            blocked=blocked,
            violations=violations,
            sanitized_content=sanitized,
        )

    async def _check_sensitive_words(self, content: str) -> list[Violation]:
        """Check content against sensitive word list."""
        violations = []
        content_lower = content.lower()

        for word in self.sensitive_words:
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, content_lower):
                violations.append(
                    Violation(
                        rule="sensitive_word",
                        severity="high",
                        message=f"Content contains sensitive word: '{word}'",
                        details={"matched_word": word},
                    )
                )

        return violations

    def _has_media(self, content: str) -> bool:
        """Detect if content contains media elements."""
        # Markdown images
        if re.search(r'!\[.*?\]\(.*?\)', content):
            return True

        # HTML images/media
        if re.search(r'<(img|video|audio|iframe)\s', content, re.IGNORECASE):
            return True

        # URLs with media extensions
        media_exts = r'\.(png|jpg|jpeg|gif|svg|webp|mp4|mp3|mov)(\?|$|\s)'
        if re.search(media_exts, content, re.IGNORECASE):
            return True

        return False

    async def _review_media(
        self,
        content: str,
        content_type: ContentType,
    ) -> list[Violation]:
        """Review media content for compliance.

        Note: This is a placeholder implementation. In production, this would
        use multi-modal AI models to analyze images/videos for compliance.
        """
        # Placeholder: just note that media was detected
        # Real implementation would analyze the actual media files
        return []

    def _sanitize_content(self, content: str, violations: list[Violation]) -> str:
        """Create sanitized version of content.

        Replaces sensitive words with placeholders.
        """
        sanitized = content

        for v in violations:
            matched_word = v.details.get("matched_word")
            if matched_word:
                # Replace with asterisks
                replacement = "*" * len(matched_word)
                sanitized = re.sub(
                    r'\b' + re.escape(matched_word) + r'\b',
                    replacement,
                    sanitized,
                    flags=re.IGNORECASE,
                )

        return sanitized

    async def filter_batch(
        self,
        items: list[tuple[str, ContentType]],
    ) -> list[FilterResult]:
        """Filter multiple content items.

        Args:
            items: List of (content, content_type) tuples

        Returns:
            List of filter results (same order as input)
        """
        return [await self.filter_output(c, t) for c, t in items]
