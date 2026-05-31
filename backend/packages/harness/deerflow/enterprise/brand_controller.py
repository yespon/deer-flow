"""Brand Controller for enterprise brand compliance.

Ensures all AI-generated content adheres to brand guidelines including:
- Forbidden words and phrases
- Required disclaimers
- Tone and style guidelines
- Visual content standards
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BrandGuidelines:
    """Brand guidelines configuration.

    Attributes:
        brand_name: Official brand name
        forbidden_words: List of words/phrases that must not be used
        required_disclaimers: Disclaimers that must be present in certain contexts
        tone_guidelines: Description of acceptable tone and style
        visual_standards: Dict of visual requirements (min_width, min_height, etc.)
    """

    brand_name: str
    forbidden_words: list[str] = field(default_factory=list)
    required_disclaimers: list[str] = field(default_factory=list)
    tone_guidelines: str | None = None
    visual_standards: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrandIssue:
    """A brand compliance issue.

    Attributes:
        type: Issue category (forbidden_word, missing_disclaimer, tone_violation, etc.)
        severity: Issue severity (block, high, medium, warning)
        message: Human-readable description of the issue
        details: Additional context about the issue
    """

    type: str
    severity: str  # block, high, medium, warning
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrandReviewResult:
    """Result of brand compliance review.

    Attributes:
        approved: True if content passes all checks
        issues: List of identified issues
        sanitized_content: Content with issues corrected (if auto-fix applied)
    """

    approved: bool
    issues: list[BrandIssue]
    sanitized_content: str | None = None


class BrandController:
    """Controller for brand compliance checking.

    Reviews content against brand guidelines and identifies violations.

    Example:
        ```python
        guidelines = BrandGuidelines(
            brand_name="Acme Corp",
            forbidden_words=["badword", "competitor"],
            required_disclaimers=["Terms apply"],
        )

        controller = BrandController(guidelines)
        result = await controller.review_content("Welcome to Acme Corp!")

        if not result.approved:
            for issue in result.issues:
                print(f"{issue.severity}: {issue.message}")
        ```
    """

    def __init__(self, guidelines: BrandGuidelines) -> None:
        self.guidelines = guidelines

    async def review_content(self, content: str) -> BrandReviewResult:
        """Review content against brand guidelines.

        Args:
            content: The content to review

        Returns:
            BrandReviewResult with approval status and any issues
        """
        issues: list[BrandIssue] = []

        # Check forbidden words
        issues.extend(self._check_forbidden_words(content))

        # Check required disclaimers
        issues.extend(self._check_required_disclaimers(content))

        # Check visual content if present
        if self.has_visual_content(content):
            issues.extend(await self._check_visual_standards(content))

        # Content is approved if no blocking issues
        approved = not any(i.severity == "block" for i in issues)

        return BrandReviewResult(
            approved=approved,
            issues=issues,
        )

    def _check_forbidden_words(self, content: str) -> list[BrandIssue]:
        """Check for forbidden words in content."""
        issues = []
        content_lower = content.lower()

        for word in self.guidelines.forbidden_words:
            # Match whole words using word boundaries
            pattern = r"\b" + re.escape(word.lower()) + r"\b"
            if re.search(pattern, content_lower):
                issues.append(
                    BrandIssue(
                        type="forbidden_word",
                        severity="block",
                        message=f"Content contains forbidden word: '{word}'",
                        details={"word": word, "context": self._get_context(content, word)},
                    )
                )

        return issues

    def _check_required_disclaimers(self, content: str) -> list[BrandIssue]:
        """Check for required disclaimers in content."""
        issues = []
        content_lower = content.lower()

        for disclaimer in self.guidelines.required_disclaimers:
            if disclaimer.lower() not in content_lower:
                issues.append(
                    BrandIssue(
                        type="missing_disclaimer",
                        severity="warning",
                        message=f"Content missing required disclaimer: '{disclaimer}'",
                        details={"disclaimer": disclaimer},
                    )
                )

        return issues

    async def _check_visual_standards(self, content: str) -> list[BrandIssue]:
        """Check visual content against brand standards.

        Note: This is a placeholder implementation. In production, this would
        analyze actual image files for compliance with visual standards.
        """
        issues = []
        standards = self.guidelines.visual_standards

        if not standards:
            return issues

        # Detect image references in content
        image_refs = self._extract_image_references(content)

        for ref in image_refs:
            # In production, this would load and analyze the actual image
            # For now, just note that visual content was detected
            if standards.get("min_width") or standards.get("min_height"):
                issues.append(
                    BrandIssue(
                        type="visual_content_detected",
                        severity="warning",
                        message=f"Visual content detected: {ref}. Ensure it meets brand standards.",
                        details={
                            "reference": ref,
                            "required_standards": standards,
                        },
                    )
                )

        return issues

    def has_visual_content(self, content: str) -> bool:
        """Detect if content contains visual elements (images, etc.)."""
        # Check for markdown images
        if re.search(r"!\[.*?\]\(.*?\)", content):
            return True

        # Check for HTML images
        if re.search(r"<img\s", content, re.IGNORECASE):
            return True

        # Check for image URLs (common extensions)
        image_extensions = r"\.(png|jpg|jpeg|gif|svg|webp)(\?|$|\s)"
        if re.search(image_extensions, content, re.IGNORECASE):
            return True

        return False

    def _extract_image_references(self, content: str) -> list[str]:
        """Extract image references from content."""
        refs = []

        # Markdown images
        markdown_pattern = r"!\[.*?\]\((.*?)\)"
        refs.extend(re.findall(markdown_pattern, content))

        # HTML images
        html_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
        refs.extend(re.findall(html_pattern, content, re.IGNORECASE))

        return refs

    def _get_context(self, content: str, word: str, context_chars: int = 30) -> str:
        """Extract context around a word match."""
        content_lower = content.lower()
        word_lower = word.lower()

        # Find position (use first occurrence)
        pos = content_lower.find(word_lower)
        if pos == -1:
            return ""

        # Calculate context window
        start = max(0, pos - context_chars)
        end = min(len(content), pos + len(word) + context_chars)

        context = content[start:end]
        return context.strip()

    async def review_batch(self, contents: list[str]) -> list[BrandReviewResult]:
        """Review multiple content items.

        Args:
            contents: List of content strings to review

        Returns:
            List of review results (same order as input)
        """
        return [await self.review_content(c) for c in contents]
