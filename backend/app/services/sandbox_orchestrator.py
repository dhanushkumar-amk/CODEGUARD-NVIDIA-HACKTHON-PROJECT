"""
Sandbox Orchestration Service.
Orchestrates provisioning, file synchronization, dependency installation,
and cleanup of isolated verification sandboxes for CodeGuard remediations.
"""
import logging
from pathlib import Path
import time
from typing import Dict, Optional, Union

from app.config import settings
from app.models.schemas import PipelineStage
from app.services.sandbox_client import (
    CommandResult,
    create_sandbox,
    destroy_sandbox,
    run_command,
    upload_files,
    SandboxCommandError,
    SandboxTimeoutError,
)
from app.state import (
    clear_scan_sandboxes,
    get_base_sandbox,
    get_scan,
    get_scan_sandboxes,
    track_base_sandbox,
    track_verification_sandbox,
)

logger = logging.getLogger(__name__)

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".turbo",
    ".idea",
    ".vscode",
}

IGNORE_EXTENSIONS = {
    ".pyc",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".zip",
    ".tar",
    ".gz",
}


def collect_repo_files(repo_path: Union[str, Path]) -> Dict[str, str]:
    """
    Recursively scans the cloned repository directory and constructs a dictionary
    of relative file paths to their UTF-8 string contents, excluding build artifacts
    and non-source binaries.
    """
    root = Path(repo_path).resolve()
    files_dict: Dict[str, str] = {}
    if not root.exists() or not root.is_dir():
        logger.warning(f"Repository path '{repo_path}' does not exist or is not a directory.")
        return files_dict

    for item in root.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(root)
        if any(part in IGNORE_DIRS for part in rel.parts):
            continue
        if item.suffix.lower() in IGNORE_EXTENSIONS:
            continue
        try:
            # Skip large files (> 2MB)
            if item.stat().st_size > 2 * 1024 * 1024:
                continue
            text = item.read_text(encoding="utf-8", errors="replace")
            files_dict[rel.as_posix()] = text
        except Exception as exc:
            logger.debug(f"Skipping file {item} during sandbox upload preparation: {exc}")

    return files_dict


async def _notify_progress(scan_id: Optional[str], progress: int, message: str) -> None:
    """Helper to safely broadcast WebSocket progress if scan_id is provided."""
    if not scan_id:
        return
    try:
        from app.routers.websocket import broadcast_progress
        await broadcast_progress(
            scan_id=scan_id,
            stage=PipelineStage.PREPARING_SANDBOX.value,
            progress=progress,
            message=message,
        )
    except Exception as exc:
        logger.debug(f"Failed to broadcast sandbox orchestrator progress for scan {scan_id}: {exc}")


async def prepare_verification_sandbox(
    repo_path: str,
    scan_id: str,
    fix_id: str,
) -> str:
    """
    Creates a new sandbox via create_sandbox() using Node base image,
    uploads the cloned repository into the sandbox via upload_files(),
    and tracks the sandbox_id against scan_id + fix_id in state.py.

    Args:
        repo_path: Path to the local repository clone.
        scan_id: Associated scan identifier.
        fix_id: Associated proposed fix identifier.

    Returns:
        The provisioned sandbox_id.
    """
    await _notify_progress(
        scan_id=scan_id,
        progress=20,
        message=f"Creating isolated verification sandbox for fix {fix_id}...",
    )

    handle = await create_sandbox(image=settings.NEBIUS_SANDBOX_DEFAULT_IMAGE)
    sandbox_id = handle.sandbox_id

    # Track in state so cleanup is guaranteed
    track_verification_sandbox(scan_id=scan_id, sandbox_id=sandbox_id, fix_id=fix_id)

    # Upload entire repository tree
    files = collect_repo_files(repo_path)
    await upload_files(sandbox_id=sandbox_id, files=files)

    logger.info(f"Prepared verification sandbox {sandbox_id} for scan {scan_id}, fix {fix_id}")
    return sandbox_id


