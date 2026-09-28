"""
LLM Client: Interface for Nebius Token Factory and NVIDIA Nemotron Models.
Supports Ultra tier (remediation & deep reasoning) and Fast tier (Nemotron-3_5-Lightning for high-speed scanning),
with automatic retries, strict JSON response formatting, cost guardrails, and token cost tracking.
"""
import asyncio
import inspect
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Union
from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger(__name__)

# Model and Pricing Constants
NEMOTRON_FAST_DEFAULT_MODEL = "nvidia/Nemotron-3_5-Lightning"
FAST_INPUT_COST_PER_1M = 0.06   # $0.06 per 1M input tokens
FAST_OUTPUT_COST_PER_1M = 0.24  # $0.24 per 1M output tokens

NEMOTRON_ULTRA_DEFAULT_MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"
ULTRA_INPUT_COST_PER_1M = 1.00   # $1.00 per 1M input tokens
ULTRA_OUTPUT_COST_PER_1M = 3.00  # $3.00 per 1M output tokens

# In-memory running usage & spend tracker
_running_fast_cost: float = 0.0
_running_ultra_cost: float = 0.0
_running_cost: float = 0.0
_total_input_tokens: int = 0
_total_output_tokens: int = 0
_fast_input_tokens: int = 0
_fast_output_tokens: int = 0
_ultra_input_tokens: int = 0
_ultra_output_tokens: int = 0
_total_calls: int = 0
_fast_calls: int = 0
_ultra_calls: int = 0
_last_call_stats: Dict[str, Any] = {}

# Per-scan in-memory tracker: scan_id -> dict
_scan_usage: Dict[str, Dict[str, Any]] = {}


def extract_json_payload(content: str) -> str:
    """
    Extracts clean JSON object if surrounded by markdown code blocks or reasoning text.
    """
    if not content:
        return ""
    # Strip leading thinking process monologue if present
    cleaned = re.sub(r"^Here's a thinking process:[\s\S]*?(?=\{\s*\"|\`\`\`json)", "", content, flags=re.IGNORECASE)
    # Check for markdown code fences ```json { ... } ```
    match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", cleaned)
    if match:
        return match.group(1).strip()
    # Check for direct JSON object { ... }
    match = re.search(r"(\{[\s\S]*\})", cleaned)
    if match:
        return match.group(1).strip()
    return content.strip()


def get_total_cost_so_far() -> float:
    """
    Returns the cumulative estimated cost in USD across all Nemotron API calls so far.
    """
    global _running_fast_cost, _running_ultra_cost
    return round(_running_fast_cost + _running_ultra_cost, 6)


def get_cost_breakdown() -> Dict[str, float]:
    """
    Returns fast, ultra, and total costs in USD.
    """
    global _running_fast_cost, _running_ultra_cost
    total = _running_fast_cost + _running_ultra_cost
    return {
        "fast_cost": round(_running_fast_cost, 6),
        "ultra_cost": round(_running_ultra_cost, 6),
        "total": round(total, 6),
    }


def get_token_usage_stats() -> Dict[str, Any]:
    """
    Returns aggregate token usage, call count, and spend metrics.
    """
    breakdown = get_cost_breakdown()
    return {
        "total_cost_usd": breakdown["total"],
        "fast_cost_usd": breakdown["fast_cost"],
        "ultra_cost_usd": breakdown["ultra_cost"],
        "total_input_tokens": _total_input_tokens,
        "total_output_tokens": _total_output_tokens,
        "fast_input_tokens": _fast_input_tokens,
        "fast_output_tokens": _fast_output_tokens,
        "ultra_input_tokens": _ultra_input_tokens,
        "ultra_output_tokens": _ultra_output_tokens,
        "total_tokens": _total_input_tokens + _total_output_tokens,
        "total_calls": _total_calls,
        "fast_calls": _fast_calls,
        "ultra_calls": _ultra_calls,
        "last_call": _last_call_stats,
    }


def get_scan_usage_stats(scan_id: str) -> Dict[str, Any]:
    """
    Returns usage statistics for a specific scan_id.
    """
    return _scan_usage.get(
        scan_id,
        {
            "scan_id": scan_id,
            "fast_calls": 0,
            "ultra_calls": 0,
            "total_calls": 0,
            "fast_cost_usd": 0.0,
            "ultra_cost_usd": 0.0,
            "total_cost_usd": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
        },
    )


