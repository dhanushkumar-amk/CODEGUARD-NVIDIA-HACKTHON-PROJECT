"""
Classifier Service: WCAG accessibility violation normalization, taxonomy classification,
severity scoring (1-10), and prioritization ranking (Phase 13).
"""
import re
from typing import Any, Dict, List, Optional, Set

from app.models.schemas import Violation, ViolationCategory


# Exact deterministic rule mapping table for static checks and standard rule IDs
RULE_TYPE_MAP: Dict[str, ViolationCategory] = {
    # Phase 12 static rules
    "image-alt": ViolationCategory.MISSING_ALT_TEXT,
    "image_alt": ViolationCategory.MISSING_ALT_TEXT,
    "label": ViolationCategory.UNLABELED_FORM_FIELD,
    "unlabeled-form-field": ViolationCategory.UNLABELED_FORM_FIELD,
    "unlabeled_form_field": ViolationCategory.UNLABELED_FORM_FIELD,
    "click-events-have-key-events": ViolationCategory.NON_INTERACTIVE_CLICK,
    "click_events_have_key_events": ViolationCategory.NON_INTERACTIVE_CLICK,
    "button-name": ViolationCategory.EMPTY_LINK_OR_BUTTON,
    "button_name": ViolationCategory.EMPTY_LINK_OR_BUTTON,
    "link-name": ViolationCategory.EMPTY_LINK_OR_BUTTON,
    "link_name": ViolationCategory.EMPTY_LINK_OR_BUTTON,
    "link-href": ViolationCategory.EMPTY_LINK_OR_BUTTON,
    "link_href": ViolationCategory.EMPTY_LINK_OR_BUTTON,
    "empty-link-or-button": ViolationCategory.EMPTY_LINK_OR_BUTTON,
    "empty_link_or_button": ViolationCategory.EMPTY_LINK_OR_BUTTON,
    "html-has-lang": ViolationCategory.MISSING_LANG,
    "html_has_lang": ViolationCategory.MISSING_LANG,
    "tabindex": ViolationCategory.FOCUS_MANAGEMENT,

    # Standard axe-core & LLM canonical rule IDs
    "color-contrast": ViolationCategory.LOW_CONTRAST,
    "color_contrast": ViolationCategory.LOW_CONTRAST,
    "heading-order": ViolationCategory.HEADING_ORDER,
    "heading_order": ViolationCategory.HEADING_ORDER,
    "landmark-main-is-top-level": ViolationCategory.MISSING_LANDMARK,
    "landmark-one-main": ViolationCategory.MISSING_LANDMARK,
    "region": ViolationCategory.MISSING_LANDMARK,
    "keyboard-trap": ViolationCategory.KEYBOARD_TRAP,
    "aria-valid-attr": ViolationCategory.ARIA_MISUSE,
    "aria-roles": ViolationCategory.ARIA_MISUSE,
    "aria-allowed-attr": ViolationCategory.ARIA_MISUSE,
    "aria-hidden-focus": ViolationCategory.ARIA_MISUSE,
    "focus-management": ViolationCategory.FOCUS_MANAGEMENT,
    "focus-order": ViolationCategory.FOCUS_MANAGEMENT,
}

# Keyword matching table for free-text LLM types (evaluated in order)
KEYWORD_TAXONOMY_MAP: List[tuple[ViolationCategory, List[str]]] = [
    (ViolationCategory.KEYBOARD_TRAP, ["keyboard-trap", "keyboard trap", "trap"]),
    (ViolationCategory.MISSING_ALT_TEXT, ["image-alt", "missing-alt", "alt text", "alt-text", "alt", "image", "img", "svg-alt"]),
    (ViolationCategory.UNLABELED_FORM_FIELD, ["unlabeled", "form-field", "form field", "input-label", "label", "input", "textarea", "select", "form"]),
    (ViolationCategory.NON_INTERACTIVE_CLICK, ["non-interactive", "click-events", "click-event", "onclick", "click"]),
    (ViolationCategory.EMPTY_LINK_OR_BUTTON, ["empty-button", "empty-link", "button-name", "link-name", "link-href", "button", "link", "href", "anchor"]),
    (ViolationCategory.LOW_CONTRAST, ["contrast", "color-contrast", "color", "luminance"]),
    (ViolationCategory.HEADING_ORDER, ["heading-order", "heading", "h1", "h2", "h3", "h4", "h5", "h6"]),
    (ViolationCategory.MISSING_LANDMARK, ["landmark", "main-landmark", "missing-landmark", "main", "header", "footer", "nav", "aside", "region"]),
    (ViolationCategory.MISSING_LANG, ["html-lang", "missing-lang", "lang", "language"]),
    (ViolationCategory.ARIA_MISUSE, ["aria-hidden", "aria-misuse", "aria-role", "aria-valid", "aria-allowed", "aria", "role"]),
    (ViolationCategory.FOCUS_MANAGEMENT, ["tabindex", "tab-index", "focus-order", "focus-management", "focus"]),
]

