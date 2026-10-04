"""
Fixer Service: Leverages NVIDIA Nemotron Ultra to synthesize WCAG 2.2 AA compliant fixes
and unified git diff patches (Phase 16).
High-stakes code remediation module with strict syntax, whitespace, and budget guardrails.
"""
import asyncio
import difflib
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from app.config import settings
from app.models.schemas import DiagnosedViolation, ProposedFix, Violation
from app.services.llm_client import (
    UltraBudgetExceededError,
    call_nemotron_fast,
    call_nemotron_ultra,
    call_with_escalation,
    extract_json_payload,
    get_scan_usage_stats,
)
from app.state import get_scan, update_scan

logger = logging.getLogger(__name__)

# Severity hierarchy for threshold filtering
SEVERITY_WEIGHTS: Dict[str, int] = {
    "critical": 4,
    "serious": 4,
    "high": 3,
    "moderate": 2,
    "medium": 2,
    "low": 1,
    "minor": 1,
}


def _normalize_code(text: str) -> str:
    """Normalizes line endings and trailing whitespace for resilient code matching."""
    if not text:
        return ""
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def get_fix_context(
    repo_path: str,
    file: str,
    line: Optional[int],
    context_lines: int = 15,
) -> Dict[str, Any]:
    """
    Returns the exact original lines to be modified (the PRECISE start/end line range
    of the element containing the violation) plus a slightly wider context window
    for the model to understand surrounding code.

    Args:
        repo_path: Root directory of cloned repository.
        file: Relative path to target file.
        line: 1-indexed target line number.
        context_lines: Lines of surrounding context before and after element.

    Returns:
        Dictionary with keys: file, line_start, line_end, original_lines, context.
    """
    target_path = Path(repo_path) / file
    if not target_path.exists():
        target_path = Path(file)
        if not target_path.exists():
            return {
                "file": file,
                "line_start": line or 1,
                "line_end": line or 1,
                "original_lines": "",
                "context": f"// Source file '{file}' not found.",
            }

    try:
        content = target_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning(f"Failed to read '{target_path}' in get_fix_context: {exc}")
        return {
            "file": file,
            "line_start": line or 1,
            "line_end": line or 1,
            "original_lines": "",
            "context": f"// Error reading file: {exc}",
        }

    lines = content.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        return {
            "file": file,
            "line_start": 1,
            "line_end": 1,
            "original_lines": "",
            "context": "// File is empty.",
        }

    target_line = line if (line and line > 0) else 1
    target_line = min(target_line, total_lines)
    target_idx = target_line - 1  # 0-indexed

    # 1. Determine element start and end lines
    start_idx = target_idx
    end_idx = target_idx

    # Look backwards from target_idx to find the start of the opening tag if target line is indented or in a child
    tag_start_pattern = re.compile(r"<\s*([a-zA-Z0-9_\-]+)")
    tag_name: Optional[str] = None

    # Check target line first
    match = tag_start_pattern.search(lines[target_idx])
    if match:
        start_idx = target_idx
        tag_name = match.group(1).lower()
    else:
        # Search backwards up to 15 lines for the opening tag
        for i in range(target_idx - 1, max(-1, target_idx - 15), -1):
            m = tag_start_pattern.search(lines[i])
            if m:
                # Ensure this opening tag hasn't already closed before target_idx
                candidate_tag = m.group(1).lower()
                chunk_between = "\n".join(lines[i:target_idx])
                if f"</{candidate_tag}>" not in chunk_between and not re.search(rf"<{candidate_tag}\b[^>]*/>", chunk_between):
                    start_idx = i
                    tag_name = candidate_tag
                    break

    # 2. Find end of element starting from start_idx
    if tag_name:
        void_tags = {"img", "input", "br", "hr", "meta", "link"}
        if tag_name in void_tags:
            # Void tag or self-closing tag: ends at first '>' or '/>'
            for j in range(start_idx, min(total_lines, start_idx + 10)):
                if ">" in lines[j]:
                    end_idx = j
                    break
        else:
            # Check if self-closing on start line or soon after
            start_line_text = lines[start_idx]
            if "/>" in start_line_text or (">" in start_line_text and f"</{tag_name}>" in start_line_text):
                end_idx = start_idx
            else:
                # Container element: scan forward for matching closing tag </tag_name>
                depth = 0
                for j in range(start_idx, min(total_lines, start_idx + 60)):
                    curr_line = lines[j]
                    # Count opens of same tag (excluding self-closing <tag ... />)
                    opens = len(re.findall(rf"<\s*{tag_name}\b(?![^>]*/>)[^>]*>", curr_line, re.IGNORECASE))
                    closes = len(re.findall(rf"</\s*{tag_name}\s*>", curr_line, re.IGNORECASE))
                    depth += (opens - closes)
                    if depth <= 0 and (closes > 0 or "/>" in curr_line or ">" in curr_line):
                        end_idx = j
                        break

    # Clamp indices
    start_idx = max(0, min(start_idx, total_lines - 1))
    end_idx = max(start_idx, min(end_idx, total_lines - 1))

    original_lines = "\n".join(lines[start_idx : end_idx + 1])
    line_start = start_idx + 1
    line_end = end_idx + 1

    # 3. Construct wider context window for LLM comprehension
    win_start = max(0, start_idx - context_lines)
    win_end = min(total_lines - 1, end_idx + context_lines)

    context_output: List[str] = [
        f"// --- Surrounding file context ({file}:{win_start + 1}-{win_end + 1}) ---"
    ]
    for i in range(win_start, win_end + 1):
        marker = ">" if (start_idx <= i <= end_idx) else " "
        context_output.append(f"{marker} {i + 1:4d} | {lines[i]}")

    return {
        "file": file,
        "line_start": line_start,
        "line_end": line_end,
        "original_lines": original_lines,
        "context": "\n".join(context_output),
    }


