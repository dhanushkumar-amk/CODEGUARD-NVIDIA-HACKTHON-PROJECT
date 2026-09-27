from fastapi import APIRouter, HTTPException, status
from app.config import settings
from app.services.llm_client import (
    call_nemotron,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMAPIError,
    LLMClientError,
)

router = APIRouter(prefix="/test-llm", tags=["Test LLM"])


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
