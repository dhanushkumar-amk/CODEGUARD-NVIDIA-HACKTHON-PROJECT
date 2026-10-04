"""
Unit tests for Aggregator Service (Phase 22).
Covers linking violations to fixes and verifications, calculating summary stats,
and building schema-valid ScanReport objects.
"""
from datetime import datetime, timezone
import pytest

from app.models.schemas import (
    DiagnosedViolation,
    ProposedFix,
    ScanReport,
    VerificationResult,
    Violation,
    ViolationCategory,
)
from app.services.aggregator_service import (
    build_scan_report,
    calculate_summary_stats,
    link_violation_to_fix_and_verification,
)
from app.state import create_scan, get_scan, scans


@pytest.fixture
def clean_scans():
    """Clear in-memory state before and after test."""
    scans.clear()
    yield
    scans.clear()


class TestLinkViolationToFixAndVerification:
    def test_verified_fix_gets_fixed_and_verified(self, clean_scans):
        scan_id = create_scan("https://github.com/example/repo")
        scan = get_scan(scan_id)

        v1 = Violation(
            id="viol_01",
            file="src/Header.tsx",
            line=10,
            type="image-alt",
            severity="critical",
            description="Missing alt attribute",
            category=ViolationCategory.MISSING_ALT_TEXT,
        )
        f1 = ProposedFix(
            fix_id="fix_01",
            violation_id="viol_01",
            file="src/Header.tsx",
            original_lines="<img />",
            fixed_lines='<img alt="Logo" />',
            status="proposed",
        )
        vr1 = VerificationResult(
            fix_id="fix_01",
            violation_id="viol_01",
            axe_score_before=60.0,
            axe_score_after=80.0,
            verified=True,
            violations_resolved=True,
        )

        scan["violations"] = [v1]
        scan["fixes"] = [f1]
        scan["verification_results"] = [vr1]

        records = link_violation_to_fix_and_verification(scan_id)
        assert len(records) == 1
        assert records[0]["final_status"] == "fixed_and_verified"
        assert records[0]["fix"].fix_id == "fix_01"
        assert records[0]["verification"].verified is True

    def test_failed_verification_gets_fixed_not_verified(self, clean_scans):
        scan_id = create_scan("https://github.com/example/repo")
        scan = get_scan(scan_id)

        v1 = Violation(
            id="viol_02",
            file="src/Button.tsx",
            line=15,
            type="button-name",
            severity="high",
            description="Empty button",
            category=ViolationCategory.EMPTY_LINK_OR_BUTTON,
        )
        f1 = ProposedFix(
            fix_id="fix_02",
            violation_id="viol_02",
            file="src/Button.tsx",
            status="proposed",
        )
        vr1 = VerificationResult(
            fix_id="fix_02",
            violation_id="viol_02",
            axe_score_before=70.0,
            axe_score_after=70.0,
            verified=False,
            reason="accessibility_score_regressed",
        )

        scan["violations"] = [v1]
        scan["fixes"] = [f1]
        scan["verification_results"] = [vr1]

        records = link_violation_to_fix_and_verification(scan_id)
        assert len(records) == 1
        assert records[0]["final_status"] == "fixed_not_verified"

    def test_fix_validation_failure_gets_fix_failed(self, clean_scans):
        scan_id = create_scan("https://github.com/example/repo")
        scan = get_scan(scan_id)

        v1 = Violation(
            id="viol_03",
            file="src/Input.tsx",
            type="label",
            severity="critical",
            description="Unlabeled input",
            category=ViolationCategory.UNLABELED_FORM_FIELD,
        )
        f1 = ProposedFix(
            fix_id="fix_03",
            violation_id="viol_03",
            file="src/Input.tsx",
            status="failed",
            failure_reason="Could not match original snippet in source code",
        )

        scan["violations"] = [v1]
        scan["fixes"] = [f1]
        scan["verification_results"] = []

        records = link_violation_to_fix_and_verification(scan_id)
        assert len(records) == 1
        assert records[0]["final_status"] == "fix_failed"

    def test_no_fix_attempted_gets_detected_only(self, clean_scans):
        scan_id = create_scan("https://github.com/example/repo")
        scan = get_scan(scan_id)

        v1 = Violation(
            id="viol_04",
            file="src/Link.tsx",
            type="color-contrast",
            severity="low",
            description="Low contrast minor link",
            category=ViolationCategory.LOW_CONTRAST,
        )

        scan["violations"] = [v1]
        scan["fixes"] = []
        scan["verification_results"] = []

        records = link_violation_to_fix_and_verification(scan_id)
        assert len(records) == 1
        assert records[0]["final_status"] == "detected_only"
        assert records[0]["fix"] is None
        assert records[0]["verification"] is None

    def test_fix_succeeded_without_verification_gets_verification_skipped(self, clean_scans):
        scan_id = create_scan("https://github.com/example/repo")
        scan = get_scan(scan_id)

        v1 = Violation(
            id="viol_05",
            file="src/Modal.tsx",
            type="landmark",
            severity="medium",
            description="Missing landmark",
            category=ViolationCategory.MISSING_LANDMARK,
        )
        f1 = ProposedFix(
            fix_id="fix_05",
            violation_id="viol_05",
            file="src/Modal.tsx",
            status="proposed",
        )

        scan["violations"] = [v1]
        scan["fixes"] = [f1]
        scan["verification_results"] = []

        records = link_violation_to_fix_and_verification(scan_id)
        assert len(records) == 1
        assert records[0]["final_status"] == "verification_skipped"


