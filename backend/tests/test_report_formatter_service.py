"""
Unit tests for Report Formatter Service (Phase 23).
Covers:
- Markdown output contains all required sections for mixed final_status values
- HTML output is valid (basic tag balance check) and contains core data
- executive_summary falls back to template correctly if LLM call fails
- save_report_files writes both files to disk and returns correct paths
"""
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from app.models.schemas import (
    CostBreakdown,
    DiagnosedViolation,
    ProposedFix,
    ScanReport,
    ScoreImprovement,
    UnifiedViolationRecord,
    VerificationResult,
    ViolationCategory,
)
from app.services.report_formatter_service import (
    format_report_as_html,
    format_report_as_markdown,
    generate_executive_summary,
    save_report_files,
)


@pytest.fixture
def sample_report():
    v1 = DiagnosedViolation(
        id="viol_01",
        file="src/Header.tsx",
        line=21,
        type="image-alt",
        severity="critical",
        description="Missing alt attribute on header logo",
        category=ViolationCategory.MISSING_ALT_TEXT,
        root_cause="Logo rendered without text alternative.",
        affected_element="img",
        user_impact="Screen reader users cannot identify logo.",
        fix_strategy="Add alt text.",
        plain_explanation="In Header.tsx, an alt attribute is required for the logo.",
    )
    f1 = ProposedFix(
        fix_id="fix_01",
        violation_id="viol_01",
        file="src/Header.tsx",
        original_lines='<img src="/logo.svg" />',
        fixed_lines='<img src="/logo.svg" alt="Company Logo" />',
        diff="--- a/src/Header.tsx\n+++ b/src/Header.tsx\n@@ -21,1 +21,1 @@\n-<img src=\"/logo.svg\" />\n+<img src=\"/logo.svg\" alt=\"Company Logo\" />\n",
        status="proposed",
    )
    vr1 = VerificationResult(
        fix_id="fix_01",
        violation_id="viol_01",
        axe_score_before=70.0,
        axe_score_after=85.0,
        verified=True,
        tests_passed=True,
        violations_resolved=True,
    )
    rec1 = UnifiedViolationRecord(
        violation=v1,
        fix=f1,
        verification=vr1,
        final_status="fixed_and_verified",
    )

    v2 = DiagnosedViolation(
        id="viol_02",
        file="src/Input.tsx",
        line=10,
        type="label",
        severity="critical",
        description="Form input missing label",
        category=ViolationCategory.UNLABELED_FORM_FIELD,
        root_cause="Input without aria-label.",
        affected_element="input",
        user_impact="Users cannot tell what the input is for.",
        fix_strategy="Add aria-label.",
        plain_explanation="Form input missing descriptive label.",
    )
    rec2 = UnifiedViolationRecord(
        violation=v2,
        fix=None,
        verification=None,
        final_status="detected_only",
    )

    v3 = DiagnosedViolation(
        id="viol_03",
        file="src/Button.tsx",
        line=30,
        type="button-name",
        severity="high",
        description="Empty icon button",
        category=ViolationCategory.EMPTY_LINK_OR_BUTTON,
        root_cause="Button has no inner text.",
        affected_element="button",
        user_impact="No button name announced.",
        fix_strategy="Add aria-label.",
        plain_explanation="Button must have accessible name.",
    )
    f3 = ProposedFix(
        fix_id="fix_03",
        violation_id="viol_03",
        file="src/Button.tsx",
        status="failed",
        failure_reason="Syntax error parsing JSX",
    )
    rec3 = UnifiedViolationRecord(
        violation=v3,
        fix=f3,
        verification=None,
        final_status="fix_failed",
    )

    summary = {
        "total_violations": 3,
        "fixed_and_verified": 1,
        "fixed_not_verified": 0,
        "detected_only": 1,
        "fix_failed": 1,
        "verification_skipped": 0,
        "score_before": 70.0,
        "score_after": 85.0,
        "improvement_points": 15.0,
        "cost_breakdown": {
            "fast_cost": 0.001,
            "ultra_cost": 0.015,
            "total_cost": 0.016,
        },
        "duration_seconds": 12.34,
    }

    return ScanReport(
        scan_id="scan_test_123",
        repo_url="https://github.com/example/demo-app",
        branch="main",
        violations=[v1, v2, v3],
        fixes=[f1, f3],
        verification_results=[vr1],
        unified_records=[rec1, rec2, rec3],
        overall_score_before=70.0,
        overall_score_after=85.0,
        overall_improvement=ScoreImprovement(score_before=70.0, score_after=85.0, improvement_points=15.0),
        summary=summary,
        cost_breakdown=CostBreakdown(fast_cost=0.001, ultra_cost=0.015, total_cost=0.016),
        total_duration_seconds=12.34,
        timestamp=datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc),
        status="completed",
    )


