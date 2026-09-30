"""
Tests for Explainer Service (Phase 15):
- LLM-diagnosed violations get a rewritten, friendly explanation for non-developers
- Template-diagnosed violations get an expanded, contextual explanation
- Explanations are cleanly truncated at sentence boundaries within max length, not mid-word
- API failures fall back to deterministic f-string default without crashing
- Batch orchestration updates all violations and preserves pipeline state
"""
from unittest.mock import AsyncMock, patch
import pytest

from app.models.schemas import DiagnosedViolation, ViolationCategory
from app.services.explainer_service import (
    build_explanation_prompt,
    generate_explanation,
    generate_all_explanations,
    truncate_at_sentence_boundary,
    MAX_EXPLANATION_LENGTH,
)
from app.state import create_scan, get_scan, update_scan, remove_scan


@pytest.mark.asyncio
async def test_llm_diagnosed_violation_gets_rewritten_explanation():
    """Verify violations diagnosed by Ultra prompt the fast model to rewrite root cause into stakeholder summary."""
    violation = DiagnosedViolation(
        id="viol_01",
        file="src/components/Header.tsx",
        line=27,
        type="click-events-have-key-events",
        severity="critical",
        description="Non-interactive <div> with onClick must have role and key handlers.",
        selector="div.menu-btn",
        category=ViolationCategory.NON_INTERACTIVE_CLICK,
        wcag_criterion="2.1.1 Keyboard",
        severity_score=10,
        priority_rank=1,
        root_cause="A non-semantic div with an onClick handler was used instead of a native button element.",
        affected_element="div.menu-btn",
        user_impact="Keyboard-only and screen reader users cannot focus or activate the menu toggle.",
        fix_strategy="Replace the div with a semantic button element.",
        confidence="high",
        diagnosis_source="llm",
    )

    mock_llm_output = (
        "The navigation menu button was built using a plain container instead of a real button. "
        "Because of this, people who use keyboards or screen readers cannot open the navigation menu. "
        "Switching this to a standard button element will make it accessible to everyone."
    )

    with patch("app.services.explainer_service.call_nemotron_fast", new_callable=AsyncMock) as mock_fast:
        mock_fast.return_value = mock_llm_output

        explanation = await generate_explanation(violation)

        mock_fast.assert_awaited_once()
        call_prompt = mock_fast.call_args[1].get("prompt") or mock_fast.call_args[0][0]
        # Verify prompt instructed model to rewrite existing technical diagnosis
        assert "non-technical stakeholders" in call_prompt
        assert "Technical Root Cause" in call_prompt
        assert explanation == mock_llm_output


@pytest.mark.asyncio
async def test_template_diagnosed_violation_gets_expanded_explanation():
    """Verify template-diagnosed violations prompt the fast model to expand generic templates with file context."""
    violation = DiagnosedViolation(
        id="viol_07",
        file="src/components/Header.tsx",
        line=21,
        type="image-alt",
        severity="critical",
        description="Images must have an alt attribute describing the image.",
        selector="img.logo",
        context_snippet='<img src="/logo.svg" />',
        category=ViolationCategory.MISSING_ALT_TEXT,
        wcag_criterion="1.1.1 Non-text Content",
        severity_score=8,
        priority_rank=7,
        root_cause="The img element lacks an alt attribute.",
        affected_element="img.logo",
        user_impact="Screen reader users hear only a raw file path.",
        fix_strategy="Add descriptive alt text.",
        confidence="high",
        diagnosis_source="template",
    )

    mock_llm_output = (
        "The company logo image in Header.tsx does not have an alt text description. "
        "People using screen readers will not know what image is displayed on the page. "
        "Adding a short description like 'Company Logo' will solve this problem."
    )

    with patch("app.services.explainer_service.call_nemotron_fast", new_callable=AsyncMock) as mock_fast:
        mock_fast.return_value = mock_llm_output

        explanation = await generate_explanation(violation)

        mock_fast.assert_awaited_once()
        call_prompt = mock_fast.call_args[1].get("prompt") or mock_fast.call_args[0][0]
        assert "Header.tsx" in call_prompt
        assert "Issue Details:" in call_prompt
        assert explanation == mock_llm_output


