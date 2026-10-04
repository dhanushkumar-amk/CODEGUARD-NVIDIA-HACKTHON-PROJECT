import logging
from pathlib import Path
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.sandbox_client import (
    SandboxAuthenticationError,
    SandboxCreationError,
    SandboxError,
    SandboxQuotaExceededError,
    SandboxTimeoutError,
    run_command,
    sandbox_session,
)
from app.services.sandbox_orchestrator import (
    get_or_create_base_sandbox,
    install_dependencies,
)
from app.state import create_scan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/test-sandbox", tags=["Test Sandbox"])


class PrepareSandboxRequest(BaseModel):
    repo_path: Optional[str] = Field(
        default=None,
        description="Path to local repository. Defaults to sandbox-scripts/demo-app",
    )
    scan_id: Optional[str] = Field(
        default=None,
        description="Optional scan ID for state tracking. Auto-generated if not provided.",
    )



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


@router.post("/prepare")
async def test_sandbox_prepare(request: Optional[PrepareSandboxRequest] = None):
    """
    Test endpoint for Phase 17:
    Takes repo_path (defaulting to demo-app), provisions/reuses base sandbox via
    get_or_create_base_sandbox(), uploads repo, executes install_dependencies(),
    and returns sandbox_id, install result, and elapsed time.
    """
    req = request or PrepareSandboxRequest()
    if req.repo_path and req.repo_path.strip():
        repo_path = req.repo_path.strip()
    else:
        # Default to seeded demo-app from Phase 12
        demo_path = Path(__file__).resolve().parent.parent.parent.parent / "sandbox-scripts" / "demo-app"
        repo_path = str(demo_path)

    scan_id = req.scan_id or create_scan(repo_url="https://github.com/example/demo-app")

    start_time = time.time()
    try:
        sandbox_id = await get_or_create_base_sandbox(repo_path=repo_path, scan_id=scan_id)
        install_res = await install_dependencies(sandbox_id=sandbox_id, repo_path=repo_path, scan_id=scan_id)
        elapsed_time = round(time.time() - start_time, 2)

        return {
            "status": "success" if install_res.exit_code == 0 else "install_failed",
            "sandbox_id": sandbox_id,
            "scan_id": scan_id,
            "repo_path": repo_path,
            "elapsed_time_seconds": elapsed_time,
            "install_result": install_res.model_dump(),
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
        logger.error(f"Unexpected error in /test-sandbox/prepare: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error preparing sandbox: {str(exc)}",
        )

