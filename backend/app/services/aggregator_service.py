"""
Aggregator Service (Phase 22).
Consolidates all intermediate pipeline outputs (violations, diagnoses, explanations,
fixes, sandbox verifications, test run statuses, costs, and timings) into a single,
cohesive ScanReport that serves as the single source of truth for CodeGuard.
"""
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional

from app.models.schemas import (
    CostBreakdown,
    DiagnosedViolation,
    ProposedFix,
    ScanReport,
    ScoreImprovement,
    UnifiedViolationRecord,
    VerificationResult,
    Violation,
)
from app.services.llm_client import get_cost_breakdown, get_scan_usage_stats
from app.state import get_scan, update_scan

logger = logging.getLogger(__name__)


def link_violation_to_fix_and_verification(scan_id: str) -> List[Dict[str, Any]]:
    """
    For every violation detected in the scan, links its matching ProposedFix (via violation_id)
    and matching VerificationResult (via fix_id).
    
    Produces one unified record per violation:
    {
        "violation": DiagnosedViolation,
        "fix": ProposedFix | None,
        "verification": VerificationResult | None,
        "final_status": str
    }
    
    final_status is computed as one of:
    - "fixed_and_verified": fix exists, verification ran, verification.verified == True
    - "fixed_not_verified": fix exists, verification ran, verification.verified == False
    - "fix_failed": fix generation or application failed
    - "detected_only": violation found but no fix was attempted (e.g. below severity threshold)
    - "verification_skipped": fix succeeded but verification didn't run (e.g. timeout / quota)
    """
    scan = get_scan(scan_id)
    if not scan:
        logger.warning(f"Scan {scan_id} not found in state store")
        return []

    raw_violations: List[Violation] = scan.get("violations", [])
    diagnosed_violations: List[DiagnosedViolation] = scan.get("diagnosed_violations", [])
    fixes: List[ProposedFix] = scan.get("fixes", [])
    verifications: List[VerificationResult] = scan.get("verification_results", [])

    # Index diagnoses by violation ID
    diag_map: Dict[str, DiagnosedViolation] = {}
    for d in diagnosed_violations:
        d_id = getattr(d, "id", None)
        if d_id:
            diag_map[d_id] = d

    # Index fixes by violation ID
    fix_map: Dict[str, ProposedFix] = {}
    for f in fixes:
        v_id = getattr(f, "violation_id", None)
        if v_id and v_id not in fix_map:
            fix_map[v_id] = f

    # Index verification results by fix ID
    verif_map: Dict[str, VerificationResult] = {}
    for vr in verifications:
        f_id = getattr(vr, "fix_id", None)
        if f_id:
            verif_map[f_id] = vr

    unified_records: List[Dict[str, Any]] = []

    for v in raw_violations:
        v_id = v.id
        # Use DiagnosedViolation if available, otherwise upgrade Violation
        if v_id in diag_map:
            diag_v = diag_map[v_id]
        elif isinstance(v, DiagnosedViolation):
            diag_v = v
        else:
            diag_v = DiagnosedViolation(
                id=v.id,
                file=v.file,
                line=v.line,
                type=v.type,
                severity=v.severity,
                description=v.description,
                selector=v.selector,
                context_snippet=v.context_snippet,
                source=v.source,
                wcag_criterion=v.wcag_criterion,
                category=v.category,
                severity_score=v.severity_score,
                priority_rank=v.priority_rank,
                root_cause="Automated accessibility defect identified by CodeGuard scanner.",
                affected_element=v.selector or v.type,
                user_impact=f"Users navigating with assistive tech will encounter friction on {v.type}.",
                fix_strategy="Apply recommended accessible attributes, semantic HTML elements, or contrast adjustments.",
                confidence="high",
                diagnosis_source="template",
                plain_explanation=v.description,
            )

        matching_fix = fix_map.get(v_id)
        matching_verif = verif_map.get(matching_fix.fix_id) if matching_fix else None

        # Determine final_status
        if matching_fix is None:
            final_status = "detected_only"
        elif matching_fix.status == "failed":
            final_status = "fix_failed"
        elif matching_verif is not None:
            if matching_verif.verified:
                final_status = "fixed_and_verified"
            else:
                final_status = "fixed_not_verified"
        else:
            final_status = "verification_skipped"

        unified_records.append({
            "violation": diag_v,
            "fix": matching_fix,
            "verification": matching_verif,
            "final_status": final_status,
        })

    return unified_records


