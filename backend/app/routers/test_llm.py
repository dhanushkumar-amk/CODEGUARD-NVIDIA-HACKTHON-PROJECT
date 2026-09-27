"""
Test LLM Router: Smoke tests for NVIDIA Nemotron models on Nebius Token Factory.
Exposes endpoints to test Ultra, Nano, and Fast (Nemotron-3_5-Lightning) tiers and query runtime spend.
"""
from fastapi import APIRouter, HTTPException, Query, status
from app.config import settings
from app.services.llm_client import (
    call_nemotron,
    call_nemotron_fast,
    get_total_cost_so_far,
    get_token_usage_stats,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMAPIError,
    LLMClientError,
)

router = APIRouter(prefix="/test-llm", tags=["Test LLM"])


@router.get("/fast")
async def test_nemotron_fast(
    prompt: str = Query(
        default="Does this JSX have an accessibility issue: <img src='logo.png' />",
        description="Accessibility check prompt for the fast tier",
    ),
    response_format: str = Query(
        default="text",
        description="Response format ('text' or 'json')",
    ),
):
    """
    Test endpoint for Nemotron Fast (Nemotron-3_5-Lightning) on Nebius Token Factory.
    Evaluates sample JSX snippet for accessibility violations and returns response with usage metrics.
    """
    try:
        response = await call_nemotron_fast(
            prompt=prompt,
            system_prompt="You are an expert web accessibility auditor focusing on WCAG 2.2 standards.",
            response_format=response_format,
        )
        usage_stats = get_token_usage_stats()
        return {
            "status": "success",
            "model_id": getattr(settings, "NEMOTRON_FAST_MODEL_ID", "nvidia/Nemotron-3_5-Lightning"),
            "prompt": prompt,
            "response": response,
            "usage": usage_stats.get("last_call", {}),
            "total_cost_so_far": get_total_cost_so_far(),
        }
    except LLMAuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except LLMRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except LLMTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e),
        )
    except (LLMAPIError, LLMClientError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.get("/cost")
async def get_cost():
    """
    Returns the cumulative running cost and token counts for Nemotron Fast calls so far.
    """
    stats = get_token_usage_stats()
    return {
        "status": "success",
        "total_cost_so_far": get_total_cost_so_far(),
        "stats": stats,
    }


@router.get("/ultra")
async def test_nemotron_ultra():
    """
    Test endpoint for Nemotron Ultra on Nebius Token Factory.
    """
    prompt = "Say hello and confirm you are Nemotron Ultra running on Nebius Token Factory"
    try:
        response = await call_nemotron(
            model_id=settings.NEMOTRON_ULTRA_MODEL_ID,
            prompt=prompt,
        )
        return {
            "status": "success",
            "model_id": settings.NEMOTRON_ULTRA_MODEL_ID,
            "prompt": prompt,
            "response": response,
        }
    except LLMAuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except LLMRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except LLMTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e),
        )
    except (LLMAPIError, LLMClientError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.get("/nano")
async def test_nemotron_nano():
    """
    Test endpoint for Nemotron Nano on Nebius Token Factory.
    """
    prompt = "Say hello and confirm you are Nemotron Nano running on Nebius Token Factory"
    try:
        response = await call_nemotron(
            model_id=settings.NEMOTRON_NANO_MODEL_ID,
            prompt=prompt,
        )
        return {
            "status": "success",
            "model_id": settings.NEMOTRON_NANO_MODEL_ID,
            "prompt": prompt,
            "response": response,
        }
    except LLMAuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except LLMRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except LLMTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e),
        )
    except (LLMAPIError, LLMClientError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
