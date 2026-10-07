"""
In-memory state store for CodeGuard.
Tracks active scans, progress states, mock remediation data, and final audit reports.

=============================================================================
PRODUCTION / ARCHITECTURAL SAFETY NOTE & KNOWN LIMITATIONS:
=============================================================================
- Design Choice:
  This module utilizes a process-local in-memory Python dictionary (`scans`)
  to store scan jobs, progress, violation states, and sandbox references.
  This architecture provides zero-dependency, ultra-fast, ephemeral execution
  tailored specifically for hackathon evaluation and single-instance serverless
  demo deployments.

- Known Limitations (Hackathon Demo vs Production):
  1. Single Instance Only: Does not support horizontal multi-instance scaling.
     All requests (REST and WebSocket) must route to the same container instance.
  2. Ephemeral Persistence: Container restarts, deployments, or cold-start
     recycles will reset active in-memory scan history.
  3. Memory Growth: In long-running processes without TTL eviction, scan
     dictionaries remain resident in memory.

- Production Roadmap:
  For enterprise multi-tenant production, replace this module with:
  - Redis / Valkey for distributed job locking, pub/sub WebSocket channels, and TTL caching.
  - PostgreSQL / Managed SQL for persistent audit history, reports, and tenant isolation.
=============================================================================
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from app.models.schemas import (
    ProposedFix,
    ScanReport,
    VerificationResult,
    Violation,
    ViolationCategory,
)

# Global in-memory dictionary storing all scan jobs
# NOTE: In-memory dictionary storage is a known design trade-off suitable for this hackathon
# single-instance demo (ephemeral persistence, no horizontal scaling, resets on container restart).
# For multi-tenant production deployments, this should be backed by Redis and PostgreSQL.
# Structure: scan_id -> dict with 'repo_url', 'branch', 'status', 'violations', 'fixes', etc.
scans: Dict[str, Dict[str, Any]] = {}


def generate_mock_scan_data(scan_id: str, repo_url: str, branch: str = "main") -> Dict[str, Any]:
    """Generates realistic placeholder scan data matching the core schema contracts."""
    violations: List[Violation] = [
        Violation(
            id="viol_01",
            file="src/components/Header.tsx",
            line=42,
            type="color-contrast",
            severity="critical",
            description="Elements must meet minimum color contrast ratio threshold (3.1:1 found, 4.5:1 required).",
            selector="button.btn-primary",
            context_snippet='<button className="text-slate-400 bg-slate-900">Submit</button>',
            wcag_criterion="1.4.3 Contrast (Minimum)",
            category=ViolationCategory.LOW_CONTRAST,
            severity_score=9,
            priority_rank=1,
        ),
        Violation(
            id="viol_02",
            file="src/pages/Login.tsx",
            line=65,
            type="label",
            severity="critical",
            description="Form <input> elements must have associated labels for screen readers.",
            selector="input#email",
            context_snippet='<input id="email" type="email" placeholder="name@domain.com" />',
            wcag_criterion="3.3.2 Labels or Instructions",
            category=ViolationCategory.UNLABELED_FORM_FIELD,
            severity_score=8,
            priority_rank=2,
        ),
        Violation(
            id="viol_03",
            file="src/components/Navbar.tsx",
            line=31,
            type="button-name",
            severity="high",
            description="Interactive icon buttons must have an accessible name or aria-label.",
            selector="button.menu-toggle",
            context_snippet='<button onClick={toggleMenu}><MenuIcon /></button>',
            wcag_criterion="4.1.2 Name, Role, Value",
            category=ViolationCategory.EMPTY_LINK_OR_BUTTON,
            severity_score=7,
            priority_rank=3,
        ),
        Violation(
            id="viol_04",
            file="src/components/ProfileModal.tsx",
            line=18,
            type="image-alt",
            severity="high",
            description="Images must have alternate text describing visual content or be explicitly marked decorative.",
            selector="img.avatar",
            context_snippet='<img src={user.avatarUrl} className="rounded-full" />',
            wcag_criterion="1.1.1 Non-text Content",
            category=ViolationCategory.MISSING_ALT_TEXT,
            severity_score=6,
            priority_rank=4,
        ),
    ]

    fixes: List[ProposedFix] = [
        ProposedFix(
            fix_id="fix_01",
            violation_id="viol_01",
            diff="""@@ -42,1 +42,1 @@