def calculate_summary_stats(
    unified_records: List[Dict[str, Any]],
    scan_id: Optional[str] = None,
    overall_score_before: Optional[float] = None,
    overall_score_after: Optional[float] = None,
    start_time: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes summary metrics across unified records:
    - Counts per final_status category
    - Counts per severity label
    - Counts per taxonomy category
    - Overall fix success rate
    - Score delta and improvement points (None if sandbox unavailable)
    - Token spend and cost breakdown
    - Total duration in seconds
    """
    by_status: Dict[str, int] = {
        "fixed_and_verified": 0,
        "fixed_not_verified": 0,
        "fix_failed": 0,
        "detected_only": 0,
        "verification_skipped": 0,
    }
    by_severity: Dict[str, int] = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }
    by_category: Dict[str, int] = {}

    total_violations = len(unified_records)

    for item in unified_records:
        status = item.get("final_status", "detected_only")
        by_status[status] = by_status.get(status, 0) + 1

        v: DiagnosedViolation = item["violation"]
        sev = (v.severity or "medium").lower()
        if sev == "serious":
            sev = "high"
        elif sev == "moderate":
            sev = "medium"
        elif sev == "minor":
            sev = "low"
        by_severity[sev] = by_severity.get(sev, 0) + 1

        cat = v.category.value if hasattr(v.category, "value") else str(v.category)
        by_category[cat] = by_category.get(cat, 0) + 1

    fixed_and_verified_count = by_status.get("fixed_and_verified", 0)
    fix_success_rate = (
        round(fixed_and_verified_count / total_violations, 3)
        if total_violations > 0
        else 0.0
    )

    improvement_points = (
        round(overall_score_after - overall_score_before, 2)
        if (overall_score_after is not None and overall_score_before is not None)
        else None
    )

    # Cost breakdown from LLM client tracker
    scan_stats = get_scan_usage_stats(scan_id) if scan_id else None
    if scan_stats and (scan_stats.get("total_cost_usd", 0.0) > 0 or scan_stats.get("total_calls", 0) > 0):
        cost_dict = {
            "fast_cost": scan_stats.get("fast_cost_usd", 0.0),
            "ultra_cost": scan_stats.get("ultra_cost_usd", 0.0),
            "total_cost": scan_stats.get("total_cost_usd", 0.0),
        }
    else:
        global_cost = get_cost_breakdown()
        cost_dict = {
            "fast_cost": global_cost.get("fast_cost", 0.0),
            "ultra_cost": global_cost.get("ultra_cost", 0.0),
            "total_cost": global_cost.get("total", 0.0),
        }

    # Tavily web search grounding counts
    from app.services.grounding_service import get_scan_search_count, get_scan_sources_count
    tavily_searches = get_scan_search_count(scan_id)
    tavily_sources = get_scan_sources_count(scan_id)
    cost_dict["tavily_searches"] = tavily_searches
    cost_dict["tavily_sources_count"] = tavily_sources

    # Elapsed duration
    duration_seconds = 0.0
    if start_time is not None:
        duration_seconds = round(time.time() - start_time, 2)
    elif scan_id:
        scan = get_scan(scan_id)
        if scan and "created_at" in scan:
            created_at = scan["created_at"]
            if isinstance(created_at, datetime):
                duration_seconds = round((datetime.now(timezone.utc) - created_at).total_seconds(), 2)

    return {
        "total_violations": total_violations,
        "fixed_and_verified": fixed_and_verified_count,
        "fixed_not_verified": by_status.get("fixed_not_verified", 0),
        "fix_failed": by_status.get("fix_failed", 0),
        "detected_only": by_status.get("detected_only", 0),
        "verification_skipped": by_status.get("verification_skipped", 0),
        "fix_success_rate": fix_success_rate,
        "by_status": by_status,
        "by_severity": by_severity,
        "by_category": by_category,
        "score_before": overall_score_before,
        "score_after": overall_score_after,
        "improvement_points": improvement_points,
        "cost_breakdown": cost_dict,
        "tavily_searches_count": tavily_searches,
        "tavily_sources_used": tavily_sources,
        "duration_seconds": duration_seconds,
    }


def build_scan_report(scan_id: str) -> ScanReport:
    """
    Builds the final unified ScanReport for a completed audit.
    Links all violations, fixes, and verifications into UnifiedViolationRecords,
    tallies all summary stats, updates state.py, and marks scan as "completed".
    """
    scan = get_scan(scan_id)
    if not scan:
        raise ValueError(f"Scan {scan_id} not found in state store")

    repo_url = scan.get("repo_url", "https://github.com/example/demo-app")
    branch = scan.get("branch", "main")
    raw_before = scan.get("overall_score_before")
    raw_after = scan.get("overall_score_after")
    overall_score_before = float(raw_before) if raw_before is not None else None
    overall_score_after = float(raw_after) if raw_after is not None else None

    # 1. Link violations, fixes, and verification outcomes
    raw_unified = link_violation_to_fix_and_verification(scan_id)
    unified_records = [UnifiedViolationRecord(**r) for r in raw_unified]

    # 2. Compute summary statistics
    start_time_val = scan.get("start_timestamp")
    summary = calculate_summary_stats(
        unified_records=raw_unified,
        scan_id=scan_id,
        overall_score_before=overall_score_before,
        overall_score_after=overall_score_after,
        start_time=start_time_val,
    )

    cost_info = CostBreakdown(**summary["cost_breakdown"])
    score_imp = (
        ScoreImprovement(
            score_before=overall_score_before,
            score_after=overall_score_after,
            improvement_points=summary["improvement_points"],
        )
        if (overall_score_before is not None and overall_score_after is not None)
        else None
    )

    # Backward-compatible lists
    raw_violations: List[Violation] = scan.get("violations", [])
    raw_fixes: List[ProposedFix] = scan.get("fixes", [])
    raw_verifications: List[VerificationResult] = scan.get("verification_results", [])

    report = ScanReport(
        scan_id=scan_id,
        repo_url=repo_url,
        branch=branch,
        violations=raw_violations,
        fixes=raw_fixes,
        verification_results=raw_verifications,
        unified_records=unified_records,
        overall_score_before=overall_score_before,
        overall_score_after=overall_score_after,
        overall_improvement=score_imp,
        summary=summary,
        cost_breakdown=cost_info,
        total_duration_seconds=summary["duration_seconds"],
        timestamp=datetime.now(timezone.utc),
        status="completed",
    )

    # 3. Save as the permanent final result in state.py
    update_scan(
        scan_id=scan_id,
        report=report,
        summary=summary,
        status="completed",
        progress=100,
    )

    logger.info(
        f"Built final unified ScanReport for {scan_id}: "
        f"{summary['fixed_and_verified']}/{summary['total_violations']} verified "
        f"({summary['score_before']}% -> {summary['score_after']}%, +{summary['improvement_points']} pts)"
    )

    return report
