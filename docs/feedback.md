# Hackathon Experience & Platform Feedback

This document captures authentic, actionable feedback on **Nebius Token Factory**, **Nebius AI Cloud Sandboxes**, and **NVIDIA Nemotron models**, based directly on the end-to-end design, implementation, and rehearsal of **CodeGuard**.

---

## 1. Nebius Token Factory

### What Worked Exceptionally Well
- **Drop-in OpenAI SDK Compatibility**: Seamless integration with the standard `openai` Python client by simply setting `base_url="https://api.tokenfactory.nebius.com/v1/"`. Asynchronous requests, streaming, and connection pooling worked out of the box without proprietary SDK friction.
- **Lightning Model Throughput & Economics**: **Nemotron 3.5 Lightning** delivered exceptional inference speed and token pricing ($0.06 per 1M prompt tokens, $0.24 per 1M completion tokens). During our full rehearsal across 65 frontend files and 90 batch chunks, high-volume scanning finished in ~90 seconds with a total LLM cost of just **$0.0412 (~4.1¢)**.
- **Inference Stability & Low Latency**: We experienced zero dropped sockets, high concurrent request handling, and sub-second Time to First Token (TTFT) across multi-turn synthesis.

### What Was Confusing or Could Be Improved
- **Promo Code & Billing Onboarding Flow**:
  - The promo code redemption process during hackathon onboarding created initial friction. The billing console required navigating several nested account settings, and error messaging was ambiguous regarding whether payment method verification was mandatory before promotional credits activated.
  - *Recommendation*: Streamline the coupon/code redemption page with instant feedback and a clear banner showing active credit balance and expiry.
- **Model ID Naming Conventions**:
  - The model naming convention in documentation and console felt inconsistent (e.g., mixing hyphens and underscores: `nvidia/Nemotron-3-Ultra-550b-a55b` vs. `nvidia/Nemotron-3_5-Lightning`).
  - *Recommendation*: Maintain a consistent naming pattern across the catalog (e.g., kebab-case or slash notation) and ensure the `/v1/models` endpoint returns descriptive metadata including context window limits, token pricing, and supported parameters (`response_format`, `tools`, etc.).
- **Structured Output Documentation**:
  - Clearer documentation on whether models support native JSON Schema enforcement (`response_format={"type": "json_schema", ...}`) versus basic JSON mode (`{"type": "json_object"}`) would have saved early trial-and-error.

---

## 2. Nebius AI Cloud Sandboxes

### What Worked Well
- **True Process & Execution Isolation**: Running untrusted, newly patched frontend code and test suites inside isolated microVMs/containers rather than on the host backend server is CodeGuard's primary security differentiator.
- **Clean Lifecycle Mechanics**: Spin-up, command execution, and teardown via Python asynchronous context managers (`async with sandbox_session() as sandbox:`) worked reliably, ensuring no orphaned containers or idle credit leakage.

### Real Friction Points & Engineering Feedback
- **Headless Browser Dependencies (Chromium / Playwright)**:
  - Standard container base images (`node:20` or `python:3.11-slim`) lack the native Linux shared libraries required by headless Chromium (`libnss3`, `libatk-bridge2.0-0`, `libcups2`, `libdrm2`, `libxcomposite`, `libxdamage`, `libgbm1`, etc.).
  - Running `npx playwright install --with-deps` inside an ephemeral sandbox took 45–60+ seconds and occasionally hit environment permission hurdles.
  - *Our Solution*: We pre-configured Playwright-specific images (`mcr.microsoft.com/playwright:v1.42.0-jammy`) and built a resilient fallback runner for fast static analysis.
  - *Recommendation*: Offer pre-warmed, pre-configured browser sandbox templates (e.g. `nebius/sandbox-playwright:latest`) specifically for automated testing and browser agent workflows.
- **Need for Sandbox Snapshots / Warm Disk Cloning**:
  - In an autonomous verification loop (apply fix -> install dependencies -> run axe-core -> run tests), reinstalling `node_modules` on every fresh sandbox creates the single biggest latency bottleneck.
  - *Recommendation*: Provide a snapshot/fork API feature where a base sandbox can be provisioned once, dependencies installed, snapshotted, and then branched into multiple lightweight sub-sandboxes in sub-second time.
- **Streaming Stdout / Stderr**:
  - Having WebSocket or SSE streaming of sandbox terminal output during long-running tasks (like `npm test`) would allow agents to detect hanging processes or infinite loops before hitting hard timeouts.

---

## 3. NVIDIA Nemotron Models

### Performance in Our Use Case: Lightning vs. Ultra

| Dimension | Nemotron 3.5 Lightning (`nvidia/Nemotron-3_5-Lightning`) | Nemotron 3 Ultra (`nvidia/Nemotron-3-Ultra-550b-a55b`) |
| :--- | :--- | :--- |
| **Primary Role** | High-throughput AST violation scanning & triage | Complex WCAG patch synthesis & contextual remediation |
| **Speed / TTFT** | Blazing (~0.8s per chunk) | Deep reasoning (~3–5s per patch) |
| **Cost Efficiency** | ~$0.0003 per chunk (90 chunks for ~$0.022) | Higher cost ($1.00/$3.00 per 1M), strictly budget-capped |
| **JSON Adherence** | High with strict system prompt & retry logic | Superior zero-shot JSON formatting and diff fidelity |
| **Contextual Reasoning** | Excellent for single-tag / AST syntax issues | Exceptional for multi-component focus trapping & ARIA state |

### Key Observations & Surprises
- **Lightning Model Consistency**:
  - Lightning proved surprisingly capable at structured accessibility categorization (tagging WCAG criteria, determining severity, locating line numbers).
  - *Surprise/Nuance*: At non-zero temperatures, Lightning occasionally included Markdown formatting fences (````json ... ````) or introductory pleasantries. Adding deterministic fence-stripping regex and JSON repair in `llm_client.py` made the pipeline 100% reliable.
- **Ultra Reasoning Capacity**:
  - Nemotron 3 Ultra demonstrated remarkable semantic understanding of intricate accessibility standards. When fixing interactive components (e.g., custom tablists requiring `role="tablist"`, `aria-selected`, and arrow key focus navigation), Ultra generated syntactically clean, regression-free unified diffs on the first attempt.
- **Budget Guardrails are Essential**:
  - Reserving Ultra for the top 10–15 critical violations while using Lightning for preliminary scanning allowed CodeGuard to audit an entire production repository for **under 5 cents**. This two-tiered model pattern made our architecture both enterprise-scalable and economically sustainable.
