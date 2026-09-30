"""
Explainer Service: Generates human-readable, non-technical plain English summaries
for accessibility violations using the fast Nemotron tier (Phase 15).
Ensures every defect in the report has an accessible explanation for stakeholders.
"""
import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from app.models.schemas import DiagnosedViolation, Violation, ViolationCategory
from app.services.llm_client import call_nemotron_fast
from app.state import get_scan, update_scan

logger = logging.getLogger(__name__)

MAX_EXPLANATION_LENGTH = 400


def truncate_at_sentence_boundary(text: str, max_chars: int = MAX_EXPLANATION_LENGTH) -> str:
    """
    Truncates text cleanly at the last sentence boundary within max_chars.
    Falls back to a word boundary if no sentence ending is found.
    """
    if not text:
        return ""

    stripped = text.strip()
    if len(stripped) <= max_chars:
        # If text ends abruptly without sentence punctuation but has an earlier complete sentence, trim dangling fragment
        if not any(stripped.endswith(p) for p in [".", "!", "?", '."', "!'", "?'"]):
            end_indices = [m.end() for m in re.finditer(r"[\.\!\?](?=\s|$)", stripped)]
            if end_indices and max(end_indices) >= 50:
                return stripped[:max(end_indices)].strip()
        return stripped

    truncated = stripped[:max_chars]

    # Look for sentence-ending punctuation followed by space, newline, or end of string
    end_indices: List[int] = []
    for match in re.finditer(r"[\.\!\?](?=\s|$)", truncated):
        end_indices.append(match.end())

    if end_indices:
        last_end = max(end_indices)
        # Ensure we don't truncate prematurely if the first sentence was very short
        if last_end >= 50 or last_end == len(truncated):
            return truncated[:last_end].strip()

    # Fallback: truncate at last word boundary before (max_chars - 3) to allow for "..."
    budget = max(0, max_chars - 3)
    last_space = stripped[:budget].rfind(" ")
    if last_space > 40:
        return stripped[:last_space].strip() + "..."

    return stripped[:max_chars].strip()


def build_explanation_prompt(diagnosed: DiagnosedViolation) -> str:
    """
    Constructs a targeted prompt for Nemotron Fast based on the diagnosis source:
    - If diagnosis_source == 'llm': Rewrites root_cause, user_impact, and fix_strategy
      into a friendly, non-technical 2-3 sentence summary for non-developer stakeholders.
    - If diagnosis_source == 'template': Expands the generic category and file context
      into a specific, clear explanation.

    Args:
        diagnosed: DiagnosedViolation instance.

    Returns:
        Structured prompt string.
    """
    cat_str = (
        diagnosed.category.value
        if isinstance(diagnosed.category, ViolationCategory)
        else str(diagnosed.category)
    )

    if getattr(diagnosed, "diagnosis_source", "template") == "llm":
        return f"""You are an accessibility advocate writing an executive report for non-technical stakeholders.
Rewrite the following technical diagnosis into 2 to 3 friendly, plain-English sentences explaining what is wrong, who is impacted, and how to fix it:

Issue Details:
- Component: {diagnosed.file} (Line {diagnosed.line or 'unknown'})
- Category: {cat_str} ({diagnosed.type})
- Severity: {diagnosed.severity}
- Technical Root Cause: {diagnosed.root_cause}
- User Impact: {diagnosed.user_impact}
- Fix Strategy: {diagnosed.fix_strategy}

Output a valid JSON object matching:
{{
  "explanation": "<summary>"
}}"""

    else:
        # Template-diagnosed violation prompt
        return f"""You are an accessibility advocate writing an executive report for non-technical stakeholders.
Explain in 2 to 3 friendly, plain-English sentences what is wrong, who is impacted, and how to fix it for {diagnosed.file}:

Issue Details:
- Component: {diagnosed.file} (Line {diagnosed.line or 'unknown'})
- Category: {cat_str}
- Rule: {diagnosed.type}
- Severity: {diagnosed.severity}
- Description: {diagnosed.description}
- Snippet: {diagnosed.context_snippet or 'None'}

Output a valid JSON object matching:
{{
  "explanation": "<summary>"
}}"""