class TestReportFormatting:
    def test_markdown_format_contains_all_required_sections(self, sample_report):
        summary_text = "This scan analyzed 3 violations. 1 was fixed and verified."
        md = format_report_as_markdown(sample_report, summary_text)

        assert "# CodeGuard Accessibility Audit & Remediation Report" in md
        assert "## Executive Summary" in md
        assert summary_text in md
        assert "## Overall Compliance Score" in md
        assert "70.0%" in md
        assert "85.0%" in md
        assert "+15.0 points" in md
        assert "## Violations & Remediation Summary" in md
        assert "Fixed And Verified" in md
        assert "Detected Only" in md
        assert "Fix Failed" in md
        assert "## Verified Fixes (Sandboxed Proof-of-Work)" in md
        assert "```diff" in md
        assert "## Known Limitations & Remaining Action Items" in md
        assert "viol_02" in md
        assert "viol_03" in md
        assert "## LLM Inference & Cost Accounting" in md
        assert "$0.016000" in md

    def test_html_format_is_valid_and_contains_core_data(self, sample_report):
        summary_text = "Executive summary test content."
        html = format_report_as_html(sample_report, summary_text)

        assert "<!DOCTYPE html>" in html
        assert "<html lang=\"en\">" in html
        assert "</html>" in html
        assert "CodeGuard Compliance Audit Report" in html
        assert "https://github.com/example/demo-app" in html
        assert "70.0%" in html
        assert "85.0%" in html
        assert summary_text in html
        assert "Fixed & Verified" in html
        assert "Detected Only" in html
        assert "Fix Failed" in html
        assert "diff-block" in html
        assert "Syntax error parsing JSX" in html


class TestExecutiveSummary:
    @pytest.mark.asyncio
    async def test_executive_summary_fallback_on_llm_failure(self, sample_report):
        with patch("app.services.report_formatter_service.call_nemotron_fast", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = RuntimeError("Nebius API unreachable")

            summary = await generate_executive_summary(sample_report)
            assert isinstance(summary, str)
            assert len(summary) > 50
            assert "3 actionable accessibility violations" in summary or "3 actionable accessibility violation" in summary
            assert "1 of 3 defects" in summary or "1 of 3 defect" in summary
            assert "70.0%" in summary
            assert "85.0%" in summary


class TestSaveReportFiles:
    def test_save_report_files_writes_both_and_returns_paths(self, sample_report, tmp_path: Path):
        with patch("app.services.report_formatter_service.GENERATED_REPORTS_DIR", tmp_path):
            res = save_report_files(sample_report, "scan_test_123", executive_summary="Summary test")
            assert "markdown_path" in res
            assert "html_path" in res

            md_file = Path(res["markdown_path"])
            html_file = Path(res["html_path"])

            assert md_file.is_file()
            assert html_file.is_file()
            assert "Summary test" in md_file.read_text(encoding="utf-8")
            assert "Summary test" in html_file.read_text(encoding="utf-8")
