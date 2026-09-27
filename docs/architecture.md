# CodeGuard System Architecture & Data-Flow Specification

This document provides the formal contract, component topology, sequence flow, and data schemas for **CodeGuard** — an autonomous accessibility remediation agent powered by **NVIDIA Nemotron** and **Nebius AI Cloud**.

---

## 1. System Topology & Architecture Diagram

```mermaid
flowchart TB
    subgraph Frontend["Frontend Layer (React 18 + Vite + TypeScript)"]
        UI_RepoInput["RepoInput Component"]
        UI_Progress["ScanProgress Component (Framer Motion)"]
        UI_Diff["FixDiffViewer & ViolationCard"]
        UI_Report["FinalReport & ComplianceChart (Recharts)"]
        WS_Client["WebSocket Client Hook (/ws/progress)"]
    end

    subgraph API["Backend API Layer (FastAPI Routers)"]
        R_Scan["/scan (POST - Trigger Audit)"]
        R_Fix["/fix (POST - Generate Patch)"]
        R_Verify["/verify (POST - Run Sandbox Test)"]
        R_Report["/report/{id} (GET - Audit Results)"]
        R_WS["/ws/progress (WebSocket Stream)"]
    end

    subgraph Orchestrator["Core Orchestration & Services"]
        SVC_Git["git_service (Repo Clone & Tree Extraction)"]
        SVC_Scan["scanner_service (AST + axe-core Static Scan)"]
        SVC_Fix["fixer_service (Prompt Engine & Diff Synth)"]
        SVC_Verify["verifier_service (Test Harness & axe Audit)"]
        SVC_Report["report_service (WCAG Scoring & PR Formatter)"]
        CLIENT_LLM["llm_client (AsyncOpenAI + Tenacity Retries)"]
        CLIENT_SB["sandbox_client (Context-Managed Lifecycle)"]
    end

    subgraph External["External Cloud Infrastructure"]
        subgraph Nebius_Token_Factory["Nebius Token Factory (OpenAI-Compatible API)"]
            M_Nano["Nemotron Nano (4B Instruct)\n• AST Noise Filtering\n• False Positive Elimination"]
            M_Ultra["Nemotron Ultra (340B Instruct)\n• WCAG 2.2 AA Patch Synthesis\n• Component Context Integration"]
        end

        subgraph Nebius_Sandboxes["Nebius AI Cloud (Execution Sandboxes)"]
            SB_Container["Ephemeral MicroVM / Container\n(Playwright + Chromium + axe-core)\n• Rendered DOM Evaluation\n• Computed CSS Contrast Audit\n• Project Unit Test Suites"]
        end
    end

    %% User Interaction
    UI_RepoInput -->|1. Submit repo URL & branch| R_Scan
    R_Scan -->|2. Enqueue Audit Task| SVC_Git
    SVC_Git -->|3. Clone repo to temp workspace| SVC_Scan

    %% Live Progress
    R_WS <-->|Real-time bidirectional status| WS_Client
    WS_Client --> UI_Progress

    %% Scan & Triage
    SVC_Scan -->|4. Parse AST violations| CLIENT_LLM
    CLIENT_LLM -->|5. Fast triage prompt| M_Nano
    M_Nano -->|6. Verified actionable defects| SVC_Fix

    %% Fix Synthesis
    SVC_Fix -->|7. Deep remediation prompt| CLIENT_LLM
    CLIENT_LLM -->|8. Patch synth request| M_Ultra
    M_Ultra -->|9. Unified diff & explanation| SVC_Verify

    %% Verification Loop
    SVC_Verify -->|10. Acquire session & push code| CLIENT_SB
    CLIENT_SB -->|11. Provision isolated environment| SB_Container
    SB_Container -->|12. Run axe & project test suite| CLIENT_SB
    CLIENT_SB -->|13. Teardown sandbox & return logs| SVC_Verify

    %% Reporting & Visualization
    SVC_Verify -->|14. Verified fixes & test results| SVC_Report
    SVC_Report -->|15. Final report payload| R_Report
    SVC_Report -->|16. Stream completion event| R_WS
    R_Report --> UI_Report
    R_WS --> UI_Diff
```

---

