"""
Grounding Service: Tavily-powered WCAG accessibility technique retrieval.
Performs domain-restricted web searches on trusted accessibility authorities
(w3.org, MDN, WebAIM, Deque, A11Y Project), caches results per category for the process
lifetime, and enriches Nemotron diagnosis and fix prompts with live grounded guidance.
"""
import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Sequence, Union

from app.config import settings
from app.models.schemas import (
    GroundingSource,
    GuidanceBundle,
    ViolationCategory,
)

logger = logging.getLogger(__name__)

# Trusted accessibility documentation domains
TRUSTED_DOMAINS: List[str] = [
    "w3.org",
    "developer.mozilla.org",
    "webaim.org",
    "dequeuniversity.com",
    "a11yproject.com",
]

# Process-lifetime in-memory cache per category
_CATEGORY_CACHE: Dict[str, Optional[GuidanceBundle]] = {}

# Per-scan search count tracking
_SCAN_SEARCH_COUNTS: Dict[str, int] = {}
_SCAN_SOURCES_USED: Dict[str, int] = {}

# Category-specific search descriptors for focused query construction
CATEGORY_QUERY_DESCRIPTIONS: Dict[Union[ViolationCategory, str], str] = {
    ViolationCategory.MISSING_ALT_TEXT: "image missing alt text alternative text decorative and informative images",
    ViolationCategory.UNLABELED_FORM_FIELD: "form input missing label aria-label htmlFor programmatic label",
    ViolationCategory.NON_INTERACTIVE_CLICK: "div span onClick button role keyboard accessibility enter space key listener",
    ViolationCategory.EMPTY_LINK_OR_BUTTON: "empty button link accessible name aria-label icon button text equivalent",
    ViolationCategory.LOW_CONTRAST: "color contrast minimum 4.5 to 1 ratio WCAG AA text background",
    ViolationCategory.HEADING_ORDER: "heading hierarchy skipped levels h1 h2 h3 sequential structure document outline",
    ViolationCategory.MISSING_LANDMARK: "landmark elements header main nav footer aside semantic HTML",
    ViolationCategory.KEYBOARD_TRAP: "keyboard trap focus management modal dialog escape focus trap loop",
    ViolationCategory.MISSING_LANG: "html lang attribute language of page BCP 47 code",
    ViolationCategory.ARIA_MISUSE: "ARIA roles states properties invalid usage first rule of ARIA semantic HTML",
    ViolationCategory.FOCUS_MANAGEMENT: "focus order positive tabindex visible focus indicator program focus",
    ViolationCategory.OTHER: "common accessibility defect remediation techniques WCAG 2.2",
}


def _normalize_category_key(category: Union[ViolationCategory, str]) -> str:
    """Normalizes category enum or string to a canonical string key."""
    if isinstance(category, ViolationCategory):
        return category.value
    return str(category).upper()


def get_scan_search_count(scan_id: Optional[str] = None) -> int:
    """Returns number of Tavily searches performed for a given scan (or overall)."""
    if scan_id and scan_id in _SCAN_SEARCH_COUNTS:
        return _SCAN_SEARCH_COUNTS[scan_id]
    return sum(_SCAN_SEARCH_COUNTS.values())


def get_scan_sources_count(scan_id: Optional[str] = None) -> int:
    """Returns number of grounding sources used in a given scan (or overall)."""
    if scan_id and scan_id in _SCAN_SOURCES_USED:
        return _SCAN_SOURCES_USED[scan_id]
    return sum(_SCAN_SOURCES_USED.values())


def record_sources_used(scan_id: Optional[str], count: int) -> None:
    """Tracks sources utilized during prompt synthesis for a scan."""
    if not scan_id:
        return
    _SCAN_SOURCES_USED[scan_id] = _SCAN_SOURCES_USED.get(scan_id, 0) + count


def reset_cache_for_testing() -> None:
    """Clears the process-lifetime cache and counters (used in unit test suites)."""
    _CATEGORY_CACHE.clear()
    _SCAN_SEARCH_COUNTS.clear()
    _SCAN_SOURCES_USED.clear()


