"""
Full End-to-End Pipeline Execution Script (Phase 14):
Runs clone/prepare -> detect -> classify -> diagnose against the seeded demo app.
Outputs:
1. Classified and Diagnosed violations with root_cause, user_impact, and fix_strategy.
2. Token usage and cost metrics (Fast vs Ultra).
3. Verification of ULTRA_MAX_CALLS_PER_SCAN guardrail triggering when lowered.
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
from app.services.classifier_service import summarize_violations
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
    print(f"CODEGUARD FULL PIPELINE EXECUTION (PHASE 14)")
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

    # Step 4: Run root-cause diagnosis using Nemotron Ultra
    print("\n[4] Running Root-Cause Diagnosis (Nemotron Ultra - Top Priority)...")
    diagnosed = await diagnose_all(scan_id, top_n=5)
    print(f"    Diagnosed {len(diagnosed)} violations.")

    print("\n" + "=" * 80)
    print(f"DIAGNOSED VIOLATION DETAILS (TOP PLANTED BUGS)")
    print("=" * 80)

    for v in diagnosed:
        print(f"\n[Priority #{v.priority_rank}] [{v.id}] {v.file}:{v.line}")
        print(f"  Category:       {v.category.value if hasattr(v.category, 'value') else v.category}")
        print(f"  Severity:       {v.severity.upper()} (Score: {v.severity_score}/10)")
        print(f"  Rule Type:      {v.type} ({v.wcag_criterion})")
        print(f"  Source:         Detection: {v.source} | Diagnosis: {v.diagnosis_source.upper()}")
        print(f"  Affected Elem:  {v.affected_element}")
        print(f"  Root Cause:     {v.root_cause}")
        print(f"  User Impact:    {v.user_impact}")
        print(f"  Fix Strategy:   {v.fix_strategy}")
        print(f"  Snippet:        {v.context_snippet}")

    # Step 5: Cost and Token Breakdown
    print("\n" + "=" * 80)
    print("COST & TOKEN USAGE BREAKDOWN (FAST vs ULTRA)")
    print("=" * 80)
    costs = get_cost_breakdown()
    print(f"Fast Cost (Scanning & Detection):  ${costs['fast_cost']:.6f} USD")
    print(f"Ultra Cost (Root-Cause Diagnosis): ${costs['ultra_cost']:.6f} USD")
    print(f"Total Combined Cost:               ${costs['total']:.6f} USD")

    usage = get_token_usage_stats()
    print("\nFull Usage Statistics:")
    print(json.dumps(usage, indent=2))

    # Step 6: Verify guardrails with artificially lowered limit
    print("\n" + "=" * 80)
    print("GUARDRAIL TEST: Lowering ULTRA_MAX_CALLS_PER_SCAN to 2")
    print("=" * 80)

    guardrail_scan_id = "demo_guardrail_test_scan"
    # Copy classified violations for guardrail test
    update_scan(
        guardrail_scan_id,
        repo_path=str(repo_root),
        violations=detected,
        status="scanned",
    )

    original_limit = getattr(settings, "ULTRA_MAX_CALLS_PER_SCAN", 5)
    settings.ULTRA_MAX_CALLS_PER_SCAN = 2
    try:
        print(f"Running diagnosis with ULTRA_MAX_CALLS_PER_SCAN={settings.ULTRA_MAX_CALLS_PER_SCAN}...")
        guardrail_results = await diagnose_all(guardrail_scan_id, top_n=5)
        sources = [v.diagnosis_source for v in guardrail_results]
        print(f"Diagnosis sources across violations: {sources}")
        llm_count = sources.count("llm")
        template_count = sources.count("template")
        print(f"Result: {llm_count} LLM calls made (at or below limit of 2), {template_count} fell back to TEMPLATE.")
        assert llm_count <= 2, f"Expected at most 2 LLM calls, got {llm_count}"
        print(">>> GUARDRAIL CONFIRMED: Successfully prevented excess Ultra calls and gracefully used template fallback! <<<")
    finally:
        settings.ULTRA_MAX_CALLS_PER_SCAN = original_limit


if __name__ == "__main__":
    asyncio.run(main())
