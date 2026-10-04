import logging
from pathlib import Path
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.models.schemas import ProposedFix
from app.services.fix_applier_service import (
    apply_and_prepare_fix,
    read_file_from_sandbox,
)
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


class ApplyFixTestRequest(BaseModel):
    repo_path: Optional[str] = Field(
        default=None,
        description="Path to local repository clone. Defaults to sandbox-scripts/demo-app",
    )
    fix: Optional[ProposedFix] = Field(
        default=None,
        description="Optional ProposedFix to apply. Defaults to the planted missing alt text bug in Header.tsx",
    )
    scan_id: Optional[str] = Field(
        default=None,
        description="Optional scan ID for tracking. Auto-generated if omitted.",
    )


@router.post("/apply-fix")
async def test_sandbox_apply_fix(request: Optional[ApplyFixTestRequest] = None):
    """
    Test endpoint for Phase 18:
    Takes repo_path and a ProposedFix (or defaults to the planted missing alt-text bug
    in Header.tsx), calls apply_and_prepare_fix(), and reads the file back from the
    sandbox via read_file_from_sandbox() to confirm the fix is present.
    """
    req = request or ApplyFixTestRequest()

    if req.repo_path and req.repo_path.strip():
        repo_path = req.repo_path.strip()
    else:
        demo_path = Path(__file__).resolve().parent.parent.parent.parent / "sandbox-scripts" / "demo-app"
        repo_path = str(demo_path)

    scan_id = req.scan_id or create_scan(repo_url="https://github.com/example/demo-app")

    # Default to the real planted missing alt-text bug from demo-app (Header.tsx:21)
    fix = req.fix or ProposedFix(
        fix_id="fix_planted_alt_text_01",
        violation_id="viol_planted_01",
        file="src/components/Header.tsx",
        line_start=21,
        line_end=21,
        original_lines='<img src="/company-logo.svg" className="h-8" />',
        fixed_lines='<img src="/company-logo.svg" alt="Company Logo" className="h-8" />',
        diff="""@@ -21,1 +21,1 @@
-<img src="/company-logo.svg" className="h-8" />
+<img src="/company-logo.svg" alt="Company Logo" className="h-8" />""",
        explanation_of_change="Added descriptive alt attribute 'Company Logo' to satisfy WCAG 1.1.1 Non-text Content.",
        confidence="high",
    )

    try:
        # 1. Ensure clean base sandbox is provisioned
        base_sandbox_id = await get_or_create_base_sandbox(repo_path=repo_path, scan_id=scan_id)

        # 2. Branch off base sandbox, apply fix, and prepare verification container
        prep_res = await apply_and_prepare_fix(
            fix=fix,
            repo_path=repo_path,
            scan_id=scan_id,
            base_sandbox_id=base_sandbox_id,
            fix_index=1,
            total_fixes=1,
        )

        if prep_res.get("status") == "failed":
            return {
                "status": "failed",
                "fix_id": fix.fix_id,
                "error": prep_res.get("error"),
                "sandbox_id": None,
                "confirmed_in_sandbox": False,
            }

        sandbox_id = prep_res["sandbox_id"]

        # 3. Read back file from the sandboxed environment to verify round-trip
        file_content_in_sandbox = await read_file_from_sandbox(sandbox_id, fix.file)

        # Confirm replacement is present
        confirmed_present = fix.fixed_lines in file_content_in_sandbox

        # Extract surrounding context snippet (~5 lines around the fix)
        lines = file_content_in_sandbox.splitlines()
        found_line_idx = -1
        for idx, line in enumerate(lines):
            if "alt=\"Company Logo\"" in line or (fix.fixed_lines and fix.fixed_lines in line):
                found_line_idx = idx
                break

        snippet = ""
        if found_line_idx != -1:
            snippet_start = max(0, found_line_idx - 2)
            snippet_end = min(len(lines), found_line_idx + 3)
            snippet = "\n".join(lines[snippet_start:snippet_end])

        return {
            "status": "applied",
            "sandbox_id": sandbox_id,
            "fix_id": fix.fix_id,
            "target_file": fix.file,
            "original_lines": fix.original_lines,
            "fixed_lines": fix.fixed_lines,
            "confirmed_in_sandbox": confirmed_present,
            "confirmed_file_snippet": snippet,
            "total_sandbox_file_lines": len(lines),
        }

    except SandboxAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except SandboxQuotaExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    except SandboxTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc))
    except (SandboxCreationError, SandboxError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except Exception as exc:
        logger.error(f"Unexpected error in /test-sandbox/apply-fix: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error applying fix in sandbox: {str(exc)}",
        )


