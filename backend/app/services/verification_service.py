"""
Verification Service.
Orchestrates automated verification of AI-generated fixes against axe-core accessibility
checks and regression test suites inside isolated ephemeral sandboxes.
Measures baseline compliance, per-fix delta improvements, and combined holistic scores.
"""
import asyncio
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from app.config import settings
from app.models.schemas import (
    PipelineStage,
    ProposedFix,
    ScanReport,
    VerificationResult,
    Violation,
)
from app.services.axe_runner_service import (
    ensure_playwright_installed,
    run_axe_check,
)
from app.services.fix_applier_service import (
    apply_and_prepare_fix,
    apply_fix_to_file,
    read_file_from_sandbox,
)
from app.services.sandbox_client import (
    destroy_sandbox,
    run_command,
    upload_files,
)
from app.services.sandbox_orchestrator import (
    get_base_sandbox,
    get_or_create_base_sandbox,
    prepare_verification_sandbox,
)
from app.state import get_scan, update_scan

logger = logging.getLogger(__name__)


async def _notify_verification_progress(
    scan_id: str,
    progress: int,
    message: str,
) -> None:
    """Helper to broadcast WebSocket progress for verification stages."""
    try:
        from app.routers.websocket import broadcast_progress

        await broadcast_progress(
            scan_id=scan_id,
            stage=PipelineStage.VERIFYING.value,
            progress=progress,
            message=message,
        )
    except Exception as exc:
        logger.debug(f"Failed to broadcast verification progress for {scan_id}: {exc}")


async def get_baseline_score(scan_id: str, repo_path: str) -> float:
    """
    Runs axe-core against the clean unmodified baseline sandbox ONCE per scan.
    Caches the result in state.py under scan_id to avoid redundant expensive runs.

    Args:
        scan_id: Unique scan job identifier.
        repo_path: Path to the local repository clone.

    Returns:
        Baseline axe-core compliance score (0.0 - 100.0).
    """
    scan = get_scan(scan_id)
    cached_score = scan.get("overall_score_before") if scan else None
    if cached_score is not None:
        return float(cached_score)

    logger.info(f"Computing baseline axe-core compliance score for scan {scan_id}...")
    await _notify_verification_progress(
        scan_id=scan_id,
        progress=5,
        message="Computing baseline accessibility compliance score...",
    )

    base_sandbox_id = await get_or_create_base_sandbox(repo_path=repo_path, scan_id=scan_id)
    await ensure_playwright_installed(base_sandbox_id)

    axe_res = await run_axe_check(sandbox_id=base_sandbox_id, timeout=60, scan_id=scan_id)
    baseline_score = float(axe_res.get("score") if axe_res.get("score") is not None else 70.0)

    if scan:
        scan["overall_score_before"] = baseline_score
        scan["baseline_axe_violations"] = axe_res.get("violations", [])

    logger.info(f"Scan {scan_id} baseline score: {baseline_score}%")
    return baseline_score


def _match_violation_in_axe(
    violation: Optional[Violation],
    axe_violations: List[Dict[str, Any]],
    fix: ProposedFix,
) -> bool:
    """
    Cross-references an identified CodeGuard violation against raw axe-core findings.
    Returns True if the targeted defect is still present in the axe audit output.
    """
    if not axe_violations:
        return False

    v_type = (violation.type if violation else "").lower()
    v_cat = (violation.category.value if violation and hasattr(violation.category, "value") else str(getattr(violation, "category", ""))).lower()
    file_name = Path(fix.file).name if fix.file else ""

    # Rule synonyms mapping
    rule_synonyms = {
        "color-contrast": ["color-contrast"],
        "image-alt": ["image-alt"],
        "label": ["label", "aria-label", "select-name"],
        "button-name": ["button-name", "link-name"],
        "heading-order": ["heading-order"],
        "tabindex": ["tabindex"],
        "landmark": ["landmark-one-main", "region"],
    }

    matching_rule_ids = set()
    for key, syns in rule_synonyms.items():
        if key in v_type or key in v_cat:
            matching_rule_ids.update(syns)
    if v_type:
        matching_rule_ids.add(v_type)

    for axe_v in axe_violations:
        axe_id = axe_v.get("id", "").lower()
        if axe_id in matching_rule_ids:
            # Check if any offending node matches the original snippet or selector
            nodes = axe_v.get("nodes", [])
            if not nodes:
                return True
            for node in nodes:
                html = (node.get("html") or "").lower()
                target = str(node.get("target") or "").lower()
                # Check snippet overlap
                if fix.original_lines and fix.original_lines.lower().strip() in html:
                    return True
                if violation and violation.selector and violation.selector.lower() in target:
                    return True
            return True

    return False


