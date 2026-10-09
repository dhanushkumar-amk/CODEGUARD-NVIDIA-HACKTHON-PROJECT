"""
Comparison Script: Tavily Grounded vs Ungrounded Pipeline Execution
Runs diagnosis and fix generation on demo app violations under two configurations:
1. Grounded Run (TAVILY_ENABLED=True)
2. Ungrounded Run (TAVILY_ENABLED=False)

Outputs:
- Number of Tavily searches executed
- Grounding sources attached to 3 fixes
- Side-by-side comparison of fixes produced with and without grounding
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
from app.services.fixer_service import generate_all_fixes
from app.services.grounding_service import (
    reset_cache_for_testing,
    get_scan_search_count,
    get_scan_sources_count,
)
from app.services.llm_client import reset_cost_tracker
from app.state import create_scan, update_scan

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("compare_grounding")


async def run_pipeline_with_grounding_flag(tavily_enabled: bool, scan_id: str, repo_root: Path):
    settings.TAVILY_ENABLED = tavily_enabled
    reset_cost_tracker()
    reset_cache_for_testing()

    files = find_frontend_files(str(repo_root))
    batch = prepare_scan_batch(str(repo_root), files)

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

    # 1. Detect
    detected = await detect_violations(scan_id)
    # 2. Diagnose top 3
    diagnosed = await diagnose_all(scan_id, top_n=3)
    # 3. Generate fixes
    fixes = await generate_all_fixes(scan_id)
    searches_count = get_scan_search_count(scan_id)

    return {
        "searches_count": searches_count,
        "diagnosed": diagnosed,
        "fixes": fixes,
    }


async def main():
    repo_root = backend_dir.parent / "sandbox-scripts" / "demo-app"
    print("=" * 80)
    print("CODEGUARD EXPERIMENT: GROUNDED VS UNGROUNDED REMEDIATION COMPARISON")
    print(f"Target Repository: {repo_root.resolve()}")
    print("=" * 80)

    # Run 1: Grounded (Tavily Enabled)
    print("\n>>> [RUN 1] Executing Grounded Pipeline (TAVILY_ENABLED=True)...")
    grounded_res = await run_pipeline_with_grounding_flag(
        tavily_enabled=True,
        scan_id="compare_grounded_scan",
        repo_root=repo_root,
    )
    grounded_searches = grounded_res["searches_count"]
    grounded_fixes = [f for f in grounded_res["fixes"] if f.status == "proposed"]

    print(f"    Grounded Run Completed: {grounded_searches} Tavily searches performed.")
    print(f"    Proposed Fixes Count:   {len(grounded_fixes)}")

    # Run 2: Ungrounded (Tavily Disabled)
    print("\n>>> [RUN 2] Executing Ungrounded Pipeline (TAVILY_ENABLED=False)...")
    ungrounded_res = await run_pipeline_with_grounding_flag(
        tavily_enabled=False,
        scan_id="compare_ungrounded_scan",
        repo_root=repo_root,
    )
    ungrounded_searches = ungrounded_res["searches_count"]
    ungrounded_fixes = [f for f in ungrounded_res["fixes"] if f.status == "proposed"]

    print(f"    Ungrounded Run Completed: {ungrounded_searches} Tavily searches performed.")
    print(f"    Proposed Fixes Count:     {len(ungrounded_fixes)}")

    # Compare 3 Fixes
    print("\n" + "=" * 80)
    print("RESULTS COMPARISON: 3 FIXES WITH AND WITHOUT TAVILY GROUNDING")
    print("=" * 80)

    # Match fixes by violation_id
    ungrounded_by_v = {f.violation_id: f for f in ungrounded_fixes}

    sample_fixes = grounded_fixes[:3]
    for idx, g_fix in enumerate(sample_fixes, 1):
        u_fix = ungrounded_by_v.get(g_fix.violation_id)
        print(f"\n{'#' * 40}")
        print(f"FIX #{idx}: {g_fix.fix_id} (Violation: {g_fix.violation_id})")
        print(f"File:       {g_fix.file} (Lines {g_fix.line_start}-{g_fix.line_end})")
        print(f"Grounded:   {g_fix.grounded}")
        print(f"Grounding Sources ({len(g_fix.grounding_sources)}):")
        for s in g_fix.grounding_sources:
            print(f"  * [{s.title}]({s.url})")

        print(f"\n[GROUNDED FIX EXPLANATION]")
        print(f"  {g_fix.explanation_of_change}")

        if u_fix:
            print(f"\n[UNGROUNDED FIX EXPLANATION]")
            print(f"  {u_fix.explanation_of_change}")

        print(f"\n[GROUNDED DIFF]")
        print("-" * 50)
        print(g_fix.diff)
        print("-" * 50)

        if u_fix:
            print(f"\n[UNGROUNDED DIFF]")
            print("-" * 50)
            print(u_fix.diff)
            print("-" * 50)

    # Save summary artifact
    output_summary = {
        "grounded_searches_count": grounded_searches,
        "ungrounded_searches_count": ungrounded_searches,
        "sample_fixes": [
            {
                "violation_id": gf.violation_id,
                "file": gf.file,
                "grounded": gf.grounded,
                "sources": [s.model_dump() for s in gf.grounding_sources],
                "grounded_explanation": gf.explanation_of_change,
                "grounded_diff": gf.diff,
                "ungrounded_explanation": ungrounded_by_v.get(gf.violation_id).explanation_of_change if ungrounded_by_v.get(gf.violation_id) else None,
                "ungrounded_diff": ungrounded_by_v.get(gf.violation_id).diff if ungrounded_by_v.get(gf.violation_id) else None,
            }
            for gf in sample_fixes
        ]
    }

    out_file = backend_dir / "scripts" / "grounding_comparison_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_summary, f, indent=2)
    print(f"\nSummary comparison written to: {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
