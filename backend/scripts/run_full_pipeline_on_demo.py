"""
Full End-to-End Pipeline Execution Script (Phases 12 -> 13 -> 14 -> 15):
Runs clone/prepare -> detect -> classify -> diagnose -> explain against the seeded demo app.
Outputs:
1. Classified and Diagnosed violations with plain_explanation and root-cause details.
2. 5 Sample Plain Explanations (mix of LLM-diagnosed and template-diagnosed items).
3. Token usage and cost metrics (Fast vs Ultra) from /test-llm/cost.
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
    print("CODEGUARD FULL PIPELINE EXECUTION (PHASE 12 -> 13 -> 14 -> 15)")
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

    print("\n" + "=" * 80)
    print("5 DIFFERENT VIOLATION EXPLANATIONS (MIX OF LLM AND TEMPLATE DIAGNOSES)")
    print("=" * 80)

    # Pick a mix: some with diagnosis_source == "llm", some with "template"
    llm_violations = [v for v in explained if v.diagnosis_source == "llm"]
    tpl_violations = [v for v in explained if v.diagnosis_source == "template"]

    # Select 5 (e.g. 2-3 from LLM, 2-3 from Template)
    selected: list = []
    if llm_violations:
        selected.extend(llm_violations[:3])
    if tpl_violations:
        needed = 5 - len(selected)
        selected.extend(tpl_violations[:needed])
    if len(selected) < 5 and len(explained) >= 5:
        remaining = [v for v in explained if v not in selected]
        selected.extend(remaining[: 5 - len(selected)])

    for i, v in enumerate(selected, 1):
        print(f"\n--- Violation #{i} ---")
        print(f"ID:                 {v.id}")
        print(f"Location:           {v.file}:{v.line}")
        print(f"Category:           {v.category.value if hasattr(v.category, 'value') else v.category}")
        print(f"Severity:           {v.severity.upper()} (Rank: {v.priority_rank})")
        print(f"Diagnosis Source:   {v.diagnosis_source.upper()} ({'Ultra LLM' if v.diagnosis_source == 'llm' else 'Fallback Template'})")
        print(f"Plain Explanation:  \"{v.plain_explanation}\"")
        print(f"Explanation Length: {len(v.plain_explanation)} chars (Max 400)")
        print(f"Technical Summary:  Root Cause: {v.root_cause[:80]}...")

    # Step 6: Cost and Token Breakdown
    print("\n" + "=" * 80)
    print("UPDATED COST & TOKEN USAGE BREAKDOWN (/test-llm/cost)")
    print("=" * 80)
    costs = get_cost_breakdown()
    print(f"Fast Model Cost (Detection & Explanations): ${costs['fast_cost']:.6f} USD")
    print(f"Ultra Model Cost (Root-Cause Diagnosis):    ${costs['ultra_cost']:.6f} USD")
    print(f"Total Combined Cost:                        ${costs['total']:.6f} USD")

    usage = get_token_usage_stats()
    print("\nFull Usage Statistics by Tier:")
    print(json.dumps(usage, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