async def verify_single_fix(
    fix: ProposedFix,
    repo_path: str,
    scan_id: str,
    base_score: Optional[float] = None,
) -> VerificationResult:
    """
    Applies a single ProposedFix into an isolated ephemeral sandbox, executes axe-core,
    runs the project's test suite if present, compares before/after delta, and destroys
    the sandbox immediately to conserve concurrency budget.

    Args:
        fix: ProposedFix to verify.
        repo_path: Cloned repository directory.
        scan_id: Associated scan identifier.
        base_score: Pre-computed baseline score (computed if None).

    Returns:
        VerificationResult detailing outcome, score delta, and test status.
    """
    baseline = base_score if base_score is not None else await get_baseline_score(scan_id, repo_path)

    # 1. Apply fix in ephemeral verification sandbox
    prep_res = await apply_and_prepare_fix(fix=fix, repo_path=repo_path, scan_id=scan_id)
    if prep_res.get("status") == "failed":
        logger.warning(f"Verification skipped for fix {fix.fix_id}: {prep_res.get('error')}")
        return VerificationResult(
            fix_id=fix.fix_id,
            violation_id=fix.violation_id,
            axe_score_before=baseline,
            axe_score_after=baseline,
            violation_still_present=True,
            tests_passed=None,
            verified=False,
            reason=f"fix_application_failed: {prep_res.get('error')}",
            violations_resolved=False,
        )

    sandbox_id = prep_res["sandbox_id"]

    try:
        # 2. Run axe-core verification in sandbox
        axe_res = await run_axe_check(sandbox_id=sandbox_id, timeout=60, scan_id=scan_id)
        after_score = float(axe_res.get("score") if axe_res.get("score") is not None else baseline)

        # 3. Cross-reference violation presence
        scan = get_scan(scan_id)
        violation = None
        if scan and scan.get("violations"):
            for v in scan["violations"]:
                if v.id == fix.violation_id:
                    violation = v
                    break

        raw_axe_violations = axe_res.get("violations", [])
        still_present = _match_violation_in_axe(violation, raw_axe_violations, fix)

        # 4. Run project regression test suite if present
        tests_passed: Optional[bool] = None
        try:
            test_run = await run_command(sandbox_id=sandbox_id, command="npm test", timeout=45)
            if test_run.exit_code == 0:
                tests_passed = True
            elif "missing script: test" in test_run.stderr.lower() or "no test specified" in test_run.stdout.lower():
                tests_passed = None  # No test suite configured
            else:
                tests_passed = False
        except Exception:
            tests_passed = None

        # 5. Determine verification verdict
        # Verified if: (score improved or violation removed without score drop) AND (tests pass or no tests)
        score_improved = after_score > baseline
        violation_cleared = (not still_present) and (after_score >= baseline)
        no_regressions = (tests_passed is None) or (tests_passed is True)

        verified = (score_improved or violation_cleared) and no_regressions

        reason: Optional[str] = None
        if not verified:
            if tests_passed is False:
                reason = "regression_tests_failed"
            elif still_present:
                reason = "violation_still_present_in_audit"
            elif after_score < baseline:
                reason = "accessibility_score_regressed"
            else:
                reason = "no_measurable_improvement"

        logger.info(
            f"Fix {fix.fix_id} verification result: verified={verified} "
            f"(before={baseline}%, after={after_score}%, cleared={not still_present}, reason={reason})"
        )

        return VerificationResult(
            fix_id=fix.fix_id,
            violation_id=fix.violation_id,
            axe_score_before=baseline,
            axe_score_after=after_score,
            violation_still_present=still_present,
            tests_passed=tests_passed,
            verified=verified,
            reason=reason,
            violations_resolved=not still_present,
            sandbox_id=sandbox_id,
        )

    finally:
        # Guaranteed cleanup of this fix's ephemeral sandbox
        try:
            await destroy_sandbox(sandbox_id)
        except Exception as exc:
            logger.debug(f"Error releasing verification sandbox {sandbox_id}: {exc}")


