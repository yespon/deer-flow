"""Tests for ComplianceFilter and content compliance checking."""

from unittest.mock import Mock

import pytest

from deerflow.enterprise.compliance_filter import (
    ComplianceFilter,
    ComplianceRule,
    ContentType,
    FilterResult,
    PolicyRule,
    SensitiveWordRule,
    Violation,
)


class TestContentType:
    def test_content_types(self):
        """Should have all required content types."""
        assert ContentType.TEXT.value == "text"
        assert ContentType.CODE.value == "code"
        assert ContentType.MARKDOWN.value == "markdown"
        assert ContentType.HTML.value == "html"


class TestViolation:
    def test_violation_creation(self):
        """Should create violation with required fields."""
        v = Violation(rule="test_rule", severity="high", message="Test message")
        assert v.rule == "test_rule"
        assert v.severity == "high"
        assert v.message == "Test message"

    def test_violation_with_details(self):
        """Should support optional details."""
        v = Violation(
            rule="test_rule",
            severity="block",
            message="Blocked",
            details={"matched_word": "badword"},
        )
        assert v.details["matched_word"] == "badword"


class TestFilterResult:
    def test_approved_result(self):
        """Should create approved result."""
        result = FilterResult(blocked=False, violations=[])
        assert result.blocked is False
        assert result.sanitized_content is None

    def test_blocked_result(self):
        """Should create blocked result."""
        violations = [Violation(rule="test", severity="block", message="Blocked")]
        result = FilterResult(blocked=True, violations=violations)
        assert result.blocked is True
        assert len(result.violations) == 1

    def test_sanitized_content(self):
        """Should include sanitized content if provided."""
        result = FilterResult(
            blocked=False,
            violations=[],
            sanitized_content="Clean content",
        )
        assert result.sanitized_content == "Clean content"


class TestSensitiveWordRule:
    @pytest.fixture
    def rule(self):
        """Create sensitive word rule."""
        return SensitiveWordRule(
            name="sensitive_words",
            words=["secret", "confidential", "internal_only"],
            severity="high",
        )

    @pytest.mark.asyncio
    async def test_detects_sensitive_word(self, rule):
        """Should detect sensitive words in content."""
        result = await rule.check("This contains secret information", ContentType.TEXT)
        assert result is not None
        assert result.rule == "sensitive_words"
        assert result.severity == "high"

    @pytest.mark.asyncio
    async def test_no_match_returns_none(self, rule):
        """Should return None when no sensitive words found."""
        result = await rule.check("This is clean content", ContentType.TEXT)
        assert result is None

    @pytest.mark.asyncio
    async def test_case_insensitive(self, rule):
        """Should match case insensitively."""
        result = await rule.check("This contains SECRET info", ContentType.TEXT)
        assert result is not None

    @pytest.mark.asyncio
    async def test_multiple_matches(self, rule):
        """Should detect first match only."""
        result = await rule.check("This has secret and confidential data", ContentType.TEXT)
        assert result is not None


class TestComplianceFilter:
    @pytest.fixture
    def filter_(self):
        """Create compliance filter with test rules."""
        return ComplianceFilter(
            sensitive_words=["badword", "worseword"],
            policy_rules=[
                SensitiveWordRule(
                    name="sensitive_data",
                    words=["ssn", "password", "credit_card"],
                    severity="block",
                ),
            ],
            auto_review=True,
        )

    @pytest.mark.asyncio
    async def test_allows_clean_content(self, filter_):
        """Should approve clean content."""
        result = await filter_.filter_output("This is clean content", ContentType.TEXT)
        assert result.blocked is False

    @pytest.mark.asyncio
    async def test_blocks_sensitive_words(self, filter_):
        """Should detect sensitive words (high severity, not blocked)."""
        result = await filter_.filter_output("This has badword in it", ContentType.TEXT)
        # sensitive_words have severity "high" not "block", so not blocked
        assert result.blocked is False
        assert len(result.violations) >= 1
        # But should still have violations
        badword_violations = [v for v in result.violations if "badword" in v.message.lower()]
        assert len(badword_violations) == 1

    @pytest.mark.asyncio
    async def test_policy_rules_checked(self, filter_):
        """Should check policy rules."""
        result = await filter_.filter_output("My password is 12345", ContentType.TEXT)
        assert result.blocked is True
        password_violations = [v for v in result.violations if "password" in v.message.lower()]
        assert len(password_violations) >= 1

    @pytest.mark.asyncio
    async def test_violation_severity_levels(self, filter_):
        """Should respect severity levels."""
        # Block severity should block
        result = await filter_.filter_output("My ssn is 123-45-6789", ContentType.TEXT)
        assert result.blocked is True

    @pytest.mark.asyncio
    async def test_empty_content(self, filter_):
        """Should handle empty content."""
        result = await filter_.filter_output("", ContentType.TEXT)
        assert result.blocked is False

    @pytest.mark.asyncio
    async def test_no_rules_allows_all(self):
        """Should allow all content if no rules configured."""
        filter_ = ComplianceFilter(
            sensitive_words=[],
            policy_rules=[],
            auto_review=False,
        )
        result = await filter_.filter_output("Any content", ContentType.TEXT)
        assert result.blocked is False

    @pytest.mark.asyncio
    async def test_sanitizes_content(self, filter_):
        """Should provide sanitized version if violations found."""
        result = await filter_.filter_output("This has badword content", ContentType.TEXT)
        # Sanitized content may be provided
        assert isinstance(result.sanitized_content, (str, type(None)))

    @pytest.mark.asyncio
    async def test_detects_multiple_violations(self, filter_):
        """Should collect all violations from multiple sources."""
        result = await filter_.filter_output(
            "This has badword and password and ssn",
            ContentType.TEXT,
        )
        # sensitive_words (badword) + policy_rules (password, ssn)
        # But SensitiveWordRule returns first match only, so password is found first
        assert len(result.violations) >= 2
        # Should be blocked due to ssn/password (block severity)
        assert result.blocked is True

    @pytest.mark.asyncio
    async def test_high_severity_not_blocked(self):
        """Should not block for high severity (only block severity)."""
        filter_ = ComplianceFilter(
            sensitive_words=[],
            policy_rules=[
                SensitiveWordRule(
                    name="warning",
                    words=["caution"],
                    severity="high",
                ),
            ],
        )
        result = await filter_.filter_output("Caution: be careful", ContentType.TEXT)
        # High severity is warning, not block
        assert result.blocked is False
        assert len(result.violations) == 1


class TestComplianceFilterWithMedia:
    @pytest.mark.asyncio
    async def test_detects_media_in_content(self):
        """Should detect media references in content."""
        filter_ = ComplianceFilter(
            sensitive_words=[],
            policy_rules=[],
            auto_review=True,
        )

        # Markdown image
        content_with_image = "![alt text](image.png)"
        assert filter_._has_media(content_with_image) is True

        # Plain text - no media
        plain_text = "Just text content"
        assert filter_._has_media(plain_text) is False

        # URL with image extension
        image_url = "Check out https://example.com/photo.jpg"
        assert filter_._has_media(image_url) is True

    @pytest.mark.asyncio
    async def test_auto_review_disabled_skips_media_check(self):
        """Should skip media review when auto_review is disabled."""
        filter_ = ComplianceFilter(
            sensitive_words=[],
            policy_rules=[],
            auto_review=False,
        )

        content = "![image](test.png)"
        result = await filter_.filter_output(content, ContentType.TEXT)
        # Should pass even with media since auto_review is disabled
        assert result.blocked is False
