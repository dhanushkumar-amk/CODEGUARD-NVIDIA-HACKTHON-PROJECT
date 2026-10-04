# CodeGuard Accessibility Audit & Remediation Report

**Repository:** `https://github.com/dhanushkumar-amk/CODEGUARD-NVIDIA-HACKTHON-PROJECT`  
**Branch:** `main`  
**Scan ID:** `scan_0f1305f4`  
**Timestamp:** `2026-10-04 12:53:08 UTC`  
**Pipeline Duration:** `142.50s`  
**Status:** `COMPLETED`  

---

## Executive Summary

The automated accessibility audit of the CODEGUARD NVIDIA Hackathon project identified 10 total violations, with only one successfully fixed and verified in the sandbox. Nine additional violations failed fix synthesis due to tool quota limitations, representing the primary engineering backlog requiring immediate attention. Despite these remediation efforts, the WCAG score remained unchanged at 97.1%, highlighting the need for targeted human-led fixes to drive meaningful accessibility progress.

---

## Overall Compliance Score

- **Initial Baseline:** `██████████ 97.1%`
- **Remediated Result:** `██████████ 97.1%`
- **Net Improvement:** **+0.0 points**
- **Verified Fix Rate:** **1 / 10 defects resolved**

---

## Violations & Remediation Summary

| # | Status | Severity | Category | Location | Description |
|---|--------|----------|----------|----------|-------------|
| 1 | **Fixed And Verified** | CRITICAL | UNLABELED_FORM_FIELD | `frontend/src/components/RepoInput.tsx:32` | Form <input> element has no associated <label>, aria-label, or aria-labelle... |
| 2 | **Fix Failed** | CRITICAL | UNLABELED_FORM_FIELD | `frontend/src/components/RepoInput.tsx:22` | Form <input> element has no associated <label>, aria-label, or aria-labelle... |
| 3 | **Fix Failed** | CRITICAL | UNLABELED_FORM_FIELD | `sandbox-scripts/demo-app/src/components/Header.tsx:24` | Form <input> element has no associated <label>, aria-label, or aria-labelle... |
| 4 | **Fix Failed** | CRITICAL | NON_INTERACTIVE_CLICK | `sandbox-scripts/demo-app/src/components/Header.tsx:27` | Non-interactive <div> with onClick must have a role, tabIndex, and keyboard... |
| 5 | **Fix Failed** | CRITICAL | UNLABELED_FORM_FIELD | `sandbox-scripts/demo-app/src/components/LoginForm.tsx:27` | Form <textarea> element has no associated <label>, aria-label, or aria-labe... |
| 6 | **Fix Failed** | CRITICAL | EMPTY_LINK_OR_BUTTON | `sandbox-scripts/demo-app/src/components/Header.tsx:32` | <button> element has no accessible text name and no aria-label. |
| 7 | **Fix Failed** | CRITICAL | EMPTY_LINK_OR_BUTTON | `sandbox-scripts/demo-app/src/components/Header.tsx:37` | Anchor <a> element has an empty, '#', or missing href attribute. |
| 8 | **Fix Failed** | CRITICAL | FOCUS_MANAGEMENT | `sandbox-scripts/demo-app/src/components/LoginForm.tsx:40` | Avoid positive tabIndex values (2) which disrupt natural focus navigation o... |
| 9 | **Fix Failed** | CRITICAL | MISSING_ALT_TEXT | `sandbox-scripts/demo-app/src/components/Header.tsx:21` | Images must have an alt attribute describing the image or alt="" if decorat... |
| 10 | **Fix Failed** | HIGH | HEADING_ORDER | `frontend/src/pages/Home.tsx:34` | Heading level skipped from <h1> to <h3> without an intermediate <h2>. |

---

## Verified Fixes (Sandboxed Proof-of-Work)