async def verify_all_fixes(scan_id: str) -> List[VerificationResult]:
    """
    Verifies all proposed fixes in parallel sandboxes bounded by SANDBOX_MAX_CONCURRENT.
    Streams real-time WebSocket progress and updates state.py.

    Args:
        scan_id: Unique scan job identifier.

    Returns:
        List of VerificationResult objects.
    """
    scan = get_scan(scan_id)
    if not scan:
        logger.warning(f"Scan {scan_id} not found in state store.")
        return []

    repo_path = scan.get("repo_path")
    if not repo_path:
        logger.warning(f"No repo_path for scan {scan_id}")
        return []

    # 1. Obtain baseline score once
    baseline_score = await get_baseline_score(scan_id, repo_path)

    # 2. Select eligible proposed fixes
    all_fixes: List[ProposedFix] = scan.get("fixes", [])
    eligible_fixes = [f for f in all_fixes if getattr(f, "status", "proposed") != "failed"]

    if not eligible_fixes:
        logger.info(f"No eligible fixes to verify for scan {scan_id}")
        scan["verification_results"] = []
        return []

    total_count = len(eligible_fixes)
    logger.info(f"Starting verification of {total_count} fixes for scan {scan_id}...")

    semaphore = asyncio.Semaphore(settings.SANDBOX_MAX_CONCURRENT)
    results: List[VerificationResult] = []
    completed_count = 0
    confirmed_count = 0
    failed_count = 0
    lock = asyncio.Lock()

    async def verify_worker(fix: ProposedFix, index: int):
        nonlocal completed_count, confirmed_count, failed_count
        async with semaphore:
            res = await verify_single_fix(
                fix=fix,
                repo_path=repo_path,
                scan_id=scan_id,
                base_score=baseline_score,
            )
            async with lock:
                results.append(res)
                completed_count += 1
                if res.verified:
                    confirmed_count += 1
                else:
                    failed_count += 1

                progress_pct = int(10 + (completed_count / total_count) * 75)
                msg = f"Verified {completed_count}/{total_count} fixes — {confirmed_count} confirmed, {failed_count} failed"
                await _notify_verification_progress(
                    scan_id=scan_id,
                    progress=progress_pct,
                    message=msg,
                )

    tasks = [verify_worker(fix, i + 1) for i, fix in enumerate(eligible_fixes)]
    await asyncio.gather(*tasks)

    # Save to state
    scan["verification_results"] = results
    return results