-<button className="text-slate-400 bg-slate-900">Submit</button>
+<button className="text-slate-100 bg-slate-900">Submit</button>""",
            explanation="Updated text color to text-slate-100 to increase contrast ratio from 3.1:1 to 5.4:1, exceeding WCAG AA minimum.",
            original_code='<button className="text-slate-400 bg-slate-900">Submit</button>',
            remediated_code='<button className="text-slate-100 bg-slate-900">Submit</button>',
        ),
        ProposedFix(
            fix_id="fix_02",
            violation_id="viol_02",
            diff="""@@ -18,1 +18,1 @@
-<img src={user.avatarUrl} className="rounded-full" />
+<img src={user.avatarUrl} alt={`${user.name}'s profile avatar`} className="rounded-full" />""",
            explanation="Added descriptive dynamic alt attribute using the user's name for assistive technology users.",
            original_code='<img src={user.avatarUrl} className="rounded-full" />',
            remediated_code='<img src={user.avatarUrl} alt={`${user.name}\'s profile avatar`} className="rounded-full" />',
        ),
        ProposedFix(
            fix_id="fix_03",
            violation_id="viol_03",
            diff="""@@ -64,2 +64,3 @@
+<label htmlFor="email" className="block text-sm font-medium text-slate-200">Email Address</label>
 <input id="email" type="email" placeholder="name@domain.com" />""",
            explanation="Associated an explicit <label htmlFor='email'> with the input field to provide proper accessibility tree association.",
            original_code='<input id="email" type="email" placeholder="name@domain.com" />',
            remediated_code='<label htmlFor="email" className="block text-sm font-medium text-slate-200">Email Address</label>\n<input id="email" type="email" placeholder="name@domain.com" />',
        ),
        ProposedFix(
            fix_id="fix_04",
            violation_id="viol_04",
            diff="""@@ -31,1 +31,1 @@
