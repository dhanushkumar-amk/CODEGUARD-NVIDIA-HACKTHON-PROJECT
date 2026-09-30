"""
Tests for Classifier Service (Phase 13):
- Known rule-based types map to the correct category every time
- Free-text LLM types are matched via keywords correctly
- Unrecognized types fall back to OTHER without crashing
- Severity scoring correctly boosts interactive elements and Level A criteria
- priority_rank is correctly assigned in descending severity order
- Violation summary aggregation returns accurate totals and breakdowns
"""
import pytest
from app.models.schemas import Violation, ViolationCategory
from app.services.classifier_service import (
    normalize_category,
    calculate_severity_score,
    map_score_to_severity_label,
    classify_violations,
    summarize_violations,
)


def test_known_rule_based_types_map_correctly():
    """Verify all deterministic rule-based types from Phase 12 map to correct canonical categories."""
    mappings = {
        "image-alt": ViolationCategory.MISSING_ALT_TEXT,
        "image_alt": ViolationCategory.MISSING_ALT_TEXT,
        "label": ViolationCategory.UNLABELED_FORM_FIELD,
        "unlabeled-form-field": ViolationCategory.UNLABELED_FORM_FIELD,
        "click-events-have-key-events": ViolationCategory.NON_INTERACTIVE_CLICK,
        "button-name": ViolationCategory.EMPTY_LINK_OR_BUTTON,
        "link-name": ViolationCategory.EMPTY_LINK_OR_BUTTON,
        "link-href": ViolationCategory.EMPTY_LINK_OR_BUTTON,
        "html-has-lang": ViolationCategory.MISSING_LANG,
        "tabindex": ViolationCategory.FOCUS_MANAGEMENT,
        # Standard axe-core rule IDs
        "color-contrast": ViolationCategory.LOW_CONTRAST,
        "heading-order": ViolationCategory.HEADING_ORDER,
        "landmark-main-is-top-level": ViolationCategory.MISSING_LANDMARK,
        "landmark-one-main": ViolationCategory.MISSING_LANDMARK,
        "keyboard-trap": ViolationCategory.KEYBOARD_TRAP,
        "aria-roles": ViolationCategory.ARIA_MISUSE,
        "aria-valid-attr": ViolationCategory.ARIA_MISUSE,
    }

    for raw_type, expected_cat in mappings.items():
        assert normalize_category(raw_type) == expected_cat, f"Failed for raw_type: {raw_type}"


def test_free_text_llm_types_matched_via_keywords():
    """Verify LLM free-text strings are categorized accurately using keyword heuristics."""
    test_cases = [
        ("Text color contrast is insufficient for dark mode", ViolationCategory.LOW_CONTRAST),
        ("img element missing alt attribute description", ViolationCategory.MISSING_ALT_TEXT),
        ("Unlabeled form input field needs label or aria-label", ViolationCategory.UNLABELED_FORM_FIELD),
        ("Heading hierarchy skipped level 1 directly to 3", ViolationCategory.HEADING_ORDER),
        ("Clickable span element missing keyboard handler and role", ViolationCategory.NON_INTERACTIVE_CLICK),
        ("Empty button with icon has no accessible name", ViolationCategory.EMPTY_LINK_OR_BUTTON),
        ("Missing top-level main landmark on page", ViolationCategory.MISSING_LANDMARK),
        ("Focus trapped inside modal dialog preventing user escape", ViolationCategory.KEYBOARD_TRAP),
        ("Page missing html lang attribute", ViolationCategory.MISSING_LANG),
        ("Invalid aria-hidden role misuse on focusable element", ViolationCategory.ARIA_MISUSE),
        ("Disrupted tab order due to positive tabindex value", ViolationCategory.FOCUS_MANAGEMENT),
    ]

    for raw_text, expected_cat in test_cases:
        result = normalize_category(raw_text)
        assert result == expected_cat, f"Expected {expected_cat} for '{raw_text}', got {result}"