def reset_cost_tracker() -> None:
    """
    Resets the in-memory running cost counters and per-scan usage records.
    Primary utility for testing.
    """
    global _running_fast_cost, _running_ultra_cost, _running_cost
    global _total_input_tokens, _total_output_tokens
    global _fast_input_tokens, _fast_output_tokens, _ultra_input_tokens, _ultra_output_tokens
    global _total_calls, _fast_calls, _ultra_calls, _last_call_stats, _scan_usage
    _running_fast_cost = 0.0
    _running_ultra_cost = 0.0
    _running_cost = 0.0
    _total_input_tokens = 0
    _total_output_tokens = 0
    _fast_input_tokens = 0
    _fast_output_tokens = 0
    _ultra_input_tokens = 0
    _ultra_output_tokens = 0
    _total_calls = 0
    _fast_calls = 0
    _ultra_calls = 0
    _last_call_stats = {}
    _scan_usage = {}


class LLMClientError(Exception):
    """Base exception for LLM client operations."""
    pass


class LLMAuthenticationError(LLMClientError):
    """Raised when authentication fails (missing or invalid API key)."""
    pass


class LLMTimeoutError(LLMClientError):
    """Raised when an LLM request times out."""
    pass


class LLMRateLimitError(LLMClientError):
    """Raised when Nebius rate limits are exceeded."""
    pass


class LLMAPIError(LLMClientError):
    """Raised when the LLM API returns an error response."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class UltraBudgetExceededError(LLMClientError):
    """Raised when Ultra model is disabled or per-scan budget / call limits are exceeded."""
    pass


# Transient exceptions suitable for exponential backoff retries
TRANSIENT_EXCEPTIONS = (
    APITimeoutError,
    RateLimitError,
    APIConnectionError,
    InternalServerError,
)

_client: Optional[AsyncOpenAI] = None
_cached_key: Optional[str] = None
_cached_base_url: Optional[str] = None
_cached_loop: Any = None


def get_client() -> AsyncOpenAI:
    """Return an AsyncOpenAI client configured for Nebius Token Factory."""
    global _client, _cached_key, _cached_base_url, _cached_loop

    api_key = settings.NEBIUS_TOKEN_FACTORY_API_KEY
    base_url = settings.NEBIUS_TOKEN_FACTORY_BASE_URL

    if not api_key or not api_key.strip() or api_key == "your_nebius_token_factory_api_key_here":
        raise LLMAuthenticationError(
            "NEBIUS_TOKEN_FACTORY_API_KEY is not configured. "
            "Please provide a valid API key in backend/.env"
        )

    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _client is None or _cached_key != api_key or _cached_base_url != base_url or _cached_loop != current_loop:
        _client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        _cached_key = api_key
        _cached_base_url = base_url
        _cached_loop = current_loop

    return _client


def _record_scan_usage(
    scan_id: str,
    tier: str,
    cost: float,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Internal helper to record usage and spend against a scan_id."""
    if scan_id not in _scan_usage:
        _scan_usage[scan_id] = {
            "scan_id": scan_id,
            "fast_calls": 0,
            "ultra_calls": 0,
            "total_calls": 0,
            "fast_cost_usd": 0.0,
            "ultra_cost_usd": 0.0,
            "total_cost_usd": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
        }
    entry = _scan_usage[scan_id]
    if tier == "ultra":
        entry["ultra_calls"] += 1
        entry["ultra_cost_usd"] = round(entry["ultra_cost_usd"] + cost, 6)
    else:
        entry["fast_calls"] += 1
        entry["fast_cost_usd"] = round(entry["fast_cost_usd"] + cost, 6)
    entry["total_calls"] += 1
    entry["total_cost_usd"] = round(entry["total_cost_usd"] + cost, 6)
    entry["input_tokens"] += input_tokens
    entry["output_tokens"] += output_tokens


@retry(
    retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _execute_chat_completion(
    client: AsyncOpenAI,
    model_id: str,
    messages: List[Dict[str, str]],
    max_tokens: int,
) -> str:
    response = await client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=max_tokens,
    )
    if not response.choices:
        return ""
    return response.choices[0].message.content or ""


