# CodeGuard Architecture & System Design

CodeGuard is an end-to-end automated accessibility remediation agent. It links code analysis, state-of-the-art LLM reasoning via NVIDIA Nemotron, and secure validation inside isolated Nebius execution sandboxes.

---

## 🏛️ High-Level System Architecture

```text
+-----------------------------------------------------------------------------------+
|                                 CodeGuard Workflow                                |
+-----------------------------------------------------------------------------------+
                                          |
                      +-------------------+-------------------+
                      |                                       |
                      v                                       v
         +--------------------------+           +--------------------------+
         |   Git / Local Codebase   |           |  Developer Web Dashboard |
         |   (React, Vue, HTML, UI) |           |   (React 18 + TS + Vite) |
         +--------------------------+           +--------------------------+
                      |                                       |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |       CodeGuard FastAPI Backend       |
                      |   - Static Ast / axe-core Parser      |
                      |   - Issue Categorizer & Context Gather|
                      |   - Prompt Engine & Verifier Loop     |
                      +---------------------------------------+
                                          |
                      +-------------------+-------------------+
                      |                                       |
                      v                                       v
        +----------------------------+         +----------------------------+
        |   Nebius Token Factory     |         |  Nebius Isolated Sandbox   |
        |  (NVIDIA Nemotron Models)  |         | (Ephemeral Execution Env)  |
        +----------------------------+         +----------------------------+
        | • Nemotron-Mini (Nano):    |         | • axe-core headless runner |
        |   Triage & token filtering |         | • Component unit tests     |
        | • Nemotron-4-340B (Ultra): |         | • Diff verification &     |
        |   Deep a11y patch synth    |         |   regression confirmation  |
        +----------------------------+         +----------------------------+
                      |                                       |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |     Verified WCAG Remediation PR      |
                      |      + Comprehensive Audit Report     |
                      +---------------------------------------+
```

---

## 🔄 Core Components

### 1. Backend Orchestration Agent (FastAPI)
- **Scanning Service**: Integrates with linters, JSX/TSX AST parsers, and axe-core rules to uncover accessibility defects (missing `aria-*`, poor contrast, missing alt tags, keyboard traps, faulty role hierarchies).
- **Context Extraction**: Pulls surrounding component code, CSS tokens, and component unit tests to provide full context to the model.
- **Verification Loop**: Manages a generate-and-verify feedback loop between Nemotron generation and sandbox testing.

### 2. Nebius Token Factory & NVIDIA Nemotron
- **Model Tiers**:
  - **Nemotron Nano (e.g. `nvidia/nemotron-mini-4b-instruct`)**: Quickly parses violation reports, eliminates false positives, and builds compact prompts.
  - **Nemotron Ultra (e.g. `nvidia/nemotron-4-340b-instruct`)**: Produces minimal, idiomatic, WCAG 2.2 AA compliant patches that respect existing component design systems.

### 3. Isolated Nebius Sandboxes
- Every patch proposed by Nemotron is injected into an isolated, ephemeral sandbox.
- Runs `axe-core` in a headless browser (Puppeteer / Playwright) against the rendered component.
- Runs the repository's existing test suite (`npm test`, `vitest`, `jest`) to ensure zero visual or functional regressions.
- Only patches passing 100% of test suites and resolving target a11y violations are delivered to the user.

### 4. Interactive Frontend (React + Vite)
- Clean, responsive monitoring dashboard to trigger repo scans, inspect real-time progress, review before/after diffs, and approve pull requests.