def test_unrecognized_types_fallback_to_other():
    """Verify completely unrecognized types safely fall back to OTHER without crashing."""
    assert normalize_category("supercalifragilistic-defect") == ViolationCategory.OTHER
    assert normalize_category("unknown_random_issue_404") == ViolationCategory.OTHER
    assert normalize_category("") == ViolationCategory.OTHER
    assert normalize_category(None) == ViolationCategory.OTHER
    assert normalize_category("   ") == ViolationCategory.OTHER


def test_severity_scoring_boosts_interactive_elements():
    """Verify violations on interactive elements receive a severity boost over static content."""
    # Static content violation
    static_v = Violation(
        id="v_static",
        file="src/components/Banner.tsx",
        line=10,
        type="missing-landmark",
        description="Missing main landmark",
        selector="div.banner",
        context_snippet="<div className='banner'>Banner Content</div>",
        category=ViolationCategory.MISSING_LANDMARK,
        wcag_criterion="1.3.1 Info and Relationships",
    )

    # Interactive element violation with same conformance level
    interactive_v = Violation(
        id="v_interactive",
        file="src/components/Form.tsx",
        line=25,
        type="label",
        description="Unlabeled input element",
        selector="input#username",
        context_snippet="<input id='username' type='text' />",
        category=ViolationCategory.UNLABELED_FORM_FIELD,
        wcag_criterion="3.3.2 Labels or Instructions",
    )

    static_score = calculate_severity_score(static_v)
    interactive_score = calculate_severity_score(interactive_v)

    assert interactive_score > static_score
    assert 1 <= static_score <= 10
    assert 1 <= interactive_score <= 10


def test_severity_scoring_boosts_level_a_criteria():
    """Verify Level A issues receive a higher conformance adjustment than Level AA/AAA."""
    # Level A issue (e.g. 1.1.1 Non-text Content)
    v_level_a = Violation(
        id="v_a",
        file="src/components/Hero.tsx",
        line=12,
        type="image-alt",
        description="Image missing alt text",
        selector="img",
        context_snippet="<img src='/pic.jpg' />",
        category=ViolationCategory.MISSING_ALT_TEXT,
        wcag_criterion="1.1.1 Non-text Content (Level A)",
    )

    # Level AA issue with similar baseline category (e.g. 1.4.3 Contrast Minimum)
    v_level_aa = Violation(
        id="v_aa",
        file="src/components/Hero.tsx",
        line=18,
        type="color-contrast",
        description="Color contrast below 4.5:1",
        selector="p",
        context_snippet="<p className='text-gray-300'>Subtext</p>",
        category=ViolationCategory.LOW_CONTRAST,
        wcag_criterion="1.4.3 Contrast (Minimum) (Level AA)",
    )

    score_a = calculate_severity_score(v_level_a)
    score_aa = calculate_severity_score(v_level_aa)

    assert score_a >= score_aa


def test_intentional_decorative_image_scores_lower():
    """Verify an image marked decorative (alt='') scores significantly lower than missing alt."""
    v_missing_alt = Violation(
        id="v1",
        file="src/components/Avatar.tsx",
        line=5,
        type="image-alt",
        description="Image missing alt text",
        selector="img",
        context_snippet="<img src='/avatar.png' />",
        category=ViolationCategory.MISSING_ALT_TEXT,
        wcag_criterion="1.1.1 Non-text Content",
    )

    v_decorative = Violation(
        id="v2",
        file="src/components/Avatar.tsx",
        line=15,
        type="image-alt",
        description="Decorative image with alt='' attribute",
        selector="img",
        context_snippet="<img src='/bg-pattern.png' alt='' />",
        category=ViolationCategory.MISSING_ALT_TEXT,
        wcag_criterion="1.1.1 Non-text Content",
    )

    score_missing = calculate_severity_score(v_missing_alt)
    score_decorative = calculate_severity_score(v_decorative)

    assert score_decorative < score_missing
    assert score_decorative <= 5


