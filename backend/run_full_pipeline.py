import sys
sys.path.insert(0, "backend")
import asyncio
import json
from pathlib import Path

from app.routers.report import get_scan_report
from app.services.aggregator_service import build_scan_report
from app.services.classifier_service import classify_violations
from app.services.detector_service import detect_violations
from app.services.diagnosis_service import diagnose_all
from app.services.explainer_service import generate_all_explanations
from app.services.fixer_service import generate_all_fixes
from app.services.scanner_service import prepare_scan_batch
from app.services.git_service import find_frontend_files
from app.services.verification_service import (
    calculate_overall_improvement,
    verify_all_fixes,
)
from app.state import create_scan, get_scan, update_scan

async def main():
    repo_path = str(Path("sandbox-scripts/demo-app").resolve())
    scan_id = create_scan("https://github.com/example/demo-app")
    print(f"=== Starting End-to-End Pipeline for Scan: {scan_id} ===")

    # 1. Scanner & Batch Preparation
    files = find_frontend_files(repo_path)
    batch = prepare_scan_batch(repo_path, files)
    update_scan(
        scan_id=scan_id,
        repo_path=repo_path,
        files=files,
        file_count=len(files),
        framework="React / Vite",
        scan_batch=batch,
        batch_count=len(batch),
    )
    print(f"1. Prepared {len(batch)} chunks across {len(files)} files.")

    # 2. Detection (Rule-based prechecks + LLM)
    violations = await detect_violations(scan_id)
    print(f"2. Detected {len(violations)} violations.")

    # 3. Diagnosis
    diagnoses = await diagnose_all(scan_id)
    print(f"3. Diagnosed {len(diagnoses)} violations with root-cause & user impact.")

    # 4. Explanations
    explanations = await generate_all_explanations(scan_id)
    print(f"4. Generated plain-English explanations.")

    # 5. Fix Synthesis
    fixes = await generate_all_fixes(scan_id)
    print(f"5. Generated {len(fixes)} remediation patches.")

    # 6. Verification
    verif_results = await verify_all_fixes(scan_id)
    print(f"6. Verified {len(verif_results)} fixes in isolated sandboxes.")

    # 7. Overall Improvement
    imp = await calculate_overall_improvement(scan_id)
    print(f"7. Overall improvement: {imp.get('score_before')}% -> {imp.get('score_after')}% (+{imp.get('improvement_points')} pts)")

    # 8. Aggregation into Final ScanReport
    report = build_scan_report(scan_id)
    print("\n=== Final ScanReport Built Successfully ===")
    print(f"Report Scan ID: {report.scan_id}")
    print(f"Report Status: {report.status}")
    print(f"Baseline Score: {report.overall_score_before}%")
    print(f"Remediated Score: {report.overall_score_after}%")
    print(f"Total Unified Records: {len(report.unified_records)}")
    print(f"Summary by Status: {json.dumps(report.summary.get('by_status', {}), indent=2)}")

    # 9. Test GET /api/report/{scan_id}
    api_report = await get_scan_report(scan_id)
    print(f"\n=== GET /api/report/{scan_id} Verification ===")
    print(f"API returned status: {api_report.status}")
    print(f"API unified_records count: {len(api_report.unified_records)}")

    # Output full report JSON to scratch file for inspection
    with open("backend/final_scan_report_output.json", "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))
    print("Full report JSON saved to backend/final_scan_report_output.json")

if __name__ == "__main__":
    asyncio.run(main())