async def get_guidance(
    category: Union[ViolationCategory, str],
    wcag_criterion: Optional[str] = None,
    scan_id: Optional[str] = None,
) -> Optional[GuidanceBundle]:
    """
    Retrieves current WCAG guidance for a given violation category:
    - Checks in-memory process cache first.
    - If un-cached, executes a focused search using Tavily restricted to trusted domains.
    - Respects TAVILY_MAX_SEARCHES_PER_SCAN and TAVILY_ENABLED.
    - On any error, timeout, or missing key, logs warning and returns None.

    Args:
        category: Violation category enum or string.
        wcag_criterion: Optional WCAG Success Criterion (e.g. '1.1.1 Non-text Content').
        scan_id: Optional scan job ID for per-scan search limits and metrics.

    Returns:
        GuidanceBundle instance or None.
    """
    cat_key = _normalize_category_key(category)

    # 1. Check process-lifetime cache first
    if cat_key in _CATEGORY_CACHE:
        cached = _CATEGORY_CACHE[cat_key]
        logger.debug(f"[Tavily Cache Hit] Returning cached guidance for category '{cat_key}'")
        return cached

    # 2. Check enabled flag
    if not getattr(settings, "TAVILY_ENABLED", True):
        logger.debug("Tavily grounding is disabled via configuration (TAVILY_ENABLED=false).")
        return None

    # 3. Check API key
    api_key = getattr(settings, "TAVILY_API_KEY", "") or ""
    if not api_key.strip():
        logger.warning("Tavily API key is not configured; continuing without grounding.")
        return None

    # 4. Check per-scan search budget limit
    max_searches = getattr(settings, "TAVILY_MAX_SEARCHES_PER_SCAN", 12)
    current_searches = _SCAN_SEARCH_COUNTS.get(scan_id, 0) if scan_id else 0
    if current_searches >= max_searches:
        logger.warning(
            f"Tavily search cap reached for scan {scan_id} ({current_searches}/{max_searches} searches). "
            f"Continuing without grounding for category '{cat_key}'."
        )
        return None

    # 5. Build focused query
    cat_desc = CATEGORY_QUERY_DESCRIPTIONS.get(
        category if isinstance(category, ViolationCategory) else getattr(ViolationCategory, cat_key, ViolationCategory.OTHER),
        "accessibility defect remediation",
    )
    if wcag_criterion and wcag_criterion.strip():
        query = f"WCAG technique fix {cat_desc} {wcag_criterion.strip()} accessible markup example"
    else:
        query = f"WCAG technique fix {cat_desc} accessible markup example"

    # 6. Execute search with Tavily
    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=api_key.strip())
        logger.info(f"Querying Tavily for WCAG guidance: '{query[:80]}...' (category={cat_key})")

        response = await asyncio.wait_for(
            client.search(
                query=query,
                include_domains=TRUSTED_DOMAINS,
                include_domains_mode="restrict",
                max_results=3,
            ),
            timeout=10.0,
        )

        if scan_id:
            _SCAN_SEARCH_COUNTS[scan_id] = _SCAN_SEARCH_COUNTS.get(scan_id, 0) + 1

        raw_results = response.get("results", []) if isinstance(response, dict) else []
        sources: List[GroundingSource] = []

        for item in raw_results[:3]:
            title = str(item.get("title", "")).strip() or "WCAG Guidance"
            url = str(item.get("url", "")).strip()
            content = str(item.get("content", "")).strip()
            # Trim snippet to protect token budget
            snippet = content[:300] if len(content) > 300 else content

            if url:
                sources.append(
                    GroundingSource(
                        title=title,
                        url=url,
                        snippet=snippet,
                    )
                )

        cat_enum = category if isinstance(category, ViolationCategory) else getattr(ViolationCategory, cat_key, ViolationCategory.OTHER)
        bundle = GuidanceBundle(
            category=cat_enum,
            sources=sources,
            retrieved_at=datetime.now(timezone.utc),
        )

        # Cache for process lifetime
        _CATEGORY_CACHE[cat_key] = bundle
        logger.info(f"Tavily retrieved {len(sources)} sources for '{cat_key}'. Cached successfully.")
        return bundle

    except asyncio.TimeoutError:
        logger.warning(f"Tavily search timed out for query '{query[:60]}...'. Continuing without grounding.")
        return None
    except Exception as exc:
        logger.warning(f"Tavily search failed for category '{cat_key}': {exc}. Continuing without grounding.")
        return None


async def warm_guidance_cache(
    categories: Sequence[Union[ViolationCategory, str]],
    wcag_map: Optional[Dict[str, str]] = None,
    scan_id: Optional[str] = None,
) -> Dict[str, Optional[GuidanceBundle]]:
    """
    Warms the process cache for all distinct categories found in a scan, concurrently.
    Used at the start of the diagnosing stage.
    """
    if not categories:
        return {}

    distinct_keys: List[str] = list(dict.fromkeys([_normalize_category_key(c) for c in categories]))
    logger.info(f"Warming Tavily WCAG guidance cache for {len(distinct_keys)} distinct categories: {distinct_keys}")

    tasks = []
    for key in distinct_keys:
        cat_enum = getattr(ViolationCategory, key, ViolationCategory.OTHER)
        criterion = wcag_map.get(key) if wcag_map else None
        tasks.append(get_guidance(cat_enum, wcag_criterion=criterion, scan_id=scan_id))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    bundle_map: Dict[str, Optional[GuidanceBundle]] = {}

    for key, res in zip(distinct_keys, results):
        if isinstance(res, GuidanceBundle):
            bundle_map[key] = res
        else:
            bundle_map[key] = None

    return bundle_map


def format_guidance_for_prompt(guidance: Optional[GuidanceBundle], max_chars: int = 1000) -> str:
    """
    Formats retrieved WCAG guidance into a concise prompt block with titles and excerpts,
    trimmed to a fixed max length to protect token cost.
    Instructs the model to prefer this guidance over its own memory when they conflict.
    """
    if not guidance or not guidance.sources:
        return ""

    lines = [
        "REFERENCE WCAG GUIDANCE (OFFICIAL TRUSTED SOURCES):",
        "NOTE: Prefer this retrieved guidance over your internal training memory if they conflict.",
    ]
    char_count = 0
    for idx, src in enumerate(guidance.sources, start=1):
        snippet = (src.snippet or "").strip().replace("\n", " ")
        if len(snippet) > 240:
            snippet = snippet[:237] + "..."
        entry = f"[{idx}] {src.title} ({src.url})\n    Guideline: {snippet}"
        if char_count + len(entry) > max_chars:
            break
        lines.append(entry)
        char_count += len(entry)

    lines.append("")
    return "\n".join(lines)