# Set of WCAG 2.1/2.2 Level A criteria identifiers
WCAG_LEVEL_A_CRITERIA: Set[str] = {
    "1.1.1", "1.2.1", "1.2.2", "1.2.3", "1.3.1", "1.3.2", "1.3.3",
    "1.4.1", "1.4.2", "2.1.1", "2.1.2", "2.1.4", "2.2.1", "2.2.2",
    "2.3.1", "2.4.1", "2.4.2", "2.4.3", "2.4.4", "2.5.1", "2.5.2",
    "2.5.3", "2.5.4", "3.1.1", "3.2.1", "3.2.2", "3.3.1", "3.3.2",
    "4.1.1", "4.1.2",
}

# Set of WCAG 2.1/2.2 Level AA criteria identifiers
WCAG_LEVEL_AA_CRITERIA: Set[str] = {
    "1.2.4", "1.2.5", "1.3.4", "1.3.5", "1.4.3", "1.4.4", "1.4.5",
    "1.4.10", "1.4.11", "1.4.12", "1.4.13", "2.4.5", "2.4.6", "2.4.7",
    "3.1.2", "3.2.3", "3.2.4", "3.3.3", "3.3.4", "4.1.3",
}


def normalize_category(raw_type: str) -> ViolationCategory:
    """
    Normalizes a raw violation type string into the canonical ViolationCategory taxonomy:
    1. Direct deterministic match against rule-based types.
    2. Case-insensitive keyword matching for LLM free-text responses.
    3. Fallback to OTHER if completely unrecognized (never crashes).

    Args:
        raw_type: Raw violation type from detector or LLM.

    Returns:
        ViolationCategory enum member.
    """
    if not raw_type or not isinstance(raw_type, str):
        return ViolationCategory.OTHER

    cleaned = raw_type.strip().lower()

    # 1. Deterministic direct lookup
    if cleaned in RULE_TYPE_MAP:
        return RULE_TYPE_MAP[cleaned]

    # Normalize dashes/underscores for keyword matching
    normalized_words = cleaned.replace("_", "-").replace(" ", "-")

    # 2. Keyword matching for free-text LLM output
    for category, keywords in KEYWORD_TAXONOMY_MAP:
        for kw in keywords:
            # Word boundary or hyphen-delimited substring match
            pattern = rf"(^|[-_\s]){re.escape(kw)}([-_\s]|$)"
            if re.search(pattern, normalized_words) or kw in normalized_words:
                return category

    # 3. Safe fallback
    return ViolationCategory.OTHER


def _is_interactive_element(violation: Violation) -> bool:
    """
    Determines whether a violation occurs on an interactive element (button, link, form control)
    based on selector, snippet, type, or category.
    """
    interactive_selectors = {"button", "a", "input", "select", "textarea", "form"}

    if violation.selector:
        sel_lower = violation.selector.lower()
        if any(tag in sel_lower for tag in interactive_selectors):
            return True

    snippet = (violation.context_snippet or "").lower()
    if any(tag in snippet for tag in ("<button", "<a ", "<input", "<select", "<textarea", "<form", "onclick", "tabindex")):
        return True

    if violation.category in (
        ViolationCategory.UNLABELED_FORM_FIELD,
        ViolationCategory.EMPTY_LINK_OR_BUTTON,
        ViolationCategory.NON_INTERACTIVE_CLICK,
    ):
        return True

    return False


def _get_wcag_conformance_adjustment(wcag_criterion: Optional[str]) -> int:
    """
    Adjusts score based on WCAG Conformance Level (Level A issues score higher than AA/AAA).
    Level A: +2
    Level AA: +1
    Level AAA: 0
    Unknown / missing: +1 default baseline
    """
    if not wcag_criterion:
        return 1

    crit_str = wcag_criterion.strip()

    # Explicit text matches
    if "level aaa" in crit_str.lower():
        return 0
    if "level aa" in crit_str.lower():
        return 1
    if "level a" in crit_str.lower():
        return 2

    # Match numeric criterion (e.g. '1.1.1', '2.4.3', etc.)
    num_match = re.search(r"\b(\d+\.\d+\.\d+)\b", crit_str)
    if num_match:
        criterion_id = num_match.group(1)
        if criterion_id in WCAG_LEVEL_A_CRITERIA:
            return 2
        if criterion_id in WCAG_LEVEL_AA_CRITERIA:
            return 1
        return 0

    return 1


