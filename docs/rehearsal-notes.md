# CodeGuard End-to-End Live Rehearsal & Verification Notes

**Rehearsal Date**: October 8, 2026  
**Environment**: Live Deployed Backend on Nebius Cloud / Render (`https://codeguard-backend-6pg4.onrender.com`), Live WebSocket (`wss://codeguard-backend-6pg4.onrender.com`), Frontend at `https://codeguard.dhanushkumar.in/` & local `http://localhost:5173`.  
**Target Repository**: `https://github.com/dhanushkumar-amk/CODEGUARD---NVIDIA-HACKTHON-PROJECT` (seeded accessibility demo files in `sandbox-scripts/demo-app/` and frontend).

---

## 1. Executive Summary & Concrete Demo Numbers

| Metric | Measured Value | Notes |
| :--- | :--- | :--- |
| **Total End-to-End Scan Time** | **101.38 seconds** (~1.69 min) | Shallow clone + 90 chunks scanned + Nemotron classification |
| **Video Target Feasibility** | **Comfortably under 2.5–3 min limit** | Ideal pacing for video demonstration without artificial speeding |
| **Actionable Violations Detected** | **13 violations** | WCAG 2.2 AA (unlabeled inputs, missing alt text, non-interactive clicks, tabindex) |
| **Frontend UI Files Discovered** | **65 files** | Evaluated across TypeScript, React, and HTML markup |
| **Cost per Single Scan** | **$0.0412 (~4.1¢)** | Fast ($0.0220) + Ultra ($0.0192) combined spend |
| **Cumulative Spend (All Runs)** | **$0.0708** | 133 total LLM calls (123 Fast, 10 Ultra) across rehearsal |
| **Real GitHub PR Created** | **PR #2** | Live on GitHub: [PR #2 Link](https://github.com/dhanushkumar-amk/CODEGUARD-NVIDIA-HACKTHON-PROJECT/pull/2) |
| **Export Formats Validated** | Standalone HTML (20.4 KB) & Markdown (7.8 KB) | Both served live via `GET /api/report/{scan_id}/download` and `/markdown` |

---

## 2. Journey Walkthrough & Verification Steps

### Step A: Live Health Check & Initialization
- `GET /health` returned `{"status": "ok"}` (200 OK).
- `POST /api/scan/start` initiated shallow clone of demo repository (`depth=1`), discovered 65 scannable UI files, and prepared 90 isolated markup batches in **3.52 seconds**.

### Step B: Live WebSocket Streaming & Chunk Inspection
- Client connected to `wss://codeguard-backend-6pg4.onrender.com/ws/{scan_id}`.
- Streamed real-time progress across all 90 chunks with live token usage and running spend updates:
  - `[ 10%] Stage: preparing`
  - `[ 23%] Stage: scanning — Scanned 21/90 chunks, 1 violation found, Cost: $0.0126`
  - `[ 52%] Stage: scanning — Scanned 47/90 chunks, 5 violations found, Cost: $0.0186`
  - `[ 96%] Stage: scanning — Scanned 87/90 chunks, 11 violations found, Cost: $0.0339`
  - `[100%] Stage: scanning — Scanned 90/90 chunks, 13 violations found, Cost: $0.0412`

### Step C: Consolidated Audit Report
- `GET /api/report/{scan_id}` returned HTTP 200 with complete structured `ScanReport`:
  - 13 unified violation records with WCAG criteria mapping.
  - Severity breakdown: 11 Critical, 2 High.
  - Category breakdown: Unlabeled Form Fields (5), Empty Link/Button (3), Heading Order (2), Missing Alt Text (1), Non-Interactive Click (1), Focus Order (1).
  - Exact duration tracked: 91.37s.

### Step D: Report Downloads (HTML & Markdown)
- `GET /api/report/{scan_id}/download` verified: returned standalone, styled HTML document (20,407 bytes) with `Content-Disposition: attachment`.
- `GET /api/report/{scan_id}/markdown` verified: returned formatted GitHub-flavored Markdown audit report (7,782 characters).

### Step E: GitHub Pull Request Automation
- Verified GitHub API authentication with personal access token (`dhanushkumar-amk`, admin write permissions).
- Automated remediation branch `refs/heads/codeguard-rehearsal-test` created off default branch `master`.
- Remediation commit created and pushed directly to branch.
- Real pull request opened: **PR #2** at `https://github.com/dhanushkumar-amk/CODEGUARD-NVIDIA-HACKTHON-PROJECT/pull/2`.

---

## 3. Failure Mode & Edge Case Testing

1. **Invalid Repository URL**:
   - Tested: `POST /api/scan/start` with `https://not-github.com/invalid/url`.
   - Result: Returned HTTP 400 with clean error detail: `"Unsupported Git host 'not-github.com'. Supported hosts: GitHub, GitLab, Bitbucket."`
   - UI does not crash or hang.

2. **Unauthorized / Foreign Repository PR Attempt**:
   - Tested: `POST /api/report/{scan_id}/create-pr` with foreign repo `https://github.com/octocat/Spoon-Knife`.
   - Result: Handled gracefully without crash, returned `{"status": "failed", "error": "GitHub API error (404): Not Found"}`.

3. **Duplicate Remediation Branch**:
   - Re-requesting PR creation for an existing scan branch returned clear user-facing message: `"Branch 'codeguard-fixes-...' already exists on repository. Please delete it on GitHub or re-run the scan."`

---

## 4. Bugs Identified & Fixed During Rehearsal

1. **Relative Links on Report Actions**:
   - *Issue*: `Report.tsx` had hardcoded `<a href="/api/report/...">` which failed when the frontend was hosted on Vercel/localhost separate from Render.
   - *Fix*: Updated links to dynamically prepend `VITE_API_BASE_URL` (`https://codeguard-backend-6pg4.onrender.com`), allowing downloads to hit the live backend regardless of frontend host.

2. **Premature WebSocket Completion Trigger**:
   - *Issue*: `useScanProgress.ts` and test scripts checked `progress >= 100` instead of `stage === 'complete'`. Because individual sub-stages (like `scanning`) broadcast `progress: 100` when finishing their phase, the UI could advance before subsequent pipeline stages finished.
   - *Fix*: Strict condition added: `if (payload.stage === 'complete' || payload.stage === 'completed')`.

3. **CORS Regex on Backend**:
   - *Issue*: `backend/app/main.py` only permitted `*.vercel.app` and `*.netlify.app`, blocking custom domains like `https://codeguard.dhanushkumar.in`.
   - *Fix*: Added `dhanushkumar.in` to `ALLOWED_ORIGIN_REGEX` and explicit origins list in `config.py`.

4. **Background Pipeline Exception Resilience**:
   - *Issue*: Background pipeline errors only logged to server console without notifying connected WebSocket clients.
   - *Fix*: Added `broadcast_progress(stage='error', ...)` in the top-level exception handler to immediately alert the UI.

---

## 5. Known Limitations & Production Roadmap

1. **In-Memory Scan State**:
   - Scan jobs and token counters are maintained in process memory. On serverless cold starts or multi-instance scaling, jobs are local to that specific container. Production roadmap: Redis + PostgreSQL.
2. **Ultra Budget Threshold**:
   - In single-scan mode, Nemotron Ultra budget guardrail ($0.05) prevents runaway spending. Multi-scan runs in a single server process accumulate spend toward this ceiling unless reset between tenant sessions.