def test_severity_label_mapping():
    """Verify score mapping to critical (8-10), high (5-7), medium (3-4), low (1-2)."""
    assert map_score_to_severity_label(10) == "critical"
    assert map_score_to_severity_label(8) == "critical"
    assert map_score_to_severity_label(7) == "high"
    assert map_score_to_severity_label(5) == "high"
    assert map_score_to_severity_label(4) == "medium"
    assert map_score_to_severity_label(3) == "medium"
    assert map_score_to_severity_label(2) == "low"
    assert map_score_to_severity_label(1) == "low"


def test_priority_rank_assigned_in_descending_severity_order():
    """Verify classify_violations assigns priority_rank 1..N in descending order of severity_score."""
    violations = [
        Violation(
            id="v_low",
            file="src/App.tsx",
            line=20,
            type="heading-order",
            description="Heading order skipped",
            selector="h3",
            category=ViolationCategory.HEADING_ORDER,
            wcag_criterion="1.3.1 Info and Relationships",
        ),
        Violation(
            id="v_high",
            file="src/components/Button.tsx",
            line=12,
            type="button-name",
            description="Empty icon button",
            selector="button",
            context_snippet="<button><i className='fa fa-trash'></i></button>",
            category=ViolationCategory.EMPTY_LINK_OR_BUTTON,
            wcag_criterion="4.1.2 Name, Role, Value",
        ),
        Violation(
            id="v_critical",
            file="src/components/Trap.tsx",
            line=30,
            type="keyboard-trap",
            description="Keyboard focus trap in modal dialog",
            selector="div.modal",
            context_snippet="<div onKeyDown={trapFocus}><input /></div>",
            category=ViolationCategory.KEYBOARD_TRAP,
            wcag_criterion="2.1.2 No Keyboard Trap",
        ),
    ]

    classified = classify_violations(violations)

    # Must be sorted in descending severity order
    scores = [v.severity_score for v in classified]
    assert scores == sorted(scores, reverse=True)

    # Priority rank must be sequential starting at 1
    for rank, v in enumerate(classified, start=1):
        assert v.priority_rank == rank

    # Top priority must be the keyboard trap
    assert classified[0].category == ViolationCategory.KEYBOARD_TRAP
    assert classified[0].priority_rank == 1
    assert classified[0].severity == "critical"


def test_summarize_violations_aggregation():
    """Verify summarize_violations returns accurate counts for categories, severity labels, and total."""
    violations = [
        Violation(
            id="v1",
            file="src/A.tsx",
            type="image-alt",
            description="Missing alt",
            category=ViolationCategory.MISSING_ALT_TEXT,
            severity="critical",
            severity_score=9,
            priority_rank=1,
        ),
        Violation(
            id="v2",
            file="src/B.tsx",
            type="label",
            description="Unlabeled input",
            category=ViolationCategory.UNLABELED_FORM_FIELD,
            severity="critical",
            severity_score=8,
            priority_rank=2,
        ),
        Violation(
            id="v3",
            file="src/C.tsx",
            type="color-contrast",
            description="Low contrast",
            category=ViolationCategory.LOW_CONTRAST,
            severity="high",
            severity_score=6,
            priority_rank=3,
        ),
        Violation(
            id="v4",
            file="src/D.tsx",
            type="heading-order",
            description="Heading order",
            category=ViolationCategory.HEADING_ORDER,
            severity="medium",
            severity_score=4,
            priority_rank=4,
        ),
    ]

    summary = summarize_violations(violations)

    assert summary["total"] == 4
    assert summary["by_severity"]["critical"] == 2
    assert summary["by_severity"]["high"] == 1
    assert summary["by_severity"]["medium"] == 1
    assert summary["by_severity"]["low"] == 0

    assert summary["by_category"][ViolationCategory.MISSING_ALT_TEXT.value] == 1
    assert summary["by_category"][ViolationCategory.UNLABELED_FORM_FIELD.value] == 1
    assert summary["by_category"][ViolationCategory.LOW_CONTRAST.value] == 1
    assert summary["by_category"][ViolationCategory.HEADING_ORDER.value] == 1
    assert summary["by_category"][ViolationCategory.KEYBOARD_TRAP.value] == 0
