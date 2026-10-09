# CodeGuard 🛡️

> **Autonomous AI Accessibility Remediation Agent powered by NVIDIA Nemotron & Nebius AI Cloud.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.0+-61DAFB.svg)](https://reactjs.org)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron--3.5--Lightning%20%7C%20Nemotron--3--Ultra-76B900.svg)](https://developer.nvidia.com)
[![Nebius Token Factory](https://img.shields.io/badge/Nebius-Token%20Factory-6C5CE7.svg)](https://nebius.com)
[![Tavily Search](https://img.shields.io/badge/Tavily-A11y%20Grounding-blueviolet.svg)](https://tavily.com)

---

## 🎬 Demo Walkthrough

![CodeGuard Demo](./docs/demo.gif)
*Watch CodeGuard autonomously scan a frontend repository, stream real-time violation diagnosis, verify patches inside an isolated Nebius sandbox, and open an automated GitHub Pull Request.*

---

## 💡 What It Does

**CodeGuard** is an autonomous accessibility agent designed to eliminate digital accessibility barriers directly within software development workflows. When provided with a public Git repository URL, CodeGuard executes an end-to-end audit, remediation, and verification pipeline:

1. **Intelligent Ingestion & Scanning**: CodeGuard performs a lightweight shallow clone of the target repository, discovers all user interface files (`.tsx`, `.jsx`, `.html`, `.vue`, `.svelte`), and constructs token-efficient abstract syntax batches. Using **NVIDIA Nemotron 3.5 Lightning**, it rapidly audits hundreds of code blocks in parallel against the **WCAG 2.2 AA** specification, flagging unlabeled form elements, missing alternative text, broken focus traps, keyboard accessibility failures, and color contrast defects.
2. **Authoritative Web Search Grounding via Tavily**: Before diagnosing root causes or generating patches, CodeGuard queries **Tavily AI Search** restricted strictly to authoritative a11y bodies (`w3.org`, `developer.mozilla.org`, `webaim.org`, `dequeuniversity.com`, `a11yproject.com`). It extracts live WCAG 2.2 techniques and verified accessible markup examples, injecting them directly into the Nemotron prompt context to ground generation in official standards rather than hallucinated patterns.
3. **Contextual Diagnosis & Patch Synthesis**: For critical accessibility violations, CodeGuard routes the problematic code and authoritative guidance to **NVIDIA Nemotron 3 Ultra (550B)**. The model analyzes component hierarchy, state management, and user interaction patterns to synthesize clean, idiomatic code remediations, generating exact unified git diffs rather than generic advice.
4. **Isolated Sandbox Verification & PR Automation**: Rather than blindly proposing code modifications, CodeGuard spins up an isolated **Nebius AI Cloud Sandbox**. Inside this microVM, it applies the synthesized patch, executes `@axe-core/playwright`, and runs the project's native test suite to verify that the accessibility defect was eliminated without causing functional regressions. Once verified, CodeGuard generates comprehensive HTML/Markdown audit reports with clickable grounding source citations and can automatically create a verified remediation branch and GitHub Pull Request.

---

## 🌍 Why It Matters

Over **1.3 billion people** worldwide—approximately 16% of the global population—live with significant disabilities. Despite clear international legal standards (such as Section 508 and the European Accessibility Act), **96% of the world's top one million websites fail basic accessibility checks** ([WebAIM Million](https://webaim.org/projects/million/)).

Most development teams want to build inclusive software, but traditional accessibility tooling creates severe bottlenecks:
- **Linting tools** (e.g., `eslint-plugin-jsx-a11y`) only identify static syntax errors and cannot fix them or understand dynamic component interactions.
- **Manual accessibility audits** cost tens of thousands of dollars, take weeks to complete, and produce lengthy PDF reports that quickly become outdated.
- **Generic AI code assistants** frequently produce hallucinated patches that break unit tests or introduce subtle regressions.

CodeGuard transforms digital accessibility from a painful, manual compliance chore into an autonomous, continuous engineering workflow—ensuring the web becomes accessible to everyone, by default.

---

## ⚡ How It Uses Nebius Token Factory

CodeGuard implements a tiered, cost-optimized LLM orchestration architecture powered by **Nebius Token Factory**:

- **High-Throughput AST Triage via Nemotron 3.5 Lightning**:
  - Priced at just **$0.06 / 1M input tokens** and **$0.24 / 1M output tokens**, Lightning performs rapid AST batch evaluation, rule classification, and violation scoring across dozens of files simultaneously with sub-second Time-to-First-Token (TTFT).
- **Deep Contextual Remediation via Nemotron 3 Ultra (550B)**:
  - Complex accessibility challenges (such as accessible focus trapping, keyboard navigation for custom tablists, and dynamic ARIA live regions) require deep multi-step reasoning. CodeGuard routes these high-severity items to Nemotron 3 Ultra to synthesize production-ready unified diffs.
- **Strict In-Memory Budget Guardrails**:
  - Each scan session is protected by strict budget limits (`ULTRA_MAX_CALLS_PER_SCAN=10` and `ULTRA_BUDGET_USD_PER_SCAN=$0.05`). If the threshold is reached, CodeGuard gracefully falls back to the fast tier, guaranteeing zero unexpected credit drain.
- **Real-World Cost Efficiency**:
  - In our Phase 28 rehearsal scanning **65 frontend files** across **90 batch chunks**, CodeGuard completed the entire end-to-end scan and remediation generation for a total LLM cost of just **$0.0412 (~4.1¢)**.

---

## 🔒 How It Uses Nebius AI Cloud Sandboxes

The **isolated verification loop** is CodeGuard's core differentiator:

```
[Synthesize Patch] ──► [Spin Up Nebius Sandbox] ──► [Apply Git Patch]
                                                            │
[Pass Verification] ◄── [Run Repository Test Suite] ◄── [Run axe-core]
        │
[Open GitHub PR / Export Report]
```

Executing untrusted, newly patched frontend code directly on host infrastructure is dangerous and unreliable. CodeGuard provisions ephemeral **Nebius AI Cloud Sandboxes** (containerized microVM environments) managed via Python asynchronous context managers:
1. **Isolated Execution**: Clones the remediation target in a sandboxed container, ensuring untrusted repository code never touches host processes.
2. **Automated axe-core Validation**: Executes headless browser audits inside the sandbox to empirically prove the WCAG violation has been resolved.
3. **Regression Prevention**: Automatically triggers the repository's native test suite (e.g. `npm test`, `jest`, `vitest`) to verify that the accessibility patch did not break existing application behavior.
4. **Guaranteed Teardown**: Sandbox destruction is enforced inside `finally` blocks upon test completion or error, preventing idle compute leakage.

---

## 🌐 Web Search Grounding via Tavily

To eliminate LLM hallucinations and anchor remediations directly to verified accessibility engineering practices, CodeGuard integrates **Tavily AI Search**:

1. **Domain-Restricted Retrieval**:
   - Web searches are strictly restricted to trusted accessibility authorities: `w3.org`, `developer.mozilla.org` (MDN), `webaim.org`, `dequeuniversity.com`, and `a11yproject.com`.
   - Before diagnosis and patch synthesis, CodeGuard queries these domains for exact WCAG 2.2 techniques (e.g., `H37`, `ARIA1`, `G183`) and verified accessible markup examples matching each violation category.
2. **Dynamic Prompt Injection**:
   - Retrieved guidance and code snippets are formatted into Nemotron 3 Ultra prompts as high-priority reference blocks, explicitly directing the model to prioritize official web standards over parametric training memory.
3. **Process-Lifetime Caching & Budget Controls**:
   - Guidance is cached in-memory per violation category across the scan lifecycle, minimizing redundant API requests and search costs (`TAVILY_MAX_SEARCHES_PER_SCAN=12`).
4. **Transparent Source Attribution**:
   - Every diagnosed violation and proposed patch includes clickable source citations linking directly to the underlying W3C or MDN standard in both the web UI and exported audit reports.
5. **Resilient Non-Blocking Fallback**:
   - If Tavily searches encounter network timeouts or an absent API key, CodeGuard gracefully falls back to parametric model synthesis without blocking the remediation pipeline.

---

## 🧠 NVIDIA Nemotron Models Used

CodeGuard relies on the following official model endpoints hosted on Nebius Token Factory (configured in [`backend/app/config.py`](backend/app/config.py)):

| Purpose | Model ID | Capabilities |
| :--- | :--- | :--- |
| **Fast Scanning & Triage** | `nvidia/Nemotron-3_5-Lightning` | High-throughput parsing, WCAG rule categorization, rapid token streaming |
| **Deep Reasoning & Fixes** | `nvidia/Nemotron-3-Ultra-550b-a55b` | 550B parameter deep reasoning, stateful ARIA logic, unified diff generation |

---

## 🏛️ Architecture

For complete system design, data flow diagrams, and schema specifications, refer to [**docs/architecture.md**](docs/architecture.md).

```text
┌────────────────────────────────────────────────────────┐
│               React 18 + Vite Dashboard                │
│    (Live WebSocket progress, Diff viewer, PR trigger)  │
└───────────────────────────▲────────────────────────────┘
                            │ WebSocket / REST
┌───────────────────────────▼────────────────────────────┐
│                  FastAPI Backend Server                │
│  ┌───────────────────────┐   ┌───────────────────────┐ │
│  │ Git Ingestion Service │   │ Aggregator & Scanner  │ │
│  └───────────────────────┘   └───────────────────────┘ │
│  ┌───────────────────────┐   ┌───────────────────────┐ │
│  │ Fixer & Diff Engine   │   │ Report & PR Generator │ │
│  └───────────────────────┘   └───────────────────────┘ │
└─────────────▲─────────────────────────────▲────────────┘
              │                             │
┌─────────────▼─────────────┐ ┌─────────────▼────────────┐
│   Nebius Token Factory    │ │ Nebius AI Cloud Sandbox  │
│  - Nemotron 3.5 Lightning │ │  - Ephemeral Container   │
│  - Nemotron 3 Ultra 550B  │ │  - axe-core + Playwright │
│  - Budget Guardrails      │ │  - Native Test Runner    │
└───────────────────────────┘ └──────────────────────────┘
```

---

## 🌐 Live Demo & Deployments

- **Deployed Web Dashboard**: [https://codeguard.dhanushkumar.in/](https://codeguard.dhanushkumar.in/)
- **Live Backend API**: [https://codeguard-backend-6pg4.onrender.com](https://codeguard-backend-6pg4.onrender.com)
- **API Health Check**: [https://codeguard-backend-6pg4.onrender.com/health](https://codeguard-backend-6pg4.onrender.com/health)
- **Interactive Swagger Docs**: [https://codeguard-backend-6pg4.onrender.com/docs](https://codeguard-backend-6pg4.onrender.com/docs)
- **Live WebSocket Endpoint**: `wss://codeguard-backend-6pg4.onrender.com/ws/{scan_id}`
- **Automated Pull Request Generated by CodeGuard**: [GitHub PR #2](https://github.com/dhanushkumar-amk/CODEGUARD-NVIDIA-HACKTHON-PROJECT/pull/2)

---

## 💻 Setup Instructions

Follow these steps to run CodeGuard locally.

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm**
- **Git**

### 1. Clone the Repository
```bash
git clone https://github.com/dhanushkumar-amk/CODEGUARD---NVIDIA-HACKTHON-PROJECT.git
cd CODEGUARD---NVIDIA-HACKTHON-PROJECT
```

### 2. Backend Setup (FastAPI)
```bash
cd backend

# Create and activate virtual environment
# Windows (PowerShell):
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
```

Edit `backend/.env` with your API credentials (refer to `backend/.env.example` and `backend/.env.production.example` for reference):
```env
NEBIUS_TOKEN_FACTORY_API_KEY=your_nebius_api_key_here
NEBIUS_SANDBOX_API_KEY=your_sandbox_api_key_here  # optional, mock fallback active by default
GITHUB_TOKEN=your_personal_access_token_here      # required for automated PR creation
TAVILY_API_KEY=your_tavily_api_key_here          # required for live WCAG web grounding
```

Start the backend server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Verify the backend is live at [http://localhost:8000/health](http://localhost:8000/health).

### 3. Frontend Setup (React + Vite)
In a new terminal window:
```bash
cd frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env

# Start Vite development server
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### 4. Running the Test Suites
```bash
# Run backend pytest suite
cd backend
pytest -v

# Run frontend test suite
cd frontend
npm test
```

---

## 🛠️ Tech Stack

Extracted from [**docs/tech-stack.md**](docs/tech-stack.md):

- **Backend**: Python 3.11, FastAPI, Pydantic v2, Uvicorn, GitPython, Tenacity (retry handling), HTTPX
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Framer Motion, Recharts, Lucide React
- **AI & Inference**: Nebius Token Factory, NVIDIA Nemotron 3.5 Lightning, NVIDIA Nemotron 3 Ultra (550B)
- **Web Search Grounding**: Tavily AI Search (`tavily-python`), domain-restricted WCAG retrieval
- **Verification & Sandboxing**: Nebius AI Cloud Sandboxes, Playwright, `@axe-core/playwright`, Headless Chromium
- **Real-time Protocol**: Native WebSockets for low-latency pipeline streaming

---

## 🔍 Known Limitations

We believe in complete engineering honesty. The following real-world limitations were documented during our Phase 28 rehearsal:

1. **In-Memory Scan State**:
   - Scan jobs, token counters, and progress states are maintained in-memory on the backend process. If the server restarts, historical scan state is cleared. *(Production roadmap: Redis + PostgreSQL persistence).*
2. **Heading-Order Violations Require Holistic Review**:
   - While CodeGuard flags heading skips (`<h1>` directly followed by `<h3>`), remediating global heading hierarchy across multiple decoupled components often requires site-wide layout refactoring rather than local single-file patches.
3. **GitHub Pull Request Creation Requires Repository Write Permissions**:
   - Automated PR creation relies on a GitHub Personal Access Token (`GITHUB_TOKEN`). CodeGuard can only push remediation branches and open PRs on repositories where the token has write/collaborator permissions. Scans on foreign or read-only repos still provide full reports and downloadable diffs.
4. **Sandbox Dependency Installation Overhead**:
   - In environments without pre-warmed container snapshots, running `npm install` inside fresh sandboxes introduces latency before test verification commences.

---

## 🚀 What We'd Build Next

1. **Persistent Multi-Tenant Storage & Dashboard**: Integrate PostgreSQL and Redis to persist audit logs, track team compliance scores over time, and support multi-tenant organizations.
2. **CI/CD GitHub Action & Pre-Commit Hook**: Package CodeGuard as a native GitHub Action to automatically fail pull requests that introduce new WCAG 2.2 AA violations before code merges.
3. **Dynamic Multimodal Accessibility**: Expand beyond static markup to evaluate live audio/video closed captions, dynamic internationalization (i18n) screen-reader announcements, and animated motion reduction (`prefers-reduced-motion`).

---

## 📄 License

MIT — see [LICENSE](LICENSE).
