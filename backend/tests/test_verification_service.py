"""
Unit tests for Verification Service (Phase 20).
Covers:
- A fix that improves the score and passes tests -> verified=True
- A fix that doesn't remove its targeted violation -> verified=False
- A fix application failure skips axe-core entirely without crashing
- A project with no test suite doesn't block verification (tests_passed=None handled gracefully)
- calculate_overall_improvement correctly aggregates multiple verified fixes into one final combined score
"""
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from app.models.schemas import ProposedFix, VerificationResult, Violation, ViolationCategory
from app.services.sandbox_client import CommandResult
from app.services.verification_service import (
    calculate_overall_improvement,
    get_baseline_score,
    verify_all_fixes,
    verify_single_fix,
)
from app.state import create_scan, get_scan


@pytest.mark.asyncio
async def test_fix_improves_score_and_passes_tests():
    """Ensure a fix that improves compliance score and passes tests receives verified=True."""
    scan_id = create_scan("https://github.com/example/test-repo")
    scan = get_scan(scan_id)
    scan["overall_score_before"] = 70.0
    scan["repo_path"] = "/tmp/mock-repo"

    fix = ProposedFix(
        fix_id="fix_good_01",
        violation_id="viol_good_01",
        file="src/App.tsx",
        original_lines='<img src="logo.png" />',
        fixed_lines='<img src="logo.png" alt="Company Logo" />',
        status="proposed",
    )

    with patch("app.services.verification_service.apply_and_prepare_fix", new_callable=AsyncMock) as mock_prep, \
         patch("app.services.verification_service.run_axe_check", new_callable=AsyncMock) as mock_axe, \
         patch("app.services.verification_service.run_test_suite", new_callable=AsyncMock) as mock_test_suite, \
         patch("app.services.verification_service.destroy_sandbox", new_callable=AsyncMock) as mock_destroy:

        mock_prep.return_value = {"status": "applied", "sandbox_id": "sb-verify-good"}
        # After score improves from 70.0 to 85.0, targeted violation cleared
        mock_axe.return_value = {
            "score": 85.0,
            "violations": [],
            "passes": 30,
        }
        # run_test_suite reports passed
        from app.models.schemas import TestRunResult
        mock_test_suite.return_value = TestRunResult(
            status="passed",
            passed=True,
            passed_count=5,
            failed_count=0,
            raw_output="PASS 5/5 tests",
            duration_seconds=1.2,
        )

        result: VerificationResult = await verify_single_fix(
            fix=fix,
            repo_path="/tmp/mock-repo",
            scan_id=scan_id,
            base_score=70.0,
        )

        assert result.verified is True
        assert result.axe_score_before == 70.0
        assert result.axe_score_after == 85.0
        assert result.violation_still_present is False
        assert result.tests_passed is True
        assert result.reason is None
        mock_destroy.assert_called_once_with("sb-verify-good")


@pytest.mark.asyncio
async def test_fix_does_not_remove_targeted_violation():
    """Ensure a fix that leaves the targeted defect in the axe audit receives verified=False."""
    scan_id = create_scan("https://github.com/example/test-repo")
    scan = get_scan(scan_id)
    scan["overall_score_before"] = 70.0

    viol = Violation(
        id="viol_img_01",
        file="src/Header.tsx",
        type="image-alt",
        description="Missing alt attribute",
        category=ViolationCategory.MISSING_ALT_TEXT,
    )
    scan["violations"] = [viol]

    fix = ProposedFix(
        fix_id="fix_flawed_01",
        violation_id="viol_img_01",
        file="src/Header.tsx",
        original_lines='<img src="avatar.png" />',
        fixed_lines='<img src="avatar.png" class="rounded" />',  # didn't add alt!
        status="proposed",
    )

    with patch("app.services.verification_service.apply_and_prepare_fix", new_callable=AsyncMock) as mock_prep, \
         patch("app.services.verification_service.run_axe_check", new_callable=AsyncMock) as mock_axe, \
         patch("app.services.verification_service.run_command", new_callable=AsyncMock) as mock_cmd, \
         patch("app.services.verification_service.destroy_sandbox", new_callable=AsyncMock):

        mock_prep.return_value = {"status": "applied", "sandbox_id": "sb-verify-flawed"}
        # Target defect still returned in axe output
        mock_axe.return_value = {
            "score": 70.0,
            "violations": [
                {
                    "id": "image-alt",
                    "nodes": [{"html": '<img src="avatar.png" class="rounded" />'}],
                }
            ],
            "passes": 20,
        }
        mock_cmd.return_value = CommandResult(stdout="Tests pass", exit_code=0)

        result = await verify_single_fix(
            fix=fix,
            repo_path="/tmp/mock-repo",
            scan_id=scan_id,
            base_score=70.0,
        )

        assert result.verified is False
        assert result.violation_still_present is True
        assert result.reason in ("violation_still_present_in_audit", "no_measurable_improvement")