@retry(
    retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _execute_chat_completion_with_usage(
    client: AsyncOpenAI,
    **kwargs: Any,
) -> Any:
    """Executes a chat completion call and returns the full response object with usage statistics."""
    return await client.chat.completions.create(**kwargs)


async def call_nemotron(
    model_id: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 1000,
) -> str:
    """
    Call Nebius Token Factory chat completions endpoint with the specified Nemotron model.

    Args:
        model_id: The model ID (e.g., settings.NEMOTRON_ULTRA_MODEL_ID)
        prompt: The user prompt string
        system_prompt: Optional system prompt to steer model behavior
        max_tokens: Maximum tokens to generate (default 1000)

    Returns:
        The model's text response
    """
    client = get_client()

    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        return await _execute_chat_completion(
            client=client,
            model_id=model_id,
            messages=messages,
            max_tokens=max_tokens,
        )
    except AuthenticationError as e:
        raise LLMAuthenticationError(f"Nebius authentication failed: {e.message}") from e
    except APITimeoutError as e:
        raise LLMTimeoutError(f"Nebius request timed out after 3 attempts: {e}") from e
    except RateLimitError as e:
        raise LLMRateLimitError(f"Nebius rate limit exceeded after 3 attempts: {e.message}") from e
    except APIStatusError as e:
        raise LLMAPIError(f"Nebius API error ({e.status_code}): {e.message}", status_code=e.status_code) from e
    except APIError as e:
        raise LLMAPIError(f"Nebius API error: {e.message}") from e
    except (LLMClientError, Exception) as e:
        if isinstance(e, LLMClientError):
            raise
        raise LLMClientError(f"Unexpected error calling Nemotron: {str(e)}") from e


async def call_nemotron_fast(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 800,
    response_format: str = "text",
    scan_id: Optional[str] = None,
) -> str:
    """
    Call the fast-tier Nemotron model (NEMOTRON_FAST_MODEL_ID, defaulting to nvidia/Nemotron-3_5-Lightning)
    specifically tuned for high-speed, cost-effective accessibility violation scanning.

    Args:
        prompt: The user code snippet or scanning query
        system_prompt: Optional system instructions guiding accessibility evaluation
        max_tokens: Token generation limit (default 800)
        response_format: 'text' or 'json' (enforces structured JSON object return)
        scan_id: Optional scan ID to track per-scan usage and spend

    Returns:
        Generated text or JSON response content
    """
    global _running_fast_cost, _running_cost, _total_input_tokens, _total_output_tokens
    global _fast_input_tokens, _fast_output_tokens, _total_calls, _fast_calls, _last_call_stats

    client = get_client()
    model_id = getattr(settings, "NEMOTRON_FAST_MODEL_ID", None) or NEMOTRON_FAST_DEFAULT_MODEL

    messages: List[Dict[str, str]] = []

    # Configure system prompt and ensure JSON instructions if requested
    effective_system = system_prompt
    use_json_mode = response_format.lower() == "json"
    if use_json_mode:
        json_directive = "You must output a valid JSON object only. Do not include markdown fences or preamble."
        effective_system = f"{effective_system}\n{json_directive}" if effective_system else json_directive

    if effective_system:
        messages.append({"role": "system", "content": effective_system})
    messages.append({"role": "user", "content": prompt})

    kwargs: Dict[str, Any] = {
        "model": model_id,
        "messages": messages,
        "max_tokens": max_tokens,
    }

    if use_json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        try:
            response = await _execute_chat_completion_with_usage(client=client, **kwargs)
        except (APIError, APIStatusError) as e:
            # Fall back to prompt instruction if endpoint rejects structured json_object parameter
            if use_json_mode and kwargs.get("response_format"):
                logger.warning(f"Structured response_format rejected ({e}); retrying with prompt-based JSON enforcement.")
                kwargs.pop("response_format", None)
                response = await _execute_chat_completion_with_usage(client=client, **kwargs)
            else:
                raise

        # Extract tokens and calculate cost ($0.06 / 1M prompt, $0.24 / 1M completion)
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "usage") and response.usage:
            input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(response.usage, "completion_tokens", 0) or 0

        call_cost = (input_tokens * FAST_INPUT_COST_PER_1M / 1_000_000.0) + (
            output_tokens * FAST_OUTPUT_COST_PER_1M / 1_000_000.0
        )

        _running_fast_cost += call_cost
        _running_cost = _running_fast_cost + _running_ultra_cost
        _total_input_tokens += input_tokens
        _total_output_tokens += output_tokens
        _fast_input_tokens += input_tokens
        _fast_output_tokens += output_tokens
        _total_calls += 1
        _fast_calls += 1

        _last_call_stats = {
            "model_id": model_id,
            "tier": "fast",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "call_cost_usd": round(call_cost, 6),
            "fast_cost_usd": round(_running_fast_cost, 6),
            "ultra_cost_usd": round(_running_ultra_cost, 6),
            "cumulative_cost_usd": round(_running_cost, 6),
        }

        if scan_id:
            _record_scan_usage(scan_id, "fast", call_cost, input_tokens, output_tokens)

        logger.info(
            f"[Nemotron Fast] {model_id} | In: {input_tokens} tok | Out: {output_tokens} tok | "
            f"Cost: ${call_cost:.6f} | Fast spend: ${_running_fast_cost:.6f} | Total spend: ${_running_cost:.6f}"
        )

        raw_content = response.choices[0].message.content or ""
        if use_json_mode:
            return extract_json_payload(raw_content)
        return raw_content

    except AuthenticationError as e:
        raise LLMAuthenticationError(f"Nebius authentication failed: {e.message}") from e
    except APITimeoutError as e:
        raise LLMTimeoutError(f"Nebius request timed out after 3 attempts: {e}") from e
    except RateLimitError as e:
        raise LLMRateLimitError(f"Nebius rate limit exceeded after 3 attempts: {e.message}") from e
    except APIStatusError as e:
        raise LLMAPIError(f"Nebius API error ({e.status_code}): {e.message}", status_code=e.status_code) from e
    except APIError as e:
        raise LLMAPIError(f"Nebius API error: {e.message}") from e
    except (LLMClientError, Exception) as e:
        if isinstance(e, LLMClientError):
            raise
        raise LLMClientError(f"Unexpected error calling Nemotron: {str(e)}") from e


