"""
Full End-to-End Pipeline Execution Script (Phases 12 -> 13 -> 14 -> 15 -> 16):
Runs clone/prepare -> detect -> classify -> diagnose -> explain -> generate_fixes against the seeded demo app.
Outputs:
1. Classified and Diagnosed violations with plain_explanation and root-cause details.
2. The generated unified diffs for 3-5 planted bugs.
3. Any fixes that failed validation, and why.
4. Token usage and cost metrics (Fast vs Ultra) from /test-llm/cost.
"""
import asyncio
import json
import logging
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.services.git_service import find_frontend_files
from app.services.scanner_service import prepare_scan_batch
from app.services.detector_service import detect_violations
from app.services.diagnosis_service import diagnose_all
from app.services.explainer_service import generate_all_explanations
from app.services.fixer_service import generate_all_fixes
from app.services.llm_client import (
    get_cost_breakdown,
    get_token_usage_stats,
    reset_cost_tracker,
)
from app.state import create_scan, get_scan, update_scan

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main():
    repo_root = backend_dir.parent / "sandbox-scripts" / "demo-app"
    print("=" * 80)
    print("CODEGUARD FULL PIPELINE EXECUTION (PHASE 12 -> 13 -> 14 -> 15 -> 16)")
    print(f"Demo Target: {repo_root.resolve()}")
    print("=" * 80)

    reset_cost_tracker()

    # Step 1: Discover frontend UI files
    files = find_frontend_files(str(repo_root))
    print(f"\n[1] Discovered {len(files)} frontend files: {files}")

    # Step 2: Prepare scan batches
    batch = prepare_scan_batch(str(repo_root), files)
    print(f"[2] Prepared {len(batch)} markup chunks for inspection")

    scan_id = "demo_full_pipeline_scan"
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
    )

    # Step 3: Run detection + classification
    print("\n[3] Running Detection + Classification (Nemotron Fast + AST rules)...")
    detected = await detect_violations(scan_id)
    print(f"    Detected and classified {len(detected)} violations.")

    # Step 4: Run root-cause diagnosis using Nemotron Ultra (top priority gets Ultra, rest template)
    print("\n[4] Running Root-Cause Diagnosis (Nemotron Ultra - Top 3 Priority)...")
    diagnosed = await diagnose_all(scan_id, top_n=3)
    print(f"    Diagnosed {len(diagnosed)} violations.")

    # Step 5: Run cheap explanation layer (Nemotron Fast for all violations)
    print("\n[5] Running Explanation Layer (Nemotron Fast - Concurrency=8)...")
    explained = await generate_all_explanations(scan_id)
    print(f"    Generated plain-English explanations for all {len(explained)} violations.")

    # Step 6: Run Code-Fix Generator (Nemotron Ultra - Concurrency=2)
    print("\n[6] Running Code-Fix Synthesis (Nemotron Ultra)...")
    fixes = await generate_all_fixes(scan_id)
    print(f"    Processed {len(fixes)} fixes total.")

    # Step 7: Display Generated Diffs for Planted Bugs
    proposed_fixes = [f for f in fixes if f.status == "proposed"]
    failed_fixes = [f for f in fixes if f.status == "failed"]

    print("\n" + "=" * 80)
    print(f"GENERATED CODE DIFFS FOR PLANTED BUGS ({len(proposed_fixes)} PROPOSED)")
    print("=" * 80)

    for i, fix in enumerate(proposed_fixes[:5], 1):
        print(f"\n--- Proposed Fix #{i}: {fix.fix_id} (Resolves {fix.violation_id}) ---")
        print(f"File:         {fix.file} (Lines {fix.line_start}-{fix.line_end})")
        print(f"Confidence:   {fix.confidence.upper()}")
        print(f"Status:       {fix.status.upper()}")
        print(f"Explanation:  {fix.explanation_of_change}")
        print("\nUnified Git Diff:")
        print("-" * 60)
        print(fix.diff)
        print("-" * 60)

    # Step 8: Display Any Failed Fixes & Rationale
    print("\n" + "=" * 80)
    print(f"FIXES THAT FAILED VALIDATION OR WERE SKIPPED ({len(failed_fixes)} ITEMS)")
    print("=" * 80)

    if not failed_fixes:
        print("None! All attempted fixes passed syntax, whitespace, and delimiter quality checks.")
    else:
        for i, fix in enumerate(failed_fixes, 1):
            print(f"\n--- Failed/Skipped Fix #{i}: {fix.fix_id} (Violation: {fix.violation_id}) ---")
            print(f"File:           {fix.file}")
            print(f"Status:         {fix.status.upper()}")
            print(f"Failure Reason: {fix.failure_reason}")

    # Step 9: Cost and Token Breakdown
    print("\n" + "=" * 80)
    print("UPDATED COST & TOKEN USAGE BREAKDOWN (/test-llm/cost)")
    print("=" * 80)
    costs = get_cost_breakdown()
    print(f"Fast Model Cost (Scanning & Explanations): ${costs['fast_cost']:.6f} USD")
    print(f"Ultra Model Cost (Diagnosis & Code Fixes): ${costs['ultra_cost']:.6f} USD")
    print(f"Total Combined Pipeline Cost:              ${costs['total']:.6f} USD")

    usage = get_token_usage_stats()
    print("\nFull Usage Statistics by Tier:")
    print(json.dumps(usage, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
