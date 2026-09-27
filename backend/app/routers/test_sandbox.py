import logging
from fastapi import APIRouter, HTTPException, status

from app.services.sandbox_client import (
    SandboxAuthenticationError,
    SandboxCreationError,
    SandboxError,
    SandboxQuotaExceededError,
    SandboxTimeoutError,
    run_command,
    sandbox_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/test-sandbox", tags=["Test Sandbox"])


@router.post("/echo")
async def test_sandbox_echo():
    """
    Smoke test: Provisions an isolated Nebius sandbox, runs `echo "sandbox works"`,
    captures stdout/stderr/exit_code, tears down the sandbox, and returns the result.
    """
    try:
        async with sandbox_session() as sandbox:
            cmd = 'echo "sandbox works"'
            cmd_result = await run_command(sandbox.sandbox_id, cmd)

            return {
                "status": "success",
                "sandbox_id": sandbox.sandbox_id,
                "image": sandbox.image,
                "command": cmd,
                "stdout": cmd_result.stdout.strip(),
                "stderr": cmd_result.stderr.strip(),
                "exit_code": cmd_result.exit_code,
                "duration_ms": cmd_result.duration_ms,
            }

    except SandboxAuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )
    except SandboxQuotaExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        )
    except SandboxTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        )
    except (SandboxCreationError, SandboxError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Unexpected error in /test-sandbox/echo: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error executing sandbox test: {str(exc)}",
        )
