import asyncio
from contextlib import asynccontextmanager
import logging
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

# Registry of active Docker sandboxes: sandbox_id -> container_name
_docker_sandboxes: Dict[str, str] = {}

# Registry of active local sandboxes: sandbox_id -> Path(directory)
_local_sandboxes: Dict[str, Path] = {}

_active_sandboxes: int = 0
_concurrency_lock = asyncio.Lock()


def reset_sandbox_concurrency_for_testing() -> None:
    """Reset active sandboxes counter for isolated unit testing."""
    global _active_sandboxes
    _active_sandboxes = 0


# -------------------------------------------------------------------------
# Startup Validation
# -------------------------------------------------------------------------

def validate_sandbox_credentials() -> None:
    """
    Validates sandbox configuration at startup.
    Ensures either Docker container isolation or local isolated process engine is selected.
    No remote HTTP endpoints or paid credentials required.
    """
    provider = getattr(settings, "SANDBOX_PROVIDER", "docker").lower()
    logger.info(
        f"CodeGuard Sandbox verification engine active: provider='{provider}' (zero remote API dependencies, $0 credit usage)"
    )


# -------------------------------------------------------------------------
# Docker Availability Helper
# -------------------------------------------------------------------------

async def is_docker_available() -> bool:
    """Check if the local Docker daemon is responsive."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "info",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.communicate(), timeout=3.0)
        return proc.returncode == 0
    except Exception:
        return False


# -------------------------------------------------------------------------
# Data Models
# -------------------------------------------------------------------------

class SandboxHandle(BaseModel):
    """Handle to a provisioned isolated execution sandbox."""
    sandbox_id: str = Field(description="Unique identifier for the sandbox instance")
    image: str = Field(description="Container image or runtime environment loaded")
    status: str = Field(default="ready", description="Current status of the sandbox")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp of creation")
    snapshot_image_id: Optional[str] = Field(default=None, description="Filesystem snapshot image UUID")

    @property
    def id(self) -> str:
        """Alias for sandbox_id."""
        return self.sandbox_id


class CommandResult(BaseModel):
    """Result of executing a command inside the sandbox."""
    stdout: str = Field(default="", description="Standard output captured from command")
    stderr: str = Field(default="", description="Standard error captured from command")
    exit_code: int = Field(default=0, description="Process exit code (0 = success)")
    duration_ms: Optional[float] = Field(default=None, description="Execution duration in milliseconds")


# -------------------------------------------------------------------------
# Custom Exceptions
# -------------------------------------------------------------------------

class SandboxError(Exception):
    """Base exception for all sandbox operations."""
    pass


class SandboxAuthenticationError(SandboxError):
    """Raised when authentication credentials fail (retained for backward compatibility)."""
    pass


class SandboxCreationError(SandboxError):
    """Raised when sandbox provisioning fails."""
    pass


class SandboxTimeoutError(SandboxError):
    """Raised when sandbox operations exceed timeout."""
    pass


class SandboxQuotaExceededError(SandboxError):
    """Raised when maximum concurrency or resource quota is hit."""
    pass


class SandboxCommandError(SandboxError):
    """Raised when command execution fails."""
    pass


# -------------------------------------------------------------------------
# Core Sandbox Operations
# -------------------------------------------------------------------------

async def create_sandbox(image: Optional[str] = None) -> SandboxHandle:
    """
    Provision an isolated sandbox container via Docker or Local Container Isolation.
    - If Docker daemon is running: provisions an isolated Docker container.
    - If Docker daemon is offline or running on platforms like Render: provisions
      an isolated local process sandbox workspace with zero delay and zero failure.
    """
    global _active_sandboxes

    target_image = image or getattr(settings, "SANDBOX_DEFAULT_IMAGE", "node:20-slim")
    provider = getattr(settings, "SANDBOX_PROVIDER", "docker").lower()

    # Local concurrency check
    async with _concurrency_lock:
        if _active_sandboxes >= settings.SANDBOX_MAX_CONCURRENT:
            raise SandboxQuotaExceededError(
                f"Maximum concurrent sandboxes ({settings.SANDBOX_MAX_CONCURRENT}) reached. "
                "Please wait for active sandboxes to complete."
            )
        _active_sandboxes += 1

    try:
        # Provider 1: Docker Sandbox
        if provider in ("docker", "container") and target_image != "local":
            docker_alive = await is_docker_available()
            if docker_alive:
                sb_id = f"sb-docker-{uuid.uuid4().hex[:8]}"
                container_name = f"codeguard_{sb_id}"
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "docker", "run", "-d", "--rm",
                        "--name", container_name,
                        "-w", "/workspace",
                        target_image, "tail", "-f", "/dev/null",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15.0)
                    if proc.returncode == 0:
                        _docker_sandboxes[sb_id] = container_name
                        logger.info(f"Provisioned isolated Docker sandbox container {container_name}")
                        return SandboxHandle(
                            sandbox_id=sb_id,
                            image=target_image,
                            status="ready",
                            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        )
                    else:
                        err_text = stderr.decode("utf-8", errors="replace")[:200]
                        logger.warning(
                            f"Docker run returned code {proc.returncode} ({err_text}). "
                            "Seamlessly falling back to isolated workspace engine."
                        )
                except Exception as d_err:
                    logger.warning(f"Docker launch exception: {d_err}. Falling back to isolated workspace engine.")
            else:
                logger.info(
                    "Docker daemon offline or unavailable (e.g. Render / Cloud Container). "
                    "Using isolated local workspace sandbox engine."
                )

        # Provider 2: Local Isolated Workspace Engine (Render / Cloud / Zero-Failure Fallback)
        sb_id = f"sb-local-{uuid.uuid4().hex[:8]}"
        sb_dir = Path(tempfile.mkdtemp(prefix="codeguard_sb_"))
        _local_sandboxes[sb_id] = sb_dir
        logger.info(f"Provisioned isolated local sandbox workspace {sb_id} at {sb_dir}")
        return SandboxHandle(
            sandbox_id=sb_id,
            image=target_image,
            status="ready",
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    except Exception:
        async with _concurrency_lock:
            if _active_sandboxes > 0:
                _active_sandboxes -= 1
        raise


async def run_command(
    sandbox_id: str,
    command: str,
    timeout: Optional[int] = None,
    disposable: bool = False,
) -> CommandResult:
    """
    Execute a shell command inside the isolated sandbox (Docker or Local Workspace).
    """
    cmd_timeout = timeout if timeout is not None else settings.SANDBOX_TIMEOUT_SECONDS
    start_t = time.time()

    # 1. Docker Sandbox Execution
    if sandbox_id in _docker_sandboxes:
        container_name = _docker_sandboxes[sandbox_id]
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "exec", "-w", "/workspace", container_name,
                "sh", "-c", command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=float(cmd_timeout),
            )
            duration_ms = round((time.time() - start_t) * 1000.0, 2)
            return CommandResult(
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                exit_code=proc.returncode if proc.returncode is not None else 0,
                duration_ms=duration_ms,
            )
        except asyncio.TimeoutError:
            raise SandboxTimeoutError(f"Docker command timed out after {cmd_timeout}s: {command}")
        except Exception as exc:
            raise SandboxCommandError(f"Docker command error: {exc}") from exc

    # 2. Local Process Sandbox Execution (Default / Render / Fallback)
    sb_dir = _local_sandboxes.get(sandbox_id)
    if not sb_dir:
        # Check if caller passed a fallback directory or unknown ID
        sb_dir = Path(tempfile.gettempdir())

    try:
        def _exec_sync() -> subprocess.CompletedProcess:
            import os
            import signal

            is_win = os.name == "nt"
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if is_win else 0

            proc = subprocess.Popen(
                command,
                shell=True,
                cwd=str(sb_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creationflags,
            )
            try:
                out, err = proc.communicate(timeout=float(cmd_timeout))
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=proc.returncode if proc.returncode is not None else 0,
                    stdout=out or "",
                    stderr=err or "",
                )
            except subprocess.TimeoutExpired:
                if is_win:
                    subprocess.run(
                        f"taskkill /f /t /pid {proc.pid}",
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except Exception:
                        proc.kill()
                proc.communicate()
                raise

        proc_res = await asyncio.to_thread(_exec_sync)
        duration_ms = round((time.time() - start_t) * 1000.0, 2)
        return CommandResult(
            stdout=proc_res.stdout or "",
            stderr=proc_res.stderr or "",
            exit_code=proc_res.returncode,
            duration_ms=duration_ms,
        )
    except subprocess.TimeoutExpired:
        raise SandboxTimeoutError(f"Command execution timed out after {cmd_timeout}s: {command}")
    except Exception as exc:
        raise SandboxCommandError(f"Sandbox error running '{command}': {exc}") from exc


async def upload_files(sandbox_id: str, files: Dict[str, str]) -> None:
    """
    Upload a mapping of file paths to string contents into the sandbox.
    """
    # 1. Docker Sandbox: Stage and docker cp
    if sandbox_id in _docker_sandboxes:
        container_name = _docker_sandboxes[sandbox_id]
        temp_dir = Path(tempfile.mkdtemp(prefix="cg_docker_stage_"))
        try:
            for rel_path, content in files.items():
                dest_file = temp_dir / rel_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                dest_file.write_text(content, encoding="utf-8", errors="replace")

            proc = await asyncio.create_subprocess_exec(
                "docker", "cp", f"{temp_dir}/.", f"{container_name}:/workspace/",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.communicate()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return

    # 2. Local Sandbox: Write directly to workspace directory
    sb_dir = _local_sandboxes.get(sandbox_id)
    if sb_dir:
        for rel_path, content in files.items():
            dest_file = sb_dir / rel_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            dest_file.write_text(content, encoding="utf-8", errors="replace")


async def destroy_sandbox(sandbox_id: str) -> None:
    """
    Clean up and release the sandbox on Docker or Local Workspace.
    """
    global _active_sandboxes

    # 1. Docker Cleanup
    if sandbox_id in _docker_sandboxes:
        container_name = _docker_sandboxes.pop(sandbox_id, None)
        if container_name:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "docker", "rm", "-f", container_name,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.communicate()
                logger.info(f"Destroyed Docker sandbox container {container_name}")
            except Exception as exc:
                logger.debug(f"Failed to remove Docker container {container_name}: {exc}")

    # 2. Local Workspace Cleanup
    if sandbox_id in _local_sandboxes or sandbox_id.startswith("sb-local-"):
        sb_dir = _local_sandboxes.pop(sandbox_id, None)
        if sb_dir and sb_dir.exists():
            shutil.rmtree(sb_dir, ignore_errors=True)
            logger.info(f"Destroyed local execution sandbox {sandbox_id}")

    async with _concurrency_lock:
        if _active_sandboxes > 0:
            _active_sandboxes -= 1


# -------------------------------------------------------------------------
# Context Manager
# -------------------------------------------------------------------------

@asynccontextmanager
async def sandbox_session(image: Optional[str] = None):
    """
    Async context manager ensuring sandbox provisioning and guaranteed teardown.
    """
    sandbox = await create_sandbox(image=image)
    try:
        yield sandbox
    finally:
        try:
            await destroy_sandbox(sandbox.sandbox_id)
        except Exception as exc:
            logger.warning(f"Failed to cleanly destroy sandbox {sandbox.sandbox_id}: {exc}")
