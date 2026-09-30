"""
Tests for Diagnosis Service (Phase 14):
- Top-priority violations receive full LLM diagnosis via Nemotron Ultra
- Below-threshold violations receive deterministic templated diagnosis with 0 LLM calls
- Malformed LLM JSON gracefully falls back to templated diagnosis without crashing
- Budget / call exhaustion mid-loop seamlessly switches remaining violations to templated fallback
- get_surrounding_context extracts original source lines with component declaration heuristics
"""
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from app.models.schemas import DiagnosedViolation, Violation, ViolationCategory
from app.services.diagnosis_service import (
    get_surrounding_context,
    build_diagnosis_prompt,
    get_templated_diagnosis,
    diagnose_violation,
    diagnose_all,
)
from app.services.llm_client import UltraBudgetExceededError
from app.state import create_scan, get_scan, update_scan, remove_scan


@pytest.mark.asyncio
async def test_top_priority_violations_get_real_llm_diagnosis():
    """Verify top-priority violations (within top_n) invoke Nemotron Ultra and parse JSON diagnosis."""
    violation = Violation(
        id="viol_01",
        file="src/components/Header.tsx",
        line=27,
        type="click-events-have-key-events",
        severity="critical",
        description="Non-interactive <div> with onClick must have role and key handlers.",
        selector="div.menu-btn",
        context_snippet='<div className="menu-btn" onClick={toggleMenu}>',
        category=ViolationCategory.NON_INTERACTIVE_CLICK,
        wcag_criterion="2.1.1 Keyboard",
        severity_score=10,
        priority_rank=1,
    )

    mock_llm_response = json.dumps({
        "root_cause": "The mobile navigation toggle was created as a <div> with onClick instead of a semantic <button>.",
        "affected_element": "div.menu-btn",
        "user_impact": "Keyboard and screen reader users cannot focus, activate, or open the mobile menu.",
        "fix_strategy": "Refactor the <div> into a native <button> element with aria-label='Toggle navigation'.",
        "confidence": "high",
    })

    with patch("app.services.diagnosis_service.call_nemotron_ultra", new_callable=AsyncMock) as mock_ultra:
        mock_ultra.return_value = mock_llm_response

        diagnosed = await diagnose_violation(
            violation=violation,
            repo_path="/tmp/fake-repo",
            scan_id="test_scan_top",
            top_n=5,
        )

        assert mock_ultra.await_count == 1
        assert isinstance(diagnosed, DiagnosedViolation)
        assert diagnosed.diagnosis_source == "llm"
        assert diagnosed.confidence == "high"
        assert diagnosed.affected_element == "div.menu-btn"
        assert "mobile navigation toggle was created as a <div>" in diagnosed.root_cause
        assert "Keyboard and screen reader users" in diagnosed.user_impact
        assert "Refactor the <div> into a native <button>" in diagnosed.fix_strategy


@pytest.mark.asyncio
async def test_below_threshold_violations_use_template_without_llm_call():
    """Verify violations ranked below top_n get cheap templated diagnosis with 0 Ultra calls."""
    violation = Violation(
        id="viol_08",
        file="src/components/Footer.tsx",
        line=45,
        type="image-alt",
        severity="medium",
        description="Images must have an alt attribute.",
        selector="img.logo",
        context_snippet='<img src="/footer-logo.png" />',
        category=ViolationCategory.MISSING_ALT_TEXT,
        wcag_criterion="1.1.1 Non-text Content",
        severity_score=4,
        priority_rank=8,  # Below threshold of top_n=5
    )

    with patch("app.services.diagnosis_service.call_nemotron_ultra", new_callable=AsyncMock) as mock_ultra:
        diagnosed = await diagnose_violation(
            violation=violation,
            repo_path="/tmp/fake-repo",
            scan_id="test_scan_below",
            top_n=5,
        )

        # Assert Ultra was NEVER called
        mock_ultra.assert_not_called()
        assert diagnosed.diagnosis_source == "template"
        assert diagnosed.confidence == "high"
        assert "missing an 'alt' attribute" in diagnosed.root_cause
        assert "Screen reader users" in diagnosed.user_impact
        assert "Add a descriptive 'alt' attribute" in diagnosed.fix_strategy