async def call_nemotron_ultra(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 1500,
    scan_id: Optional[str] = None,
) -> str:
    """
    Call Nemotron Ultra (NEMOTRON_ULTRA_MODEL_ID, defaulting to nvidia/Nemotron-3-Ultra-550b-a55b)
    for deep accessibility reasoning, complex diagnosis, and fix synthesis.
    
    Protected by cost guardrails:
    - Verifies ULTRA_ENABLED is True
    - Enforces per-scan ULTRA_MAX_CALLS_PER_SCAN limit (default: 5)
    - Enforces per-scan ULTRA_BUDGET_USD_PER_SCAN limit (default: $0.05)
    - Uses 90-second timeout to accommodate slower deep reasoning response time
    - Logs exact token counts and costs ($1.00 / 1M input, $3.00 / 1M output)
    - Tracks per-scan and global tier-separated spend
    """
    global _running_ultra_cost, _running_cost, _total_input_tokens, _total_output_tokens
    global _ultra_input_tokens, _ultra_output_tokens, _total_calls, _ultra_calls, _last_call_stats

    # Check 1: ULTRA_ENABLED switch
    if not getattr(settings, "ULTRA_ENABLED", True):
        raise UltraBudgetExceededError("Nemotron Ultra is currently disabled (ULTRA_ENABLED=False).")

    # Check 2 & 3: Per-scan call count and budget limits
    if scan_id:
        scan_record = _scan_usage.get(scan_id, {})
        calls = scan_record.get("ultra_calls", 0)
        cost = scan_record.get("ultra_cost_usd", 0.0)
        max_calls = getattr(settings, "ULTRA_MAX_CALLS_PER_SCAN", 5)
        budget = getattr(settings, "ULTRA_BUDGET_USD_PER_SCAN", 0.05)

        if calls >= max_calls:
            raise UltraBudgetExceededError(
                f"Per-scan Ultra call limit ({max_calls}) reached for scan '{scan_id}' (calls={calls})."
            )
        if cost >= budget:
            raise UltraBudgetExceededError(
                f"Per-scan Ultra budget limit (${budget:.4f}) exceeded for scan '{scan_id}' (spent=${cost:.6f})."
            )

    client = get_client()
    model_id = getattr(settings, "NEMOTRON_ULTRA_MODEL_ID", None) or NEMOTRON_ULTRA_DEFAULT_MODEL

    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = await _execute_chat_completion_with_usage(
            client=client,
            model=model_id,
            messages=messages,
            max_tokens=max_tokens,
            timeout=90.0,
        )

        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "usage") and response.usage:
            input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(response.usage, "completion_tokens", 0) or 0

        call_cost = (input_tokens * ULTRA_INPUT_COST_PER_1M / 1_000_000.0) + (
            output_tokens * ULTRA_OUTPUT_COST_PER_1M / 1_000_000.0
        )

        _running_ultra_cost += call_cost
        _running_cost = _running_fast_cost + _running_ultra_cost
        _total_input_tokens += input_tokens
        _total_output_tokens += output_tokens
        _ultra_input_tokens += input_tokens
        _ultra_output_tokens += output_tokens
        _total_calls += 1
        _ultra_calls += 1

        _last_call_stats = {
            "model_id": model_id,
            "tier": "ultra",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "call_cost_usd": round(call_cost, 6),
            "ultra_cost_usd": round(_running_ultra_cost, 6),
            "fast_cost_usd": round(_running_fast_cost, 6),
            "cumulative_cost_usd": round(_running_cost, 6),
        }

        if scan_id:
            _record_scan_usage(scan_id, "ultra", call_cost, input_tokens, output_tokens)

        logger.info(
            f"[Nemotron Ultra] {model_id} | In: {input_tokens} tok | Out: {output_tokens} tok | "
            f"Cost: ${call_cost:.6f} | Ultra spend: ${_running_ultra_cost:.6f} | Total spend: ${_running_cost:.6f}"
        )

        return response.choices[0].message.content or ""

    except UltraBudgetExceededError:
        raise
    except AuthenticationError as e:
        raise LLMAuthenticationError(f"Nebius authentication failed: {e.message}") from e
    except APITimeoutError as e:
        raise LLMTimeoutError(f"Nebius Ultra request timed out after 3 attempts: {e}") from e
    except RateLimitError as e:
        raise LLMRateLimitError(f"Nebius rate limit exceeded after 3 attempts: {e.message}") from e
    except APIStatusError as e:
        raise LLMAPIError(f"Nebius API error ({e.status_code}): {e.message}", status_code=e.status_code) from e
    except APIError as e:
        raise LLMAPIError(f"Nebius API error: {e.message}") from e
    except (LLMClientError, Exception) as e:
        if isinstance(e, LLMClientError):
            raise
        raise LLMClientError(f"Unexpected error calling Nemotron Ultra: {str(e)}") from e


