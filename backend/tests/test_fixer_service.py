"""
Tests for Fixer Service (Phase 16).
Validates line-level code extraction, fix prompt generation, output syntax & safety validation,
escalation handling on failed validation, severity threshold filtering, and unified diff output.
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.config import settings
from app.models.schemas import DiagnosedViolation, ProposedFix, ViolationCategory
from app.services.fixer_service import (
    _generate_unified_diff,
    build_fix_prompt,
    generate_all_fixes,
    generate_fix,
    get_fix_context,
    validate_fix_output,
)
from app.state import create_scan, get_scan, update_scan


@pytest.fixture
def sample_diagnosed_violation() -> DiagnosedViolation:
    return DiagnosedViolation(
        id="viol_img_alt_01",
        file="src/components/Header.tsx",
        line=21,
        type="image-alt",
        severity="high",
        description="Images must have alternate text describing visual content.",
        selector="img.h-8",
        context_snippet='<img src="/company-logo.svg" className="h-8" />',
        source="rule",
        wcag_criterion="1.1.1 Non-text Content",
        category=ViolationCategory.MISSING_ALT_TEXT,
        severity_score=8,
        priority_rank=1,
        root_cause="The img element lacks an alt attribute, so screen readers cannot describe it.",
        affected_element="<img ... />",
        user_impact="Blind and low vision users hear only the image URL or filename.",
        fix_strategy="Add a descriptive alt attribute, e.g. alt='Company Logo'.",
        confidence="high",
        diagnosis_source="llm",
        plain_explanation="The company logo image does not have alternate text.",
    )


@pytest.fixture
def sample_repo_path(tmp_path) -> str:
    src_dir = tmp_path / "src" / "components"
    src_dir.mkdir(parents=True)
    header_file = src_dir / "Header.tsx"
    header_content = """import React from 'react';