@pytest.mark.asyncio
async def test_fix_application_failure_skips_axe_core():
    """Ensure fix application failure skips axe check entirely and marks verified=False."""
    scan_id = create_scan("https://github.com/example/test-repo")

    fix = ProposedFix(
        fix_id="fix_cant_apply",
        violation_id="viol_missing",
        file="src/NonExistent.tsx",
        original_lines="<div>foo</div>",
        fixed_lines="<div>bar</div>",
    )

    with patch("app.services.verification_service.apply_and_prepare_fix", new_callable=AsyncMock) as mock_prep, \
         patch("app.services.verification_service.run_axe_check", new_callable=AsyncMock) as mock_axe:

        mock_prep.return_value = {
            "status": "failed",
            "sandbox_id": None,
            "error": "Could not locate original snippet",
        }

        result = await verify_single_fix(
            fix=fix,
            repo_path="/tmp/mock-repo",
            scan_id=scan_id,
            base_score=75.0,
        )

        assert result.verified is False
        assert "fix_application_failed" in (result.reason or "")
        mock_axe.assert_not_called()


@pytest.mark.asyncio
async def test_project_with_no_test_suite_does_not_block_verification():
    """Ensure projects without npm test scripts have tests_passed=None and verify successfully."""
    scan_id = create_scan("https://github.com/example/no-tests-repo")

    fix = ProposedFix(
        fix_id="fix_no_tests",
        violation_id="viol_btn_01",
        file="src/Button.tsx",
        original_lines="<button><i></i></button>",
        fixed_lines='<button aria-label="Refresh"><i></i></button>',
    )

    with patch("app.services.verification_service.apply_and_prepare_fix", new_callable=AsyncMock) as mock_prep, \
         patch("app.services.verification_service.run_axe_check", new_callable=AsyncMock) as mock_axe, \
         patch("app.services.verification_service.run_command", new_callable=AsyncMock) as mock_cmd, \
         patch("app.services.verification_service.destroy_sandbox", new_callable=AsyncMock):

        mock_prep.return_value = {"status": "applied", "sandbox_id": "sb-no-tests"}
        mock_axe.return_value = {"score": 82.0, "violations": []}
        # npm test reports missing script
        mock_cmd.return_value = CommandResult(
            stdout="",
            stderr="npm ERR! Missing script: test",
            exit_code=1,
        )

        result = await verify_single_fix(
            fix=fix,
            repo_path="/tmp/mock-repo",
            scan_id=scan_id,
            base_score=75.0,
        )

        assert result.verified is True
        assert result.tests_passed is None
        assert result.axe_score_after == 82.0


@pytest.mark.asyncio
async def test_calculate_overall_improvement_aggregates_verified_fixes():
    """Ensure calculate_overall_improvement applies all verified fixes together for final combined score."""
    scan_id = create_scan("https://github.com/example/combined-repo")
    scan = get_scan(scan_id)
    scan["overall_score_before"] = 72.0
    scan["repo_path"] = "/tmp/combined-repo"

    fix1 = ProposedFix(fix_id="fix_01", violation_id="viol_01", file="src/Header.tsx", original_lines="a", fixed_lines="b")
    fix2 = ProposedFix(fix_id="fix_02", violation_id="viol_02", file="src/Footer.tsx", original_lines="c", fixed_lines="d")
    scan["fixes"] = [fix1, fix2]

    scan["verification_results"] = [
        VerificationResult(fix_id="fix_01", axe_score_before=72.0, axe_score_after=80.0, verified=True),
        VerificationResult(fix_id="fix_02", axe_score_before=72.0, axe_score_after=82.0, verified=True),
    ]

    with patch("app.services.verification_service.prepare_verification_sandbox", new_callable=AsyncMock) as mock_prep_sb, \
         patch("app.services.verification_service.read_file_from_sandbox", new_callable=AsyncMock) as mock_read, \
         patch("app.services.verification_service.apply_fix_to_file", return_value="patched"), \
         patch("app.services.verification_service.upload_files", new_callable=AsyncMock) as mock_upload, \
         patch("app.services.verification_service.run_axe_check", new_callable=AsyncMock) as mock_axe, \
         patch("app.services.verification_service.destroy_sandbox", new_callable=AsyncMock) as mock_destroy:

        mock_prep_sb.return_value = "sb-combined-all"
        mock_read.return_value = "original file"
        mock_axe.return_value = {"score": 92.5, "violations": []}

        summary = await calculate_overall_improvement(scan_id)

        assert summary["score_before"] == 72.0
        assert summary["score_after"] == 92.5
        assert summary["improvement_points"] == 20.5
        assert summary["fixes_verified"] == 2
        assert summary["fixes_failed"] == 0
        assert scan["overall_score_after"] == 92.5
        assert scan["status"] == "completed"
        mock_destroy.assert_called_once_with("sb-combined-all")