def calculate_severity_score(violation: Violation) -> int:
    """
    Calculates a normalized 1-10 severity score for an accessibility violation based on:
    - Category baseline (functional significance)
    - Decorative vs critical contextual checks (e.g. alt="" intentional decorative vs missing entirely)
    - Conformance level adjustment (Level A > Level AA > Level AAA)
    - Interactive element boost (+1 for buttons, inputs, links vs static text)

    Args:
        violation: Violation object.

    Returns:
        Integer score between 1 and 10.
    """
    category = violation.category
    snippet = violation.context_snippet or ""
    desc = (violation.description or "").lower()

    # 1. Base score per category
    if category == ViolationCategory.KEYBOARD_TRAP:
        base_score = 8
    elif category == ViolationCategory.NON_INTERACTIVE_CLICK:
        base_score = 7
    elif category == ViolationCategory.UNLABELED_FORM_FIELD:
        base_score = 7
    elif category == ViolationCategory.MISSING_ALT_TEXT:
        # Check if alt="" was intentional decorative or missing entirely
        is_decorative = bool(
            re.search(r'\balt\s*=\s*["\']\s*["\']', snippet)
            or re.search(r'\brole\s*=\s*["\'](?:presentation|none)["\']', snippet, re.IGNORECASE)
            or "decorative image" in desc
            or "marked decorative" in desc
            or "explicitly decorative" in desc
        )
        if is_decorative:
            base_score = 2
        elif _is_interactive_element(violation):
            base_score = 7
        else:
            base_score = 6
    elif category == ViolationCategory.EMPTY_LINK_OR_BUTTON:
        base_score = 6
    elif category == ViolationCategory.LOW_CONTRAST:
        base_score = 5
    elif category == ViolationCategory.FOCUS_MANAGEMENT:
        base_score = 6
    elif category == ViolationCategory.MISSING_LANG:
        base_score = 5
    elif category == ViolationCategory.ARIA_MISUSE:
        base_score = 5
    elif category == ViolationCategory.HEADING_ORDER:
        base_score = 4
    elif category == ViolationCategory.MISSING_LANDMARK:
        base_score = 4
    else:  # OTHER
        base_score = 3

    # 2. Adjust based on WCAG conformance level (Level A > Level AA > Level AAA)
    wcag_adjustment = _get_wcag_conformance_adjustment(violation.wcag_criterion)

    # 3. Boost score slightly for violations on interactive elements vs static content
    interactive_boost = 1 if _is_interactive_element(violation) else 0

    total_score = base_score + wcag_adjustment + interactive_boost

    # Clamp strictly to range 1-10
    return max(1, min(10, total_score))


def map_score_to_severity_label(score: int) -> str:
    """
    Maps a 1-10 numeric severity score to a canonical severity label:
    8-10 -> "critical"
    5-7  -> "high"
    3-4  -> "medium"
    1-2  -> "low"

    Args:
        score: Severity score (1-10).

    Returns:
        String severity label ("critical", "high", "medium", "low").
    """
    if score >= 8:
        return "critical"
    elif score >= 5:
        return "high"
    elif score >= 3:
        return "medium"
    else:
        return "low"


def classify_violations(violations: List[Violation]) -> List[Violation]:
    """
    Applies normalization, severity scoring, and prioritization ranking across all violations:
    1. Normalizes raw type into canonical ViolationCategory.
    2. Calculates a 1-10 severity score (the source of truth).
    3. Maps the severity score to a display label ("critical", "high", "medium", "low").
    4. Sorts violations by severity_score descending (stable sort).
    5. Assigns priority_rank (1 = highest priority).

    Args:
        violations: List of raw or deduplicated Violation objects.

    Returns:
        List of classified, scored, and prioritized Violation objects.
    """
    for v in violations:
        # Determine category (fallback to inspecting description if type is generic or OTHER)
        category = normalize_category(v.type)
        if category == ViolationCategory.OTHER and v.description:
            category_from_desc = normalize_category(v.description)
            if category_from_desc != ViolationCategory.OTHER:
                category = category_from_desc

        v.category = category
        score = calculate_severity_score(v)
        v.severity_score = score
        v.severity = map_score_to_severity_label(score)

    # Sort descending by severity_score (priority 1 = highest severity score)
    sorted_violations = sorted(violations, key=lambda v: (v.severity_score or 0), reverse=True)

    # Assign priority_rank (1-based index)
    for rank, v in enumerate(sorted_violations, start=1):
        v.priority_rank = rank

    return sorted_violations


def summarize_violations(violations: List[Violation]) -> Dict[str, Any]:
    """
    Generates summary statistics for a collection of violations:
    - Counts per category
    - Counts per severity label (critical, high, medium, low)
    - Total count

    Args:
        violations: List of classified Violation objects.

    Returns:
        Dictionary summary overview.
    """
    by_category: Dict[str, int] = {cat.value: 0 for cat in ViolationCategory}
    by_severity: Dict[str, int] = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    for v in violations:
        cat_key = v.category.value if isinstance(v.category, ViolationCategory) else str(v.category)
        if cat_key in by_category:
            by_category[cat_key] += 1
        else:
            by_category["OTHER"] += 1

        sev_label = (v.severity or "high").lower()
        if sev_label in by_severity:
            by_severity[sev_label] += 1
        elif sev_label == "serious":
            by_severity["high"] += 1
        elif sev_label == "moderate":
            by_severity["medium"] += 1
        elif sev_label == "minor":
            by_severity["low"] += 1
        else:
            by_severity["medium"] += 1

    return {
        "total": len(violations),
        "by_category": by_category,
        "by_severity": by_severity,
    }
