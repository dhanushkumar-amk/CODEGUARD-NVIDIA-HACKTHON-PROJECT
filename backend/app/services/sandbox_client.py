import asyncio
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import Dict, Optional
import uuid
import httpx
from pydantic import BaseModel, Field
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger(__name__)

# Registry of active local sandboxes: sandbox_id -> Path(directory)
_local_sandboxes: Dict[str, Path] = {}


# -------------------------------------------------------------------------
# Data Models
# -------------------------------------------------------------------------

class SandboxHandle(BaseModel):
    """Handle to a provisioned Nebius isolated execution sandbox."""
    sandbox_id: str = Field(description="Unique identifier for the sandbox instance")
    image: str = Field(description="Container image loaded into the sandbox")
    status: str = Field(default="ready", description="Current status of the sandbox")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp of creation")

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
    """Raised when authentication with Nebius Sandbox API fails (401/403)."""
    pass


class SandboxCreationError(SandboxError):
    """Raised when provisioning a new sandbox fails."""
    pass


class SandboxTimeoutError(SandboxError):
    """Raised when a command or sandbox operation exceeds its allocated timeout."""
    pass


class SandboxQuotaExceededError(SandboxError):
    """Raised when Nebius sandbox concurrency or account quotas are exceeded (429)."""
    pass


class SandboxCommandError(SandboxError):
    """Raised when an unexpected communication error occurs executing a command."""
    pass


# -------------------------------------------------------------------------
# Concurrency & Network Retry Configuration
# -------------------------------------------------------------------------

# Transient network errors suitable for retrying HTTP requests
TRANSIENT_NETWORK_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.NetworkError,
)

_active_sandboxes: int = 0
_concurrency_lock = asyncio.Lock()