class TestCalculateSummaryStats:
    def test_tallies_counts_across_categories_and_severities(self):
        v1 = DiagnosedViolation(
            id="v1",
            file="f1.tsx",
            type="image-alt",
            severity="critical",
            description="Alt missing",
            category=ViolationCategory.MISSING_ALT_TEXT,
            root_cause="cause",
            affected_element="img",
            user_impact="impact",
            fix_strategy="strat",
        )
        v2 = DiagnosedViolation(
            id="v2",
            file="f2.tsx",
            type="label",
            severity="high",
            description="Label missing",
            category=ViolationCategory.UNLABELED_FORM_FIELD,
            root_cause="cause",
            affected_element="input",
            user_impact="impact",
            fix_strategy="strat",
        )
        v3 = DiagnosedViolation(
            id="v3",
            file="f3.tsx",
            type="color-contrast",
            severity="low",
            description="Contrast issue",
            category=ViolationCategory.LOW_CONTRAST,
            root_cause="cause",
            affected_element="p",
            user_impact="impact",
            fix_strategy="strat",
        )

        records = [
            {"violation": v1, "fix": None, "verification": None, "final_status": "fixed_and_verified"},
            {"violation": v2, "fix": None, "verification": None, "final_status": "fixed_not_verified"},
            {"violation": v3, "fix": None, "verification": None, "final_status": "detected_only"},
        ]

        stats = calculate_summary_stats(
            unified_records=records,
            overall_score_before=60.0,
            overall_score_after=85.0,
        )

        assert stats["total_violations"] == 3
        assert stats["fixed_and_verified"] == 1
        assert stats["fixed_not_verified"] == 1
        assert stats["detected_only"] == 1
        assert stats["fix_success_rate"] == 0.333
        assert stats["by_severity"]["critical"] == 1
        assert stats["by_severity"]["high"] == 1
        assert stats["by_severity"]["low"] == 1
        assert stats["by_category"]["MISSING_ALT_TEXT"] == 1
        assert stats["by_category"]["UNLABELED_FORM_FIELD"] == 1
        assert stats["by_category"]["LOW_CONTRAST"] == 1
        assert stats["improvement_points"] == 25.0


class TestBuildScanReport:
    def test_produces_schema_valid_scan_report(self, clean_scans):
        scan_id = create_scan("https://github.com/example/repo")
        scan = get_scan(scan_id)

        v1 = Violation(
            id="viol_01",
            file="src/Header.tsx",
            line=21,
            type="image-alt",
            severity="critical",
            description="Missing alt",
            category=ViolationCategory.MISSING_ALT_TEXT,
        )
        f1 = ProposedFix(
            fix_id="fix_01",
            violation_id="viol_01",
            file="src/Header.tsx",
            original_lines="<img />",
            fixed_lines='<img alt="Logo" />',
            status="proposed",
        )
        vr1 = VerificationResult(
            fix_id="fix_01",
            violation_id="viol_01",
            axe_score_before=70.0,
            axe_score_after=90.0,
            verified=True,
            violations_resolved=True,
        )

        scan["violations"] = [v1]
        scan["fixes"] = [f1]
        scan["verification_results"] = [vr1]
        scan["overall_score_before"] = 70.0
        scan["overall_score_after"] = 90.0

        report: ScanReport = build_scan_report(scan_id)

        assert isinstance(report, ScanReport)
        assert report.scan_id == scan_id
        assert report.status == "completed"
        assert report.overall_score_before == 70.0
        assert report.overall_score_after == 90.0
        assert report.overall_improvement.improvement_points == 20.0
        assert len(report.unified_records) == 1
        assert report.unified_records[0].final_status == "fixed_and_verified"
        assert report.summary["fixed_and_verified"] == 1
        assert report.cost_breakdown is not None
        assert report.timestamp is not None
