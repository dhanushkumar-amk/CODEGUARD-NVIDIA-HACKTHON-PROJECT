"""
LLM Client: Interface for Nebius Token Factory and NVIDIA Nemotron Models.
Supports Ultra tier (remediation) and Fast tier (Nemotron-3_5-Lightning for high-speed scanning),
with automatic retries, strict JSON response formatting, and token cost tracking ($0.06/$0.24 per 1M).
"""
import logging
from typing import Any, Dict, List, Optional
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

# In-memory running usage & spend tracker
_running_cost: float = 0.0
_total_input_tokens: int = 0
_total_output_tokens: int = 0
_total_calls: int = 0
_last_call_stats: Dict[str, Any] = {}


def get_total_cost_so_far() -> float:
    """
    Returns the cumulative estimated cost in USD for Nemotron Fast API calls so far.
    """
    global _running_cost
    return round(_running_cost, 6)


def get_token_usage_stats() -> Dict[str, Any]:
    """
    Returns aggregate token usage, call count, and spend metrics.
    """
    return {
        "total_cost_usd": round(_running_cost, 6),
        "total_input_tokens": _total_input_tokens,
        "total_output_tokens": _total_output_tokens,
        "total_tokens": _total_input_tokens + _total_output_tokens,
        "total_calls": _total_calls,
        "last_call": _last_call_stats,
    }


def reset_cost_tracker() -> None:
    """
    Resets the in-memory running cost counters. Primary utility for testing.
    """
    global _running_cost, _total_input_tokens, _total_output_tokens, _total_calls, _last_call_stats
    _running_cost = 0.0
    _total_input_tokens = 0
    _total_output_tokens = 0
    _total_calls = 0
    _last_call_stats = {}


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


def get_client() -> AsyncOpenAI:
    """Return an AsyncOpenAI client configured for Nebius Token Factory."""
    global _client, _cached_key, _cached_base_url

    api_key = settings.NEBIUS_TOKEN_FACTORY_API_KEY
    base_url = settings.NEBIUS_TOKEN_FACTORY_BASE_URL

    if not api_key or not api_key.strip() or api_key == "your_nebius_token_factory_api_key_here":
        raise LLMAuthenticationError(
            "NEBIUS_TOKEN_FACTORY_API_KEY is not configured. "
            "Please provide a valid API key in backend/.env"
        )

    if _client is None or _cached_key != api_key or _cached_base_url != base_url:
        _client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        _cached_key = api_key
        _cached_base_url = base_url

    return _client


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
) -> str:
    """
    Call the fast-tier Nemotron model (NEMOTRON_FAST_MODEL_ID, defaulting to nvidia/Nemotron-3_5-Lightning)
    specifically tuned for high-speed, cost-effective accessibility violation scanning.

    Args:
        prompt: The user code snippet or scanning query
        system_prompt: Optional system instructions guiding accessibility evaluation
        max_tokens: Token generation limit (default 800)
        response_format: 'text' or 'json' (enforces structured JSON object return)

    Returns:
        Generated text or JSON response content

    Features:
        - Automatically passes response_format={'type': 'json_object'} when requested
        - Falls back gracefully to prompt-based JSON if strict format is rejected
        - Computes and logs exact token counts and costs ($0.06 / $0.24 per 1M)
        - Updates running total spend tracker
    """
    global _running_cost, _total_input_tokens, _total_output_tokens, _total_calls, _last_call_stats

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

        _running_cost += call_cost
        _total_input_tokens += input_tokens
        _total_output_tokens += output_tokens
        _total_calls += 1

        _last_call_stats = {
            "model_id": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "call_cost_usd": round(call_cost, 6),
            "cumulative_cost_usd": round(_running_cost, 6),
        }

        logger.info(
            f"[Nemotron Fast] {model_id} | In: {input_tokens} tok | Out: {output_tokens} tok | "
            f"Cost: ${call_cost:.6f} | Total spend: ${_running_cost:.6f}"
        )

        if not response.choices:
            return ""
        return response.choices[0].message.content or ""

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
