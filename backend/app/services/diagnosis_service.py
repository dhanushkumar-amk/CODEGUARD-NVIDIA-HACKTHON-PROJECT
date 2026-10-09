"""
Diagnosis Service: Root-cause analysis module using NVIDIA Nemotron Ultra (Phase 14).
Provides deep architectural context, user impact explanations, and strategic remediation
plans for prioritized accessibility violations.
"""
import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.models.schemas import DiagnosedViolation, Violation, ViolationCategory
from app.services.grounding_service import (
    format_guidance_for_prompt,
    get_guidance,
    record_sources_used,
    warm_guidance_cache,
)
from app.services.llm_client import (
    UltraBudgetExceededError,
    call_nemotron_ultra,
    extract_json_payload,
)
from app.state import get_scan, update_scan

logger = logging.getLogger(__name__)


# Standard templated fallback diagnoses by category (used for lower-priority or budget exhaustion)
TEMPLATED_DIAGNOSES: Dict[ViolationCategory, Dict[str, str]] = {
    ViolationCategory.MISSING_ALT_TEXT: {
        "root_cause": "The <img> element is missing an 'alt' attribute, leaving assistive technologies with no accessible label or description for visual content.",
        "affected_element": "img",
        "user_impact": "Screen reader users will not understand the visual content or purpose of the image, hearing only a raw filename, URL path, or silence.",
        "fix_strategy": "Add a descriptive 'alt' attribute conveying the meaning of the image, or add alt='' if the image is purely decorative.",
        "confidence": "high",
    },
    ViolationCategory.UNLABELED_FORM_FIELD: {
        "root_cause": "The form control element lacks a programmatically associated <label>, aria-label, or aria-labelledby attribute.",
        "affected_element": "input",
        "user_impact": "Screen reader users focusing on this form control will hear no description or purpose, making form completion difficult or impossible.",
        "fix_strategy": "Associate an explicit <label htmlFor='...'> matching the input id, or provide an informative aria-label attribute.",
        "confidence": "high",
    },
    ViolationCategory.NON_INTERACTIVE_CLICK: {
        "root_cause": "A non-interactive container element (such as a <div> or <span>) has an onClick event listener attached without a semantic role, tabIndex, or keyboard handler.",
        "affected_element": "div",
        "user_impact": "Keyboard-only, screen reader, and switch-access users cannot focus, activate, or navigate this control.",
        "fix_strategy": "Replace the generic container with a native <button> element, or add role='button', tabIndex={0}, and an onKeyDown handler for Enter and Space.",
        "confidence": "high",
    },
    ViolationCategory.EMPTY_LINK_OR_BUTTON: {
        "root_cause": "An interactive button or anchor element contains an icon or empty content with no accessible text name, aria-label, or title.",
        "affected_element": "button",
        "user_impact": "Screen readers announce the element as an unlabelled button or link, leaving users unable to discern what action will occur.",
        "fix_strategy": "Add an aria-label attribute or include visually hidden text (e.g. .sr-only span) describing the button or link action.",
        "confidence": "high",
    },
    ViolationCategory.LOW_CONTRAST: {
        "root_cause": "Foreground text color and background color combinations do not satisfy the minimum WCAG AA contrast ratio threshold of 4.5:1 (or 3:1 for large text).",
        "affected_element": "text",
        "user_impact": "Users with low vision, color vision deficiencies, or those in brightly lit environments cannot comfortably read the content.",
        "fix_strategy": "Adjust the text color or background color tokens to increase luminance contrast to at least 4.5:1.",
        "confidence": "high",
    },
    ViolationCategory.HEADING_ORDER: {
        "root_cause": "Heading levels are skipped or disordered (e.g. jumping from <h1> directly to <h3>), fragmenting the document outline hierarchy.",
        "affected_element": "heading",
        "user_impact": "Screen reader users who rely on heading hotkeys to scan and navigate the page structure receive a fragmented, confusing mental model.",
        "fix_strategy": "Restructure heading elements sequentially (h1 -> h2 -> h3) without skipping intermediate levels.",
        "confidence": "high",
    },
    ViolationCategory.MISSING_LANDMARK: {
        "root_cause": "Core content sections are rendered outside semantic HTML5 landmark regions (<main>, <header>, <nav>, <footer>, <aside>).",
        "affected_element": "landmark",
        "user_impact": "Assistive technology users cannot use landmark navigation keys to jump directly to the primary page contents.",
        "fix_strategy": "Wrap the primary component content in a semantic <main> element, and enclose top-level navigation in <nav>.",
        "confidence": "high",
    },
    ViolationCategory.KEYBOARD_TRAP: {
        "root_cause": "Keyboard focus enters an element or modal container and cannot be moved away using standard keyboard navigation keys.",
        "affected_element": "container",
        "user_impact": "Keyboard-only users become permanently trapped within the component and are forced to reload the page.",
        "fix_strategy": "Implement an Escape key listener to close the modal, and ensure focus cycling returns to the trigger element on dismissal.",
        "confidence": "high",
    },
    ViolationCategory.MISSING_LANG: {
        "root_cause": "The root <html> element does not specify a valid language code in its 'lang' attribute.",
        "affected_element": "html",
        "user_impact": "Screen reader speech synthesizers cannot select the proper pronunciation rules, dictionary, or accent for the document text.",
        "fix_strategy": "Add a valid BCP 47 language code to the <html> tag, e.g. <html lang='en'>.",
        "confidence": "high",
    },
    ViolationCategory.ARIA_MISUSE: {
        "root_cause": "ARIA roles, states, or properties are invalid, redundant with native HTML semantics, or conflict with child elements.",
        "affected_element": "element",
        "user_impact": "Assistive technologies may announce conflicting, misleading, or suppressed accessibility information.",
        "fix_strategy": "Remove redundant ARIA attributes, ensure roles match valid WAI-ARIA authoring patterns, and prefer semantic HTML.",
        "confidence": "high",
    },
    ViolationCategory.FOCUS_MANAGEMENT: {
        "root_cause": "Positive tabIndex values or improper focus manipulation disrupts the natural reading and sequential navigation order.",
        "affected_element": "element",
        "user_impact": "Keyboard focus jumps erratically across the viewport rather than following the visual or logical layout.",
        "fix_strategy": "Remove positive tabIndex attributes (use tabIndex={0} or {-1}) and arrange elements in natural DOM source order.",
        "confidence": "high",
    },
    ViolationCategory.OTHER: {
        "root_cause": "An accessibility violation was detected that does not match standard canonical rule patterns.",
        "affected_element": "element",
        "user_impact": "Assistive technology users may encounter functional friction or barriers interacting with this component.",
        "fix_strategy": "Inspect the offending element and update markup to conform with relevant WCAG 2.2 Success Criteria.",
        "confidence": "medium",
    },
}


