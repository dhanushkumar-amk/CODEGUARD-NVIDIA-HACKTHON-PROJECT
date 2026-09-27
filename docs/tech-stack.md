# CodeGuard Technology Stack & Architecture Decisions

This document details the architectural choices, component rationale, and deployment considerations for **CodeGuard** — the automated accessibility remediation agent.

---

## 🏛️ Technology Stack Summary

| Layer | Technology | Primary Rationale |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI (Python 3.11+)** | High-performance asynchronous execution, native OpenAPI schema generation via Pydantic v2, and first-class WebSocket support for real-time progress streaming. |
| **Frontend Framework** | **React 18 + TypeScript + Vite** | Instant Hot Module Replacement (HMR), static type safety matching backend schemas, and fast production bundle builds. |
| **Styling & Motion** | **Tailwind CSS + Framer Motion** | Utility-first responsive styling with fluid micro-animations for pipeline progress tracking. |
| **Data Visualization** | **Recharts** | Interactive SVG before/after WCAG compliance scoring comparison. |
| **AI / Reasoning Tier** | **NVIDIA Nemotron via Nebius Token Factory** | Two-tiered model strategy: **Nemotron Nano (4B)** for high-throughput violation triage; **Nemotron Ultra (340B)** for complex WCAG 2.2 AA patch synthesis. |
| **Execution Sandboxes** | **Nebius AI Cloud Sandboxes** | Ephemeral, isolated microVM/container environments ensuring untrusted generated code cannot access backend host resources. |
| **Headless Browser / a11y** | **Playwright + @axe-core/playwright** | Full rendered DOM evaluation, computed CSS color contrast checking, and headless Chromium stability over Puppeteer. |
| **Real-time Transport** | **WebSockets (`/ws/progress`)** | Low-latency, bidirectional streaming of pipeline stages (cloning → scanning → triaging → synthesizing → verifying) without HTTP polling. |
| **Resilience & Retries** | **Tenacity** | Asynchronous exponential backoff retries on transient network disconnects without retrying test suite execution failures. |

---

## 🔍 Key Architectural Decisions & "Why" Rationale

### 1. Playwright vs. Puppeteer
* **Multi-Platform Consistency**: Playwright provides modern container support across Linux distributions with unified headless browser engines.
* **Auto-Waiting & Stability**: Playwright handles dynamic client-side hydration in modern web frameworks (React, Vue, Next.js) before axe-core evaluates the DOM, preventing race conditions.
* **First-Class axe Integration**: The `@axe-core/playwright` package directly injects the axe script and extracts structured WCAG 2.2 AA violations with exact DOM selectors and computed styles.

### 2. Two-Tiered Nemotron Model Architecture
* **Nemotron Nano (`nvidia/nemotron-mini-4b-instruct`)**:
  - Fast, cost-efficient triage agent.
  - Parses static AST scan outputs, eliminates false positives, and strips irrelevant lines from code context before calling large models.
* **Nemotron Ultra (`nvidia/nemotron-4-340b-instruct`)**:
  - High-capacity reasoning engine.
  - Generates idiomatic, minimal code diffs that preserve existing component props, TypeScript types, and design systems while achieving WCAG AA compliance.

### 3. Asynchronous Context Manager for Sandbox Teardown
* Spin-up and teardown are wrapped in `async with sandbox_session() as sandbox:`:
* **Guaranteed Teardown**: Guarantees `destroy_sandbox` is dispatched in a `finally` block even if a command times out or an assertion errors out mid-run, preventing resource leaks and credit burn.
* **Concurrency Gating**: Local semaphore protection ensures concurrent sandboxes do not exceed `SANDBOX_MAX_CONCURRENT`.

### 4. WebSockets over Server-Sent Events (SSE)
* Provides full bidirectional communication for interactive remediation: the frontend can stream progress and also transmit user approvals, fix confirmations, or cancel signals over a single persistent connection.

---

## ⚠️ Sandbox Compatibility & Chromium Dependencies (Critical Notice)

### The Challenge
Standard base container images (such as generic `node:20`, `node:alpine`, or `python:3.11-slim`) **do not include Chromium or its required Linux shared libraries** (`libnss3`, `libatk-bridge2.0-0`, `libcups2`, `libdrm2`, `libxcomposite`, `libxdamage`, `libxrandr`, `libgbm1`, etc.).

Running `playwright install chromium` inside an unconfigured sandbox will either:
1. **Fail** with `Host system is missing dependencies to run browsers`.
2. **Incur significant latency** (30–60+ seconds per sandbox boot) downloading browser binaries over the network.

### Recommended Solutions
1. **Pre-configured Playwright Container Image (Recommended)**:
   - Configure `NEBIUS_SANDBOX_DEFAULT_IMAGE=mcr.microsoft.com/playwright:v1.42.0-jammy` or deploy a lightweight custom Docker image (`codeguard-runner:latest`).
   - These images have Chromium and all required C-libraries pre-baked into the container layer, enabling instant sub-second boot times.
2. **Two-Stage Analysis Architecture**:
   - **Stage 1 (Fast AST & Static Analysis)**: Run regex, JSX AST parsing, and headless JSDOM checks inside a standard lightweight `node:20` sandbox.
   - **Stage 2 (Full Browser Render)**: Dispatch only components requiring visual CSS contrast calculations (e.g. background color inheritance) into the Playwright-enabled sandbox.
