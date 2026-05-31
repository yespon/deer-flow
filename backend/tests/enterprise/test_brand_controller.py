"""Tests for BrandController and brand compliance."""

import pytest

from deerflow.enterprise.brand_controller import (
    BrandController,
    BrandGuidelines,
    BrandIssue,
    BrandReviewResult,
)


class TestBrandGuidelines:
    def test_guidelines_creation(self):
        """Should create guidelines with all fields."""
        guidelines = BrandGuidelines(
            brand_name="Acme Corp",
            forbidden_words=["bad", "worse"],
            required_disclaimers=["Terms apply"],
            tone_guidelines="Professional and friendly",
            visual_standards={"min_width": 100, "min_height": 100},
        )
        assert guidelines.brand_name == "Acme Corp"
        assert "bad" in guidelines.forbidden_words
        assert "Terms apply" in guidelines.required_disclaimers

    def test_guidelines_defaults(self):
        """Should use sensible defaults."""
        guidelines = BrandGuidelines(brand_name="Test")
        assert guidelines.forbidden_words == []
        assert guidelines.required_disclaimers == []
        assert guidelines.tone_guidelines is None
        assert guidelines.visual_standards == {}


class TestBrandReviewResult:
    def test_approved_result(self):
        """Should create approved result."""
        result = BrandReviewResult(approved=True, issues=[])
        assert result.approved is True
        assert len(result.issues) == 0

    def test_rejected_result(self):
        """Should create rejected result with issues."""
        issues = [
            BrandIssue(type="forbidden_word", severity="high", message="Bad word found"),
        ]
        result = BrandReviewResult(approved=False, issues=issues)
        assert result.approved is False
        assert len(result.issues) == 1


class TestBrandController:
    @pytest.fixture
    def guidelines(self):
        """Create brand guidelines for testing."""
        return BrandGuidelines(
            brand_name="Acme Corp",
            forbidden_words=["badword", "worseword", "terrible"],
            required_disclaimers=["Terms and conditions apply", "Privacy policy"],
            tone_guidelines="Professional, friendly, no slang",
            visual_standards={"min_width": 100, "min_height": 100},
        )

    @pytest.fixture
    def controller(self, guidelines):
        """Create brand controller with guidelines."""
        return BrandController(guidelines)

    @pytest.mark.asyncio
    async def test_approves_clean_content(self, controller):
        """Should approve content without issues."""
        content = "Welcome to Acme Corp! We provide excellent service."
        result = await controller.review_content(content)
        assert result.approved is True

    @pytest.mark.asyncio
    async def test_rejects_forbidden_word(self, controller):
        """Should reject content with forbidden words."""
        content = "This is a badword example"
        result = await controller.review_content(content)
        assert result.approved is False
        forbidden_issues = [i for i in result.issues if i.type == "forbidden_word"]
        assert len(forbidden_issues) == 1
        assert forbidden_issues[0].type == "forbidden_word"
        assert "badword" in forbidden_issues[0].message

    @pytest.mark.asyncio
    async def test_case_insensitive_forbidden_words(self, controller):
        """Should detect forbidden words regardless of case."""
        content = "This contains BADWORD in uppercase"
        result = await controller.review_content(content)
        assert result.approved is False

    @pytest.mark.asyncio
    async def test_multiple_forbidden_words(self, controller):
        """Should detect multiple forbidden words."""
        content = "This has badword and worseword and terrible"
        result = await controller.review_content(content)
        assert result.approved is False
        forbidden_issues = [i for i in result.issues if i.type == "forbidden_word"]
        assert len(forbidden_issues) == 3

    @pytest.mark.asyncio
    async def test_missing_required_disclaimer(self, controller):
        """Should warn if required disclaimer is missing."""
        content = "Some marketing content without disclaimers"
        result = await controller.review_content(content)
        # Missing disclaimers are warnings, not blocks
        disclaimer_issues = [i for i in result.issues if i.type == "missing_disclaimer"]
        assert len(disclaimer_issues) > 0
        assert all(i.severity == "warning" for i in disclaimer_issues)

    @pytest.mark.asyncio
    async def test_content_with_disclaimer(self, controller):
        """Should pass when disclaimer is present."""
        content = "Great offer! Terms and conditions apply. Privacy policy also applies."
        result = await controller.review_content(content)
        disclaimer_issues = [i for i in result.issues if i.type == "missing_disclaimer"]
        assert len(disclaimer_issues) == 0

    @pytest.mark.asyncio
    async def test_empty_content(self, controller):
        """Should handle empty content."""
        result = await controller.review_content("")
        assert result.approved is True

    @pytest.mark.asyncio
    async def test_no_guidelines_allows_all(self):
        """Should allow all content if no forbidden words configured."""
        guidelines = BrandGuidelines(brand_name="Open Brand", forbidden_words=[])
        controller = BrandController(guidelines)
        result = await controller.review_content("Any content including badword is ok")
        assert result.approved is True

    @pytest.mark.asyncio
    async def test_partial_word_match_not_detected(self, controller):
        """Should not match forbidden words as substrings (word boundary check)."""
        content = "This is notabadword because it's compound"
        # "badword" is a substring but not a whole word - should not be detected
        result = await controller.review_content(content)
        forbidden_issues = [i for i in result.issues if i.type == "forbidden_word"]
        assert len(forbidden_issues) == 0


class TestBrandControllerWithVisual:
    @pytest.mark.asyncio
    async def test_has_visual_content_detection(self):
        """Should detect visual content in message."""
        guidelines = BrandGuidelines(
            brand_name="Test",
            visual_standards={"min_width": 100},
        )
        controller = BrandController(guidelines)

        # Text content
        assert controller.has_visual_content("Just text") is False

        # Image markdown
        assert controller.has_visual_content("![alt](image.png)") is True

        # HTML image
        assert controller.has_visual_content('<img src="test.jpg">') is True

    @pytest.mark.asyncio
    async def test_visual_content_review(self):
        """Should review visual content standards."""
        guidelines = BrandGuidelines(
            brand_name="Test",
            visual_standards={"min_width": 100, "min_height": 100},
        )
        controller = BrandController(guidelines)

        # This would need actual image analysis in production
        # For now, just test the method exists and returns result
        content = "![logo](image.png)"
        result = await controller.review_content(content)
        # Visual review may add issues if standards not met
        assert isinstance(result, BrandReviewResult)
