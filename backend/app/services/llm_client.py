import logging
from typing import Dict, List, Optional
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

    Raises:
        LLMAuthenticationError: If the API key is not configured or is rejected
        LLMTimeoutError: If the request times out after 3 attempts
        LLMRateLimitError: If rate limit is hit and persists after retries
        LLMAPIError: If the API returns a status or bad request error
        LLMClientError: For any unexpected errors
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
    except Exception as e:
        raise LLMClientError(f"Unexpected error calling Nemotron: {str(e)}") from e