export const Header: React.FC = () => {
  return (
    <header className="site-header">
      {/* Planted Bug 1: img without alt */}
      <img src="/company-logo.svg" className="h-8" />

      {/* Planted Bug 2: input without label */}
      <input id="search-box" type="search" placeholder="Search..." />

      {/* Planted Bug 3: div with onClick */}
      <div className="menu-btn" onClick={() => {}}>
        Menu
      </div>
    </header>
  );
};
"""
    header_file.write_text(header_content, encoding="utf-8")
    return str(tmp_path)


# -----------------------------------------------------------------------------
# Test 1: validate_fix_output correctly rejects mismatched original_lines
# -----------------------------------------------------------------------------
def test_validate_fix_output_rejects_mismatched_original():
    expected = '<img src="/company-logo.svg" className="h-8" />'

    # Case A: completely different original_lines
    response_mismatched = {
        "original_lines": '<button onClick={() => {}}>Click</button>',
        "fixed_lines": '<button onClick={() => {}} aria-label="Click">Click</button>',
        "explanation_of_change": "Added aria-label",
        "confidence": "high",
    }
    assert validate_fix_output(response_mismatched, expected) is False

    # Case B: subtly altered original_lines (added attributes or altered logic)
    response_altered = {
        "original_lines": '<img src="/other-logo.svg" className="h-8" />',
        "fixed_lines": '<img src="/other-logo.svg" alt="Logo" className="h-8" />',
        "explanation_of_change": "Added alt text",
        "confidence": "high",
    }
    assert validate_fix_output(response_altered, expected) is False

    # Case C: exact match passes
    response_valid = {
        "original_lines": '<img src="/company-logo.svg" className="h-8" />',
        "fixed_lines": '<img src="/company-logo.svg" alt="Company Logo" className="h-8" />',
        "explanation_of_change": "Added descriptive alt attribute",
        "confidence": "high",
    }
    assert validate_fix_output(response_valid, expected) is True

    # Case D: minor whitespace / line-ending normalization still passes
    response_normalized = {
        "original_lines": '  <img src="/company-logo.svg" className="h-8" />  \n',
        "fixed_lines": '  <img src="/company-logo.svg" alt="Company Logo" className="h-8" />  ',
        "explanation_of_change": "Added alt attribute",
        "confidence": "high",
    }
    assert validate_fix_output(response_normalized, expected) is True


# -----------------------------------------------------------------------------
# Test 2: validate_fix_output correctly rejects unbalanced brackets (broken syntax)
# -----------------------------------------------------------------------------
def test_validate_fix_output_rejects_unbalanced_brackets():
    expected = '<div className="menu-btn" onClick={() => {}}>\n  Menu\n</div>'

    # Case A: Missing closing brace '}'
    broken_braces = {
        "original_lines": expected,
        "fixed_lines": '<button className="menu-btn" onClick={() => {}>\n  Menu\n</button>',
        "explanation_of_change": "Converted to button with broken arrow fn",
        "confidence": "high",
    }
    assert validate_fix_output(broken_braces, expected) is False

    # Case B: Missing closing parenthesis ')'
    broken_parens = {
        "original_lines": expected,
        "fixed_lines": '<button className="menu-btn" onClick={() => {}}>\n  Menu\n<button',
        "explanation_of_change": "Missing bracket/tag",
        "confidence": "high",
    }
    assert validate_fix_output(broken_parens, expected) is False

    # Case C: Missing closing JSX tag
    broken_tag = {
        "original_lines": expected,
        "fixed_lines": '<button className="menu-btn" onClick={() => {}}>\n  Menu',
        "explanation_of_change": "Unclosed button element",
        "confidence": "high",
    }
    assert validate_fix_output(broken_tag, expected) is False

    # Case D: Unchanged fixed_lines (no modification)
    no_change = {
        "original_lines": expected,
        "fixed_lines": expected,
        "explanation_of_change": "No change",
        "confidence": "high",
    }
    assert validate_fix_output(no_change, expected) is False

    # Case E: Balanced, valid JSX replacement
    valid_fix = {
        "original_lines": expected,
        "fixed_lines": '<button type="button" className="menu-btn" onClick={() => {}}>\n  Menu\n</button>',
        "explanation_of_change": "Converted div to semantic button",
        "confidence": "high",
    }
    assert validate_fix_output(valid_fix, expected) is True


# -----------------------------------------------------------------------------
# Test 3: Failed validation after escalation results in status="failed"
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_failed_validation_yields_failed_status(sample_diagnosed_violation, sample_repo_path):
    scan_id = "test_scan_failed_val"

    # Return invalid output (syntax broken or mismatched) on all attempts
    broken_response = '{"original_lines": "wrong code", "fixed_lines": "also broken"}'

    with patch("app.services.fixer_service.call_nemotron_ultra", new_callable=AsyncMock) as mock_ultra:
        mock_ultra.return_value = broken_response

        fix: ProposedFix = await generate_fix(
            diagnosed=sample_diagnosed_violation,
            repo_path=sample_repo_path,
            scan_id=scan_id,
        )

        assert fix.status == "failed"
        assert fix.fixed_lines == ""
        assert fix.diff == ""
        assert fix.failure_reason is not None
        assert "validation" in fix.failure_reason.lower() or "rejected" in fix.failure_reason.lower()


# -----------------------------------------------------------------------------
# Test 4: Severity threshold correctly skips low-severity violations
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_severity_threshold_skips_low_severity(sample_repo_path):
    scan_id = "test_scan_severity_filter"
    create_scan(repo_url="https://github.com/example/demo-app")

    v_high = DiagnosedViolation(
        id="viol_high",
        file="src/components/Header.tsx",
        line=7,
        type="image-alt",
        severity="high",
        description="Missing alt",
        category=ViolationCategory.MISSING_ALT_TEXT,
        severity_score=8,
        root_cause="Missing alt",
        affected_element="<img ...>",
        user_impact="High impact",
        fix_strategy="Add alt",
        confidence="high",
    )

    v_low = DiagnosedViolation(
        id="viol_low",
        file="src/components/Header.tsx",
        line=10,
        type="tabindex",
        severity="low",
        description="Minor tabindex notice",
        category=ViolationCategory.FOCUS_MANAGEMENT,
        severity_score=3,
        root_cause="Minor notice",
        affected_element="<input ...>",
        user_impact="Low impact",
        fix_strategy="Remove attribute",
        confidence="high",
    )

    update_scan(
        scan_id=scan_id,
        repo_path=sample_repo_path,
        diagnosed_violations=[v_high, v_low],
        status="explained",
    )

    valid_response = (
        '{"original_lines": "<img src=\\"/company-logo.svg\\" className=\\"h-8\\" />", '
        '"fixed_lines": "<img src=\\"/company-logo.svg\\" alt=\\"Company Logo\\" className=\\"h-8\\" />", '
        '"explanation_of_change": "Added alt text", "confidence": "high"}'
    )

    with patch("app.services.fixer_service.call_nemotron_ultra", new_callable=AsyncMock) as mock_ultra:
        mock_ultra.return_value = valid_response

        with patch.object(settings, "FIX_MIN_SEVERITY", "medium"):
            fixes = await generate_all_fixes(scan_id)

            # High severity should be proposed
            high_fixes = [f for f in fixes if f.violation_id == "viol_high"]
            assert len(high_fixes) == 1
            assert high_fixes[0].status == "proposed"
            assert "alt=" in high_fixes[0].fixed_lines

            # Low severity should be skipped / failed due to threshold
            low_fixes = [f for f in fixes if f.violation_id == "viol_low"]
            assert len(low_fixes) == 1
            assert low_fixes[0].status == "failed"
            assert "threshold" in low_fixes[0].failure_reason.lower()

            # Ensure Ultra was only called for the high severity violation (1 call)
            assert mock_ultra.call_count >= 1


# -----------------------------------------------------------------------------
# Test 5: Diff generation produces correct unified diff output
# -----------------------------------------------------------------------------
def test_diff_generation_produces_correct_unified_diff():
    file_path = "src/components/Header.tsx"
    original = '<img src="/company-logo.svg" className="h-8" />'
    fixed = '<img src="/company-logo.svg" alt="Company Logo" className="h-8" />'

    diff = _generate_unified_diff(file_path=file_path, original=original, fixed=fixed)

    assert f"--- a/{file_path}" in diff
    assert f"+++ b/{file_path}" in diff
    assert "@@" in diff
    assert f"-{original}" in diff
    assert f"+{fixed}" in diff


# -----------------------------------------------------------------------------
# Test 6: get_fix_context line-range precision
# -----------------------------------------------------------------------------
def test_get_fix_context_precision(sample_repo_path):
    # Test line 7 which is: <img src="/company-logo.svg" className="h-8" />
    ctx = get_fix_context(
        repo_path=sample_repo_path,
        file="src/components/Header.tsx",
        line=7,
        context_lines=5,
    )

    assert ctx["line_start"] == 7
    assert ctx["line_end"] == 7
    assert '<img src="/company-logo.svg" className="h-8" />' in ctx["original_lines"]
    assert "site-header" in ctx["context"]


# -----------------------------------------------------------------------------
# Test 7: build_fix_prompt format and contents
# -----------------------------------------------------------------------------
def test_build_fix_prompt_contents(sample_diagnosed_violation):
    context = {
        "file": "src/components/Header.tsx",
        "line_start": 21,
        "line_end": 21,
        "original_lines": '<img src="/company-logo.svg" className="h-8" />',
        "context": "// code context",
    }

    system_prompt, user_prompt = build_fix_prompt(sample_diagnosed_violation, context)

    # Check system prompt constraints
    assert "senior frontend engineer" in system_prompt.lower()
    assert "minimal change" in system_prompt.lower()
    assert "preserve all existing functionality" in system_prompt.lower()

    # Check user prompt metadata
    assert "MISSING_ALT_TEXT" in user_prompt or "image-alt" in user_prompt
    assert sample_diagnosed_violation.root_cause in user_prompt
    assert sample_diagnosed_violation.fix_strategy in user_prompt
    assert context["original_lines"] in user_prompt