def get_surrounding_context(repo_path: str, file: str, line: Optional[int], context_lines: int = 20) -> str:
    """
    Reads the ORIGINAL full file (not an extracted chunk) and returns a window of lines
    surrounding the violation, plus the component's declaration, props, and state if detectable.

    Args:
        repo_path: Absolute or relative path to the cloned repository root.
        file: Relative path to the file within the repository.
        line: 1-indexed line number of the violation.
        context_lines: Number of surrounding lines to include in the primary window.

    Returns:
        Formatted code context string with line numbers.
    """
    target_path = Path(repo_path) / file
    if not target_path.exists():
        target_path = Path(file)
        if not target_path.exists():
            return f"// Source file '{file}' not available on disk."

    try:
        content = target_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning(f"Failed to read file '{target_path}' for context: {exc}")
        return f"// Error reading file '{file}': {exc}"

    lines = content.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        return "// File is empty."

    viol_line = line if (line and line > 0) else 1
    viol_line = min(viol_line, total_lines)

    # 1. Calculate window around violation line
    half_win = context_lines // 2
    win_start = max(1, viol_line - half_win)
    win_end = min(total_lines, viol_line + half_win)

    # 2. Heuristic: locate nearest component/function declaration above the violation line
    comp_declaration_line: Optional[int] = None
    decl_pattern = re.compile(
        r"^\s*(?:export\s+(?:default\s+)?)?(?:function|const|class)\s+([A-Za-z0-9_]+)",
        re.MULTILINE,
    )

    for idx in range(viol_line - 1, -1, -1):
        line_str = lines[idx]
        if decl_pattern.match(line_str) or re.search(r"function\s+[A-Za-z0-9_]+\s*\(|const\s+[A-Za-z0-9_]+\s*:\s*React\.FC", line_str):
            comp_declaration_line = idx + 1
            break

    output_lines: List[str] = []

    # If component declaration was found well above the window start, include it with props/state
    if comp_declaration_line and comp_declaration_line < win_start:
        decl_end = min(win_start - 1, comp_declaration_line + 10)
        output_lines.append(f"// --- Component declaration and state (lines {comp_declaration_line}-{decl_end}) ---")
        for i in range(comp_declaration_line, decl_end + 1):
            marker = ">" if i == viol_line else " "
            output_lines.append(f"{marker} {i:4d} | {lines[i - 1]}")

        if decl_end < win_start - 1:
            output_lines.append("   ... [lines omitted] ...")

    output_lines.append(f"// --- Violation surrounding context (lines {win_start}-{win_end}) ---")
    for i in range(win_start, win_end + 1):
        marker = ">" if i == viol_line else " "
        output_lines.append(f"{marker} {i:4d} | {lines[i - 1]}")

    return "\n".join(output_lines)


