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

logger = logging.getLogger(__name__)

MAX_EXPLANATION_LENGTH = 400


def truncate_at_sentence_boundary(text: str, max_chars: int = MAX_EXPLANATION_LENGTH) -> str:
    """
    Truncates text cleanly at the last sentence boundary within max_chars.
    Falls back to a word boundary if no sentence ending is found.
    """
    if not text or len(text) <= max_chars:
        return text.strip()

    truncated = text[:max_chars]

    # Look for sentence-ending punctuation followed by space, newline, or end of string
    end_indices: List[int] = []
    for match in re.finditer(r"[\.\!\?](?=\s|$)", truncated):
        end_indices.append(match.end())

    if end_indices:
        last_end = max(end_indices)
        # Ensure we don't truncate prematurely if the first sentence was very short
        if last_end >= 60 or last_end == len(truncated):
            return truncated[:last_end].strip()

    # Fallback: truncate at last word boundary
    last_space = truncated.rfind(" ")
    if last_space > 60:
        return truncated[:last_space].strip() + "..."

    return truncated.strip()


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
        return f"""/no_think
You are an accessibility advocate writing an executive report for non-technical stakeholders (product managers, designers, compliance officers).
Rewrite the following technical accessibility diagnosis into a clear, friendly, non-technical summary in 2 to 3 sentences.
Do not use technical jargon or code tags. Explain simply what is wrong, who is impacted, and the recommended solution. Keep your response under 350 characters.

Issue Details:
- Category: {cat_str} ({diagnosed.type})
- Location: {diagnosed.file} (Line {diagnosed.line or 'unknown'})
- Severity: {diagnosed.severity}
- Technical Root Cause: {diagnosed.root_cause}
- User Impact: {diagnosed.user_impact}
- Fix Strategy: {diagnosed.fix_strategy}

Write ONLY the friendly summary paragraph. No preamble or markdown fences:"""

    else:
        # Template-diagnosed violation prompt
        return f"""/no_think
You are an accessibility advocate writing an executive report for non-technical stakeholders.
Write a friendly, 2 to 3 sentence explanation of the following accessibility violation found in {diagnosed.file}.
Explain in plain English what the issue is, why it matters to users with disabilities, and how to fix it. Keep your response under 350 characters.

Issue Details:
- Category: {cat_str}
- Rule: {diagnosed.type}
- Severity: {diagnosed.severity}
- File: {diagnosed.file} (Line {diagnosed.line or 'unknown'})
- Description: {diagnosed.description}
- Snippet: {diagnosed.context_snippet or 'None'}

Write ONLY the friendly summary paragraph. No preamble or markdown fences:"""


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
            system_prompt="You are a concise accessibility writer. Provide only the 2-3 sentence summary requested. Do not include markdown code blocks or quotes.",
            max_tokens=200,
            response_format="text",
        )

        cleaned = raw_text.strip().strip('"').strip("'")
        # Remove any leading conversational fillers
        cleaned = re.sub(r"^(?:Here is|Summary:|Explanation:)\s*", "", cleaned, flags=re.IGNORECASE)

        if cleaned and len(cleaned) >= 20:
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
