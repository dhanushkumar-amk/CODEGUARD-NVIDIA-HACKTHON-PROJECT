"""
Script to execute the CodeGuard Accessibility Violation Detector against the seeded demo app.
Outputs:
1. Full list of detected violations (rule + LLM)
2. Breakdown of planted bugs caught vs missed
3. Token usage and cost metrics
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.git_service import find_frontend_files
from app.services.scanner_service import prepare_scan_batch
from app.services.detector_service import detect_violations
from app.services.llm_client import get_token_usage_stats, reset_cost_tracker
from app.state import create_scan, get_scan, update_scan

PLANTED_BUGS = [
    {
        "id": 1,
        "name": "Missing alt on <img>",
        "file": "src/components/Header.tsx",
        "expected_type": "image-alt",
        "wcag": "1.1.1 Non-text Content",
    },
    {
        "id": 2,
        "name": "Unlabeled form <input>",
        "file": "src/components/Header.tsx",
        "expected_type": "label",
        "wcag": "3.3.2 Labels or Instructions",
    },
    {
        "id": 3,
        "name": "Clickable <div> without role/tabIndex/keyboard handler",
        "file": "src/components/Header.tsx",
        "expected_type": "click-events-have-key-events",
        "wcag": "2.1.1 Keyboard",
    },
    {
        "id": 4,
        "name": "Empty <button> without text or aria-label",
        "file": "src/components/Header.tsx",
        "expected_type": "button-name",
        "wcag": "4.1.2 Name, Role, Value",
    },
    {
        "id": 5,
        "name": "Anchor <a> with href='#'",
        "file": "src/components/Header.tsx",
        "expected_type": "link-href",
        "wcag": "2.4.4 Link Purpose (In Context)",
    },
    {
        "id": 6,
        "name": "Positive tabIndex value on <button>",
        "file": "src/components/LoginForm.tsx",
        "expected_type": "tabindex",
        "wcag": "2.4.3 Focus Order",
    },
    {
        "id": 7,
        "name": "Unlabeled <textarea>",
        "file": "src/components/LoginForm.tsx",
        "expected_type": "label",
        "wcag": "3.3.2 Labels or Instructions",
    },
    {
        "id": 8,
        "name": "Low contrast text (#d1d5db on #ffffff)",
        "file": "src/components/LoginForm.tsx",
        "expected_type": "color-contrast",
        "wcag": "1.4.3 Contrast (Minimum)",
    },
    {
        "id": 9,
        "name": "Skipped heading level (<h1> to <h3>)",
        "file": "src/App.tsx",
        "expected_type": "heading-order",
        "wcag": "1.3.1 Info and Relationships",
    },
    {
        "id": 10,
        "name": "Missing <main> landmark",
        "file": "src/App.tsx",
        "expected_type": "landmark-main-is-top-level",
        "wcag": "1.3.1 Info and Relationships",
    },
]


async def main():
    repo_root = backend_dir.parent / "sandbox-scripts" / "demo-app"
    print(f"Scanning demo app at: {repo_root.resolve()}")

    files = find_frontend_files(str(repo_root))
    print(f"Discovered {len(files)} frontend files: {files}")

    batch = prepare_scan_batch(str(repo_root), files)
    print(f"Prepared scan batch with {len(batch)} chunks:\n")
    for ch in batch:
        print(f" - [{ch['file']}] chunk #{ch['chunk_index']} (start_line={ch['start_line']}, ~{ch['estimated_tokens']} tok)")

    scan_id = "demo_scan_run"
    update_scan(
        scan_id=scan_id,
        repo_url="sandbox-scripts/demo-app",
        branch="main",
        status="prepared",
        files=files,
        file_count=len(files),
        scan_batch=batch,
        batch_count=len(batch),
    )

    print("\nStarting detector_service.detect_violations()...")
    violations = await detect_violations(scan_id)

    print(f"\n=================== DETECTED VIOLATIONS ({len(violations)}) ===================")
    for v in violations:
        crit = f" ({v.wcag_criterion})" if v.wcag_criterion else ""
        print(
            f"[{v.id}] {v.file}:{v.line} | [{v.severity.upper()}] {v.type}{crit}\n"
            f"     Source: {v.source}\n"
            f"     Desc:   {v.description}\n"
            f"     Code:   {v.context_snippet}\n"
        )

    # Compare with planted bugs
    print("=================== PLANTED BUGS EVALUATION ===================")
    caught_count = 0
    missed_count = 0

    for bug in PLANTED_BUGS:
        # Check if any violation matches the file and expected defect
        matched_viols = [
            v for v in violations
            if bug["file"] in v.file and (
                bug["expected_type"] in v.type
                or v.type in bug["expected_type"]
                or (bug["id"] == 10 and ("landmark" in v.type or "landmark" in v.description.lower() or "main" in v.description.lower()))
                or (bug["id"] == 9 and ("heading" in v.type or "heading" in v.description.lower()))
                or (bug["id"] == 8 and ("contrast" in v.type or "contrast" in v.description.lower()))
            )
        ]

        if matched_viols:
            caught_count += 1
            v_info = ", ".join([f"{v.id} (L{v.line}, src={v.source}, type={v.type})" for v in matched_viols])
            print(f"[CAUGHT] Bug #{bug['id']}: {bug['name']} ({bug['file']}) -> Detected: {v_info}")
        else:
            missed_count += 1
            print(f"[MISSED] Bug #{bug['id']}: {bug['name']} ({bug['file']})")

    print(f"\nSummary: {caught_count}/{len(PLANTED_BUGS)} planted bugs CAUGHT, {missed_count} MISSED.")

    # Cost Metrics
    usage = get_token_usage_stats()
    print("\n=================== LLM TOKEN USAGE & COST ===================")
    print(json.dumps(usage, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