async def install_dependencies(
    sandbox_id: str,
    repo_path: Optional[str] = None,
    scan_id: Optional[str] = None,
) -> CommandResult:
    """
    Runs npm install (or yarn install if yarn.lock is detected) inside the sandbox.
    Uses configurable timeout NPM_INSTALL_TIMEOUT_SECONDS (default 180s).
    Returns a CommandResult directly so failures can be surfaced clearly without raising.

    Args:
        sandbox_id: Identifier of the target sandbox.
        repo_path: Optional path to repository to check for lockfiles.
        scan_id: Optional scan ID for WebSocket progress notification.

    Returns:
        CommandResult with stdout, stderr, exit_code, and duration_ms.
    """
    # Detect package manager lockfile
    is_yarn = False
    if repo_path:
        yarn_lock = Path(repo_path) / "yarn.lock"
        if yarn_lock.exists() and yarn_lock.is_file():
            is_yarn = True
    else:
        # Check active scans if repo_path not passed explicitly
        if scan_id:
            scan_data = get_scan(scan_id)
            if scan_data and scan_data.get("repo_path"):
                is_yarn = (Path(scan_data["repo_path"]) / "yarn.lock").exists()

    install_cmd = "yarn install" if is_yarn else "npm install"

    await _notify_progress(
        scan_id=scan_id,
        progress=50,
        message="Installing dependencies in verification environment...",
    )

    logger.info(f"Running '{install_cmd}' in sandbox {sandbox_id} (timeout={settings.NPM_INSTALL_TIMEOUT_SECONDS}s)")
    start_t = time.time()

    try:
        result = await run_command(
            sandbox_id=sandbox_id,
            command=install_cmd,
            timeout=settings.NPM_INSTALL_TIMEOUT_SECONDS,
        )
        return result
    except SandboxTimeoutError as exc:
        duration_ms = round((time.time() - start_t) * 1000.0, 2)
        err_msg = f"Dependency installation timed out after {settings.NPM_INSTALL_TIMEOUT_SECONDS}s: {exc}"
        logger.warning(err_msg)
        return CommandResult(
            stdout="",
            stderr=err_msg,
            exit_code=124,
            duration_ms=duration_ms,
        )
    except SandboxCommandError as exc:
        duration_ms = round((time.time() - start_t) * 1000.0, 2)
        err_msg = f"Dependency installation command failed: {exc}"
        logger.warning(err_msg)
        return CommandResult(
            stdout="",
            stderr=err_msg,
            exit_code=1,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        duration_ms = round((time.time() - start_t) * 1000.0, 2)
        err_msg = f"Unexpected error during dependency installation: {exc}"
        logger.error(err_msg, exc_info=True)
        return CommandResult(
            stdout="",
            stderr=err_msg,
            exit_code=1,
            duration_ms=duration_ms,
        )


async def get_or_create_base_sandbox(
    repo_path: str,
    scan_id: str,
) -> str:
    """
    Cost optimization: Reuses an existing clean baseline sandbox for scan_id,
    or creates one, uploads repo files, runs dependency installation once,
    and records it in state.py.

    Args:
        repo_path: Path to the local repository clone.
        scan_id: Associated scan identifier.

    Returns:
        The baseline sandbox_id.
    """
    existing_base_id = get_base_sandbox(scan_id)
    if existing_base_id:
        logger.info(f"Reusing existing base sandbox {existing_base_id} for scan {scan_id}")
        return existing_base_id

    await _notify_progress(
        scan_id=scan_id,
        progress=10,
        message="Provisioning baseline sandbox environment...",
    )

    handle = await create_sandbox(image=settings.NEBIUS_SANDBOX_DEFAULT_IMAGE)
    sandbox_id = handle.sandbox_id
    track_base_sandbox(scan_id=scan_id, sandbox_id=sandbox_id)

    await _notify_progress(
        scan_id=scan_id,
        progress=30,
        message="Synchronizing repository files into base sandbox...",
    )

    files = collect_repo_files(repo_path)
    await upload_files(sandbox_id=sandbox_id, files=files)

    # Run dependency installation on clean baseline
    install_res = await install_dependencies(
        sandbox_id=sandbox_id,
        repo_path=repo_path,
        scan_id=scan_id,
    )

    if install_res.exit_code != 0:
        logger.warning(
            f"Base sandbox {sandbox_id} dependency installation finished with exit code {install_res.exit_code}: {install_res.stderr[:200]}"
        )

    await _notify_progress(
        scan_id=scan_id,
        progress=100,
        message="Baseline verification sandbox ready.",
    )

    logger.info(f"Initialized base sandbox {sandbox_id} for scan {scan_id}")
    return sandbox_id


async def cleanup_scan_sandboxes(scan_id: str) -> None:
    """
    Looks up all sandbox_ids associated with a scan_id (base + any verification
    sandboxes) and destroys them all, resetting state tracking.
    Guaranteed not to raise so top-level cleanup pipelines continue gracefully.

    Args:
        scan_id: Associated scan identifier.
    """
    sandbox_ids = get_scan_sandboxes(scan_id)
    if not sandbox_ids:
        logger.info(f"No active sandboxes found to clean up for scan {scan_id}")
        return

    logger.info(f"Cleaning up {len(sandbox_ids)} sandboxes for scan {scan_id}: {sandbox_ids}")

    for sb_id in sandbox_ids:
        try:
            await destroy_sandbox(sb_id)
        except Exception as exc:
            logger.warning(f"Error destroying sandbox {sb_id} during cleanup for scan {scan_id}: {exc}")

    clear_scan_sandboxes(scan_id)
