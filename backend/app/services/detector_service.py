"""
Detector Service: Accessibility violation detection module (Phase 11).
Combines free, instant static rule-based prechecks with NVIDIA Nemotron Fast
tiered LLM analysis to produce high-precision WCAG 2.2 violations.
"""
import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.models.schemas import Violation
from app.services.llm_client import (
    call_with_escalation,
    extract_json_payload,
)
from app.state import get_scan, update_scan

logger = logging.getLogger(__name__)


def mask_comments(text: str) -> str:
    """
    Masks JSX and HTML comments with spaces while preserving line breaks and string length.
    Ensures regex checks never match tags or attributes inside code comments.
    """
    def _preserve_lines(m: re.Match) -> str:
        s = m.group(0)
        return "".join("\n" if ch == "\n" else " " for ch in s)

    text = re.sub(r"\{\/\*[\s\S]*?\*\/\}", _preserve_lines, text)
    text = re.sub(r"<!--[\s\S]*?-->", _preserve_lines, text)
    return text


def rule_based_precheck(chunk: Dict[str, Any]) -> List[Violation]:
    """
    Performs fast, cost-free static heuristic analysis for common WCAG violations:
    - <img> without alt attribute
    - <input>/<select>/<textarea> without label, aria-label or aria-labelledby
    - <div>/<span> with onClick but no role, tabIndex or key handler
    - <button> or <a> with no text content and no aria-label
    - <a> with empty or '#' href
    - missing <html lang>
    - positive tabIndex values

    Args:
        chunk: Batch chunk dictionary containing 'file', 'content', and 'start_line'.

    Returns:
        List of Violation objects with source="rule".
    """
    file_path = chunk.get("file", "unknown")
    raw_content = chunk.get("content", "")
    content = mask_comments(raw_content)
    raw_lines = raw_content.splitlines()
    start_line = int(chunk.get("start_line", 1) or 1)

    violations: List[Violation] = []

    # 1. <img> without alt attribute
    for m in re.finditer(r"<img\b([^>]*)>", content, re.IGNORECASE):
        attrs = m.group(1)
        if not re.search(r"\balt\s*=", attrs, re.IGNORECASE):
            line = start_line + content[: m.start()].count("\n")
            violations.append(
                Violation(
                    id="",
                    file=file_path,
                    line=line,
                    type="image-alt",
                    severity="critical",
                    description="Images must have an alt attribute describing the image or alt=\"\" if decorative.",
                    selector="img",
                    context_snippet=m.group(0).strip()[:150],
                    source="rule",
                    wcag_criterion="1.1.1 Non-text Content",
                )
            )

    # 2. <input>/<select>/<textarea> without label, aria-label or aria-labelledby
    for m in re.finditer(r"<(input|select|textarea)\b([^>]*)>", content, re.IGNORECASE):
        tag = m.group(1).lower()
        attrs = m.group(2)
        # Skip hidden inputs or submit/reset with value
        if tag == "input" and re.search(r'\btype\s*=\s*["\']hidden["\']', attrs, re.IGNORECASE):
            continue

        has_aria = bool(re.search(r"\baria-label(?:ledby)?\s*=", attrs, re.IGNORECASE))
        has_associated_label = False
        id_m = re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', attrs, re.IGNORECASE)
        if id_m:
            elem_id = re.escape(id_m.group(1))
            if re.search(rf"<label\b[^>]*\b(?:htmlFor|for)\s*=\s*[\"']{elem_id}[\"']", content, re.IGNORECASE):
                has_associated_label = True

        preceding = content[: m.start()]
        lbl_open = preceding.rfind("<label")
        lbl_close = preceding.rfind("</label")
        is_wrapped = (lbl_open != -1) and (lbl_close == -1 or lbl_close < lbl_open)

        if not (has_aria or has_associated_label or is_wrapped):
            line = start_line + content[: m.start()].count("\n")
            violations.append(
                Violation(
                    id="",
                    file=file_path,
                    line=line,
                    type="label",
                    severity="critical",
                    description=f"Form <{tag}> element has no associated <label>, aria-label, or aria-labelledby.",
                    selector=tag,
                    context_snippet=m.group(0).strip()[:150],
                    source="rule",
                    wcag_criterion="3.3.2 Labels or Instructions",
                )
            )

    # 3. <div>/<span> with onClick but no role, tabIndex or key handler
    for m in re.finditer(r"<(div|span)\b([^>]*)>", content, re.IGNORECASE):
        tag = m.group(1)
        attrs = m.group(2)
        if re.search(r"\bonclick\s*=", attrs, re.IGNORECASE):
            has_role = bool(re.search(r"\brole\s*=", attrs, re.IGNORECASE))
            has_tabindex = bool(re.search(r"\btabindex\s*=", attrs, re.IGNORECASE))
            has_key = bool(re.search(r"\bonkey(?:down|press|up)\s*=", attrs, re.IGNORECASE))
            if not (has_role and has_tabindex and has_key):
                line = start_line + content[: m.start()].count("\n")
                violations.append(
                    Violation(
                        id="",
                        file=file_path,
                        line=line,
                        type="click-events-have-key-events",
                        severity="serious",
                        description=f"Non-interactive <{tag}> with onClick must have a role, tabIndex, and keyboard handler (onKeyDown).",
                        selector=tag,
                        context_snippet=m.group(0).strip()[:150],
                        source="rule",
                        wcag_criterion="2.1.1 Keyboard",
                    )
                )

    # 4. <button> or <a> with no text content and no aria-label
    for m in re.finditer(
        r"<(button|a)\b([^>]*)>(.*?)(?:<\/\1>|$)|<(button|a)\b([^>]*)\/>",
        content,
        re.IGNORECASE | re.DOTALL,
    ):
        tag = (m.group(1) or m.group(4)).lower()
        attrs = m.group(2) or m.group(5) or ""
        inner = m.group(3) or ""
        has_aria = bool(re.search(r"\b(?:aria-label|aria-labelledby|title)\s*=", attrs, re.IGNORECASE))

        inner_text = re.sub(r"<[^>]+>", "", inner).strip()
        has_inner_label = bool(
            inner_text
            or re.search(r"\balt\s*=\s*[\"'][^\"']+[\"']", inner, re.IGNORECASE)
            or re.search(r"\baria-label\s*=\s*[\"'][^\"']+[\"']", inner, re.IGNORECASE)
        )
        if not (has_aria or has_inner_label):
            line = start_line + content[: m.start()].count("\n")
            v_type = "button-name" if tag == "button" else "link-name"
            violations.append(
                Violation(
                    id="",
                    file=file_path,
                    line=line,
                    type=v_type,
                    severity="serious",
                    description=f"<{tag}> element has no accessible text name and no aria-label.",
                    selector=tag,
                    context_snippet=m.group(0).strip()[:150],
                    source="rule",
                    wcag_criterion="4.1.2 Name, Role, Value",
                )
            )

    # 5. <a> with empty or "#" href
    for m in re.finditer(r"<a\b([^>]*)>", content, re.IGNORECASE):
        attrs = m.group(1)
        href_m = re.search(r'\bhref\s*=\s*(?:["\']([^"\']*)["\']|\{([^}]+)\})', attrs, re.IGNORECASE)
        is_invalid = False
        if href_m:
            val = (href_m.group(1) or href_m.group(2) or "").strip()
            if val in ("", "#", '"#"', "'#'", "javascript:void(0)", "javascript:void(0);", "javascript:;"):
                is_invalid = True
        else:
            is_invalid = True

        if is_invalid:
            line = start_line + content[: m.start()].count("\n")
            violations.append(
                Violation(
                    id="",
                    file=file_path,
                    line=line,
                    type="link-href",
                    severity="moderate",
                    description="Anchor <a> element has an empty, '#', or missing href attribute.",
                    selector="a",
                    context_snippet=m.group(0).strip()[:150],
                    source="rule",
                    wcag_criterion="2.4.4 Link Purpose (In Context)",
                )
            )

    # 6. missing <html lang>
    for m in re.finditer(r"<html\b([^>]*)>", content, re.IGNORECASE):
        attrs = m.group(1)
        if not re.search(r"\blang\s*=", attrs, re.IGNORECASE):
            line = start_line + content[: m.start()].count("\n")
            violations.append(
                Violation(
                    id="",
                    file=file_path,
                    line=line,
                    type="html-has-lang",
                    severity="critical",
                    description="<html> element is missing a lang attribute (e.g. lang=\"en\").",
                    selector="html",
                    context_snippet=m.group(0).strip()[:150],
                    source="rule",
                    wcag_criterion="3.1.1 Language of Page",
                )
            )

    # 7. positive tabIndex values
    for m in re.finditer(
        r'\btabindex\s*=\s*(?:["\']?([1-9]\d*)["\']?|\{\s*([1-9]\d*)\s*\})',
        content,
        re.IGNORECASE,
    ):
        val = m.group(1) or m.group(2)
        line = start_line + content[: m.start()].count("\n")
        violations.append(
            Violation(
                id="",
                file=file_path,
                line=line,
                type="tabindex",
                severity="moderate",
                description=f"Avoid positive tabIndex values ({val}) which disrupt natural focus navigation order.",
                selector=None,
                context_snippet=content[max(0, m.start() - 25) : min(len(content), m.end() + 25)].strip(),
                source="rule",
                wcag_criterion="2.4.3 Focus Order",
            )
        )

    # 8. Empty <title> element
    for m in re.finditer(r"<title\b[^>]*>(\s*)</title>", content, re.IGNORECASE):
        line = start_line + content[: m.start()].count("\n")
        violations.append(
            Violation(
                id="",
                file=file_path,
                line=line,
                type="document-title",
                severity="serious",
                description="<title> element is empty. Provide a descriptive, informative document title.",
                selector="title",
                context_snippet=m.group(0).strip()[:150],
                source="rule",
                wcag_criterion="2.4.2 Page Titled",
            )
        )

    # 9. Focusable element with aria-hidden="true"
    for m in re.finditer(r"<(button|a|input|select|textarea)\b([^>]*\baria-hidden\s*=\s*[\"']true[\"'][^>]*)>", content, re.IGNORECASE):
        line = start_line + content[: m.start()].count("\n")
        tag = m.group(1).lower()
        violations.append(
            Violation(
                id="",
                file=file_path,
                line=line,
                type="aria-hidden-focus",
                severity="critical",
                description=f"Focusable <{tag}> element must not have aria-hidden=\"true\" as it hides focused controls from assistive technology.",
                selector=tag,
                context_snippet=m.group(0).strip()[:150],
                source="rule",
                wcag_criterion="4.1.2 Name, Role, Value",
            )
        )

    # 10. <iframe> without title
    for m in re.finditer(r"<iframe\b([^>]*)>", content, re.IGNORECASE):
        attrs = m.group(1)
        if not re.search(r"\btitle\s*=", attrs, re.IGNORECASE):
            line = start_line + content[: m.start()].count("\n")
            violations.append(
                Violation(
                    id="",
                    file=file_path,
                    line=line,
                    type="frame-title",
                    severity="serious",
                    description="<iframe> element must have a non-empty title attribute describing its embedded content.",
                    selector="iframe",
                    context_snippet=m.group(0).strip()[:150],
                    source="rule",
                    wcag_criterion="4.1.2 Name, Role, Value",
                )
            )

    # 11. Viewport scaling disabled
    for m in re.finditer(r"<meta\b[^>]*\bname\s*=\s*[\"']viewport[\"'][^>]*>", content, re.IGNORECASE):
        meta_tag = m.group(0)
        if re.search(r"user-scalable\s*=\s*no|maximum-scale\s*=\s*1(?:\.0)?(?:\b|,|;)", meta_tag, re.IGNORECASE):
            line = start_line + content[: m.start()].count("\n")
            violations.append(
                Violation(
                    id="",
                    file=file_path,
                    line=line,
                    type="meta-viewport",
                    severity="critical",
                    description="Viewport meta tag disables zoom/scaling (user-scalable=no or maximum-scale=1), preventing low-vision users from enlarging text.",
                    selector="meta",
                    context_snippet=meta_tag.strip()[:150],
                    source="rule",
                    wcag_criterion="1.4.4 Resize Text",
                )
            )

    # 12. Placeholder or useless image alt text (alt="image", alt="photo", etc.)
    for m in re.finditer(r'<img\b([^>]*\balt\s*=\s*["\'](image|photo|picture|icon|graphic)["\'][^>]*)>', content, re.IGNORECASE):
        line = start_line + content[: m.start()].count("\n")
        violations.append(
            Violation(
                id="",
                file=file_path,
                line=line,
                type="image-alt",
                severity="serious",
                description="Image has generic placeholder alt text (e.g. alt=\"image\"). Provide informative descriptive text.",
                selector="img",
                context_snippet=m.group(0).strip()[:150],
                source="rule",
                wcag_criterion="1.1.1 Non-text Content",
            )
        )

    # 13. Duplicate ID attribute within file
    all_ids = list(re.finditer(r'\bid\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE))
    seen_ids: Dict[str, int] = {}
    for im in all_ids:
        val = im.group(1).strip()
        seen_ids[val] = seen_ids.get(val, 0) + 1
    for im in all_ids:
        val = im.group(1).strip()
        if seen_ids[val] > 1:
            line = start_line + content[: im.start()].count("\n")
            violations.append(
                Violation(
                    id="",
                    file=file_path,
                    line=line,
                    type="duplicate-id",
                    severity="critical",
                    description=f"Duplicate id attribute '{val}' detected. ID values must be unique across the document.",
                    selector=f"#{val}",
                    context_snippet=content[max(0, im.start() - 20) : min(len(content), im.end() + 20)].strip(),
                    source="rule",
                    wcag_criterion="4.1.1 Parsing",
                )
            )

    # 14. Missing <main> landmark
    if re.search(r"<body\b", content, re.IGNORECASE) and not re.search(r"<(?:main\b|div\b[^>]*\brole=[\"']main[\"'])", content, re.IGNORECASE):
        body_pos = re.search(r"<body\b", content, re.IGNORECASE).start()
        line = max(1, start_line + content[:body_pos].count("\n"))
        violations.append(
            Violation(
                id="",
                file=file_path,
                line=line,
                type="landmark-one-main",
                severity="moderate",
                description="Document is missing a <main> landmark containing the primary page content.",
                selector="body",
                context_snippet="<body>",
                source="rule",
                wcag_criterion="1.3.1 Info and Relationships",
            )
        )

    # 15. Missing skip-to-content link
    if re.search(r"<body\b", content, re.IGNORECASE) and not re.search(r'href\s*=\s*["\']#content["\']|class\s*=\s*["\'][^"\']*skip-link', content, re.IGNORECASE):
        body_pos = re.search(r"<body\b", content, re.IGNORECASE).start()
        line = max(1, start_line + content[:body_pos].count("\n"))
        violations.append(
            Violation(
                id="",
                file=file_path,
                line=line,
                type="bypass",
                severity="moderate",
                description="Page is missing a skip-to-content link to allow keyboard users to bypass navigation.",
                selector="body",
                context_snippet="<body>",
                source="rule",
                wcag_criterion="2.4.1 Bypass Blocks",
            )
        )

    # 16. Data table without <th> header cells
    for m in re.finditer(r"<table\b[^>]*>([\s\S]*?)</table>", content, re.IGNORECASE):
        tbl_body = m.group(1)
        if re.search(r"<td\b", tbl_body, re.IGNORECASE) and not re.search(r"<th\b", tbl_body, re.IGNORECASE):
            line = start_line + content[: m.start()].count("\n")
            violations.append(
                Violation(
                    id="",
                    file=file_path,
                    line=line,
                    type="table-header",
                    severity="serious",
                    description="Data <table> has data cells (<td>) but lacks header cells (<th>) or column/row scope.",
                    selector="table",
                    context_snippet=m.group(0).strip()[:150],
                    source="rule",
                    wcag_criterion="1.3.1 Info and Relationships",
                )
            )

    return violations


def build_detection_prompt(chunk: Dict[str, Any], known_issues: List[Violation]) -> str:
    """
    Constructs an optimized prompt instructing the model to find additional accessibility
    violations beyond statically known rule-based issues.

    Args:
        chunk: Batch chunk dictionary containing 'file', 'content', and 'start_line'.
        known_issues: List of rule-based violations already identified in this chunk.

    Returns:
        Structured prompt string.
    """
    file_path = chunk.get("file", "unknown")
    start_line = chunk.get("start_line", 1) or 1
    content = chunk.get("content", "")

    known_summary = ""
    if known_issues:
        known_lines = [f"- Line {v.line}: [{v.type}] {v.description}" for v in known_issues]
        known_summary = (
            "The following issues were ALREADY detected by static rules in this snippet:\n"
            + "\n".join(known_lines)
            + "\nDO NOT report these existing issues again.\n\n"
        )

    return f"""/no_think
You are an expert accessibility auditor and a pure JSON API.
Do not output any thinking process, introduction, or markdown explanations.
Begin your response directly with '{{'.

Analyze the following source code snippet from file: {file_path}
The snippet starts at line {start_line} of the file.

{known_summary}Inspect the snippet for ADDITIONAL accessibility violations, specifically:
- Color contrast hints (e.g. low-contrast Tailwind classes or light gray text like #999, #aaa, text-gray-400 on white backgrounds)
- Heading hierarchy violations (e.g. <h1> skipped directly to <h3>, multiple <h1>s, missing <h1>)
- Missing semantic landmarks (<main>, <header>, <nav>, <footer>, <aside>)
- ARIA misuse (invalid attributes, incorrect roles, redundant ARIA)
- Focus management & keyboard navigation traps
- Form validation errors and missing error descriptions (aria-describedby, aria-invalid)

Code snippet to inspect:
```
{content}
```

CRITICAL INSTRUCTIONS:
1. "line_offset" MUST be a 0-indexed integer representing the line offset within the code snippet where the defect occurs (0 for line 1 of the snippet).
2. "severity" MUST be one of: "critical", "serious", "moderate", "minor".
3. "wcag_criterion" should specify the WCAG 2.2 Success Criterion (e.g. "1.4.3 Contrast (Minimum)").
4. If the code is clean or has no additional violations, return exactly: {{"violations": []}}
5. Do NOT invent issues.

Respond ONLY with a valid JSON object in this exact format:
{{
  "violations": [
    {{
      "line_offset": 0,
      "type": "heading-order",
      "severity": "moderate",
      "description": "Heading level skipped from <h1> to <h3> without an intermediate <h2>.",
      "wcag_criterion": "1.3.1 Info and Relationships"
    }}
  ]
}}
"""


def extract_violations_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Robustly extracts {"violations": [...]} from text even if surrounded by
    explanations, markdown formatting, or reasoning monologues.
    """
    if not text:
        return None

    # 1. Try standard extract_json_payload first
    try:
        cleaned = extract_json_payload(text)
        data = json.loads(cleaned)
        if isinstance(data, dict) and "violations" in data and isinstance(data["violations"], list):
            return data
    except Exception:
        pass

    # 2. Match explicit {"violations": [...]}
    match = re.search(r"(\{\s*\"violations\"\s*:\s*\[[\s\S]*?\]\s*\})", text)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict) and "violations" in data and isinstance(data["violations"], list):
                return data
        except Exception:
            pass

    # 3. Match code fences
    for block in re.finditer(r"```(?:json)?\s*([\s\S]*?)\s*```", text):
        try:
            data = json.loads(block.group(1).strip())
            if isinstance(data, dict) and "violations" in data and isinstance(data["violations"], list):
                return data
        except Exception:
            pass

    return None


async def detect_violations_in_chunk(chunk: Dict[str, Any], scan_id: str) -> List[Violation]:
    """
    Performs hybrid accessibility violation detection on a single code chunk:
    1. Runs rule_based_precheck first.
    2. Skips LLM invocation if chunk has no JSX or HTML markup tags.
    3. Calls call_with_escalation with a quality check ensuring valid JSON structure.
    4. Calculates absolute line numbers using chunk start_line and line_offset.
    5. Safely falls back to rule-based violations if JSON parsing fails.

    Args:
        chunk: Chunk data dictionary.
        scan_id: Current scan identifier.

    Returns:
        List of Violation objects (both rule and LLM detected).
    """
    # 1. Run rule-based precheck first
    rule_violations = rule_based_precheck(chunk)

    content = chunk.get("content", "")
    # 2. Skip LLM call if chunk has no markup elements
    if not re.search(r"<[A-Za-z][\s\S]*>", content):
        return rule_violations

    # 3. Quality check function to ensure valid JSON payload
    def quality_check(response_text: str) -> bool:
        data = extract_violations_json(response_text)
        return data is not None

    prompt = build_detection_prompt(chunk, rule_violations)

    try:
        response_text = await call_with_escalation(
            prompt=prompt,
            system_prompt=(
                "You are an expert WCAG 2.2 accessibility auditor. "
                "Output strictly a valid JSON object matching the requested schema. No markdown formatting."
            ),
            scan_id=scan_id,
            quality_check=quality_check,
        )
    except Exception as exc:
        logger.warning(f"LLM detection failed for {chunk.get('file')}: {exc}. Returning rule violations only.")
        return rule_violations

    # 4. Parse LLM JSON results
    llm_violations: List[Violation] = []
    data = extract_violations_json(response_text)
    if not data:
        logger.warning(
            f"Failed to parse LLM JSON response for {chunk.get('file')}. "
            f"Raw text was: {response_text[:200]}... Returning rule-based findings."
        )
        return rule_violations

    raw_violations = data.get("violations", [])
    file_path = chunk.get("file", "unknown")
    start_line = int(chunk.get("start_line", 1) or 1)
    content_lines = content.splitlines()
    total_lines = len(content_lines)

    for item in raw_violations:
        if not isinstance(item, dict):
            continue

        try:
            line_offset = int(item.get("line_offset", 0))
        except (ValueError, TypeError):
            line_offset = 0

        # Clamp offset to snippet length
        line_offset = max(0, min(line_offset, max(0, total_lines - 1)))
        abs_line = start_line + line_offset
        snippet = content_lines[line_offset].strip() if 0 <= line_offset < total_lines else None

        sev = str(item.get("severity", "serious")).lower()
        if sev not in ("critical", "serious", "moderate", "minor"):
            if sev == "high":
                sev = "serious"
            elif sev == "low":
                sev = "minor"
            else:
                sev = "serious"

        llm_violations.append(
            Violation(
                id="",
                file=file_path,
                line=abs_line,
                type=str(item.get("type", "accessibility-defect")).strip().lower(),
                severity=sev,
                description=str(item.get("description", "Accessibility violation detected.")).strip(),
                selector=item.get("selector"),
                context_snippet=snippet,
                source="llm",
                wcag_criterion=item.get("wcag_criterion"),
            )
        )

    seen = {(v.type, v.line) for v in rule_violations}
    deduped_llm = [v for v in llm_violations if (v.type, v.line) not in seen]
    return rule_violations + deduped_llm


async def detect_violations(scan_id: str) -> List[Violation]:
    """
    Coordinates batch accessibility violation detection for a scan:
    - Loads prepared chunks from state.py
    - Processes chunks concurrently using asyncio.Semaphore (limit 5)
    - Deduplicates identical rule vs LLM findings (rule-based takes precedence)
    - Assigns unique IDs (viol_01, viol_02, ...)
    - Streams WebSocket progress updates as chunks complete
    - Persists results to state.py

    Args:
        scan_id: Unique scan job identifier.

    Returns:
        List of all deduplicated Violation objects.
    """
    scan_data = get_scan(scan_id)
    if not scan_data:
        logger.warning(f"Scan {scan_id} not found in state store.")
        return []

    batch = scan_data.get("scan_batch", [])
    if not batch:
        logger.info(f"No scan chunks available for scan {scan_id}.")
        update_scan(scan_id, violations=[], status="scanned")
        return []

    total_chunks = len(batch)
    semaphore = asyncio.Semaphore(5)
    scanned_chunks = 0
    found_violations = 0
    progress_lock = asyncio.Lock()

    all_raw_violations: List[Violation] = []

    async def _process_chunk(chunk: Dict[str, Any]) -> List[Violation]:
        nonlocal scanned_chunks, found_violations
        async with semaphore:
            chunk_results = await detect_violations_in_chunk(chunk, scan_id=scan_id)

            async with progress_lock:
                scanned_chunks += 1
                found_violations += len(chunk_results)
                progress_pct = int((scanned_chunks / total_chunks) * 100)
                msg = f"Scanned {scanned_chunks}/{total_chunks} chunks — {found_violations} violations found so far"

                try:
                    from app.routers.websocket import broadcast_progress
                    await broadcast_progress(
                        scan_id=scan_id,
                        stage="scanning",
                        progress=progress_pct,
                        message=msg,
                        data={
                            "scanned_chunks": scanned_chunks,
                            "total_chunks": total_chunks,
                            "violations_found": found_violations,
                        },
                    )
                except Exception as ws_err:
                    logger.debug(f"Progress streaming skipped: {ws_err}")

            return chunk_results

    tasks = [_process_chunk(c) for c in batch]
    chunk_outputs = await asyncio.gather(*tasks, return_exceptions=False)

    for sublist in chunk_outputs:
        all_raw_violations.extend(sublist)

    # Deduplication:
    # If a rule-based and LLM violation have the same file + line + type, keep the rule-based one.
    rule_keys: Set[Tuple[str, Optional[int], str]] = set()
    rule_violations: List[Violation] = []
    llm_violations: List[Violation] = []

    for v in all_raw_violations:
        norm_type = v.type.lower().replace("_", "-")
        key = (v.file, v.line, norm_type)
        if v.source == "rule":
            if key not in rule_keys:
                rule_keys.add(key)
                rule_violations.append(v)
        else:
            llm_violations.append(v)

    deduped: List[Violation] = list(rule_violations)
    llm_keys: Set[Tuple[str, Optional[int], str]] = set(rule_keys)

    for v in llm_violations:
        norm_type = v.type.lower().replace("_", "-")
        key = (v.file, v.line, norm_type)
        if key not in llm_keys:
            llm_keys.add(key)
            deduped.append(v)

    # Phase 13: Classify violations (category normalization, severity scoring, prioritization ranking)
    from app.services.classifier_service import classify_violations
    classified = classify_violations(deduped)

    # Assign clean sequential IDs in priority order
    for idx, v in enumerate(classified, 1):
        v.id = f"viol_{idx:02d}"

    # Update in-memory state
    update_scan(
        scan_id=scan_id,
        violations=classified,
        status="scanned",
    )

    try:
        from app.routers.websocket import broadcast_progress
        await broadcast_progress(
            scan_id=scan_id,
            stage="scanning",
            progress=100,
            message=f"Accessibility audit complete: {len(classified)} actionable violations detected.",
            data={"violations_count": len(classified)},
        )
    except Exception as ws_err:
        logger.debug(f"Final progress streaming skipped: {ws_err}")

    logger.info(f"Scan {scan_id} audit complete. Detected {len(classified)} violations across {total_chunks} chunks.")
    return classified
