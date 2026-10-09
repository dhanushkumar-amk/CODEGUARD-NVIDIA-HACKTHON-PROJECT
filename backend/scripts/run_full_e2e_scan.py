import asyncio
import json
import logging
from pathlib import Path
import sys
import time

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.services.git_service import find_frontend_files
from app.services.scanner_service import prepare_scan_batch
from app.services.detector_service import detect_violations
from app.services.diagnosis_service import diagnose_all
from app.services.explainer_service import generate_all_explanations
from app.services.fixer_service import generate_all_fixes
from app.services.verification_service import verify_all_fixes, calculate_overall_improvement
from app.services.aggregator_service import build_scan_report
from app.services.report_formatter_service import generate_executive_summary, save_report_files
from app.state import update_scan, get_scan

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main():
    repo_root = backend_dir.parent / "sandbox-scripts" / "demo-app"
    print("=" * 80)
    print("RUNNING COMPLETE CODEGUARD PIPELINE ON DEMO REPO")
    print(f"Target: {repo_root.resolve()}")
    print("=" * 80)

    start_time = time.time()
    scan_id = "test_run_e2e_demo"

    # 1. Discover files
    files = find_frontend_files(str(repo_root))
    print(f"[Stage 1: Clone & Discover] Discovered {len(files)} files: {files}")

    # 2. Batch prepare
    batch = prepare_scan_batch(str(repo_root), files)
    print(f"[Stage 2: Markup Extraction] Extracted {len(batch)} chunks")

    update_scan(
        scan_id=scan_id,
        repo_path=str(repo_root),
        repo_url="sandbox-scripts/demo-app",
        branch="main",
        status="prepared",
        files=files,
        file_count=len(files),
        scan_batch=batch,
        batch_count=len(batch),
        start_timestamp=start_time,
    )

    # 3. Detect violations
    print("[Stage 3: Detection] Running AST and heuristic detection...")
    violations = await detect_violations(scan_id)
    print(f"    Detected {len(violations)} accessibility violations.")

    # 4. Diagnose
    print("[Stage 4: Diagnosis & Grounding] Running diagnosis with Nemotron Ultra...")
    diagnosed = await diagnose_all(scan_id, top_n=settings.DIAGNOSIS_TOP_N)
    print(f"    Diagnosed {len(diagnosed)} violations.")

    # 5. Explain
    print("[Stage 5: Plain English Explanations] Generating explanations with Nemotron Fast...")
    explained = await generate_all_explanations(scan_id)
    print(f"    Generated explanations for {len(explained)} violations.")

    # 6. Generate Fixes
    print("[Stage 6: Fix Synthesis] Synthesizing remediation patches with Nemotron Ultra...")
    fixes = await generate_all_fixes(scan_id)
    proposed_count = sum(1 for f in fixes if f.status == "proposed")
    print(f"    Synthesized {len(fixes)} fixes ({proposed_count} proposed).")

    # 7. Verification
    print("[Stage 7: Isolated Sandbox Verification] Executing verification...")
    v_results = await verify_all_fixes(scan_id)
    verified_count = sum(1 for v in v_results if v.verified)
    unverified_count = sum(1 for v in v_results if not v.verified)
    print(f"    Verification results: {verified_count} verified, {unverified_count} unverified/failed.")

    # 8. Holistic Improvement
    print("[Stage 8: Improvement Calculation] Calculating score delta...")
    improvement = await calculate_overall_improvement(scan_id)

    # 9. Build Report & Executive Summary
    print("[Stage 9: Report Aggregation] Building final unified ScanReport...")
    report = build_scan_report(scan_id)
    exec_summary = await generate_executive_summary(report)
    report.executive_summary = exec_summary
    update_scan(scan_id=scan_id, report=report, executive_summary=exec_summary)

    # 10. Save Report files to disk
    save_report_files(report, scan_id, executive_summary=exec_summary)

    elapsed_time = round(time.time() - start_time, 2)

    print("\n" + "=" * 80)
    print("PIPELINE EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Total Violations:          {len(report.violations)}")
    print(f"Proposed Fixes:            {len(report.fixes)}")
    print(f"Fixes Verified:            {report.summary.get('fixed_and_verified', 0)}")
    print(f"Fixes Unverified:          {report.summary.get('fixed_not_verified', 0)}")
    print(f"Baseline Score:            {report.overall_score_before}")
    print(f"Remediated Score:          {report.overall_score_after}")
    print(f"Elapsed Time:              {elapsed_time}s")
    print(f"Status:                    {report.status}")
    print(f"Executive Summary:         {exec_summary}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
