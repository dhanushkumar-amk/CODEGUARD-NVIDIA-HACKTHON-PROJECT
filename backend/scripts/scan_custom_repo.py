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
from app.state import update_scan, get_scan

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main():
    repo_url = "https://github.com/mdturp/transformersjs_image_superresolution"
    print("=" * 80)
    print(f"TESTING TARGET REPO: {repo_url}")
    print("=" * 80)

    # 0. Check Docker Status
    docker_up = await is_docker_available()
    print(f"[0] Docker Daemon Active: {docker_up}")
    if docker_up:
        print("    -> Real Docker Container isolation engine will be used!")
    else:
        print("    -> Warning: Docker not detected, falling back to local sandbox.")

    scan_id = "test_custom_transformersjs"
    start_time = time.time()

    # 1. Clone repository
    print("\n[Stage 1: Clone Repository]")
    repo_path = clone_repo(repo_url=repo_url, scan_id=scan_id, branch="main")
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
        branch="main",
        status="prepared",
        files=files,
        file_count=len(files),
        metadata=metadata,
        framework=metadata.get("framework", "Vanilla HTML/JS"),
        scan_batch=batch,
        batch_count=len(batch),
        start_timestamp=start_time,
    )

    # 4. Detect violations
    print("\n[Stage 3: Violation Detection]")
    violations = await detect_violations(scan_id)
    print(f"    Detected {len(violations)} accessibility violations.")
    for idx, v in enumerate(violations[:5], 1):
        print(f"    {idx}. [{v.type}] {v.description} ({v.severity}) in {v.file}:{v.line}")
    if len(violations) > 5:
        print(f"    ... and {len(violations) - 5} more.")

    # 5. Diagnose
    print("\n[Stage 4: Diagnosis & Root-Cause Analysis]")
    diagnosed = await diagnose_all(scan_id, top_n=settings.DIAGNOSIS_TOP_N)
    print(f"    Diagnosed {len(diagnosed)} violations.")

    # 6. Explanations
    print("\n[Stage 5: Plain English Explanations]")
    explained = await generate_all_explanations(scan_id)
    print(f"    Generated explanations for {len(explained)} violations.")

    # 7. Generate Fixes
    print("\n[Stage 6: Code-Fix Synthesis]")
    fixes = await generate_all_fixes(scan_id)
    proposed_count = sum(1 for f in fixes if f.status == "proposed")
    print(f"    Synthesized {len(fixes)} remediation diffs ({proposed_count} proposed).")

    # 8. Sandbox Verification
    print("\n[Stage 7: Isolated Sandbox Verification]")
    v_results = await verify_all_fixes(scan_id)
    verified_count = sum(1 for v in v_results if v.verified)
    unverified_count = sum(1 for v in v_results if not v.verified)
    print(f"    Sandbox Verification Results: {verified_count} verified, {unverified_count} unverified/manual.")

    # 9. Overall Improvement
    print("\n[Stage 8: Compliance Delta Calculation]")
    improvement = await calculate_overall_improvement(scan_id)
    print(f"    Overall score improvement: {improvement}")

    # 10. Final Report
    print("\n[Stage 9: Build Unified Report]")
    report = build_scan_report(scan_id)
    exec_summary = await generate_executive_summary(report)
    report.executive_summary = exec_summary
    update_scan(scan_id=scan_id, report=report, executive_summary=exec_summary)

    saved_paths = save_report_files(report, scan_id, executive_summary=exec_summary)
    print(f"    Saved report files: {saved_paths}")

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 80)
    print(f"SCAN COMPLETED SUCCESSFULLY in {elapsed}s!")
    print(f"Total Violations: {len(report.violations)}")
    print(f"Fixed & Verified: {verified_count}")
    print(f"Initial Score: {report.overall_score_before} -> Final Score: {report.overall_score_after}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