def _is_usable_explanation(text: str) -> bool:
    """Validates that candidate text is a real human-readable summary without model scratchpad artifacts."""
    if not text:
        return False
    s = text.strip()
    if len(s) < 50:
        return False
    # Ensure it doesn't start with raw JSON, markdown fences, list markers, numbers, or quotes
    if re.match(r'^(?:[{\[#*"`\-\d]|(?:\d+\.))', s):
        return False
    # Ensure there is at least one terminal sentence boundary
    if not (any(s.endswith(p) for p in [".", "!", "?", '."', "!'", "?'"]) or re.search(r"[.!?]\s", s)):
        return False
    lower = s.lower()
    disallowed = [
        "thinking process",
        "analyze user request",
        "analyze the request",
        "your 2-3 sentence",
        "<summary>",
        "let's count",
        "check character",
        "output only",
        "draft ",
        "wait, ",
        "snippet is",
        "i'll output",
        "i will output",
        "key points",
        "deconstruct",
        "let me",
        "format as",
        "anti-pattern",
    ]
    if any(d in lower for d in disallowed):
        return False
    return True


def _get_fallback_explanation(diagnosed: DiagnosedViolation) -> str:
    """
    Generates a deterministic fallback explanation when LLM inference fails or is skipped.
    """
    cat_readable = (
        diagnosed.category.value.replace("_", " ").title()
        if hasattr(diagnosed.category, "value")
        else str(diagnosed.category)
    )
    file_name = diagnosed.file.split("/")[-1].split("\\")[-1]

    if diagnosed.description:
        desc = diagnosed.description.rstrip(".")
        return f"In {file_name}, a {diagnosed.severity.lower()} priority {cat_readable} issue was identified: {desc}. Addressing this ensures full compliance and accessible interaction for assistive technology users."

    return f"A {diagnosed.severity.lower()} priority {cat_readable} issue was found in {file_name}. Remediating this component will remove barriers for users relying on keyboard navigation and screen readers."


async def generate_explanation(diagnosed: DiagnosedViolation) -> str:
    """
    Generates a plain-English explanation for a single violation using the fast model.
    Enforces a strict maximum length (400 chars) with clean sentence boundary truncation.
    Safely falls back to a deterministic string if LLM inference fails.

    Args:
        diagnosed: DiagnosedViolation instance.

    Returns:
        Clean plain-English explanation string.
    """
    prompt = build_explanation_prompt(diagnosed)

    try:
        raw_text = await call_nemotron_fast(
            prompt=prompt,
            system_prompt=(
                "You are an accessibility advocate writing concise executive summaries for non-technical stakeholders. "
                "Respond with a valid JSON object containing an 'explanation' string. Do not output preamble or markdown blocks."
            ),
            max_tokens=600,
            response_format="json",
        )

        cleaned = ""
        # 1. Try structured JSON parsing directly
        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict) and "explanation" in parsed:
                candidate = str(parsed["explanation"]).strip()
                if _is_usable_explanation(candidate):
                    cleaned = candidate
        except Exception:
            pass

        # 2. Try regex extraction of JSON explanation value
        if not cleaned:
            json_match = re.search(r'"explanation"\s*:\s*"((?:[^"\\]|\\.)*?)(?:"|\Z)', raw_text, re.DOTALL)
            if json_match:
                candidate = json_match.group(1).replace(r'\"', '"').replace(r'\n', ' ').strip()
                if _is_usable_explanation(candidate):
                    cleaned = candidate

        # 3. If model emitted chain of thought with quotes, extract the candidate quote
        if not cleaned:
            quotes = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', raw_text)
            good_quotes = [q.strip() for q in quotes if _is_usable_explanation(q.strip())]
            if good_quotes:
                cleaned = good_quotes[-1]

        # 4. Fall back to text parsing if response wasn't clean JSON or quoted
        if not cleaned:
            raw_stripped = raw_text.strip().strip('"').strip("'")
            raw_stripped = re.sub(r"<think>.*?</think>", "", raw_stripped, flags=re.DOTALL).strip()

            paragraphs = [p.strip() for p in raw_stripped.split("\n\n") if p.strip()]
            candidate_paragraphs = [p for p in paragraphs if _is_usable_explanation(p.strip())]
            if candidate_paragraphs:
                cleaned = candidate_paragraphs[-1]

        if cleaned and _is_usable_explanation(cleaned):
            return truncate_at_sentence_boundary(cleaned, max_chars=MAX_EXPLANATION_LENGTH)

    except Exception as exc:
        logger.warning(
            f"Fast LLM explanation failed for violation {diagnosed.id} in {diagnosed.file}: {exc}. "
            "Falling back to template default."
        )

    return truncate_at_sentence_boundary(_get_fallback_explanation(diagnosed), max_chars=MAX_EXPLANATION_LENGTH)


