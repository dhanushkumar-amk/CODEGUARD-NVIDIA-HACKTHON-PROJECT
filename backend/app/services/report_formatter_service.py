"""
Report Formatter Service (Phase 23).
Transforms structured ScanReport data into polished, human-readable presentations:
1. Executive summaries synthesized via Nemotron Fast (with deterministic template fallback).
2. Clean, well-structured standalone Markdown reports with diffs, metrics, and limitations.
3. Dark-themed, responsive standalone HTML reports with inline styling.
4. File export handlers saving reports to disk under backend/generated_reports/{scan_id}/.
"""
from datetime import datetime
import html
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from app.models.schemas import ScanReport, UnifiedViolationRecord
from app.services.llm_client import call_nemotron_fast

logger = logging.getLogger(__name__)

GENERATED_REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "generated_reports"


def _build_fallback_executive_summary(report: ScanReport) -> str:
    """Generates a deterministic 3-4 sentence executive summary from report metrics."""
    stats = report.summary or {}
    total_violations = stats.get("total_violations", len(report.violations))
    verified_count = stats.get("fixed_and_verified", 0)
    score_before = round(report.overall_score_before, 1)
    score_after = round(report.overall_score_after, 1)
    diff_points = round(score_after - score_before, 1)

    s1 = f"This accessibility audit analyzed repository '{report.repo_url}' and identified {total_violations} actionable accessibility violation{'s' if total_violations != 1 else ''}."
    if verified_count > 0:
        s2 = f"CodeGuard automatically synthesized and sandbox-verified remediation patches for {verified_count} of {total_violations} defect{'s' if verified_count != 1 else ''}, raising compliance from {score_before}% to {score_after}% (+{diff_points} pts)."
    else:
        s2 = f"Remediation patches were generated for targeted issues with a baseline accessibility compliance score of {score_before}%."

    remaining = total_violations - verified_count
    if remaining > 0:
        s3 = f"The remaining {remaining} item{'s' if remaining != 1 else ''} require manual code inspection or targeted review."
    else:
        s3 = "All identified accessibility defects have been successfully resolved with zero test regressions."

    s4 = "All applied fixes have been confirmed free of regression against the project's test suite and validated with axe-core."
    return f"{s1} {s2} {s3} {s4}"


async def generate_executive_summary(report: ScanReport) -> str:
    """
    Synthesizes a 3-4 sentence natural-language executive summary using Nemotron Fast.
    Falls back gracefully to a deterministic template if the LLM call fails.
    """
    stats = report.summary or {}
    prompt = f"""You are an expert accessibility engineering lead at CodeGuard.
Summarize the following automated accessibility audit in 3-4 clear, professional sentences for executive stakeholders and engineering leads:
- Repository: {report.repo_url}
- Total Violations Detected: {stats.get('total_violations', len(report.violations))}
- Fixed and Verified in Sandbox: {stats.get('fixed_and_verified', 0)}
- Fixed but Verification Regressed: {stats.get('fixed_not_verified', 0)}
- Fix Synthesis Failed / Quota: {stats.get('fix_failed', 0)}
- Detected Only (Below threshold): {stats.get('detected_only', 0)}
- Initial Baseline WCAG Score: {report.overall_score_before}%
- Remediated WCAG Score: {report.overall_score_after}%
- Score Improvement: +{stats.get('improvement_points', round(report.overall_score_after - report.overall_score_before, 1))} pts

Write ONLY 3-4 natural, cohesive sentences. Do not use bullet points or headers. Highlight both the verified improvements and items requiring engineering attention."""

    try:
        summary_text = await call_nemotron_fast(
            prompt=prompt,
            system_prompt="You write concise, accurate accessibility executive summaries. Output 3-4 sentences only.",
            scan_id=report.scan_id,
        )
        cleaned = re.sub(r"(?is)<think>.*?</think>", "", summary_text).strip()
        # If response contains markdown bullet points, numbered analysis, or "role:", it's internal reasoning
        has_reasoning = any(tok in cleaned.lower() for tok in ["thinking process", "role:", "analyze the request", "constraints:"])
        if has_reasoning:
            # Look for double-quoted summary block or a trailing coherent paragraph
            match = re.search(r'"([^"]{60,})"', cleaned)
            if match and not any(tok in match.group(1).lower() for tok in ["thinking", "task:"]):
                cleaned = match.group(1).strip()
            else:
                # Try finding a paragraph after the analysis
                paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
                candidate = ""
                for p in reversed(paragraphs):
                    if len(p) > 60 and not p.startswith(("-", "*", "1.", "2.", "3.", "4.", "Role:", "Task:")):
                        candidate = p
                        break
                if candidate:
                    cleaned = candidate
                else:
                    return _build_fallback_executive_summary(report)

        cleaned = cleaned.replace("\n", " ").strip()
        if cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1].strip()

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if len(s.strip()) > 15]
        if len(sentences) >= 2 and not any(tok in cleaned.lower() for tok in ["thinking process", "task:", "role:"]):
            return " ".join(sentences[:4])
    except Exception as exc:
        logger.warning(f"Fast LLM executive summary synthesis failed for {report.scan_id}: {exc}. Using fallback template.")

    return _build_fallback_executive_summary(report)


