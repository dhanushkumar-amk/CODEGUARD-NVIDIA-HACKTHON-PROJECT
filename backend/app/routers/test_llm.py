"""
Test LLM Router: Smoke tests for NVIDIA Nemotron models on Nebius Token Factory.
Exposes endpoints to test Ultra (reasoning & remediation), Fast (Nemotron-3_5-Lightning),
escalation fallbacks, and runtime cost tracking.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from app.config import settings
from app.services.llm_client import (
    call_nemotron,
    call_nemotron_fast,
    call_nemotron_ultra,
    call_with_escalation,
    get_total_cost_so_far,
    get_cost_breakdown,
    get_token_usage_stats,
    get_scan_usage_stats,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMAPIError,
    LLMClientError,
    UltraBudgetExceededError,
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
    Returns running cost breakdown across fast and ultra tiers, plus cumulative token stats.
    """
    breakdown = get_cost_breakdown()
    stats = get_token_usage_stats()
    return {
        "status": "success",
        "fast_cost": breakdown["fast_cost"],
        "ultra_cost": breakdown["ultra_cost"],
        "total": breakdown["total"],
        "total_cost_so_far": breakdown["total"],
        "stats": stats,
    }


@router.get("/ultra")
async def test_nemotron_ultra(
    prompt: str = Query(
        default="Explain why this button is inaccessible to keyboard users: <div onClick={go}>Submit</div>",
        description="Accessibility reasoning prompt for the Ultra tier",
    ),
    scan_id: Optional[str] = Query(
        default=None,
        description="Optional scan ID for tracking budget and usage",
    ),
):
    """
    Test endpoint for Nemotron Ultra deep reasoning on Nebius Token Factory.
    Sends a reasoning prompt and returns the generated remediation analysis along with token usage and cost.
    """
    try:
        response = await call_nemotron_ultra(
            prompt=prompt,
            system_prompt="You are an expert accessibility engineer providing deep reasoning on WCAG 2.2 AA violations.",
            scan_id=scan_id,
        )
        usage_stats = get_token_usage_stats()
        breakdown = get_cost_breakdown()
        last_call = usage_stats.get("last_call", {})
        return {
            "status": "success",
            "model_id": getattr(settings, "NEMOTRON_ULTRA_MODEL_ID", "nvidia/Nemotron-3-Ultra-550b-a55b"),
            "prompt": prompt,
            "response": response,
            "token_usage": last_call,
            "cost": last_call.get("call_cost_usd", 0.0),
            "usage": last_call,
            "fast_cost": breakdown["fast_cost"],
            "ultra_cost": breakdown["ultra_cost"],
            "total_cost": breakdown["total"],
        }
    except UltraBudgetExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
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


@router.get("/escalation")
async def test_nemotron_escalation(
    prompt: str = Query(
        default="Explain why this button is inaccessible to keyboard users: <div onClick={go}>Submit</div>",
        description="Prompt to evaluate through the tiered escalation flow",
    ),
    scan_id: Optional[str] = Query(
        default="test-escalation-scan",
        description="Scan ID for per-scan budget tracking",
    ),
):
    """
    Test endpoint for tiered model escalation.
    Runs call_with_escalation with a quality_check that deliberately fails on the first pass,
    proving the Fast-to-Ultra fallback and retry mechanism works reliably.
    """
    first_call_evaluated = False

    def deliberate_failure_check(output: str) -> bool:
        nonlocal first_call_evaluated
        if not first_call_evaluated:
            first_call_evaluated = True
            # Deliberately fail first pass to force escalation to Ultra
            return False
        return True

    try:
        response = await call_with_escalation(
            prompt=prompt,
            system_prompt="You are an expert accessibility engineer providing WCAG 2.2 analysis.",
            scan_id=scan_id,
            quality_check=deliberate_failure_check,
        )
        breakdown = get_cost_breakdown()
        usage_stats = get_token_usage_stats()
        return {
            "status": "success",
            "message": "Tiered escalation triggered from Fast to Ultra successfully",
            "escalation_attempted": first_call_evaluated,
            "prompt": prompt,
            "response": response,
            "fast_cost": breakdown["fast_cost"],
            "ultra_cost": breakdown["ultra_cost"],
            "total_cost": breakdown["total"],
            "last_call": usage_stats.get("last_call", {}),
            "scan_usage": get_scan_usage_stats(scan_id) if scan_id else {},
        }
    except UltraBudgetExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
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