async def generate_all_explanations(scan_id: str) -> List[DiagnosedViolation]:
    """
    Coordinates explanation generation across all diagnosed violations in a scan:
    - Loads diagnosed violations from state.py
    - Concurrently processes violations (semaphore limit 8) using the fast model
    - Enriches each DiagnosedViolation with a 'plain_explanation' field
    - Emits WebSocket progress updates during explanation generation
    - Persists updated list back to state.py

    Args:
        scan_id: Scan job identifier.

    Returns:
        List of enriched DiagnosedViolation instances.
    """
    scan_data = get_scan(scan_id)
    if not scan_data:
        logger.warning(f"Scan {scan_id} not found in state store.")
        return []

    violations_raw = scan_data.get("diagnosed_violations") or scan_data.get("violations", [])
    if not violations_raw:
        logger.info(f"No violations to explain for scan {scan_id}.")
        update_scan(scan_id, violations=[], status="explained")
        return []

    # Ensure all items are DiagnosedViolation instances
    diagnosed_list: List[DiagnosedViolation] = []
    for item in violations_raw:
        if isinstance(item, DiagnosedViolation):
            diagnosed_list.append(item)
        elif isinstance(item, Violation):
            from app.services.diagnosis_service import get_templated_diagnosis
            diagnosed_list.append(get_templated_diagnosis(item))
        elif isinstance(item, dict):
            diagnosed_list.append(DiagnosedViolation(**item))

    total = len(diagnosed_list)
    semaphore = asyncio.Semaphore(8)  # Fast model is inexpensive and supports higher concurrency
    completed = 0
    progress_lock = asyncio.Lock()

    async def _explain_task(item: DiagnosedViolation) -> DiagnosedViolation:
        nonlocal completed
        async with semaphore:
            explanation = await generate_explanation(item)
            item.plain_explanation = explanation

            async with progress_lock:
                completed += 1
                progress_pct = int((completed / total) * 100)
                msg = f"Wrote explanations for {completed}/{total} violations"

                try:
                    from app.routers.websocket import broadcast_progress
                    await broadcast_progress(
                        scan_id=scan_id,
                        stage="explaining",
                        progress=progress_pct,
                        message=msg,
                        data={
                            "explained_count": completed,
                            "total_count": total,
                            "latest_violation_id": item.id,
                        },
                    )
                except Exception as ws_err:
                    logger.debug(f"Progress streaming skipped: {ws_err}")

            return item

    tasks = [_explain_task(v) for v in diagnosed_list]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # Persist updated list to state
    update_scan(
        scan_id=scan_id,
        diagnosed_violations=results,
        violations=results,
        status="explained",
    )

    try:
        from app.routers.websocket import broadcast_progress
        await broadcast_progress(
            scan_id=scan_id,
            stage="explaining",
            progress=100,
            message=f"Plain English explanations generated for all {len(results)} violations.",
            data={"explained_count": len(results)},
        )
    except Exception as ws_err:
        logger.debug(f"Final explanation streaming skipped: {ws_err}")

    logger.info(f"Scan {scan_id}: Explanations generated for {len(results)} violations.")
    return results