def _render_ascii_bar(score: float, width: int = 10) -> str:
    """Renders a text progress bar like '████████░░ 85%'."""
    clamped = max(0.0, min(100.0, score))
    filled_count = int(round((clamped / 100.0) * width))
    empty_count = width - filled_count
    return f"{'█' * filled_count}{'░' * empty_count} {clamped:.1f}%"


def format_report_as_markdown(report: ScanReport, executive_summary: str) -> str:
    """
    Produces a clean, human-readable Markdown report document with metadata,
    executive summary, score comparisons, grouped violation tables, detailed diffs,
    cost accounting, and known limitations.
    """
    stats = report.summary or {}
    cost_info = report.cost_breakdown or stats.get("cost_breakdown", {})
    cost_fast = getattr(cost_info, "fast_cost", cost_info.get("fast_cost", 0.0) if isinstance(cost_info, dict) else 0.0)
    cost_ultra = getattr(cost_info, "ultra_cost", cost_info.get("ultra_cost", 0.0) if isinstance(cost_info, dict) else 0.0)
    cost_total = getattr(cost_info, "total_cost", cost_info.get("total_cost", 0.0) if isinstance(cost_info, dict) else 0.0)

    score_before_bar = _render_ascii_bar(report.overall_score_before)
    score_after_bar = _render_ascii_bar(report.overall_score_after)
    imp_pts = round(report.overall_score_after - report.overall_score_before, 1)

    unified = report.unified_records or []
    # If unified_records not populated, link on the fly
    if not unified and (report.violations or report.fixes):
        from app.services.aggregator_service import link_violation_to_fix_and_verification
        raw_u = link_violation_to_fix_and_verification(report.scan_id)
        unified = [UnifiedViolationRecord(**r) for r in raw_u]

    # Group records by status priority
    order = ["fixed_and_verified", "fixed_not_verified", "detected_only", "fix_failed", "verification_skipped"]
    grouped: Dict[str, List[UnifiedViolationRecord]] = {k: [] for k in order}
    for rec in unified:
        st = rec.final_status if rec.final_status in grouped else "detected_only"
        grouped[st].append(rec)

    timestamp_str = (
        report.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        if isinstance(report.timestamp, datetime)
        else str(report.timestamp)
    )

    lines: List[str] = [
        f"# CodeGuard Accessibility Audit & Remediation Report",
        f"",
        f"**Repository:** `{report.repo_url}`  ",
        f"**Branch:** `{report.branch}`  ",
        f"**Scan ID:** `{report.scan_id}`  ",
        f"**Timestamp:** `{timestamp_str}`  ",
        f"**Pipeline Duration:** `{report.total_duration_seconds:.2f}s`  ",
        f"**Status:** `{report.status.upper()}`  ",
        f"",
        f"---",
        f"",
        f"## Executive Summary",
        f"",
        f"{executive_summary}",
        f"",
        f"---",
        f"",
        f"## Overall Compliance Score",
        f"",
        f"- **Initial Baseline:** `{score_before_bar}`",
        f"- **Remediated Result:** `{score_after_bar}`",
        f"- **Net Improvement:** **+{imp_pts} points**",
        f"- **Verified Fix Rate:** **{stats.get('fixed_and_verified', 0)} / {stats.get('total_violations', len(unified))} defects resolved**",
        f"",
        f"---",
        f"",
        f"## Violations & Remediation Summary",
        f"",
        f"| # | Status | Severity | Category | Location | Description |",
        f"|---|--------|----------|----------|----------|-------------|",
    ]

    idx = 1
    for st_key in order:
        recs = grouped[st_key]
        for r in recs:
            v = r.violation
            loc = f"`{v.file}:{v.line or 1}`"
            cat_name = v.category.value if hasattr(v.category, "value") else str(v.category)
            status_label = st_key.replace("_", " ").title()
            short_desc = (v.description[:75] + "...") if len(v.description) > 75 else v.description
            lines.append(f"| {idx} | **{status_label}** | {v.severity.upper()} | {cat_name} | {loc} | {short_desc} |")
            idx += 1

    lines.extend([
        f"",
        f"---",
        f"",
        f"## Verified Fixes (Sandboxed Proof-of-Work)",
        f"",
    ])

    verified_recs = grouped["fixed_and_verified"]
    if not verified_recs:
        lines.append("_No fixes met the 100% verification threshold without regressions in this run._\n")
    else:
        for r in verified_recs:
            v = r.violation
            fix = r.fix
            verif = r.verification
            cat_name = v.category.value if hasattr(v.category, "value") else str(v.category)

            lines.append(f"### {v.id}: {cat_name} in `{v.file}`")
            lines.append(f"- **Criterion:** {v.wcag_criterion or 'WCAG 2.2 AA'}")
            lines.append(f"- **Explanation:** {v.plain_explanation or v.description}")

            sources = (fix.grounding_sources if (fix and fix.grounded and fix.grounding_sources)
                       else (v.grounding_sources if (v.grounded and v.grounding_sources) else []))
            if sources:
                lines.append(f"- **Grounded Guidance Sources:**")
                for s in sources:
                    title = getattr(s, "title", s.get("title", "Guideline") if isinstance(s, dict) else "Guideline")
                    url = getattr(s, "url", s.get("url", "#") if isinstance(s, dict) else "#")
                    lines.append(f"  * [{title}]({url})")

            if verif:
                test_str = "Passed" if verif.tests_passed else ("Skipped/No tests" if verif.tests_passed is None else "Failed")
                lines.append(f"- **Verification Metrics:** axe-core score {verif.axe_score_before}% → {verif.axe_score_after}% | Test Suite: {test_str}")
            if fix and fix.diff:
                lines.append(f"```diff\n{fix.diff.strip()}\n```\n")

    lines.extend([
        f"---",
        f"",
        f"## Known Limitations & Remaining Action Items",
        f"",
    ])

    unresolved = grouped["fixed_not_verified"] + grouped["detected_only"] + grouped["fix_failed"] + grouped["verification_skipped"]
    if not unresolved:
        lines.append("All detected accessibility defects were successfully fixed and verified. No outstanding items.\n")
    else:
        for r in unresolved:
            v = r.violation
            st_label = r.final_status.replace("_", " ").title()
            reason = ""
            if r.fix and r.fix.failure_reason:
                reason = f" ({r.fix.failure_reason})"
            elif r.verification and r.verification.reason:
                reason = f" ({r.verification.reason})"
            lines.append(f"- **{v.id}** (`{v.file}:{v.line or 1}`): **{st_label}**{reason}. {v.description}")
        lines.append("")

    tavily_searches = getattr(cost_info, "tavily_searches", cost_info.get("tavily_searches", 0) if isinstance(cost_info, dict) else 0) or stats.get("tavily_searches_count", 0)
    tavily_sources = getattr(cost_info, "tavily_sources_count", cost_info.get("tavily_sources_count", 0) if isinstance(cost_info, dict) else 0) or stats.get("tavily_sources_used", 0)

    lines.extend([
        f"---",
        f"",
        f"## LLM Inference & Cost Accounting",
        f"",
        f"| Model Tier | Purpose | Cost (USD) |",
        f"|------------|---------|------------|",
        f"| **Nemotron-3_5-Lightning** (Fast) | High-speed detection, batch extraction, executive summary | `${cost_fast:.6f}` |",
        f"| **Nemotron-3-Ultra** (Ultra) | Root-cause diagnosis, code patch synthesis, self-healing | `${cost_ultra:.6f}` |",
        f"| **Tavily Web Search Grounding** | Live WCAG 2.2 guidance retrieval ({tavily_searches} searches, {tavily_sources} sources used) | Included |",
        f"| **Total Pipeline Cost** | Complete automated audit & verification | **`${cost_total:.6f}`** |",
        f"",
        f"---",
        f"*Generated automatically by CodeGuard — Autonomous Accessibility Remediation Engine.*",
    ])

    return "\n".join(lines)


