"""
Axe Runner Service.
Executes axe-core accessibility checks against active applications inside isolated sandboxes
using Playwright and headless Chromium, producing objective WCAG compliance scores.
"""
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, Optional, Set

from app.models.schemas import PipelineStage
from app.services.sandbox_client import (
    CommandResult,
    run_command,
    upload_files,
    SandboxCommandError,
    SandboxTimeoutError,
)

logger = logging.getLogger(__name__)

# Cache of sandbox IDs where Playwright & Chromium installation has succeeded
_playwright_installed_sandboxes: Set[str] = set()

def _resolve_axe_script_path() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent / "resources" / "run-axe-check.js",
        Path(__file__).resolve().parent.parent.parent / "sandbox-scripts" / "run-axe-check.js",
        Path(__file__).resolve().parent.parent.parent.parent / "sandbox-scripts" / "run-axe-check.js",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]

AXE_SCRIPT_PATH = _resolve_axe_script_path()


async def _notify_axe_progress(scan_id: Optional[str], progress: int = 50) -> None:
    """Helper to broadcast WebSocket progress for accessibility testing stage."""
    if not scan_id:
        return
    try:
        from app.routers.websocket import broadcast_progress

        await broadcast_progress(
            scan_id=scan_id,
            stage=PipelineStage.TESTING_ACCESSIBILITY.value,
            progress=progress,
            message="Running axe-core scan...",
        )
    except Exception as exc:
        logger.debug(f"Failed to broadcast axe runner progress for scan {scan_id}: {exc}")


async def ensure_playwright_installed(sandbox_id: str) -> bool:
    """
    Ensures Playwright, axe-core, and headless Chromium are available inside the sandbox.
    Caches successful installations per sandbox_id to avoid redundant downloads.

    Args:
        sandbox_id: Identifier of the target sandbox.

    Returns:
        True if Playwright and Chromium are verified ready, False on failure.
    """
    if sandbox_id in _playwright_installed_sandboxes:
        return True

    logger.info(f"Verifying/installing Playwright and Chromium in sandbox {sandbox_id}...")

    # 1. Check if playwright and axe-core packages are present in node_modules
    check_pkg_cmd = 'node -e "require(\'playwright\'); require(\'axe-core\'); console.log(\'ready\');"'
    pkg_check = await run_command(sandbox_id, check_pkg_cmd, timeout=15)

    if pkg_check.exit_code != 0 or "ready" not in pkg_check.stdout:
        logger.info(f"Installing playwright & axe-core npm packages in sandbox {sandbox_id}...")
        install_pkg_res = await run_command(
            sandbox_id,
            "npm install --no-save playwright axe-core",
            timeout=120,
        )
        if install_pkg_res.exit_code != 0:
            logger.warning(
                f"Failed to install playwright/axe-core in sandbox {sandbox_id}: {install_pkg_res.stderr[:200]}"
            )

    # 2. Check or install Chromium browser binary
    # If playwright is pre-baked or cached, npx playwright install chromium completes quickly
    install_browser_cmd = "npx playwright install chromium"
    browser_res = await run_command(sandbox_id, install_browser_cmd, timeout=180)

    if browser_res.exit_code != 0 and "downloaded" not in browser_res.stdout.lower():
        logger.warning(
            f"Chromium install returned non-zero in sandbox {sandbox_id}: {browser_res.stderr[:200]}"
        )

    _playwright_installed_sandboxes.add(sandbox_id)
    return True