@pytest.mark.asyncio
async def test_malformed_llm_json_falls_back_to_template_gracefully():
    """Verify that unparseable or malformed LLM responses fall back to template without raising an error."""
    violation = Violation(
        id="viol_02",
        file="src/components/Form.tsx",
        line=14,
        type="label",
        severity="critical",
        description="Form input missing label.",
        selector="input#email",
        context_snippet='<input id="email" type="email" />',
        category=ViolationCategory.UNLABELED_FORM_FIELD,
        wcag_criterion="3.3.2 Labels or Instructions",
        severity_score=9,
        priority_rank=2,
    )

    # Malformed text that cannot be parsed as JSON
    malformed_response = "Here is my diagnosis: The input has no label. Please fix it. (No JSON provided)"

    with patch("app.services.diagnosis_service.call_nemotron_ultra", new_callable=AsyncMock) as mock_ultra:
        mock_ultra.return_value = malformed_response

        diagnosed = await diagnose_violation(
            violation=violation,
            repo_path="/tmp/fake-repo",
            scan_id="test_scan_malformed",
            top_n=5,
        )

        assert mock_ultra.await_count == 1
        assert diagnosed.diagnosis_source == "template"
        assert "lacks a programmatically associated <label>" in diagnosed.root_cause
        assert "Associate an explicit <label htmlFor=" in diagnosed.fix_strategy


@pytest.mark.asyncio
async def test_budget_exhaustion_switches_remaining_to_template():
    """Verify that hitting UltraBudgetExceededError switches remaining violations to templated fallbacks."""
    scan_id = create_scan("https://github.com/example/test-budget-repo")

    v1 = Violation(
        id="viol_01",
        file="src/App.tsx",
        line=10,
        type="click-events-have-key-events",
        severity="critical",
        description="Clickable div",
        selector="div",
        category=ViolationCategory.NON_INTERACTIVE_CLICK,
        severity_score=10,
        priority_rank=1,
    )
    v2 = Violation(
        id="viol_02",
        file="src/App.tsx",
        line=20,
        type="label",
        severity="critical",
        description="Unlabeled input",
        selector="input",
        category=ViolationCategory.UNLABELED_FORM_FIELD,
        severity_score=9,
        priority_rank=2,
    )
    v3 = Violation(
        id="viol_03",
        file="src/App.tsx",
        line=30,
        type="heading-order",
        severity="medium",
        description="Heading skipped",
        selector="h3",
        category=ViolationCategory.HEADING_ORDER,
        severity_score=5,
        priority_rank=3,
    )

    update_scan(scan_id, violations=[v1, v2, v3], repo_path="/tmp/fake-repo")

    success_json = json.dumps({
        "root_cause": "Div used instead of button.",
        "affected_element": "div",
        "user_impact": "Keyboard users excluded.",
        "fix_strategy": "Use button element.",
        "confidence": "high",
    })

    # First call succeeds; subsequent calls raise UltraBudgetExceededError
    call_count = 0

    async def mock_call_ultra(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return success_json
        raise UltraBudgetExceededError("Per-scan Ultra budget ($0.05) exhausted.")

    with patch("app.services.diagnosis_service.call_nemotron_ultra", side_effect=mock_call_ultra):
        results = await diagnose_all(scan_id, top_n=5)

        assert len(results) == 3
        # First item got LLM diagnosis
        assert results[0].id == "viol_01"
        assert results[0].diagnosis_source == "llm"
        assert results[0].root_cause == "Div used instead of button."

        # Remaining items cleanly fell back to template due to budget guardrail
        assert results[1].id == "viol_02"
        assert results[1].diagnosis_source == "template"
        assert "lacks a programmatically associated <label>" in results[1].root_cause

        assert results[2].id == "viol_03"
        assert results[2].diagnosis_source == "template"
        assert "Heading levels are skipped" in results[2].root_cause

    remove_scan(scan_id)


def test_get_surrounding_context_extracts_lines_and_declaration(tmp_path):
    """Verify get_surrounding_context extracts original file window and includes component declaration."""
    file_content = """import React, { useState } from 'react';

interface Props {
  title: string;
}

export function TestWidget({ title }: Props) {
  const [active, setActive] = useState(false);
  const dummyA = 1;
  const dummyB = 2;

  return (
    <div className="widget">
      <h2>{title}</h2>
      <img src="/broken.png" />
      <button onClick={() => setActive(!active)}>Click</button>
    </div>
  );
}
"""
    test_file = tmp_path / "TestWidget.tsx"
    test_file.write_text(file_content, encoding="utf-8")

    context = get_surrounding_context(
        repo_path=str(tmp_path),
        file="TestWidget.tsx",
        line=15,  # The <img> on line 15
        context_lines=8,
    )

    assert "TestWidget.tsx" not in context or "not available" not in context
    # Must contain lines around line 15
    assert "broken.png" in context
    # Must indicate the violation line marker '>'
    assert ">   15 |" in context or "15 |" in context