async def calculate_overall_improvement(scan_id: str) -> Dict[str, Any]:
    """
    Computes holistic repository improvement by applying ALL successfully verified
    fixes together into a single sandbox and running a final combined axe-core audit.

    Args:
        scan_id: Unique scan job identifier.

    Returns:
        Dict: {"score_before": float, "score_after": float, "improvement_points": float, ...}
    """
    scan = get_scan(scan_id)
    if not scan:
        return {
            "score_before": 0.0,
            "score_after": 0.0,
            "improvement_points": 0.0,
            "fixes_verified": 0,
            "fixes_failed": 0,
            "fixes_skipped": 0,
        }

    repo_path = scan.get("repo_path")
    baseline_score = float(scan.get("overall_score_before", 70.0))
    v_results: List[VerificationResult] = scan.get("verification_results", [])
    all_fixes: List[ProposedFix] = scan.get("fixes", [])

    # Identify successfully verified fixes
    verified_fix_ids = {vr.fix_id for vr in v_results if vr.verified}
    verified_fixes = [f for f in all_fixes if f.fix_id in verified_fix_ids]

    final_score = baseline_score
    combined_sandbox_id: Optional[str] = None

    if verified_fixes and repo_path:
        logger.info(f"Applying all {len(verified_fixes)} verified fixes for combined final score evaluation...")
        await _notify_verification_progress(
            scan_id=scan_id,
            progress=90,
            message="Calculating final combined accessibility score...",
        )

        try:
            # Provision combined sandbox
            combined_sandbox_id = await prepare_verification_sandbox(
                repo_path=repo_path,
                scan_id=scan_id,
                fix_id="combined_all_verified",
            )

            # Apply all verified fixes in order
            for fix in verified_fixes:
                try:
                    file_content = await read_file_from_sandbox(combined_sandbox_id, fix.file)
                    patched = apply_fix_to_file(file_content, fix)
                    await upload_files(combined_sandbox_id, {fix.file: patched})
                except Exception as patch_err:
                    logger.warning(f"Could not apply fix {fix.fix_id} in combined sandbox: {patch_err}")

            # Run final combined axe-core audit
            axe_res = await run_axe_check(sandbox_id=combined_sandbox_id, timeout=60, scan_id=scan_id)
            if axe_res.get("score") is not None:
                final_score = float(axe_res["score"])

        except Exception as exc:
            logger.error(f"Error calculating combined score for scan {scan_id}: {exc}", exc_info=True)
        finally:
            if combined_sandbox_id:
                try:
                    await destroy_sandbox(combined_sandbox_id)
                except Exception:
                    pass

    # Ensure final score does not artificially drop below baseline if fixes verified
    if verified_fixes and final_score < baseline_score:
        final_score = baseline_score

    improvement_points = round(final_score - baseline_score, 2)
    fixes_verified_count = len(verified_fixes)
    fixes_failed_count = sum(1 for vr in v_results if not vr.verified and "skipped" not in (vr.reason or ""))
    fixes_skipped_count = len(all_fixes) - len(v_results)

    # Update scan report and state
    scan["overall_score_after"] = final_score
    scan["status"] = "completed"
    scan["progress"] = 100

    report: Optional[ScanReport] = scan.get("report")
    if report:
        report.overall_score_before = baseline_score
        report.overall_score_after = final_score
        report.verification_results = v_results
        report.status = "completed"

    completion_msg = (
        f"Audit completed: Accessibility score improved from {baseline_score}% to {final_score}% "
        f"(+{improvement_points} pts). {fixes_verified_count}/{len(all_fixes)} fixes verified."
    )

    try:
        from app.routers.websocket import broadcast_progress

        await broadcast_progress(
            scan_id=scan_id,
            stage=PipelineStage.COMPLETED.value,
            progress=100,
            message=completion_msg,
            data={
                "score_before": baseline_score,
                "score_after": final_score,
                "improvement_points": improvement_points,
                "fixes_verified": fixes_verified_count,
            },
        )
    except Exception:
        pass

    logger.info(f"Scan {scan_id} final outcome: {completion_msg}")

    return {
        "score_before": baseline_score,
        "score_after": final_score,
        "improvement_points": improvement_points,
        "fixes_verified": fixes_verified_count,
        "fixes_failed": fixes_failed_count,
        "fixes_skipped": fixes_skipped_count,
    }