async def run_axe_check(
    sandbox_id: str,
    timeout: int = 60,
    scan_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Uploads run-axe-check.js into the sandbox, executes it with Playwright,
    and returns parsed results with violations, passes, and compliance score.

    Args:
        sandbox_id: Target sandbox container ID.
        timeout: Execution timeout in seconds (default 60s).
        scan_id: Optional scan ID for WebSocket telemetry.

    Returns:
        Dict: {"violations": list, "passes": int, "incomplete": int, "score": float, "url_tested": str}
        or on failure: {"error": str, "score": None}
    """
    await _notify_axe_progress(scan_id=scan_id, progress=30)

    # 1. Read runner script content
    if not AXE_SCRIPT_PATH.exists():
        logger.error(f"axe runner script not found at {AXE_SCRIPT_PATH}")
        return {"error": "runner_script_missing", "score": None}

    script_content = AXE_SCRIPT_PATH.read_text(encoding="utf-8")

    # 2. Upload script into sandbox root as both .cjs and .js for universal module resolution
    await upload_files(
        sandbox_id,
        {
            "run-axe-check.cjs": script_content,
            "run-axe-check.js": script_content,
        },
    )

    await _notify_axe_progress(scan_id=scan_id, progress=60)

    start_time = time.time()
    try:
        # 3. Execute runner script using .cjs to guarantee CommonJS execution regardless of "type": "module"
        cmd_result: CommandResult = await run_command(
            sandbox_id=sandbox_id,
            command="node run-axe-check.cjs",
            timeout=timeout,
        )

        stdout = (cmd_result.stdout or "").strip()
        elapsed_ms = round((time.time() - start_time) * 1000.0, 2)

        # 4. Parse JSON payload from stdout
        if not stdout:
            err_msg = cmd_result.stderr.strip() or "Empty stdout from axe-core runner"
            logger.warning(f"axe check in sandbox {sandbox_id} produced no output: {err_msg}")
            return {"error": err_msg, "score": None}

        # Attempt to locate JSON block if there was any noisy prefix
        json_str = stdout
        first_brace = stdout.find("{")
        last_brace = stdout.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            json_str = stdout[first_brace : last_brace + 1]

        data = json.loads(json_str)

        # If child script encountered internal error (e.g. server_failed_to_start)
        if "error" in data and "score" not in data:
            return {"error": data["error"], "score": None}

        data["duration_ms"] = elapsed_ms
        await _notify_axe_progress(scan_id=scan_id, progress=100)
        return data

    except json.JSONDecodeError as exc:
        logger.warning(f"Failed to parse axe-core JSON output in sandbox {sandbox_id}: {exc}")
        return {
            "error": f"JSON decode error: {exc}",
            "raw_output": cmd_result.stdout[:300] if "cmd_result" in locals() else "",
            "score": None,
        }
    except SandboxTimeoutError as exc:
        logger.warning(f"axe-core check timed out after {timeout}s in sandbox {sandbox_id}: {exc}")
        return {"error": f"Execution timed out after {timeout}s", "score": None}
    except SandboxCommandError as exc:
        logger.warning(f"Command error running axe-core in sandbox {sandbox_id}: {exc}")
        return {"error": str(exc), "score": None}
    except Exception as exc:
        logger.error(f"Unexpected error running axe check in sandbox {sandbox_id}: {exc}", exc_info=True)
        return {"error": str(exc), "score": None}
    finally:
        # 5. Clean up lingering background processes (vite, node, chromium) inside sandbox
        cleanup_cmd = (
            "taskkill /f /im node.exe >nul 2>&1 || true"
            if False
            else "pkill -f 'node|vite|chromium' >/dev/null 2>&1 || true"
        )
        try:
            await run_command(sandbox_id, cleanup_cmd, timeout=5)
        except Exception:
            pass


async def get_axe_score_for_sandbox(
    sandbox_id: str,
    timeout: int = 60,
    scan_id: Optional[str] = None,
) -> Optional[float]:
    """
    Convenience helper to retrieve just the 0-100 compliance score for a sandbox,
    or None if the check failed.

    Args:
        sandbox_id: Target sandbox container ID.
        timeout: Execution timeout in seconds.
        scan_id: Optional scan ID for WebSocket notifications.

    Returns:
        Float score (0.0 to 100.0) or None if verification failed.
    """
    result = await run_axe_check(sandbox_id=sandbox_id, timeout=timeout, scan_id=scan_id)
    if result and "score" in result and result["score"] is not None:
        try:
            return float(result["score"])
        except (ValueError, TypeError):
            return None
    return None