def test_truncation_at_sentence_boundary():
    """Verify text exceeding max length is truncated at the last sentence boundary, never mid-word."""
    sent1 = "The search input field on the home page does not have a visible text label."
    sent2 = "Visitors using screen reader software cannot tell what kind of information should be entered."
    sent3 = "This very long third sentence describes detailed technical instructions that exceed the strict character budget."

    full_text = f"{sent1} {sent2} {sent3}"
    assert len(full_text) > 200

    # Truncate with budget that fits sentence 1 and 2, but cuts into sentence 3
    truncated = truncate_at_sentence_boundary(full_text, max_chars=180)

    # Must end cleanly at the period of sentence 2
    assert truncated.endswith(".")
    assert sent1 in truncated
    assert sent2 in truncated
    assert "instructions that exceed" not in truncated
    # Ensure no trailing broken word fragments
    assert not truncated.endswith("...")
    assert len(truncated) <= 180


def test_truncation_no_sentence_boundary_falls_back_to_words():
    """Verify that when no period exists near the limit, truncation cuts at a word boundary rather than mid-word."""
    unpunctuated = (
        "this is a very long run on sentence without any periods or punctuation marks that "
        "continues talking about accessibility barriers and screen reader accessibility and keyboard controls"
    )
    truncated = truncate_at_sentence_boundary(unpunctuated, max_chars=100)
    assert len(truncated) <= 100
    assert truncated.endswith("...")
    # Assert last word is not sliced in half
    assert not truncated.endswith("accessib...")


@pytest.mark.asyncio
async def test_api_failure_falls_back_to_default_fstring():
    """Verify fast model API errors fall back to deterministic f-string without crashing or raising."""
    violation = DiagnosedViolation(
        id="viol_03",
        file="src/components/LoginForm.tsx",
        line=27,
        type="label",
        severity="critical",
        description="Form textarea element has no associated label.",
        selector="textarea",
        category=ViolationCategory.UNLABELED_FORM_FIELD,
        wcag_criterion="3.3.2 Labels or Instructions",
        severity_score=10,
        priority_rank=3,
        root_cause="Generic root cause",
        affected_element="textarea",
        user_impact="Generic user impact",
        fix_strategy="Generic fix strategy",
        confidence="high",
        diagnosis_source="llm",
    )

    with patch("app.services.explainer_service.call_nemotron_fast", side_effect=Exception("API connection timeout")):
        fallback = await generate_explanation(violation)

        assert isinstance(fallback, str)
        assert len(fallback) > 0
        assert "LoginForm.tsx" in fallback
        assert "critical" in fallback.lower()
        assert "unlabeled form field" in fallback.lower()


@pytest.mark.asyncio
async def test_generate_all_explanations_orchestration():
    """Verify generate_all_explanations runs batch concurrent explanations and saves plain_explanation to state."""
    scan_id = create_scan("https://github.com/example/test-explainer-repo")

    v1 = DiagnosedViolation(
        id="viol_01",
        file="src/Header.tsx",
        type="click-events-have-key-events",
        severity="critical",
        description="Clickable div",
        selector="div",
        category=ViolationCategory.NON_INTERACTIVE_CLICK,
        root_cause="Div instead of button",
        affected_element="div",
        user_impact="Cannot click",
        fix_strategy="Use button",
        confidence="high",
        diagnosis_source="llm",
    )
    v2 = DiagnosedViolation(
        id="viol_02",
        file="src/Footer.tsx",
        type="image-alt",
        severity="medium",
        description="Missing alt",
        selector="img",
        category=ViolationCategory.MISSING_ALT_TEXT,
        root_cause="No alt",
        affected_element="img",
        user_impact="Cannot see",
        fix_strategy="Add alt",
        confidence="high",
        diagnosis_source="template",
    )

    update_scan(scan_id, diagnosed_violations=[v1, v2])

    with patch("app.services.explainer_service.call_nemotron_fast", new_callable=AsyncMock) as mock_fast:
        mock_fast.return_value = "A clear and friendly explanation of the accessibility issue for everyone."

        results = await generate_all_explanations(scan_id)

        assert len(results) == 2
        for item in results:
            assert isinstance(item, DiagnosedViolation)
            assert item.plain_explanation == "A clear and friendly explanation of the accessibility issue for everyone."

        # Verify state store was updated
        saved_scan = get_scan(scan_id)
        assert saved_scan["status"] == "explained"
        assert len(saved_scan["violations"]) == 2
        assert saved_scan["violations"][0].plain_explanation != ""

    remove_scan(scan_id)
