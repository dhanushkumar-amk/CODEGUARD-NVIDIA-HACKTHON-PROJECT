import asyncio
import json
import logging
from pathlib import Path
import sys
import time

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.services.git_service import clone_repo, find_frontend_files, get_repo_metadata
from app.services.scanner_service import prepare_scan_batch
from app.services.detector_service import detect_violations
from app.services.diagnosis_service import diagnose_all
from app.services.explainer_service import generate_all_explanations
from app.services.fixer_service import generate_all_fixes
from app.services.verification_service import verify_all_fixes, calculate_overall_improvement
from app.services.aggregator_service import build_scan_report
from app.services.report_formatter_service import generate_executive_summary, save_report_files
from app.services.sandbox_client import is_docker_available
from app.services.github_service import create_remediation_pr
from app.state import update_scan, get_scan, create_scan

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main():
    repo_url = "https://github.com/dhanushkumar-amk/Clinic-Application"
    branch = "main"
    print("=" * 80)
    print(f"CODEGUARD END-TO-END AUDIT & REMEDIATION PIPELINE")
    print(f"Target Repository: {repo_url}")
    print(f"Target Branch: {branch}")
    print("=" * 80)

    # 0. Check Docker Status
    docker_up = await is_docker_available()
    print(f"[0] Docker Daemon Active: {docker_up}")
    if docker_up:
        print("    -> Real Docker Container isolation engine will be used!")
    else:
        print("    -> Docker not active: using fast local workspace sandbox engine.")

    # 1. Create scan state and clone repository
    scan_id = create_scan(repo_url=repo_url, branch=branch)
    start_time = time.time()

    print("\n[Stage 1: Clone Repository]")
    repo_path = clone_repo(repo_url=repo_url, scan_id=scan_id, branch=branch)
    print(f"    Repository cloned to: {repo_path}")

    # 2. Discover UI files & metadata
    files = find_frontend_files(repo_path)
    metadata = get_repo_metadata(repo_path)
    print(f"    Discovered {len(files)} frontend UI files: {files}")
    print(f"    Detected framework: {metadata.get('framework', 'Vanilla HTML/JS')}")

    # 3. Batch prepare
    batch = prepare_scan_batch(repo_path, files)
    print(f"\n[Stage 2: Markup Extraction] Extracted {len(batch)} chunks for scanning.")

    update_scan(
        scan_id=scan_id,
        repo_path=repo_path,
        repo_url=repo_url,
        branch=branch,
        status="prepared",
        files=files,
        file_count=len(files),
        metadata=metadata,
        framework=metadata.get("framework", "Vanilla HTML/JS"),
        scan_batch=batch,
        batch_count=len(batch),
        start_timestamp=start_time,
        is_active_real_scan=True,
    )

    # 4. Detect violations
    print("\n[Stage 3: Violation Detection]")
    violations = await detect_violations(scan_id)
    print(f"    Detected {len(violations)} accessibility violations.")
    for idx, v in enumerate(violations, 1):
        print(f"    {idx}. [{v.type}] {v.description} ({v.severity}) in {v.file}:{v.line}")

    # 5. Diagnose
    print("\n[Stage 4: Diagnosis & Tavily Web Grounding]")
    diagnosed = await diagnose_all(scan_id, top_n=min(len(violations), settings.DIAGNOSIS_TOP_N or 10))
    print(f"    Diagnosed {len(diagnosed)} violations with WCAG grounding.")

    # 6. Explanations
    print("\n[Stage 5: Plain English Explanations]")
    explained = await generate_all_explanations(scan_id)
    print(f"    Generated explanations for {len(explained)} violations.")

    # 7. Generate Fixes
    print("\n[Stage 6: Code-Fix Synthesis via Nemotron Ultra]")
    fixes = await generate_all_fixes(scan_id)
    proposed_count = sum(1 for f in fixes if f.status == "proposed")
    print(f"    Synthesized {len(fixes)} remediation diffs ({proposed_count} proposed).")
    for f in fixes:
        status_tag = f.status.upper()
        if f.status == "proposed":
            print(f"    - [{status_tag}] {f.fix_id} on {f.file}:{f.line_start} (confidence: {f.confidence})")
        else:
            print(f"    - [{status_tag}] {f.fix_id} on {f.file}: {f.failure_reason}")

    # 8. Sandbox Verification
    print("\n[Stage 7: Isolated Sandbox Verification & Regression Testing]")
    v_results = await verify_all_fixes(scan_id)
    verified_count = sum(1 for v in v_results if v.verified)
    unverified_count = sum(1 for v in v_results if not v.verified)
    print(f"    Sandbox Verification Results: {verified_count} verified, {unverified_count} unverified/manual.")
    for vr in v_results:
        ver_tag = "VERIFIED PASS" if vr.verified else "UNVERIFIED"
        print(f"    - [{ver_tag}] {vr.fix_id} (before: {vr.axe_score_before} -> after: {vr.axe_score_after}, tests_passed: {vr.tests_passed})")

    # 9. Overall Improvement
    print("\n[Stage 8: Compliance Delta Calculation]")
    improvement = await calculate_overall_improvement(scan_id)
    print(f"    Overall score improvement: {improvement}")

    # 10. Final Report
    print("\n[Stage 9: Build Unified Audit Report]")
    report = build_scan_report(scan_id)
    exec_summary = await generate_executive_summary(report)
    report.executive_summary = exec_summary
    update_scan(scan_id=scan_id, report=report, executive_summary=exec_summary)

    saved_paths = save_report_files(report, scan_id, executive_summary=exec_summary)
    print(f"    Saved report files: {saved_paths}")

    # 11. Automated PR Creation
    print("\n[Stage 10: Automated GitHub Pull Request Creation]")
    pr_result = create_remediation_pr(repo_url=repo_url, scan_id=scan_id)
    print(f"    PR Result: {json.dumps(pr_result, indent=2)}")

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 80)
    print(f"E2E PIPELINE EXECUTION FINISHED in {elapsed}s!")
    print(f"Scan ID: {scan_id}")
    print(f"Total Violations: {len(report.violations)}")
    print(f"Verified Fixes: {verified_count}")
    print(f"Initial Score: {report.overall_score_before} -> Remediated Score: {report.overall_score_after}")
    if pr_result.get("status") == "success":
        print(f"SUCCESS: Remediation Pull Request opened at: {pr_result.get('pr_url')}")
    else:
        print(f"PR Creation note: {pr_result.get('error')}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