## 2. End-to-End Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend as React Frontend
    participant WS as WebSocket (/ws/progress)
    participant API as FastAPI Router
    participant Git as git_service
    participant Scanner as scanner_service
    participant Fixer as fixer_service
    participant Verifier as verifier_service
    participant LLM as llm_client
    participant Nano as Nemotron Nano (4B)
    participant Ultra as Nemotron Ultra (340B)
    participant Sandbox as Nebius Sandbox
    participant Report as report_service

    User->>Frontend: Enter GitHub Repo URL + Branch
    Frontend->>WS: Connect to /ws/progress
    WS-->>Frontend: Connection Accepted (ready)

    Frontend->>API: POST /scan { repo_url, branch }
    API-->>Frontend: 202 Accepted { scan_id, status: "queued" }

    API->>WS: Broadcast { stage: "init", progress: 5, message: "Cloning repository..." }
    WS-->>Frontend: Update ScanProgress UI (5%)

    API->>Git: clone_repository(repo_url, branch)
    Git-->>API: Local workspace path (/tmp/codeguard-xyz)
    API->>WS: Broadcast { stage: "cloning", progress: 15, message: "Discovered 24 frontend files" }
    WS-->>Frontend: Update ScanProgress UI (15%)

    API->>Scanner: run_ast_scan(workspace_path)
    Scanner->>LLM: call_nemotron(NANO_MODEL_ID, raw_ast_violations)
    LLM->>Nano: POST /chat/completions (Triage Prompt)
    Nano-->>LLM: Actionable WCAG Violations (Filtered)
    LLM-->>Scanner: Filtered Violations List
    Scanner-->>API: List[Violation]
    API->>WS: Broadcast { stage: "scanning", progress: 40, violations_found: 6 }
    WS-->>Frontend: Render ViolationCard list (40%)

    loop For Each Violation in Violations
        API->>Fixer: generate_remediation_patch(violation, file_context)
        Fixer->>LLM: call_nemotron(ULTRA_MODEL_ID, fix_prompt)
        LLM->>Ultra: POST /chat/completions (Synthesize WCAG Fix)
        Ultra-->>LLM: Code Diff + Remediated File Content
        LLM-->>Fixer: ProposedFix { diff, remediated_code }
        Fixer-->>API: ProposedFix

        API->>WS: Broadcast { stage: "fixing", progress: 60, current: 1, total: 6 }
        WS-->>Frontend: Display FixDiffViewer preview

        API->>Verifier: verify_patch_in_sandbox(patch, workspace_path)
        Verifier->>Sandbox: POST /sandboxes (Image: Playwright+Chromium)
        Sandbox-->>Verifier: SandboxHandle { sandbox_id }
        Verifier->>Sandbox: POST /sandboxes/{id}/files (Upload Patched Files)
        Verifier->>Sandbox: POST /sandboxes/{id}/commands ("npm test && python run_axe.py")
        Sandbox-->>Verifier: CommandResult { exit_code: 0, stdout, duration_ms }
        Verifier->>Sandbox: DELETE /sandboxes/{id} (Guaranteed Cleanup)
        Verifier-->>API: VerificationResult { verified: true, tests_passed: true }

        API->>WS: Broadcast { stage: "verifying", progress: 85, verified: true }
        WS-->>Frontend: Mark ViolationCard as Resolved (Green Badge)
    end

    API->>Report: generate_compliance_report(violations, verification_results)
    Report-->>API: ScanReport { score_before: 62, score_after: 100 }
    API->>WS: Broadcast { stage: "completed", progress: 100, report: ScanReport }
    WS-->>Frontend: Render FinalReport, ComplianceChart, and Export PR button
```

---

## 3. Step-by-Step Data Flow & WebSocket Contract

### Step 1: Session Initiation & Handshake
* **Trigger**: User inputs a repository URL (e.g. `https://github.com/org/web-app`) and clicks **Scan Repo**.
* **Transport**:
  - WebSocket connection initialized at `ws://localhost:8000/ws/progress`.
  - HTTP `POST /scan` dispatched.
* **HTTP Request Body**:
  ```json
  {
    "repo_url": "https://github.com/org/web-app",
    "branch": "main"
  }
  ```
* **HTTP Response (Immediate)**:
  ```json
  {
    "scan_id": "scan_a1b2c3d4",
    "status": "queued",
    "created_at": "2026-09-27T19:30:00Z"
  }
  ```
* **WebSocket Event**:
  ```json
  {
    "stage": "init",
    "scan_id": "scan_a1b2c3d4",
    "progress": 5,
    "message": "Initialized scan request. Connecting to repository...",
    "timestamp": "2026-09-27T19:30:01Z"
  }
  ```

---