def build_fix_prompt(diagnosed: DiagnosedViolation, context: Dict[str, Any]) -> Tuple[str, str]:
    """
    Constructs the system prompt and user prompt for Nemotron Ultra fix generation.

    Args:
        diagnosed: DiagnosedViolation with root cause, user impact, and fix strategy.
        context: Context dictionary containing file, line_start, line_end, original_lines, context.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    system_prompt = (
        "You are a senior frontend engineer and accessibility architect specializing in React, TypeScript, "
        "and WCAG 2.2 AA compliance.\n"
        "Your task is to fix the identified accessibility violation by generating a precise, minimal code patch.\n\n"
        "STRICT REQUIREMENTS:\n"
        "1. Make ONLY the minimal change required to fix the accessibility violation.\n"
        "2. Preserve all existing functionality, styles, classes, event handlers, props, and child components.\n"
        "3. Never rewrite unrelated code or reformat surrounding lines.\n"
        "4. The 'original_lines' output field MUST EXACTLY match the provided original code block character-for-character, including indentation and whitespace.\n"
        "5. The 'fixed_lines' output field must be valid TypeScript/JSX syntax with balanced tags, brackets, and quotes.\n"
        "6. Respond ONLY with a valid JSON object matching the requested schema. No markdown fences, no conversational text."
    )

    cat_name = diagnosed.category.value if hasattr(diagnosed.category, "value") else str(diagnosed.category)
    file_name = context.get("file", diagnosed.file)
    l_start = context.get("line_start", diagnosed.line or 1)
    l_end = context.get("line_end", diagnosed.line or 1)
    orig_code = context.get("original_lines", "")

    user_prompt = f"""Generate an accessible remediation patch for this defect:

VIOLATION METADATA:
- Target File: {file_name} (Lines {l_start} to {l_end})
- Category: {cat_name}
- Rule: {diagnosed.type}
- WCAG Criterion: {diagnosed.wcag_criterion or 'WCAG 2.2 AA'}
- Severity: {diagnosed.severity}

ROOT CAUSE & REMEDIATION STRATEGY:
- Root Cause: {diagnosed.root_cause}
- Fix Strategy: {diagnosed.fix_strategy}
- User Impact: {diagnosed.user_impact}

SURROUNDING FILE CONTEXT:
```tsx
{context.get('context', '')}
```

EXACT ORIGINAL CODE BLOCK TO REPLACE (Lines {l_start}-{l_end}):
```tsx
{orig_code}
```