async def call_with_escalation(
    prompt: str,
    system_prompt: Optional[str] = None,
    scan_id: Optional[str] = None,
    quality_check: Optional[Callable[[str], Union[bool, Any]]] = None,
) -> str:
    """
    Tiered execution pattern:
    1. Tries call_nemotron_fast first.
    2. If quality_check is provided and returns False (e.g., output isn't valid JSON or missing fields),
       retries once with call_nemotron_ultra.
    3. If Ultra is unavailable because of budget or disabled, returns the fast model's result
       and logs a warning instead of crashing.
    """
    fast_result = await call_nemotron_fast(
        prompt=prompt,
        system_prompt=system_prompt,
        scan_id=scan_id,
    )

    if quality_check is None:
        return fast_result

    try:
        passed = quality_check(fast_result)
        if inspect.isawaitable(passed):
            passed = await passed
    except Exception as check_err:
        logger.warning(f"[Quality Check] Evaluation raised exception: {check_err}. Escalating to Ultra.")
        passed = False

    if passed:
        return fast_result

    logger.warning("[Escalation] Fast model output failed quality check. Escalating to Nemotron Ultra...")

    try:
        return await call_nemotron_ultra(
            prompt=prompt,
            system_prompt=system_prompt,
            scan_id=scan_id,
        )
    except UltraBudgetExceededError as e:
        logger.warning(
            f"[Escalation] Nemotron Ultra unavailable due to budget or guardrails ({e}). "
            f"Falling back to fast model result."
        )
        return fast_result
    except Exception as e:
        logger.warning(
            f"[Escalation] Nemotron Ultra invocation failed ({e}). "
            f"Falling back to fast model result."
        )
        return fast_result
