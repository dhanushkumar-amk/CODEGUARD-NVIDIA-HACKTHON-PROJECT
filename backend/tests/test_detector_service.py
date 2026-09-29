"""
Tests for Detector Service (Phase 11):
- Rule-based precheck catching missing alt, unlabeled input, and clickable div
- Valid LLM JSON parsed with accurate line number calculation
- Malformed LLM JSON gracefully falls back to rule-based findings
- Duplicate rule + LLM findings are deduplicated with rule precedence
- Clean code returns an empty list without inventing issues
"""
import json
from unittest.mock import AsyncMock, patch
import pytest

from app.models.schemas import Violation
from app.services.detector_service import (
    rule_based_precheck,
    build_detection_prompt,
    detect_violations_in_chunk,
    detect_violations,
)
from app.state import create_scan, get_scan, update_scan, remove_scan


def test_rule_based_catches_common_violations():
    """Verify static rule_based_precheck catches missing alt, unlabeled input, and clickable div."""
    chunk = {
        "file": "src/components/BrokenHero.tsx",
        "start_line": 20,
        "content": """export function BrokenHero() {
  return (
    <div>
      <img src="/avatar.jpg" className="w-12 h-12" />
      <input id="username" type="text" placeholder="Enter username" />
      <div onClick={() => console.log('clicked')} className="cursor-pointer">
        Clickable Box
      </div>
      <button><i className="fa fa-star"></i></button>
      <a href="#">Help Link</a>
      <div tabIndex={3}>Positive tab index</div>
    </div>
  );
}""",
    }

    violations = rule_based_precheck(chunk)
    assert len(violations) >= 5

    types = {v.type for v in violations}
    assert "image-alt" in types
    assert "label" in types
    assert "click-events-have-key-events" in types
    assert "button-name" in types
    assert "link-href" in types
    assert "tabindex" in types

    # Verify attributes on violations
    for v in violations:
        assert v.source == "rule"
        assert v.file == "src/components/BrokenHero.tsx"
        assert v.line is not None
        assert v.line >= 20  # Must be mapped relative to start_line (20)
        assert v.wcag_criterion is not None

    # Check specific line numbers
    img_v = next(v for v in violations if v.type == "image-alt")
    assert img_v.line == 23  # line 20 + 3 offset = line 23


@pytest.mark.asyncio
async def test_valid_llm_json_parsing_and_line_calculation():
    """Verify valid LLM JSON is parsed and line numbers are calculated correctly using start_line."""
    chunk = {
        "file": "src/pages/Dashboard.tsx",
        "start_line": 50,
        "content": """export default function Dashboard() {
  return (
    <div>
      <h1>Main Title</h1>
      <h3>Subsection Skipping H2</h3>
      <p style={{ color: '#d1d5db', backgroundColor: '#ffffff' }}>Low contrast text</p>
    </div>
  );
}""",
    }

    mock_llm_response = json.dumps({
        "violations": [
            {
                "line_offset": 4,
                "type": "heading-order",
                "severity": "moderate",
                "description": "Heading level skipped from <h1> to <h3> without an <h2>.",
                "wcag_criterion": "1.3.1 Info and Relationships",
            },
            {
                "line_offset": 5,
                "type": "color-contrast",
                "severity": "serious",
                "description": "Text contrast ratio is below 4.5:1 threshold.",
                "wcag_criterion": "1.4.3 Contrast (Minimum)",
            },
        ]
    })

    with patch("app.services.detector_service.call_with_escalation", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_llm_response

        violations = await detect_violations_in_chunk(chunk, scan_id="test_scan")

        assert len(violations) == 2
        heading_v = next(v for v in violations if v.type == "heading-order")
        contrast_v = next(v for v in violations if v.type == "color-contrast")

        assert heading_v.source == "llm"
        assert heading_v.line == 50 + 4  # 54
        assert heading_v.wcag_criterion == "1.3.1 Info and Relationships"

        assert contrast_v.source == "llm"
        assert contrast_v.line == 50 + 5  # 55
        assert contrast_v.severity == "serious"


@pytest.mark.asyncio
async def test_malformed_llm_json_fallback():
    """Verify malformed LLM output logs a warning and falls back to rule-based results only."""
    chunk = {
        "file": "src/components/Banner.tsx",
        "start_line": 10,
        "content": """<div>
  <img src="banner.png" />
</div>""",
    }

    # Malformed response: garbage text not parseable as JSON
    malformed_response = "Here are the violations I found: 1. Broken image on line 2. No JSON provided."

    with patch("app.services.detector_service.call_with_escalation", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = malformed_response

        violations = await detect_violations_in_chunk(chunk, scan_id="test_scan")

        # Must not crash, should return the 1 rule-based finding
        assert len(violations) == 1
        assert violations[0].type == "image-alt"
        assert violations[0].source == "rule"
        assert violations[0].line == 11


@pytest.mark.asyncio
async def test_duplicate_rule_and_llm_findings_deduplicated():
    """Verify that identical findings from rule and LLM on same file+line+type keep only the rule-based one."""
    scan_id = create_scan("https://github.com/example/test-repo")

    chunk = {
        "file": "src/components/Card.tsx",
        "chunk_index": 0,
        "start_line": 15,
        "content": """<section>
  <img src="/card.png" />
</section>""",
    }

    update_scan(scan_id, scan_batch=[chunk])

    # LLM returns the exact same image-alt defect at offset 1 (line 16)
    mock_llm_response = json.dumps({
        "violations": [
            {
                "line_offset": 1,
                "type": "image-alt",
                "severity": "critical",
                "description": "Image missing alt text.",
                "wcag_criterion": "1.1.1 Non-text Content",
            }
        ]
    })

    with patch("app.services.detector_service.call_with_escalation", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_llm_response

        results = await detect_violations(scan_id)

        # Deduplication must result in exactly 1 violation
        assert len(results) == 1
        assert results[0].type == "image-alt"
        assert results[0].source == "rule"  # Rule takes precedence
        assert results[0].line == 16
        assert results[0].id == "viol_01"

    remove_scan(scan_id)


@pytest.mark.asyncio
async def test_clean_code_returns_empty_list():
    """Verify accessible clean code returns an empty list without invented issues."""
    chunk = {
        "file": "src/components/CleanNav.tsx",
        "start_line": 1,
        "content": """<nav aria-label="Main Navigation">
  <a href="/home">Home</a>
  <a href="/about">About</a>
  <img src="/logo.png" alt="Company logo" />
</nav>""",
    }

    mock_llm_response = json.dumps({"violations": []})

    with patch("app.services.detector_service.call_with_escalation", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_llm_response

        violations = await detect_violations_in_chunk(chunk, scan_id="test_scan")

        assert violations == []