def build_diagnosis_prompt(
    violation: Violation,
    context: str,
    guidance: Optional[Any] = None,
) -> Tuple[str, str]:
    """
    Constructs the system prompt and user prompt for Nemotron Ultra root-cause diagnosis,
    optionally incorporating live web-grounded WCAG guidance from Tavily.

    Args:
        violation: The Violation instance to diagnose.
        context: Extracted surrounding code context string.
        guidance: Optional GuidanceBundle retrieved via Tavily.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    system_prompt = (
        "You are an expert accessibility architect and WCAG 2.2 auditor. "
        "Your task is to analyze the provided code context and diagnose the exact architectural "
        "root cause of an accessibility violation. Be precise, highly technical, and avoid vague generalities.\n"
        "You must respond ONLY with a valid JSON object matching the requested schema. Do not include markdown code fences or conversational text."
    )

    cat_name = violation.category.value if isinstance(violation.category, ViolationCategory) else str(violation.category)
    guidance_section = ""
    if guidance:
        guidance_text = format_guidance_for_prompt(guidance)
        if guidance_text:
            guidance_section = f"\n{guidance_text}\n"

    user_prompt = f"""Analyze this accessibility defect and determine why the surrounding code structure caused it.

VIOLATION METADATA:
- File & Line: {violation.file}:{violation.line}
- Rule ID: {violation.type}
- Normalized Category: {cat_name}
- WCAG Success Criterion: {violation.wcag_criterion or 'WCAG 2.2 AA'}
- Severity: {violation.severity} (Score: {violation.severity_score or 'N/A'}/10, Priority Rank: #{violation.priority_rank or 'N/A'})
- Offending Snippet: {violation.context_snippet or 'N/A'}
- Initial Description: {violation.description}
{guidance_section}
SURROUNDING SOURCE CODE CONTEXT:
```tsx
{context}
```

REQUIRED OUTPUT FORMAT:
Respond with a single valid JSON object with the following fields:
{{
  "root_cause": "Plain-English technical explanation of WHY this defect exists in the code architecture (e.g. 'the icon button was implemented with a div and onClick instead of a semantic button element, so it has no keyboard focus or role')",
  "affected_element": "Specific element, JSX tag, or component affected (e.g. '<div className=\"menu-btn\">')",
  "user_impact": "Plain-English explanation of who is affected and how (e.g. 'screen reader and keyboard-only users cannot activate this control')",
  "fix_strategy": "A short, actionable technical description of the RIGHT approach to resolve it cleanly without code",
  "confidence": "high"
}}
"""

    return system_prompt, user_prompt


def get_templated_diagnosis(
    violation: Violation,
    guidance: Optional[Any] = None,
) -> DiagnosedViolation:
    """
    Generates a high-quality deterministic fallback diagnosis based on the violation's
    normalized category. Used when below top-N priority threshold, when Ultra budget is
    exhausted, or if LLM JSON parsing fails.
    """
    cat = violation.category if isinstance(violation.category, ViolationCategory) else ViolationCategory.OTHER
    template = TEMPLATED_DIAGNOSES.get(cat, TEMPLATED_DIAGNOSES[ViolationCategory.OTHER])

    affected = violation.selector or template.get("affected_element", "element")
    if violation.context_snippet and len(violation.context_snippet) < 60:
        affected = violation.context_snippet.strip()

    is_grounded = bool(guidance and getattr(guidance, "sources", None))
    sources = list(guidance.sources) if is_grounded else []

    return DiagnosedViolation(
        id=violation.id,
        file=violation.file,
        line=violation.line,
        type=violation.type,
        severity=violation.severity,
        description=violation.description,
        selector=violation.selector,
        context_snippet=violation.context_snippet,
        source=violation.source,
        wcag_criterion=violation.wcag_criterion,
        category=violation.category,
        severity_score=violation.severity_score,
        priority_rank=violation.priority_rank,
        root_cause=template["root_cause"],
        affected_element=affected,
        user_impact=template["user_impact"],
        fix_strategy=template["fix_strategy"],
        confidence=template.get("confidence", "high"),
        diagnosis_source="template",
        grounded=is_grounded,
        grounding_sources=sources,
    )


async def diagnose_violation(
    violation: Violation,
    repo_path: str,
    scan_id: str,
    top_n: Optional[int] = None,
) -> DiagnosedViolation:
    """
    Diagnoses a single accessibility violation:
    - Looks up grounded WCAG guidance via Tavily (cached per category).
    - If priority_rank is beyond top_n threshold, returns cheap templated diagnosis.
    - If within threshold, calls Nemotron Ultra for deep root-cause reasoning.
    - If budget limit (UltraBudgetExceededError) is hit or parsing fails, falls back gracefully.

    Args:
        violation: The Violation instance to diagnose.
        repo_path: Path to repository clone.
        scan_id: Unique scan job identifier.
        top_n: Max priority rank eligible for Ultra LLM diagnosis (default from settings).

    Returns:
        DiagnosedViolation instance.
    """
    threshold = top_n if top_n is not None else getattr(settings, "DIAGNOSIS_TOP_N", 15)

    # 1. Look up grounded WCAG guidance for this category
    guidance = await get_guidance(
        category=violation.category,
        wcag_criterion=violation.wcag_criterion,
        scan_id=scan_id,
    )
    is_grounded = bool(guidance and guidance.sources)
    grounding_sources = list(guidance.sources) if is_grounded else []
    if is_grounded:
        record_sources_used(scan_id, len(grounding_sources))

    # 2. Check priority threshold: only call Ultra for top N violations
    rank = violation.priority_rank
    if rank is not None and rank > threshold:
        logger.info(
            f"Violation {violation.id} (priority rank #{rank}) is below top {threshold}; "
            "using deterministic templated diagnosis."
        )
        return get_templated_diagnosis(violation, guidance=guidance)

    # 3. Extract surrounding code context from the original file
    context = get_surrounding_context(
        repo_path=repo_path,
        file=violation.file,
        line=violation.line,
        context_lines=24,
    )

    system_prompt, user_prompt = build_diagnosis_prompt(violation, context, guidance=guidance)

    # 4. Call Nemotron Ultra with cost guardrails
    try:
        raw_response = await call_nemotron_ultra(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=800,
            scan_id=scan_id,
        )
    except UltraBudgetExceededError as budget_err:
        logger.warning(
            f"Ultra budget/call limit reached while diagnosing {violation.id}: {budget_err}. "
            "Falling back to templated diagnosis."
        )
        return get_templated_diagnosis(violation, guidance=guidance)
    except Exception as llm_err:
        logger.warning(
            f"Nemotron Ultra diagnosis failed for {violation.id}: {llm_err}. "
            "Falling back to templated diagnosis."
        )
        return get_templated_diagnosis(violation, guidance=guidance)

    # 5. Parse JSON payload
    cleaned_json = extract_json_payload(raw_response)
    try:
        data = json.loads(cleaned_json)
        if isinstance(data, dict) and "root_cause" in data:
            return DiagnosedViolation(
                id=violation.id,
                file=violation.file,
                line=violation.line,
                type=violation.type,
                severity=violation.severity,
                description=violation.description,
                selector=violation.selector,
                context_snippet=violation.context_snippet,
                source=violation.source,
                wcag_criterion=violation.wcag_criterion,
                category=violation.category,
                severity_score=violation.severity_score,
                priority_rank=violation.priority_rank,
                root_cause=str(data.get("root_cause", "")).strip() or "Architectural accessibility defect.",
                affected_element=str(data.get("affected_element", violation.selector or "element")).strip(),
                user_impact=str(data.get("user_impact", "")).strip() or "Users of assistive technology may be affected.",
                fix_strategy=str(data.get("fix_strategy", "")).strip() or "Remediate according to WCAG guidelines.",
                confidence=str(data.get("confidence", "high")).strip().lower(),
                diagnosis_source="llm",
                grounded=is_grounded,
                grounding_sources=grounding_sources,
            )
    except Exception as parse_err:
        logger.warning(
            f"Failed to parse LLM diagnosis JSON for {violation.id} ({parse_err}). "
            f"Raw text: {raw_response[:120]}... Falling back to template."
        )

    return get_templated_diagnosis(violation, guidance=guidance)


async def diagnose_all(scan_id: str, top_n: Optional[int] = None) -> List[DiagnosedViolation]:
    """
    Coordinates root-cause diagnosis across all classified violations in a scan:
    - Warms Tavily WCAG guidance cache for all unique categories found concurrently
    - Emits WebSocket message for the grounding stage
    - Retrieves classified violations from state.py
    - Sorts by priority_rank ascending (1 = highest priority)
    - Processes with an asyncio.Semaphore(2) to prevent excessive Ultra concurrent load
    - Emits WebSocket progress updates during diagnosis
    - Persists DiagnosedViolation objects to state.py

    Args:
        scan_id: Scan job identifier.
        top_n: Optional override for max violations to diagnose via Ultra.

    Returns:
        List of DiagnosedViolation instances.
    """
    scan_data = get_scan(scan_id)
    if not scan_data:
        logger.warning(f"Scan {scan_id} not found in state store.")
        return []

    raw_violations: List[Violation] = scan_data.get("violations", [])
    if not raw_violations:
        logger.info(f"No violations to diagnose for scan {scan_id}.")
        update_scan(scan_id, diagnosed_violations=[], status="diagnosed")
        return []

    repo_path = scan_data.get("repo_path", "")
    threshold = top_n if top_n is not None else getattr(settings, "DIAGNOSIS_TOP_N", 15)

    # 0. Warm Tavily guidance cache across all distinct categories found, and emit WebSocket progress
    categories = [v.category for v in raw_violations if v.category]
    wcag_map = {
        (v.category.value if hasattr(v.category, "value") else str(v.category)): (v.wcag_criterion or "")
        for v in raw_violations
    }

    try:
        from app.routers.websocket import broadcast_progress
        await broadcast_progress(
            scan_id=scan_id,
            stage="grounding",
            progress=5,
            message="Looking up current WCAG guidance with Tavily...",
            data={"category_count": len(set(str(c) for c in categories))},
        )
    except Exception as ws_err:
        logger.debug(f"Grounding WebSocket message skipped: {ws_err}")

    try:
        await warm_guidance_cache(categories=categories, wcag_map=wcag_map, scan_id=scan_id)
    except Exception as warm_err:
        logger.warning(f"Tavily cache warming failed: {warm_err}. Continuing with scan.")

    # Sort strictly by priority_rank (None ranks go to the end)
    sorted_violations = sorted(
        raw_violations,
        key=lambda v: (v.priority_rank if v.priority_rank is not None else 9999),
    )

    total_violations = len(sorted_violations)
    semaphore = asyncio.Semaphore(2)  # Ultra is slower; limit to 2 concurrent calls
    completed_count = 0
    progress_lock = asyncio.Lock()
    diagnosed_results: List[DiagnosedViolation] = []

    async def _diagnose_task(v: Violation) -> DiagnosedViolation:
        nonlocal completed_count
        async with semaphore:
            result = await diagnose_violation(
                violation=v,
                repo_path=repo_path,
                scan_id=scan_id,
                top_n=threshold,
            )

            async with progress_lock:
                completed_count += 1
                progress_pct = int((completed_count / total_violations) * 100)
                msg = f"Diagnosed {completed_count}/{total_violations} violations (source={result.diagnosis_source})"

                try:
                    from app.routers.websocket import broadcast_progress
                    await broadcast_progress(
                        scan_id=scan_id,
                        stage="diagnosing",
                        progress=progress_pct,
                        message=msg,
                        data={
                            "diagnosed_count": completed_count,
                            "total_count": total_violations,
                            "latest_violation_id": v.id,
                            "latest_diagnosis_source": result.diagnosis_source,
                        },
                    )
                except Exception as ws_err:
                    logger.debug(f"Progress streaming skipped: {ws_err}")

            return result

    tasks = [_diagnose_task(v) for v in sorted_violations]
    diagnosed_results = await asyncio.gather(*tasks, return_exceptions=False)

    # Save to state store (update both 'diagnosed_violations' and 'violations' for full pipeline compatibility)
    update_scan(
        scan_id=scan_id,
        diagnosed_violations=diagnosed_results,
        violations=diagnosed_results,
        status="diagnosed",
    )

    try:
        from app.routers.websocket import broadcast_progress
        await broadcast_progress(
            scan_id=scan_id,
            stage="diagnosing",
            progress=100,
            message=f"Root-cause diagnosis complete for all {len(diagnosed_results)} violations.",
            data={"diagnosed_count": len(diagnosed_results)},
        )
    except Exception as ws_err:
        logger.debug(f"Final diagnosis streaming skipped: {ws_err}")

    logger.info(
        f"Scan {scan_id} diagnosis complete: {len(diagnosed_results)} violations diagnosed "
        f"(top {threshold} eligible for Ultra)."
    )
    return diagnosed_results
