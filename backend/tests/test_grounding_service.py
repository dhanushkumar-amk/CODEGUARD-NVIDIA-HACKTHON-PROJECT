"""
Unit and integration tests for Tavily-powered WCAG Grounding Service (Requirement 6).
Tests verify:
1. Cache returns the same GuidanceBundle without a second API call.
2. Tavily failure or timeout returns None and the pipeline completes gracefully.
3. TAVILY_MAX_SEARCHES_PER_SCAN budget cap is strictly respected.
4. Diagnosis and fix prompts contain the reference guidance block ONLY when guidance exists.
All external Tavily API calls are mocked.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.config import settings
from app.models.schemas import (
    DiagnosedViolation,
    GroundingSource,
    GuidanceBundle,
    Violation,
    ViolationCategory,
)
from app.services.diagnosis_service import (
    build_diagnosis_prompt,
    diagnose_violation,
)
from app.services.fixer_service import (
    build_fix_prompt,
)
from app.services.grounding_service import (
    format_guidance_for_prompt,
    get_guidance,
    get_scan_search_count,
    reset_cache_for_testing,
    warm_guidance_cache,
)


@pytest.fixture(autouse=True)
def clean_cache():
    """Reset the grounding in-memory cache and search counters before and after each test."""
    reset_cache_for_testing()
    yield
    reset_cache_for_testing()


@pytest.mark.asyncio
async def test_cache_returns_same_bundle_without_second_api_call():
    """Verify that repeated queries for the same category hit the cache and do not make a second API call."""
    mock_results = {
        "results": [
            {
                "title": "W3C: Images Tutorial - Informative Images",
                "url": "https://www.w3.org/WAI/tutorials/images/informative/",
                "content": "Informative images convey a concept that can be expressed in words and require descriptive alternative text.",
            },
            {
                "title": "MDN: Alternative text for images",
                "url": "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img#alt",
                "content": "The alt attribute holds a text description of the image.",
            },
        ]
    }

    mock_search = AsyncMock(return_value=mock_results)

    with patch("app.config.settings.TAVILY_API_KEY", "tvly-test-mock-key"), \
         patch("app.config.settings.TAVILY_ENABLED", True), \
         patch("tavily.AsyncTavilyClient.search", mock_search):

        # First query: should query Tavily
        bundle1 = await get_guidance(ViolationCategory.MISSING_ALT_TEXT, scan_id="test_scan_1")
        assert bundle1 is not None
        assert len(bundle1.sources) == 2
        assert bundle1.sources[0].title == "W3C: Images Tutorial - Informative Images"
        assert mock_search.call_count == 1
        assert get_scan_search_count("test_scan_1") == 1

        # Second query for same category: should return cached bundle without calling Tavily
        bundle2 = await get_guidance(ViolationCategory.MISSING_ALT_TEXT, scan_id="test_scan_1")
        assert bundle2 is not None
        assert bundle2 is bundle1  # Exact same cached instance
        assert mock_search.call_count == 1  # Still 1 call, not 2
        assert get_scan_search_count("test_scan_1") == 1


@pytest.mark.asyncio
async def test_tavily_failure_returns_none_and_pipeline_completes():
    """Verify that if Tavily fails (network error, timeout, HTTP 500), get_guidance returns None and diagnose_violation still succeeds."""
    mock_search = AsyncMock(side_effect=Exception("Connection refused by remote host"))

    test_violation = Violation(
        id="viol_fail_test",
        file="src/components/Input.tsx",
        line=15,
        type="label",
        severity="critical",
        description="Form element has no label",
        category=ViolationCategory.UNLABELED_FORM_FIELD,
        priority_rank=20,  # Will use templated fallback diagnosis
    )

    with patch("app.config.settings.TAVILY_API_KEY", "tvly-test-mock-key"), \
         patch("app.config.settings.TAVILY_ENABLED", True), \
         patch("tavily.AsyncTavilyClient.search", mock_search):

        # get_guidance should gracefully catch error and return None
        guidance = await get_guidance(test_violation.category, scan_id="test_scan_fail")
        assert guidance is None

        # diagnose_violation should still complete and produce a valid DiagnosedViolation
        diagnosed = await diagnose_violation(
            violation=test_violation,
            repo_path="",
            scan_id="test_scan_fail",
            top_n=10,
        )
        assert diagnosed is not None
        assert diagnosed.id == "viol_fail_test"
        assert diagnosed.grounded is False
        assert len(diagnosed.grounding_sources) == 0


@pytest.mark.asyncio
async def test_search_cap_is_respected():
    """Verify that TAVILY_MAX_SEARCHES_PER_SCAN cap halts outgoing requests when exceeded."""
    mock_results = {
        "results": [
            {
                "title": "MDN Web Docs",
                "url": "https://developer.mozilla.org",
                "content": "Accessibility guidance",
            }
        ]
    }
    mock_search = AsyncMock(return_value=mock_results)

    with patch("app.config.settings.TAVILY_API_KEY", "tvly-test-mock-key"), \
         patch("app.config.settings.TAVILY_ENABLED", True), \
         patch("app.config.settings.TAVILY_MAX_SEARCHES_PER_SCAN", 2), \
         patch("tavily.AsyncTavilyClient.search", mock_search):

        scan_id = "test_cap_scan"

        # Search 1: category 1
        res1 = await get_guidance(ViolationCategory.MISSING_ALT_TEXT, scan_id=scan_id)
        assert res1 is not None
        assert mock_search.call_count == 1
        assert get_scan_search_count(scan_id) == 1

        # Search 2: category 2
        res2 = await get_guidance(ViolationCategory.UNLABELED_FORM_FIELD, scan_id=scan_id)
        assert res2 is not None
        assert mock_search.call_count == 2
        assert get_scan_search_count(scan_id) == 2

        # Search 3: category 3 should hit cap (max 2) and return None without calling Tavily
        res3 = await get_guidance(ViolationCategory.LOW_CONTRAST, scan_id=scan_id)
        assert res3 is None
        assert mock_search.call_count == 2  # Still 2 calls
        assert get_scan_search_count(scan_id) == 2


def test_prompt_contains_guidance_block_only_when_guidance_exists():
    """Verify that diagnosis and fix prompts include the reference guidance block if and only if guidance exists."""
    violation = Violation(
        id="viol_prompt_test",
        file="src/Button.tsx",
        line=10,
        type="button-name",
        severity="high",
        description="Button has no accessible name",
        category=ViolationCategory.EMPTY_LINK_OR_BUTTON,
    )

    diagnosed = DiagnosedViolation(
        id="viol_prompt_test",
        file="src/Button.tsx",
        line=10,
        type="button-name",
        severity="high",
        description="Button has no accessible name",
        category=ViolationCategory.EMPTY_LINK_OR_BUTTON,
        root_cause="The button only contains an SVG icon with no text label.",
        affected_element="<button className='icon-btn'>",
        user_impact="Screen reader users cannot identify what the button activates.",
        fix_strategy="Add aria-label or sr-only text.",
        confidence="high",
        diagnosis_source="llm",
    )

    context_dict = {
        "file": "src/Button.tsx",
        "line_start": 10,
        "line_end": 12,
        "original_lines": "<button className='icon-btn'><svg /></button>",
        "context": "export const IconButton = () => <button className='icon-btn'><svg /></button>;",
    }

    # Case A: No guidance provided
    _, user_diag_no_guidance = build_diagnosis_prompt(violation, context=context_dict["context"], guidance=None)
    assert "REFERENCE WCAG GUIDANCE (OFFICIAL TRUSTED SOURCES):" not in user_diag_no_guidance
    assert "Prefer this retrieved guidance over your internal training memory" not in user_diag_no_guidance

    _, user_fix_no_guidance = build_fix_prompt(diagnosed, context=context_dict, guidance=None)
    assert "REFERENCE WCAG GUIDANCE (OFFICIAL TRUSTED SOURCES):" not in user_fix_no_guidance

    # Case B: GuidanceBundle provided
    sample_bundle = GuidanceBundle(
        category=ViolationCategory.EMPTY_LINK_OR_BUTTON,
        sources=[
            GroundingSource(
                title="W3C WCAG Technique ARIA8",
                url="https://www.w3.org/WAI/WCAG22/Techniques/aria/ARIA8",
                snippet="Using aria-label for link or button purpose when visual text is absent.",
            )
        ],
        retrieved_at=datetime.now(timezone.utc),
    )

    _, user_diag_with_guidance = build_diagnosis_prompt(violation, context=context_dict["context"], guidance=sample_bundle)
    assert "REFERENCE WCAG GUIDANCE (OFFICIAL TRUSTED SOURCES):" in user_diag_with_guidance
    assert "W3C WCAG Technique ARIA8" in user_diag_with_guidance
    assert "https://www.w3.org/WAI/WCAG22/Techniques/aria/ARIA8" in user_diag_with_guidance
    assert "Prefer this retrieved guidance over your internal training memory" in user_diag_with_guidance

    _, user_fix_with_guidance = build_fix_prompt(diagnosed, context=context_dict, guidance=sample_bundle)
    assert "REFERENCE WCAG GUIDANCE (OFFICIAL TRUSTED SOURCES):" in user_fix_with_guidance
    assert "W3C WCAG Technique ARIA8" in user_fix_with_guidance
    assert "https://www.w3.org/WAI/WCAG22/Techniques/aria/ARIA8" in user_fix_with_guidance