### Step 2: Ingestion & File Tree Discovery (`git_service`)
* **Operation**: GitPython performs a shallow clone (`--depth 1`) into an isolated temporary folder. Scans the workspace tree for files ending in `.tsx`, `.jsx`, `.html`, `.vue`, `.svelte`.
* **Internal Data Output**: `workspace_path: Path`, `target_files: List[Path]`.
* **WebSocket Event**:
  ```json
  {
    "stage": "cloning",
    "scan_id": "scan_a1b2c3d4",
    "progress": 15,
    "message": "Repository cloned successfully. Discovered 18 frontend components.",
    "data": {
      "branch": "main",
      "file_count": 18,
      "files": ["src/components/Header.tsx", "src/pages/Login.tsx"]
    },
    "timestamp": "2026-09-27T19:30:04Z"
  }
  ```

---

### Step 3: Accessibility Scanning & Nano Triage (`scanner_service`)
* **Operation**: Static AST analysis uncovers missing `alt` attributes, unassociated `<label>` elements, invalid ARIA roles, and keyboard navigation issues.
* **LLM Call**: Calls `Nemotron-Nano` via `llm_client.call_nemotron` to triage warnings:
  ```text
  Prompt: "Given these raw AST a11y violations in Login.tsx, eliminate false positives where aria-labelledby is dynamically assigned, and return verified WCAG 2.2 AA violations in JSON."
  ```
* **Internal Data Output**: `List[Violation]`.
* **WebSocket Event**:
  ```json
  {
    "stage": "scanning",
    "scan_id": "scan_a1b2c3d4",
    "progress": 40,
    "message": "Accessibility audit complete: 4 actionable violations detected.",
    "data": {
      "violations_count": 4,
      "violations": [
        {
          "id": "viol_01",
          "file": "src/components/Header.tsx",
          "line": 42,
          "type": "color-contrast",
          "severity": "critical",
          "description": "Elements must meet minimum color contrast ratio threshold (3.1:1 found, 4.5:1 required).",
          "selector": "button.btn-primary",
          "context_snippet": "<button className=\"text-slate-400 bg-slate-900\">Submit</button>"
        }
      ]
    },
    "timestamp": "2026-09-27T19:30:10Z"
  }
  ```

---

### Step 4: Remediation Patch Synthesis (`fixer_service`)
* **Operation**: For each violation, context extraction pulls 30 lines above and below the violating element, plus design system tokens.
* **LLM Call**: Calls `Nemotron-Ultra` (340B) via `llm_client.call_nemotron`:
  ```text
  Prompt: "Synthesize a minimal, non-breaking WCAG 2.2 AA compliant fix for this button. Return the unified git diff and updated component code."
  ```
* **Internal Data Output**: `ProposedFix`.
* **WebSocket Event**:
  ```json
  {
    "stage": "fixing",
    "scan_id": "scan_a1b2c3d4",
    "progress": 65,
    "message": "Synthesized remediation patch for viol_01 in Header.tsx.",
    "data": {
      "violation_id": "viol_01",
      "fix_id": "fix_01",
      "explanation": "Updated text color to text-slate-100 to increase contrast ratio from 3.1:1 to 5.4:1.",
      "diff": "@@ -42,1 +42,1 @@\n-<button className=\"text-slate-400 bg-slate-900\">Submit</button>\n+<button className=\"text-slate-100 bg-slate-900\">Submit</button>"
    },
    "timestamp": "2026-09-27T19:30:18Z"
  }
  ```

---

### Step 5: Ephemeral Sandbox Verification (`verifier_service`)
* **Operation**: Uses `async with sandbox_session() as sandbox:`:
  1. Calls Nebius API `POST /sandboxes` to spawn container.
  2. Calls `upload_files` to push patched components.
  3. Executes `npm test` and axe-core Playwright evaluation inside sandbox.
  4. Confirms violation is resolved and 0 unit test regressions occurred.
  5. Destroys sandbox in `finally` block.
* **Internal Data Output**: `VerificationResult`.
* **WebSocket Event**:
  ```json
  {
    "stage": "verifying",
    "scan_id": "scan_a1b2c3d4",
    "progress": 85,
    "message": "Patch fix_01 verified in Nebius Sandbox with 0 test regressions.",
    "data": {
      "fix_id": "fix_01",
      "violation_id": "viol_01",
      "verified": true,
      "tests_passed": true,
      "axe_score_before": 62.5,
      "axe_score_after": 100.0,
      "duration_ms": 1420.0
    },
    "timestamp": "2026-09-27T19:30:26Z"
  }
  ```

---