def _get_headers() -> Dict[str, str]:
    """Retrieve auth and content headers for Nebius Sandbox API calls."""
    api_key = settings.NEBIUS_SANDBOX_API_KEY
    if not api_key or not api_key.strip() or api_key == "your_nebius_sandbox_api_key_here":
        api_key = settings.NEBIUS_TOKEN_FACTORY_API_KEY

    if not api_key or not api_key.strip() or api_key == "your_nebius_sandbox_api_key_here":
        raise SandboxAuthenticationError(
            "NEBIUS_SANDBOX_API_KEY (or NEBIUS_TOKEN_FACTORY_API_KEY) is not configured. "
            "Please provide a valid API key in environment variables."
        )
    return {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


@retry(
    retry=retry_if_exception_type(TRANSIENT_NETWORK_EXCEPTIONS),
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=1, max=3),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _send_request(
    method: str,
    endpoint: str,
    json_data: Optional[Dict] = None,
    timeout: Optional[float] = None,
) -> httpx.Response:
    """
    Send an HTTP request with retry logic for transient network failures only.
    Command execution status (e.g. failing tests with exit_code != 0) are not retried.
    """
    headers = _get_headers()
    base_url = settings.NEBIUS_SANDBOX_BASE_URL.rstrip("/")
    url = f"{base_url}{endpoint}"
    req_timeout = timeout if timeout is not None else float(settings.SANDBOX_TIMEOUT_SECONDS)

    async with httpx.AsyncClient(timeout=req_timeout) as client:
        return await client.request(
            method=method,
            url=url,
            headers=headers,
            json=json_data,
        )


# -------------------------------------------------------------------------
# Core Sandbox Operations
# -------------------------------------------------------------------------

async def create_sandbox(image: Optional[str] = None) -> SandboxHandle:
    """
    Provision a new isolated sandbox container via Nebius's Sandbox API.

    Args:
        image: Container image (e.g., node:20, python:3.11).
               Defaults to settings.NEBIUS_SANDBOX_DEFAULT_IMAGE.

    Returns:
        SandboxHandle with sandbox_id and metadata.

    Raises:
        SandboxAuthenticationError: When credentials are missing or invalid.
        SandboxQuotaExceededError: When maximum concurrency or Nebius quota is hit.
        SandboxCreationError: If provisioning fails on Nebius Cloud.
        SandboxTimeoutError: If provisioning times out.
    """
    global _active_sandboxes

    target_image = image or settings.NEBIUS_SANDBOX_DEFAULT_IMAGE

    # Local concurrency check
    async with _concurrency_lock:
        if _active_sandboxes >= settings.SANDBOX_MAX_CONCURRENT:
            raise SandboxQuotaExceededError(
                f"Maximum concurrent sandboxes ({settings.SANDBOX_MAX_CONCURRENT}) reached. "
                "Please wait for active sandboxes to complete."
            )
        _active_sandboxes += 1

    # Check auth configuration
    api_key = settings.NEBIUS_SANDBOX_API_KEY
    if not api_key or not api_key.strip():
        raise SandboxAuthenticationError(
            "NEBIUS_SANDBOX_API_KEY is not configured. "
            "Please provide a valid API key in backend/.env"
        )

    # Local isolated sandbox environment if running locally/dev
    if api_key in ("local", "your_nebius_sandbox_api_key_here"):
        sb_id = f"sb-local-{uuid.uuid4().hex[:8]}"
        sb_dir = Path(tempfile.mkdtemp(prefix="codeguard_sb_"))
        _local_sandboxes[sb_id] = sb_dir
        logger.info(f"Provisioned local execution sandbox {sb_id} at {sb_dir}")
        return SandboxHandle(
            sandbox_id=sb_id,
            image=target_image,
            status="ready",
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    try:
        payload = {
            "image": target_image,
            "timeout": settings.SANDBOX_TIMEOUT_SECONDS,
        }

        try:
            response = await _send_request(
                method="POST",
                endpoint="/sandboxes",
                json_data=payload,
                timeout=float(settings.SANDBOX_TIMEOUT_SECONDS),
            )
        except httpx.TimeoutException as exc:
            raise SandboxTimeoutError(f"Timed out provisioning sandbox with image {target_image}: {exc}") from exc
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            raise SandboxCreationError(f"Network error connecting to Nebius Sandbox API: {exc}") from exc

        if response.status_code in (401, 403):
            raise SandboxAuthenticationError(
                f"Authentication failed with Nebius Sandbox API (HTTP {response.status_code}): {response.text}"
            )
        elif response.status_code == 429:
            raise SandboxQuotaExceededError(
                f"Nebius Sandbox quota exceeded (HTTP 429): {response.text}"
            )
        elif response.status_code not in (200, 201):
            raise SandboxCreationError(
                f"Failed to create sandbox (HTTP {response.status_code}): {response.text}"
            )

        data = response.json()
        sandbox_id = (
            data.get("sandbox_id")
            or data.get("id")
            or (data.get("data", {}).get("id") if isinstance(data.get("data"), dict) else None)
        )

        if not sandbox_id:
            raise SandboxCreationError(f"No sandbox ID returned from Nebius API: {data}")

        return SandboxHandle(
            sandbox_id=str(sandbox_id),
            image=target_image,
            status=data.get("status", "ready"),
            created_at=data.get("created_at"),
        )

    except Exception:
        # Roll back concurrency counter if creation failed
        async with _concurrency_lock:
            if _active_sandboxes > 0:
                _active_sandboxes -= 1
        raise


async def run_command(
    sandbox_id: str,
    command: str,
    timeout: Optional[int] = None,
) -> CommandResult:
    """
    Execute a shell command inside the isolated sandbox.

    Args:
        sandbox_id: ID of the running sandbox.
        command: Shell command string to execute.
        timeout: Execution timeout in seconds. Defaults to SANDBOX_TIMEOUT_SECONDS.

    Returns:
        CommandResult with stdout, stderr, and exit_code.

    Raises:
        SandboxTimeoutError: If the command exceeds the timeout.
        SandboxAuthenticationError: If auth credentials fail.
        SandboxCommandError: If the API endpoint returns an unexpected error.
    """
    cmd_timeout = timeout if timeout is not None else settings.SANDBOX_TIMEOUT_SECONDS

    # 1. Local isolated sandbox execution
    if sandbox_id in _local_sandboxes:
        sb_dir = _local_sandboxes[sandbox_id]
        start_t = time.time()
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=str(sb_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=float(cmd_timeout),
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise SandboxTimeoutError(f"Command execution timed out after {cmd_timeout}s: {command}")

            duration_ms = round((time.time() - start_t) * 1000.0, 2)
            return CommandResult(
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                exit_code=proc.returncode if proc.returncode is not None else 0,
                duration_ms=duration_ms,
            )
        except SandboxTimeoutError:
            raise
        except Exception as exc:
            raise SandboxCommandError(f"Local sandbox error running '{command}': {exc}") from exc

    # 2. Remote Nebius Cloud sandbox execution
    payload = {
        "command": command,
        "timeout": cmd_timeout,
    }

    try:
        response = await _send_request(
            method="POST",
            endpoint=f"/sandboxes/{sandbox_id}/commands",
            json_data=payload,
            timeout=float(cmd_timeout + 5),  # HTTP client timeout slightly higher than command timeout
        )
    except httpx.TimeoutException as exc:
        raise SandboxTimeoutError(f"Command execution timed out after {cmd_timeout}s: {command}") from exc
    except (httpx.ConnectError, httpx.NetworkError) as exc:
        raise SandboxCommandError(f"Network error executing command in sandbox {sandbox_id}: {exc}") from exc

    if response.status_code in (401, 403):
        raise SandboxAuthenticationError(f"Authentication failed on command execution: {response.text}")
    elif response.status_code in (408, 504):
        raise SandboxTimeoutError(f"Command execution timed out on Nebius Cloud: {response.text}")
    elif response.status_code == 429:
        raise SandboxQuotaExceededError(f"Nebius rate limit or quota exceeded: {response.text}")
    elif response.status_code not in (200, 201):
        raise SandboxCommandError(
            f"Failed to execute command in sandbox {sandbox_id} (HTTP {response.status_code}): {response.text}"
        )

    data = response.json()
    return CommandResult(
        stdout=data.get("stdout", ""),
        stderr=data.get("stderr", ""),
        exit_code=int(data.get("exit_code", data.get("return_code", 0))),
        duration_ms=data.get("duration_ms"),
    )


async def upload_files(sandbox_id: str, files: Dict[str, str]) -> None:
    """
    Upload a mapping of file paths to string contents into the sandbox.

    Args:
        sandbox_id: ID of the running sandbox.
        files: Dictionary mapping file paths (e.g. 'src/App.tsx') to contents.

    Raises:
        SandboxAuthenticationError: If credentials fail.
        SandboxError: If file upload fails.
    """
    # 1. Local isolated sandbox file upload
    if sandbox_id in _local_sandboxes:
        sb_dir = _local_sandboxes[sandbox_id]
        for rel_path, content in files.items():
            dest_file = sb_dir / rel_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            dest_file.write_text(content, encoding="utf-8", errors="replace")
        return

    # 2. Remote Nebius Cloud file upload
    payload = {
        "files": files,
    }

    try:
        response = await _send_request(
            method="POST",
            endpoint=f"/sandboxes/{sandbox_id}/files",
            json_data=payload,
        )
    except httpx.TimeoutException as exc:
        raise SandboxTimeoutError(f"File upload to sandbox {sandbox_id} timed out: {exc}") from exc
    except (httpx.ConnectError, httpx.NetworkError) as exc:
        raise SandboxError(f"Network error uploading files to sandbox {sandbox_id}: {exc}") from exc

    if response.status_code in (401, 403):
        raise SandboxAuthenticationError(f"Authentication failed during file upload: {response.text}")
    elif response.status_code not in (200, 201, 204):
        raise SandboxError(f"Failed to upload files to sandbox {sandbox_id} (HTTP {response.status_code}): {response.text}")


async def destroy_sandbox(sandbox_id: str) -> None:
    """
    Clean up and release the sandbox on Nebius AI Cloud or local environment.

    Args:
        sandbox_id: ID of the sandbox to destroy.
    """
    global _active_sandboxes

    # 1. Local isolated sandbox teardown
    if sandbox_id in _local_sandboxes or sandbox_id.startswith("sb-local-"):
        sb_dir = _local_sandboxes.pop(sandbox_id, None)
        if sb_dir and sb_dir.exists():
            shutil.rmtree(sb_dir, ignore_errors=True)
            logger.info(f"Destroyed local execution sandbox {sandbox_id}")
        async with _concurrency_lock:
            if _active_sandboxes > 0:
                _active_sandboxes -= 1
        return

    # 2. Remote Nebius Cloud teardown
    try:
        response = await _send_request(
            method="DELETE",
            endpoint=f"/sandboxes/{sandbox_id}",
            timeout=30.0,
        )
        if response.status_code not in (200, 204, 404):
            logger.warning(
                f"Unexpected status code {response.status_code} while destroying sandbox {sandbox_id}: {response.text}"
            )
    except Exception as exc:
        logger.warning(f"Error requesting teardown for sandbox {sandbox_id}: {exc}")
    finally:
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

    Usage:
        async with sandbox_session() as sandbox:
            result = await run_command(sandbox.id, "echo hello")
    """
    sandbox = await create_sandbox(image=image)
    try:
        yield sandbox
    finally:
        try:
            await destroy_sandbox(sandbox.sandbox_id)
        except Exception as exc:
            logger.warning(f"Failed to cleanly destroy sandbox {sandbox.sandbox_id}: {exc}")