-<button onClick={toggleMenu}><MenuIcon /></button>
+<button onClick={toggleMenu} aria-label="Toggle navigation menu"><MenuIcon /></button>""",
            explanation="Added aria-label='Toggle navigation menu' to ensure screen readers announce purpose of icon button.",
            original_code='<button onClick={toggleMenu}><MenuIcon /></button>',
            remediated_code='<button onClick={toggleMenu} aria-label="Toggle navigation menu"><MenuIcon /></button>',
        ),
    ]

    verification_results: List[VerificationResult] = [
        VerificationResult(
            fix_id="fix_01",
            violation_id="viol_01",
            axe_score_before=62.5,
            axe_score_after=100.0,
            tests_passed=True,
            violations_resolved=True,
            verified=True,
            sandbox_id="sb-nebius-verify-01",
            sandbox_logs="[axe-core] Passed 0 color-contrast defects. [npm test] 12/12 tests passed (0 regressions).",
        ),
        VerificationResult(
            fix_id="fix_02",
            violation_id="viol_02",
            axe_score_before=62.5,
            axe_score_after=100.0,
            tests_passed=True,
            violations_resolved=True,
            verified=True,
            sandbox_id="sb-nebius-verify-02",
            sandbox_logs="[axe-core] Passed 0 image-alt defects. [npm test] 12/12 tests passed (0 regressions).",
        ),
        VerificationResult(
            fix_id="fix_03",
            violation_id="viol_03",
            axe_score_before=62.5,
            axe_score_after=100.0,
            tests_passed=True,
            violations_resolved=True,
            verified=True,
            sandbox_id="sb-nebius-verify-03",
            sandbox_logs="[axe-core] Passed 0 label defects. [npm test] 12/12 tests passed (0 regressions).",
        ),
        VerificationResult(
            fix_id="fix_04",
            violation_id="viol_04",
            axe_score_before=62.5,
            axe_score_after=100.0,
            tests_passed=True,
            violations_resolved=True,
            verified=True,
            sandbox_id="sb-nebius-verify-04",
            sandbox_logs="[axe-core] Passed 0 button-name defects. [npm test] 12/12 tests passed (0 regressions).",
        ),
    ]

    report = ScanReport(
        scan_id=scan_id,
        repo_url=repo_url,
        branch=branch,
        violations=violations,
        fixes=fixes,
        verification_results=verification_results,
        overall_score_before=62.5,
        overall_score_after=100.0,
        status="completed",
        timestamp=datetime.now(timezone.utc),
    )

    return {
        "scan_id": scan_id,
        "repo_url": repo_url,
        "branch": branch,
        "status": "completed",
        "progress": 100,
        "violations": violations,
        "fixes": fixes,
        "verification_results": verification_results,
        "report": report,
        "base_sandbox_id": None,
        "verification_sandbox_ids": [],
        "sandbox_map": {},
        "created_at": datetime.now(timezone.utc),
    }


def create_scan(repo_url: str, branch: str = "main") -> str:
    """Creates a new scan job entry and returns its unique scan_id."""
    scan_id = f"scan_{uuid.uuid4().hex[:8]}"
    scans[scan_id] = generate_mock_scan_data(scan_id=scan_id, repo_url=repo_url, branch=branch)
    return scan_id


def get_scan(scan_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves scan data for the specified scan_id, generating mock data if not found."""
    if scan_id not in scans:
        scans[scan_id] = generate_mock_scan_data(scan_id=scan_id, repo_url="https://github.com/example/demo-app")
    return scans.get(scan_id)


def update_scan(scan_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Updates attributes of an existing scan."""
    scan = get_scan(scan_id)
    if scan:
        scan.update(kwargs)
    return scan


def remove_scan(scan_id: str) -> Optional[Dict[str, Any]]:
    """Removes a scan from in-memory state."""
    return scans.pop(scan_id, None)


def track_base_sandbox(scan_id: str, sandbox_id: str) -> None:
    """Tracks the base clean baseline sandbox for a scan."""
    scan = get_scan(scan_id)
    if scan:
        scan["base_sandbox_id"] = sandbox_id


def get_base_sandbox(scan_id: str) -> Optional[str]:
    """Retrieves the base clean baseline sandbox ID for a scan if provisioned."""
    scan = get_scan(scan_id)
    return scan.get("base_sandbox_id") if scan else None


def track_verification_sandbox(scan_id: str, sandbox_id: str, fix_id: Optional[str] = None) -> None:
    """Tracks a verification sandbox provisioned for testing a specific fix."""
    scan = get_scan(scan_id)
    if scan:
        v_list = scan.setdefault("verification_sandbox_ids", [])
        if sandbox_id not in v_list:
            v_list.append(sandbox_id)
        if fix_id:
            s_map = scan.setdefault("sandbox_map", {})
            s_map[fix_id] = sandbox_id


def get_scan_sandboxes(scan_id: str) -> List[str]:
    """Returns all sandbox IDs (base and verification) associated with a scan."""
    scan = get_scan(scan_id)
    if not scan:
        return []
    sandboxes: List[str] = []
    base_id = scan.get("base_sandbox_id")
    if base_id:
        sandboxes.append(base_id)
    for v_id in scan.get("verification_sandbox_ids", []):
        if v_id and v_id not in sandboxes:
            sandboxes.append(v_id)
    return sandboxes


def clear_scan_sandboxes(scan_id: str) -> None:
    """Resets all tracked sandbox IDs for a scan."""
    scan = get_scan(scan_id)
    if scan:
        scan["base_sandbox_id"] = None
        scan["verification_sandbox_ids"] = []
        scan["sandbox_map"] = {}