### Step 6: Audit Finalization & Reporting (`report_service`)
* **Operation**: Calculates compliance improvement, formats audit summary, prepares Git patch branch.
* **HTTP Endpoint**: `GET /report/{scan_id}` returns final `ScanReport`.
* **WebSocket Event**:
  ```json
  {
    "stage": "completed",
    "scan_id": "scan_a1b2c3d4",
    "progress": 100,
    "message": "All violations remediated and verified in Nebius Sandboxes.",
    "data": {
      "overall_score_before": 62.5,
      "overall_score_after": 100.0,
      "total_violations": 4,
      "resolved_violations": 4,
      "unresolved_violations": 0
    },
    "timestamp": "2026-09-27T19:30:28Z"
  }
  ```

---

## 4. Core Pydantic Schemas

Below are the contract definitions that unify the backend models, router responses, and frontend TypeScript typings.

```python
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ViolationSeverity(str, Enum):
    CRITICAL = "critical"
    SERIOUS = "serious"
    MODERATE = "moderate"
    MINOR = "minor"


class PipelineStage(str, Enum):
    INIT = "init"
    CLONING = "cloning"
    SCANNING = "scanning"
    FIXING = "fixing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    ERROR = "error"


class Violation(BaseModel):
    """Represents a specific accessibility defect identified in source code."""
    id: str = Field(description="Unique violation identifier (e.g. 'viol_01')")
    file: str = Field(description="Relative repository path to violating file")
    line: Optional[int] = Field(default=None, description="Starting line number in file")
    type: str = Field(description="WCAG Rule identifier (e.g. 'color-contrast', 'image-alt')")
    severity: ViolationSeverity = Field(description="Impact severity rating")
    description: str = Field(description="Human-readable WCAG defect explanation")
    selector: Optional[str] = Field(default=None, description="DOM or JSX element selector")
    context_snippet: Optional[str] = Field(default=None, description="Original offending code snippet")


class ProposedFix(BaseModel):
    """Represents an AI-synthesized remediation patch generated by Nemotron Ultra."""
    fix_id: str = Field(description="Unique fix identifier")
    violation_id: str = Field(description="Associated violation identifier")
    diff: str = Field(description="Unified git diff string")
    explanation: str = Field(description="Rationale detailing how the fix achieves WCAG compliance")
    original_code: str = Field(description="Original unpatched code block")
    remediated_code: str = Field(description="New accessible replacement code block")


class VerificationResult(BaseModel):
    """Outcome of executing the patched codebase within an isolated Nebius Sandbox."""
    fix_id: str = Field(description="Identifier of verified fix")
    violation_id: str = Field(description="Identifier of verified violation")
    axe_score_before: float = Field(description="Axe-core compliance score before remediation (0-100)")
    axe_score_after: float = Field(description="Axe-core compliance score after remediation (0-100)")
    tests_passed: bool = Field(description="Whether repository unit/regression tests passed cleanly")
    violations_resolved: bool = Field(description="Whether axe-core confirmed the defect was resolved")
    verified: bool = Field(description="True if both tests passed and violation resolved with 0 regressions")
    sandbox_id: Optional[str] = Field(default=None, description="Nebius sandbox execution container ID")
    sandbox_logs: Optional[str] = Field(default=None, description="Captured stdout/stderr from verification run")


class ScanReport(BaseModel):
    """Comprehensive accessibility audit report delivered to the frontend dashboard."""
    scan_id: str = Field(description="Unique scan job identifier")
    repo_url: str = Field(description="Target repository URL")
    branch: str = Field(default="main", description="Target git branch audited")
    violations: List[Violation] = Field(default_factory=list, description="All detected accessibility violations")
    fixes: List[ProposedFix] = Field(default_factory=list, description="All synthesized remediation patches")
    verification_results: List[VerificationResult] = Field(
        default_factory=list, description="Sandbox verification logs and test statuses"
    )
    overall_score_before: float = Field(description="Baseline repository WCAG compliance percentage")
    overall_score_after: float = Field(description="Post-remediation WCAG compliance percentage")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC completion timestamp")
    status: str = Field(default="completed", description="Overall execution status")


class WebSocketProgressMessage(BaseModel):
    """Message schema streamed over /ws/progress to drive real-time dashboard animations."""
    stage: PipelineStage = Field(description="Current active pipeline stage")
    scan_id: str = Field(description="Current scan identifier")
    progress: int = Field(ge=0, le=100, description="Pipeline completion percentage (0-100)")
    message: str = Field(description="Human-readable status update text")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Contextual payload (violations, diffs, scores)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message generation timestamp")
```