REQUIRED JSON RESPONSE FORMAT:
Respond with a single valid JSON object containing exactly these fields:
{{
  "original_lines": {json.dumps(orig_code)},
  "fixed_lines": "<replacement code block resolving the violation>",
  "explanation_of_change": "<concise technical summary of the attributes or tags changed and why>",
  "confidence": "high"
}}
"""
    return system_prompt, user_prompt


def _extract_json_fix(content: str) -> Optional[Dict[str, Any]]:
    """Robustly extracts and parses JSON payload, stripping reasoning and markdown blocks."""
    if not content:
        return None
    # 1. Strip chain-of-thought or thinking blocks
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", content, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^Here's a thinking process:[\s\S]*?(?=\{\s*\"|\`\`\`json)", "", cleaned, flags=re.IGNORECASE).strip()

    # 2. Try direct json.loads
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 3. Check for markdown code fences ```json { ... } ```
    match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", cleaned)
    if match:
        try:
            data = json.loads(match.group(1).strip())
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    # 4. Search for outermost { ... }
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidate = cleaned[first_brace : last_brace + 1].strip()
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    return None


def validate_fix_output(fix_response: Union[Dict[str, Any], str], expected_original: str) -> bool:
    """
    Validates model fix synthesis output for correctness, safety, and syntactic sanity:
    - Confirms original_lines matches (or very closely matches, allowing minor whitespace normalization) what was actually sent
    - Confirms fixed_lines is non-empty and different from original_lines
    - Confirms fixed_lines doesn't obviously break syntax (balanced braces/brackets/parens match expected)
    - Returns False (reject the fix) if any check fails.

    Args:
        fix_response: Parsed JSON dictionary or raw string response from LLM.
        expected_original: The expected original source lines that were to be replaced.

    Returns:
        True if fix passes all quality checks, False otherwise.
    """
    data: Dict[str, Any]
    if isinstance(fix_response, str):
        extracted = _extract_json_fix(fix_response)
        if not extracted:
            return False
        data = extracted
    elif isinstance(fix_response, dict):
        data = fix_response
    else:
        return False

    orig = data.get("original_lines")
    fixed = data.get("fixed_lines")

    # 1. Basic field presence and type validation
    if not isinstance(orig, str) or not isinstance(fixed, str):
        return False

    # 2. Check original_lines match
    if orig != expected_original:
        # Allow minor whitespace / line-ending normalization
        if _normalize_code(orig) != _normalize_code(expected_original):
            logger.debug(f"[Validation Failed] original_lines did not match expected source.\nGot:\n{orig}\nExpected:\n{expected_original}")
            return False

    # 3. Check fixed_lines is non-empty and changed
    fixed_stripped = fixed.strip()
    if not fixed_stripped:
        logger.debug("[Validation Failed] fixed_lines is empty.")
        return False

    if _normalize_code(fixed) == _normalize_code(expected_original):
        logger.debug("[Validation Failed] fixed_lines is identical to original_lines (no change made).")
        return False

    # 4. Syntactic sanity check: balanced delimiters (braces, brackets, parentheses)
    for open_char, close_char in [("{", "}"), ("[", "]"), ("(", ")")]:
        expected_balance = expected_original.count(open_char) - expected_original.count(close_char)
        fixed_balance = fixed.count(open_char) - fixed.count(close_char)

        if expected_balance != fixed_balance:
            logger.debug(
                f"[Validation Failed] Unbalanced delimiter '{open_char}{close_char}': "
                f"expected delta {expected_balance}, got delta {fixed_balance}"
            )
            return False

        # If original code was self-contained (balanced), fixed code must also have 0 delta
        if expected_balance == 0 and (fixed.count(open_char) != fixed.count(close_char)):
            return False

    # 5. Tag balance check for JSX/HTML tags
    orig_tag_open = len(re.findall(r"<\s*[a-zA-Z0-9_\-]+(?![^>]*/>)[^>]*>", expected_original))
    orig_tag_close = len(re.findall(r"</\s*[a-zA-Z0-9_\-]+\s*>", expected_original))
    fixed_tag_open = len(re.findall(r"<\s*[a-zA-Z0-9_\-]+(?![^>]*/>)[^>]*>", fixed))
    fixed_tag_close = len(re.findall(r"</\s*[a-zA-Z0-9_\-]+\s*>", fixed))

    orig_tag_delta = orig_tag_open - orig_tag_close
    fixed_tag_delta = fixed_tag_open - fixed_tag_close
    if orig_tag_delta != fixed_tag_delta:
        logger.debug(f"[Validation Failed] Unbalanced JSX tag count: orig_delta={orig_tag_delta}, fixed_delta={fixed_tag_delta}")
        return False

    return True


def _generate_unified_diff(file_path: str, original: str, fixed: str) -> str:
    """Produces a clean unified diff string from original_lines to fixed_lines."""
    orig_lines = original.splitlines(keepends=True)
    fixed_lines = fixed.splitlines(keepends=True)

    # Ensure trailing newlines for clean diff calculation
    if orig_lines and not orig_lines[-1].endswith("\n"):
        orig_lines[-1] += "\n"
    if fixed_lines and not fixed_lines[-1].endswith("\n"):
        fixed_lines[-1] += "\n"

    diff = difflib.unified_diff(
        orig_lines,
        fixed_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )
    return "\n".join(diff)


async def generate_fix(
    diagnosed: DiagnosedViolation,
    repo_path: str,
    scan_id: str,
) -> ProposedFix:
    """
    Generates a validated code patch for a diagnosed violation.
    - Builds context and prompt.
    - Invokes Nemotron Ultra (or Fast with escalation depending on FIX_GENERATION_MODEL).
    - Uses validate_fix_output as quality check.
    - If valid, generates unified git diff and returns status="proposed".
    - If validation fails repeatedly or budget exhausted, returns status="failed" with failure_reason.

    Args:
        diagnosed: The DiagnosedViolation to remediate.
        repo_path: Cloned repository filesystem path.
        scan_id: Scan job identifier.

    Returns:
        ProposedFix model instance.
    """
    context = get_fix_context(
        repo_path=repo_path,
        file=diagnosed.file,
        line=diagnosed.line or 1,
        context_lines=15,
    )
    expected_original = context["original_lines"]
    l_start = context["line_start"]
    l_end = context["line_end"]
    target_file = context["file"]

    if not expected_original.strip():
        return ProposedFix(
            fix_id=f"fix_{diagnosed.id}",
            violation_id=diagnosed.id,
            file=target_file,
            line_start=l_start,
            line_end=l_end,
            original_lines="",
            fixed_lines="",
            diff="",
            explanation_of_change="",
            confidence="low",
            status="failed",
            failure_reason=f"Could not locate target lines in '{target_file}'.",
        )

    system_prompt, user_prompt = build_fix_prompt(diagnosed, context)
    model_choice = getattr(settings, "FIX_GENERATION_MODEL", "ultra").lower()

    raw_response = ""
    parsed_json: Optional[Dict[str, Any]] = None
    is_valid = False
    failure_reason: Optional[str] = None

    try:
        if model_choice == "ultra":
            # Default straight to Nemotron Ultra for high-stakes code accuracy
            try:
                raw_response = await call_nemotron_ultra(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    max_tokens=1500,
                    scan_id=scan_id,
                )
                parsed_json = _extract_json_fix(raw_response)
                is_valid = validate_fix_output(parsed_json, expected_original) if parsed_json else False
                if not is_valid:
                    logger.debug(f"Ultra output invalid for {diagnosed.id}; raw preview: {raw_response[:200]}")
            except UltraBudgetExceededError as budget_err:
                logger.warning(f"Ultra budget exceeded for scan {scan_id}; attempting fast model escalation: {budget_err}")
                raw_response = await call_with_escalation(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    scan_id=scan_id,
                    quality_check=lambda r: validate_fix_output(r, expected_original),
                )
                parsed_json = _extract_json_fix(raw_response)
                is_valid = validate_fix_output(parsed_json, expected_original) if parsed_json else False
            except Exception as ultra_err:
                logger.warning(f"Nemotron Ultra invocation failed for {diagnosed.id}: {ultra_err}")
                failure_reason = f"Nemotron Ultra inference error: {ultra_err}"

        else:
            # Escalation mode: fast model first, escalate to Ultra on validation failure
            raw_response = await call_with_escalation(
                prompt=user_prompt,
                system_prompt=system_prompt,
                scan_id=scan_id,
                quality_check=lambda r: validate_fix_output(r, expected_original),
            )
            parsed_json = _extract_json_fix(raw_response)
            is_valid = validate_fix_output(parsed_json, expected_original) if parsed_json else False

    except Exception as exc:
        logger.warning(f"Code fix generation failed for {diagnosed.id}: {exc}")
        failure_reason = f"Fix generation error: {str(exc)}"

    # If first pass failed validation, attempt one targeted retry if parsed_json was invalid
    if not is_valid and not failure_reason:
        try:
            logger.info(f"Retrying fix generation for {diagnosed.id} with stricter precision constraints...")
            retry_prompt = (
                f"{user_prompt}\n\nIMPORTANT: Your previous output failed validation. "
                f"You MUST ensure 'original_lines' matches EXACTLY:\n{expected_original}\n"
                "And ensure 'fixed_lines' has balanced brackets/tags and is non-empty. "
                "Respond ONLY with a valid JSON object."
            )
            raw_response = await call_nemotron_ultra(
                prompt=retry_prompt,
                system_prompt=system_prompt,
                max_tokens=1500,
                scan_id=scan_id,
            )
            parsed_json = _extract_json_fix(raw_response)
            is_valid = validate_fix_output(parsed_json, expected_original) if parsed_json else False
        except Exception as retry_err:
            logger.warning(f"Retry fix generation failed for {diagnosed.id}: {retry_err}")
            failure_reason = f"Validation failed after escalation and retry: {retry_err}"

    if not is_valid or not parsed_json:
        fail_msg = failure_reason or "Output failed syntax and safety validation checks."
        logger.warning(f"Fix rejected for violation {diagnosed.id}: {fail_msg}")
        return ProposedFix(
            fix_id=f"fix_{diagnosed.id}",
            violation_id=diagnosed.id,
            file=target_file,
            line_start=l_start,
            line_end=l_end,
            original_lines=expected_original,
            fixed_lines="",
            diff="",
            explanation_of_change="",
            confidence="low",
            status="failed",
            failure_reason=fail_msg,
        )

    # Success: build unified git diff and return ProposedFix
    fixed_lines = str(parsed_json.get("fixed_lines", ""))
    explanation = str(parsed_json.get("explanation_of_change", "Accessibility defect resolved."))
    confidence = str(parsed_json.get("confidence", "high")).lower()
    if confidence not in ("high", "medium", "low"):
        confidence = "high"

    diff_str = _generate_unified_diff(
        file_path=target_file,
        original=expected_original,
        fixed=fixed_lines,
    )

    return ProposedFix(
        fix_id=f"fix_{diagnosed.id}",
        violation_id=diagnosed.id,
        file=target_file,
        line_start=l_start,
        line_end=l_end,
        original_lines=expected_original,
        fixed_lines=fixed_lines,
        diff=diff_str,
        explanation_of_change=explanation,
        confidence=confidence,
        status="proposed",
    )


async def generate_all_fixes(scan_id: str) -> List[ProposedFix]:
    """
    Coordinates code-fix generation across all diagnosed violations in a scan:
    - Loads diagnosed and explained violations from state.py
    - Filters out violations below configurable severity threshold (e.g. skip 'low' to save budget)
    - Concurrently processes violations (semaphore limit 2 for Ultra model)
    - Respects remaining per-scan Ultra budget
    - Emits WebSocket progress updates during execution
    - Persists fixes in state.py and returns list.

    Args:
        scan_id: Unique scan job identifier.

    Returns:
        List of ProposedFix model instances.
    """
    scan_data = get_scan(scan_id)
    if not scan_data:
        logger.warning(f"Scan {scan_id} not found in state store.")
        return []

    repo_path = scan_data.get("repo_path", "")
    violations_raw = scan_data.get("diagnosed_violations") or scan_data.get("violations", [])
    if not violations_raw:
        logger.info(f"No diagnosed violations to fix for scan {scan_id}.")
        update_scan(scan_id, fixes=[], status="fixed")
        return []

    # Convert to DiagnosedViolation instances
    diagnosed_list: List[DiagnosedViolation] = []
    for item in violations_raw:
        if isinstance(item, DiagnosedViolation):
            diagnosed_list.append(item)
        elif isinstance(item, Violation):
            from app.services.diagnosis_service import get_templated_diagnosis
            diagnosed_list.append(get_templated_diagnosis(item))
        elif isinstance(item, dict):
            diagnosed_list.append(DiagnosedViolation(**item))

    # Filter by severity threshold
    min_sev_str = getattr(settings, "FIX_MIN_SEVERITY", "medium").lower()
    min_weight = SEVERITY_WEIGHTS.get(min_sev_str, 2)

    eligible_violations: List[DiagnosedViolation] = []
    skipped_fixes: List[ProposedFix] = []

    for v in diagnosed_list:
        v_weight = SEVERITY_WEIGHTS.get(v.severity.lower(), 2)
        if v_weight >= min_weight:
            eligible_violations.append(v)
        else:
            logger.info(f"Skipping fix generation for violation {v.id} (severity '{v.severity}' below threshold '{min_sev_str}').")
            skipped_fixes.append(
                ProposedFix(
                    fix_id=f"fix_{v.id}",
                    violation_id=v.id,
                    file=v.file,
                    line_start=v.line or 1,
                    line_end=v.line or 1,
                    original_lines=v.context_snippet or "",
                    fixed_lines="",
                    diff="",
                    explanation_of_change=f"Reported but not auto-fixed (severity '{v.severity}' below auto-fix threshold).",
                    confidence="low",
                    status="failed",
                    failure_reason=f"Severity '{v.severity}' is below configured auto-fix threshold ('{min_sev_str}').",
                )
            )

    total_eligible = len(eligible_violations)
    if total_eligible == 0:
        logger.info(f"No violations met the severity threshold ({min_sev_str}) for auto-remediation.")
        all_fixes = skipped_fixes
        update_scan(scan_id, fixes=all_fixes, status="fixed")
        return all_fixes

    # Check remaining Ultra budget
    usage = get_scan_usage_stats(scan_id)
    spent = usage.get("ultra_cost_usd", 0.0)
    budget = getattr(settings, "ULTRA_BUDGET_USD_PER_SCAN", 0.05)

    if spent >= budget:
        logger.warning(
            f"Ultra budget already reached for scan {scan_id} (${spent:.4f} >= ${budget:.4f}). "
            "Fixes cannot be synthesized with Ultra."
        )
        budget_failed_fixes = [
            ProposedFix(
                fix_id=f"fix_{v.id}",
                violation_id=v.id,
                file=v.file,
                line_start=v.line or 1,
                line_end=v.line or 1,
                original_lines=v.context_snippet or "",
                fixed_lines="",
                diff="",
                explanation_of_change="",
                confidence="low",
                status="failed",
                failure_reason=f"Per-scan Ultra budget limit (${budget:.4f}) reached.",
            )
            for v in eligible_violations
        ]
        all_fixes = budget_failed_fixes + skipped_fixes
        update_scan(scan_id, fixes=all_fixes, status="fixed")
        return all_fixes

    semaphore = asyncio.Semaphore(2)  # Ultra limit 2 concurrent requests
    completed = 0
    progress_lock = asyncio.Lock()
    generated_fixes: List[ProposedFix] = []

    async def _fix_task(v: DiagnosedViolation) -> ProposedFix:
        nonlocal completed
        async with semaphore:
            fix = await generate_fix(
                diagnosed=v,
                repo_path=repo_path,
                scan_id=scan_id,
            )

            async with progress_lock:
                completed += 1
                progress_pct = int((completed / total_eligible) * 100)
                msg = f"Generated {completed}/{total_eligible} fixes"

                try:
                    from app.routers.websocket import broadcast_progress
                    await broadcast_progress(
                        scan_id=scan_id,
                        stage="generating_fixes",
                        progress=progress_pct,
                        message=msg,
                        data={
                            "generated_count": completed,
                            "total_count": total_eligible,
                            "latest_fix_id": fix.fix_id,
                            "latest_status": fix.status,
                        },
                    )
                except Exception as ws_err:
                    logger.debug(f"Progress streaming skipped: {ws_err}")

            return fix

    tasks = [_fix_task(v) for v in eligible_violations]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    generated_fixes = list(results)

    all_fixes = generated_fixes + skipped_fixes

    # Store in scan state
    update_scan(
        scan_id=scan_id,
        fixes=all_fixes,
        status="fixed",
    )

    try:
        from app.routers.websocket import broadcast_progress
        proposed_count = len([f for f in all_fixes if f.status == "proposed"])
        await broadcast_progress(
            scan_id=scan_id,
            stage="generating_fixes",
            progress=100,
            message=f"Code-fix synthesis complete: {proposed_count}/{len(all_fixes)} patches proposed.",
            data={
                "total_fixes": len(all_fixes),
                "proposed_count": proposed_count,
                "failed_count": len(all_fixes) - proposed_count,
            },
        )
    except Exception as ws_err:
        logger.debug(f"Final progress streaming skipped: {ws_err}")

    logger.info(f"Scan {scan_id}: Fix generation complete ({proposed_count} proposed, {len(all_fixes) - proposed_count} failed).")
    return all_fixes


async def generate_remediation_patch(violation: Violation, component_context: str = "") -> ProposedFix:
    """Backward-compatible alias for single violation remediation."""
    if isinstance(violation, DiagnosedViolation):
        diagnosed = violation
    else:
        from app.services.diagnosis_service import get_templated_diagnosis
        diagnosed = get_templated_diagnosis(violation)
    return await generate_fix(diagnosed=diagnosed, repo_path=".", scan_id="standalone")