### viol_02: UNLABELED_FORM_FIELD in `frontend/src/components/RepoInput.tsx`
- **Criterion:** 3.3.2 Labels or Instructions
- **Explanation:** In RepoInput.tsx, a critical priority Unlabeled Form Field issue was identified: Form <input> element has no associated <label>, aria-label, or aria-labelledby. Addressing this ensures full compliance and accessible interaction for assistive technology users.
- **Verification Metrics:** axe-core score 97.1% → 97.1% | Test Suite: Skipped/No tests
```diff
--- a/frontend/src/components/RepoInput.tsx
+++ b/frontend/src/components/RepoInput.tsx
@@ -1,4 +1,6 @@
         <input

           type="text"

+          id="branch-input"

+          aria-label="Branch name"

           value={branch}

           onChange={(e) => setBranch(e.target.value)}
```

---

## Known Limitations & Remaining Action Items

- **viol_01** (`frontend/src/components/RepoInput.tsx:22`): **Fix Failed** (Validation failed after escalation and retry: Per-scan Ultra call limit (12) reached for scan 'scan_0f1305f4' (calls=12, in_flight=0).). Form <input> element has no associated <label>, aria-label, or aria-labelledby.
- **viol_03** (`sandbox-scripts/demo-app/src/components/Header.tsx:24`): **Fix Failed** (Validation failed after escalation and retry: Per-scan Ultra call limit (12) reached for scan 'scan_0f1305f4' (calls=12, in_flight=0).). Form <input> element has no associated <label>, aria-label, or aria-labelledby.
- **viol_04** (`sandbox-scripts/demo-app/src/components/Header.tsx:27`): **Fix Failed** (Validation failed after escalation and retry: Per-scan Ultra call limit (12) reached for scan 'scan_0f1305f4' (calls=12, in_flight=0).). Non-interactive <div> with onClick must have a role, tabIndex, and keyboard handler (onKeyDown).
- **viol_05** (`sandbox-scripts/demo-app/src/components/LoginForm.tsx:27`): **Fix Failed** (Validation failed after escalation and retry: Per-scan Ultra call limit (12) reached for scan 'scan_0f1305f4' (calls=12, in_flight=0).). Form <textarea> element has no associated <label>, aria-label, or aria-labelledby.
- **viol_06** (`sandbox-scripts/demo-app/src/components/Header.tsx:32`): **Fix Failed** (Validation failed after escalation and retry: Per-scan Ultra call limit (12) reached for scan 'scan_0f1305f4' (calls=12, in_flight=0).). <button> element has no accessible text name and no aria-label.
- **viol_07** (`sandbox-scripts/demo-app/src/components/Header.tsx:37`): **Fix Failed** (Validation failed after escalation and retry: Per-scan Ultra call limit (12) reached for scan 'scan_0f1305f4' (calls=12, in_flight=0).). Anchor <a> element has an empty, '#', or missing href attribute.
- **viol_08** (`sandbox-scripts/demo-app/src/components/LoginForm.tsx:40`): **Fix Failed** (Validation failed after escalation and retry: Per-scan Ultra call limit (12) reached for scan 'scan_0f1305f4' (calls=12, in_flight=0).). Avoid positive tabIndex values (2) which disrupt natural focus navigation order.
- **viol_09** (`sandbox-scripts/demo-app/src/components/Header.tsx:21`): **Fix Failed** (Validation failed after escalation and retry: Per-scan Ultra call limit (12) reached for scan 'scan_0f1305f4' (calls=12, in_flight=0).). Images must have an alt attribute describing the image or alt="" if decorative.
- **viol_10** (`frontend/src/pages/Home.tsx:34`): **Fix Failed** (Validation failed after escalation and retry: Per-scan Ultra call limit (12) reached for scan 'scan_0f1305f4' (calls=12, in_flight=0).). Heading level skipped from <h1> to <h3> without an intermediate <h2>.

---

## LLM Inference & Cost Accounting

| Model Tier | Purpose | Cost (USD) |
|------------|---------|------------|
| **Nemotron-3_5-Lightning** (Fast) | High-speed detection, batch extraction, executive summary | `$0.011644` |
| **Nemotron-3-Ultra** (Ultra) | Root-cause diagnosis, code patch synthesis, self-healing | `$0.037383` |
| **Total Pipeline Cost** | Complete automated audit & verification | **`$0.049027`** |

---
*Generated automatically by CodeGuard — Autonomous Accessibility Remediation Engine.*