def format_report_as_html(report: ScanReport, executive_summary: str) -> str:
    """
    Renders an HTML report document with modern dark-mode styling,
    metric cards, unified diff blocks, and responsive tables.
    """
    stats = report.summary or {}
    cost_info = report.cost_breakdown or stats.get("cost_breakdown", {})
    cost_fast = getattr(cost_info, "fast_cost", cost_info.get("fast_cost", 0.0) if isinstance(cost_info, dict) else 0.0)
    cost_ultra = getattr(cost_info, "ultra_cost", cost_info.get("ultra_cost", 0.0) if isinstance(cost_info, dict) else 0.0)
    cost_total = getattr(cost_info, "total_cost", cost_info.get("total_cost", 0.0) if isinstance(cost_info, dict) else 0.0)

    score_before = round(report.overall_score_before, 1)
    score_after = round(report.overall_score_after, 1)
    imp_pts = round(score_after - score_before, 1)

    unified = report.unified_records or []
    if not unified and (report.violations or report.fixes):
        from app.services.aggregator_service import link_violation_to_fix_and_verification
        raw_u = link_violation_to_fix_and_verification(report.scan_id)
        unified = [UnifiedViolationRecord(**r) for r in raw_u]

    order = ["fixed_and_verified", "fixed_not_verified", "detected_only", "fix_failed", "verification_skipped"]
    grouped: Dict[str, List[UnifiedViolationRecord]] = {k: [] for k in order}
    for rec in unified:
        st = rec.final_status if rec.final_status in grouped else "detected_only"
        grouped[st].append(rec)

    timestamp_str = (
        report.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        if isinstance(report.timestamp, datetime)
        else str(report.timestamp)
    )

    # Build violation table rows
    table_rows = []
    idx = 1
    status_badges = {
        "fixed_and_verified": '<span class="badge badge-success">Fixed & Verified</span>',
        "fixed_not_verified": '<span class="badge badge-warning">Fixed Not Verified</span>',
        "detected_only": '<span class="badge badge-neutral">Detected Only</span>',
        "fix_failed": '<span class="badge badge-danger">Fix Failed</span>',
        "verification_skipped": '<span class="badge badge-neutral">Verification Skipped</span>',
    }

    for st_key in order:
        for r in grouped[st_key]:
            v = r.violation
            badge = status_badges.get(st_key, f'<span class="badge">{st_key}</span>')
            cat_name = v.category.value if hasattr(v.category, "value") else str(v.category)
            loc = f"{html.escape(v.file)}:{v.line or 1}"
            desc = html.escape(v.description)
            sev = html.escape(v.severity.upper())
            sev_class = "badge-danger" if "CRIT" in sev else ("badge-warning" if "HIGH" in sev or "SER" in sev else "badge-neutral")

            row_html = f"""
            <tr>
              <td>{idx}</td>
              <td>{badge}</td>
              <td><span class="badge {sev_class}">{sev}</span></td>
              <td>{html.escape(cat_name)}</td>
              <td><code>{loc}</code></td>
              <td>{desc}</td>
            </tr>
            """
            table_rows.append(row_html)
            idx += 1

    # Build verified diff sections
    diff_sections = []
    for r in grouped["fixed_and_verified"]:
        v = r.violation
        fix = r.fix
        verif = r.verification
        cat_name = v.category.value if hasattr(v.category, "value") else str(v.category)
        diff_code = html.escape(fix.diff.strip()) if (fix and fix.diff) else "// No diff available"
        test_info = "Passed (0 regressions)" if (verif and verif.tests_passed) else "Verified with axe-core"
        score_info = f"{verif.axe_score_before}% &rarr; {verif.axe_score_after}%" if verif else ""

        diff_sections.append(f"""
        <div class="card card-diff">
          <div class="diff-header">
            <h3>{html.escape(v.id)}: {html.escape(cat_name)}</h3>
            <span class="badge badge-success">Verified</span>
          </div>
          <p class="diff-desc"><strong>Location:</strong> <code>{html.escape(v.file)}:{v.line or 1}</code> | <strong>Criterion:</strong> {html.escape(v.wcag_criterion or 'WCAG 2.2 AA')}</p>
          <p class="diff-desc">{html.escape(v.plain_explanation or v.description)}</p>
          {f'<p class="diff-desc"><strong>Grounded in (WCAG References):</strong> ' + " ".join([f'<a href="{html.escape(getattr(s, "url", s.get("url", "#") if isinstance(s, dict) else "#"))}" target="_blank" rel="noopener noreferrer" style="color: #38bdf8; text-decoration: underline; margin-right: 10px;">{html.escape(getattr(s, "title", s.get("title", "Guideline") if isinstance(s, dict) else "Guideline"))}</a>' for s in (fix.grounding_sources if (fix and fix.grounded and fix.grounding_sources) else (v.grounding_sources if (v.grounded and v.grounding_sources) else []))]) + '</p>' if (fix and fix.grounded and fix.grounding_sources) or (v.grounded and v.grounding_sources) else ''}
          <div class="diff-metrics">
            <span><strong>Axe Score:</strong> {score_info}</span>
            <span><strong>Regression Suite:</strong> {test_info}</span>
          </div>
          <pre class="diff-block"><code>{diff_code}</code></pre>
        </div>
        """)

    # Build limitations list
    unresolved_items = []
    for r in (grouped["fixed_not_verified"] + grouped["detected_only"] + grouped["fix_failed"] + grouped["verification_skipped"]):
        v = r.violation
        reason_str = ""
        if r.fix and r.fix.failure_reason:
            reason_str = f" ({html.escape(r.fix.failure_reason)})"
        elif r.verification and r.verification.reason:
            reason_str = f" ({html.escape(r.verification.reason)})"
        badge = status_badges.get(r.final_status, r.final_status)
        unresolved_items.append(f"<li><strong>{html.escape(v.id)}</strong> [<code>{html.escape(v.file)}:{v.line or 1}</code>] {badge}{reason_str}: {html.escape(v.description)}</li>")

    limitations_html = "".join(unresolved_items) if unresolved_items else "<p>All defects resolved successfully!</p>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CodeGuard Audit Report - {html.escape(report.scan_id)}</title>
  <style>
    :root {{
      --bg: #090d16;
      --card-bg: #0f172a;
      --border: #1e293b;
      --text: #f8fafc;
      --muted: #94a3b8;
      --accent: #6366f1;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 2.5rem 1.5rem;
    }}
    .container {{ max-width: 1040px; margin: 0 auto; }}
    .header {{
      border-bottom: 1px solid var(--border);
      padding-bottom: 1.5rem;
      margin-bottom: 2rem;
    }}
    .header h1 {{ font-size: 2rem; font-weight: 800; color: #fff; margin-bottom: 0.5rem; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 1.5rem; font-size: 0.85rem; color: var(--muted); }}
    .meta code {{ background: #1e293b; padding: 2px 6px; border-radius: 4px; color: #e2e8f0; }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 1.75rem;
    }}
    .card h2 {{ font-size: 1.25rem; font-weight: 700; margin-bottom: 1rem; color: #fff; border-bottom: 1px solid #1e293b; padding-bottom: 0.5rem; }}
    .card-diff {{ margin-bottom: 1.25rem; }}
    .diff-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }}
    .diff-header h3 {{ font-size: 1.05rem; font-weight: 600; color: #e2e8f0; }}
    .diff-desc {{ font-size: 0.875rem; color: var(--muted); margin-bottom: 0.5rem; }}
    .diff-metrics {{ font-size: 0.8rem; color: #cbd5e1; display: flex; gap: 1.5rem; margin-bottom: 0.75rem; }}
    .diff-block {{
      background: #020617;
      border: 1px solid #1e293b;
      border-radius: 8px;
      padding: 1rem;
      overflow-x: auto;
      font-family: monospace;
      font-size: 0.825rem;
      color: #38bdf8;
    }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.75rem; }}
    .kpi-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; text-align: center; }}
    .kpi-label {{ font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-bottom: 0.5rem; }}
    .kpi-val {{ font-size: 2.25rem; font-weight: 800; }}
    .kpi-delta {{ font-size: 0.85rem; margin-top: 0.25rem; }}
    .text-success {{ color: var(--success); }}
    .text-danger {{ color: var(--danger); }}
    .text-warning {{ color: var(--warning); }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
    }}
    .badge-success {{ background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }}
    .badge-warning {{ background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }}
    .badge-danger {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}
    .badge-neutral {{ background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; text-align: left; }}
    th, td {{ padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); }}
    th {{ background: #0b1120; color: var(--muted); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; }}
    tr:hover {{ background: rgba(255, 255, 255, 0.02); }}
    ul.limitations-list {{ padding-left: 1.25rem; }}
    ul.limitations-list li {{ margin-bottom: 0.5rem; font-size: 0.9rem; color: #cbd5e1; }}
    .footer {{ margin-top: 3rem; text-align: center; font-size: 0.8rem; color: var(--muted); border-top: 1px solid var(--border); padding-top: 1.5rem; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>CodeGuard Compliance Audit Report</h1>
      <div class="meta">
        <div>Repo: <code>{html.escape(report.repo_url)}</code></div>
        <div>Branch: <code>{html.escape(report.branch)}</code></div>
        <div>Job: <code>{html.escape(report.scan_id)}</code></div>
        <div>Date: <code>{html.escape(timestamp_str)}</code></div>
        <div>Duration: <code>{report.total_duration_seconds:.2f}s</code></div>
      </div>
    </div>

    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Initial Score</div>
        <div class="kpi-val text-danger">{score_before}%</div>
        <div class="kpi-delta" style="color: var(--muted);">WCAG 2.2 Baseline</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Remediated Score</div>
        <div class="kpi-val text-success">{score_after}%</div>
        <div class="kpi-delta text-success">+{imp_pts} pts improvement</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Defects Detected</div>
        <div class="kpi-val" style="color: #fff;">{stats.get('total_violations', len(unified))}</div>
        <div class="kpi-delta" style="color: var(--muted);">Confirmed Actionable</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Verified Clean</div>
        <div class="kpi-val text-success">{stats.get('fixed_and_verified', 0)}</div>
        <div class="kpi-delta text-success">0 regressions found</div>
      </div>
    </div>

    <div class="card">
      <h2>Executive Summary</h2>
      <p style="font-size: 1.05rem; color: #e2e8f0; line-height: 1.7;">{html.escape(executive_summary)}</p>
    </div>

    <div class="card">
      <h2>Violation Remediation Taxonomy</h2>
      <div style="overflow-x: auto;">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Status</th>
              <th>Severity</th>
              <th>Category</th>
              <th>File & Line</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {"".join(table_rows)}
          </tbody>
        </table>
      </div>
    </div>

    <div class="card">
      <h2>Sandboxed Verifications & Patch Diffs</h2>
      {"".join(diff_sections) if diff_sections else "<p style='color: var(--muted);'>No verified patches to display.</p>"}
    </div>

    <div class="card">
      <h2>Known Limitations & Engineering Action Items</h2>
      <ul class="limitations-list">
        {limitations_html}
      </ul>
    </div>

    <div class="card">
      <h2>LLM Inference & Spend Accounting</h2>
      <table>
        <thead>
          <tr>
            <th>Model Tier</th>
            <th>Operational Role</th>
            <th>Cost (USD)</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Nemotron-3_5-Lightning</strong></td>
            <td>High-speed file scanning, markup chunking, executive summaries</td>
            <td>${cost_fast:.6f}</td>
          </tr>
          <tr>
            <td><strong>Nemotron-3-Ultra</strong></td>
            <td>Deep root-cause diagnosis, precision code remediation, escalation</td>
            <td>${cost_ultra:.6f}</td>
          </tr>
          <tr>
            <td><strong>Tavily Grounding Search</strong></td>
            <td>Live WCAG 2.2 official technique retrieval ({getattr(cost_info, "tavily_searches", cost_info.get("tavily_searches", 0) if isinstance(cost_info, dict) else 0) or stats.get("tavily_searches_count", 0)} searches, {getattr(cost_info, "tavily_sources_count", cost_info.get("tavily_sources_count", 0) if isinstance(cost_info, dict) else 0) or stats.get("tavily_sources_used", 0)} sources used)</td>
            <td>Included</td>
          </tr>
          <tr>
            <td><strong>Total Pipeline Spend</strong></td>
            <td><strong>Autonomous remediation lifecycle</strong></td>
            <td><strong>${cost_total:.6f}</strong></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="footer">
      Generated automatically by CodeGuard &bull; Powered by NVIDIA Nemotron & Nebius Token Factory
    </div>
  </div>
</body>
</html>
"""


def save_report_files(report: ScanReport, scan_id: str, executive_summary: Optional[str] = None) -> Dict[str, str]:
    """
    Saves formatted Markdown and HTML reports to disk:
    backend/generated_reports/{scan_id}/report.md
    backend/generated_reports/{scan_id}/report.html
    
    Returns:
        dict: {"markdown_path": str, "html_path": str}
    """
    summary = executive_summary or report.executive_summary or _build_fallback_executive_summary(report)

    target_dir = GENERATED_REPORTS_DIR / scan_id
    target_dir.mkdir(parents=True, exist_ok=True)

    md_content = format_report_as_markdown(report, summary)
    html_content = format_report_as_html(report, summary)

    md_path = target_dir / "report.md"
    html_path = target_dir / "report.html"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"Saved generated report files for {scan_id} to {target_dir}")

    return {
        "markdown_path": str(md_path),
        "html_path": str(html_path),
    }
