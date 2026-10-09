import asyncio
from contextlib import asynccontextmanager
import logging
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any, Dict, Optional
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

# Registry of active remote ConTree sandboxes: sandbox_id -> state dict
_remote_sandboxes: Dict[str, Dict[str, Any]] = {}

_active_sandboxes: int = 0
_concurrency_lock = asyncio.Lock()


# -------------------------------------------------------------------------
# Startup Validation
# -------------------------------------------------------------------------

def validate_sandbox_credentials() -> None:
    """
    Validates that required Nebius Sandbox (ConTree) credentials are configured.
    Raises RuntimeError with a clear message if base URL, token, or project ID is missing.
    """
    base_url = (settings.NEBIUS_SANDBOX_BASE_URL or "").strip()
    api_key = (settings.NEBIUS_SANDBOX_API_KEY or "").strip()
    project_id = (settings.NEBIUS_SANDBOX_PROJECT_ID or "").strip()

    missing = []
    if not base_url:
        missing.append("NEBIUS_SANDBOX_BASE_URL")
    if not api_key:
        missing.append("NEBIUS_SANDBOX_API_KEY")
    if not project_id:
        missing.append("NEBIUS_SANDBOX_PROJECT_ID")

    if missing:
        raise RuntimeError(
            f"Missing required Nebius Sandbox configuration at startup: {', '.join(missing)}. "
            "Base URL (default: https://api.studio.nebius.com/sandboxes), API token (NEBIUS_SANDBOX_API_KEY), "
            "and Project ID (NEBIUS_SANDBOX_PROJECT_ID) are all required to run CodeGuard sandbox verification."
        )


# -------------------------------------------------------------------------
# Data Models
# -------------------------------------------------------------------------

class SandboxHandle(BaseModel):
    """Handle to a provisioned Nebius isolated execution sandbox."""
    sandbox_id: str = Field(description="Unique identifier for the sandbox instance")
    image: str = Field(description="Container image loaded into the sandbox")
    status: str = Field(default="ready", description="Current status of the sandbox")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp of creation")
    snapshot_image_id: Optional[str] = Field(default=None, description="ConTree filesystem snapshot image UUID")

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
# Network & Auth Configuration
# -------------------------------------------------------------------------

TRANSIENT_NETWORK_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.NetworkError,
)


def _get_headers() -> Dict[str, str]:
    """
    Retrieve auth and project headers for real Nebius Sandbox (ConTree) API calls.
    ConTree requires both Authorization: Bearer <token> AND Project: <project_id>.
    """
    api_key = settings.NEBIUS_SANDBOX_API_KEY
    if not api_key or not api_key.strip() or api_key == "your_nebius_sandbox_api_key_here":
        api_key = settings.NEBIUS_TOKEN_FACTORY_API_KEY

    project_id = settings.NEBIUS_SANDBOX_PROJECT_ID
    if not project_id or not project_id.strip() or project_id == "your_nebius_project_id_here":
        project_id = "project-e00rc89xqcxqxz4bqy"

    if not api_key or not api_key.strip() or api_key == "your_nebius_sandbox_api_key_here":
        raise SandboxAuthenticationError(
            "NEBIUS_SANDBOX_API_KEY is not configured. "
            "Please provide a valid API key in environment variables."
        )

    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if project_id and project_id.strip():
        headers["Project"] = project_id.strip()

    return headers


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
    content: Optional[bytes] = None,
    timeout: Optional[float] = None,
    custom_headers: Optional[Dict[str, str]] = None,
) -> httpx.Response:
    """Send an HTTP request to the real ConTree endpoint."""
    headers = _get_headers()
    if custom_headers:
        headers.update(custom_headers)

    base_url = settings.NEBIUS_SANDBOX_BASE_URL.rstrip("/")
    # Real ConTree endpoints are rooted at /v1/...
    ep = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    url = f"{base_url}{ep}"
    req_timeout = timeout if timeout is not None else float(settings.SANDBOX_TIMEOUT_SECONDS)

    async with httpx.AsyncClient(timeout=req_timeout) as client:
        return await client.request(
            method=method,
            url=url,
            headers=headers,
            json=json_data,
            content=content,
        )


async def check_api_whoami() -> Dict[str, Any]:
    """
    Calls the real ConTree /v1/whoami endpoint to verify connection, token validity,
    limits, and permissions on Nebius Cloud.
    """
    response = await _send_request(
        method="GET",
        endpoint="/v1/whoami",
        timeout=15.0,
    )
    if response.status_code in (401, 403):
        raise SandboxAuthenticationError(
            f"Authentication failed on Nebius Sandboxes /v1/whoami (HTTP {response.status_code}): {response.text}"
        )
    elif response.status_code != 200:
        raise SandboxError(
            f"Nebius Sandboxes whoami check failed (HTTP {response.status_code}): {response.text}"
        )
    return response.json()


# -------------------------------------------------------------------------
# Core Sandbox Operations
# -------------------------------------------------------------------------

async def create_sandbox(image: Optional[str] = None) -> SandboxHandle:
    """
    Provision a new isolated sandbox container via Nebius's real ConTree Sandbox API.

    Args:
        image: Container image (e.g., node:20).
               Defaults to settings.NEBIUS_SANDBOX_DEFAULT_IMAGE.

    Returns:
        SandboxHandle with sandbox_id and metadata.

    Raises:
        SandboxAuthenticationError: When credentials are missing or invalid.
        SandboxQuotaExceededError: When maximum concurrency or Nebius quota is hit.
        SandboxCreationError: If provisioning fails or token lacks spawn permissions.
        SandboxTimeoutError: If provisioning times out.
    """
    global _active_sandboxes

    target_image = image or settings.NEBIUS_SANDBOX_DEFAULT_IMAGE

    # Check auth configuration
    api_key = settings.NEBIUS_SANDBOX_API_KEY
    if not api_key or not api_key.strip():
        raise SandboxAuthenticationError(
            "NEBIUS_SANDBOX_API_KEY is not configured. "
            "Please provide a valid API key in backend/.env"
        )

    # Local concurrency check
    async with _concurrency_lock:
        if _active_sandboxes >= settings.SANDBOX_MAX_CONCURRENT:
            raise SandboxQuotaExceededError(
                f"Maximum concurrent sandboxes ({settings.SANDBOX_MAX_CONCURRENT}) reached. "
                "Please wait for active sandboxes to complete."
            )
        _active_sandboxes += 1

    # Local isolated sandbox environment if configured for offline development / unit tests
    if api_key in ("local", "your_nebius_sandbox_api_key_here") or target_image == "local":
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

    # Remote Nebius ConTree Sandbox Verification & Initialization
    try:
        try:
            whoami_data = await check_api_whoami()
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as net_err:
            raise SandboxCreationError(f"Network error reaching Nebius Sandbox API: {net_err}") from net_err

        # Check permissions returned by the real ConTree service
        perms = whoami_data.get("permissions", {})
        can_spawn = perms.get("spawn", False) or perms.get("spawn_disposable", False)
        if not can_spawn:
            raise SandboxCreationError(
                f"Nebius Sandbox API returned insufficient permissions (HTTP 403): "
                f"Token '{whoami_data.get('token_uuid')}' lacks 'spawn' and 'spawn_disposable' permissions "
                f"for project '{settings.NEBIUS_SANDBOX_PROJECT_ID}'."
            )

        sb_id = f"sb-contree-{uuid.uuid4().hex[:8]}"
        _remote_sandboxes[sb_id] = {
            "image": target_image,
            "current_image": target_image,
            "snapshot_image_id": None,
            "files": {},
            "status": "ready",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        return SandboxHandle(
            sandbox_id=sb_id,
            image=target_image,
            status="ready",
            created_at=_remote_sandboxes[sb_id]["created_at"],
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
    Execute a shell command inside the isolated sandbox using ConTree snapshotting.

    Args:
        sandbox_id: ID of the running sandbox.
        command: Shell command string to execute.
        timeout: Execution timeout in seconds. Defaults to SANDBOX_TIMEOUT_SECONDS.
        disposable: If False, ConTree snapshots the updated filesystem for subsequent commands.

    Returns:
        CommandResult with stdout, stderr, and exit_code.

    Raises:
        SandboxTimeoutError: If the command exceeds the timeout.
        SandboxAuthenticationError: If auth credentials fail.
        SandboxCommandError: If the API endpoint returns an error.
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

    # 2. Remote Nebius ConTree Sandbox execution
    sb_state = _remote_sandboxes.get(sandbox_id)
    if not sb_state:
        # Check if it was an ephemeral single-run container
        sb_state = {
            "current_image": settings.NEBIUS_SANDBOX_DEFAULT_IMAGE,
            "files": {},
        }

    current_image = sb_state.get("snapshot_image_id") or sb_state.get("current_image") or settings.NEBIUS_SANDBOX_DEFAULT_IMAGE
    files_spec = sb_state.get("files", {})

    spawn_payload = {
        "image": current_image,
        "command": "sh",
        "args": ["-c", command],
        "shell": True,
        "cwd": "/workspace",
        "disposable": disposable,
        "timeout": cmd_timeout,
        "files": files_spec,
        "env": {},
    }

    start_t = time.time()
    try:
        response = await _send_request(
            method="POST",
            endpoint="/v1/instances",
            json_data=spawn_payload,
            timeout=float(cmd_timeout + 15),
        )
    except httpx.TimeoutException as exc:
        raise SandboxTimeoutError(f"Timed out spawning instance for command: {exc}") from exc
    except (httpx.ConnectError, httpx.NetworkError) as exc:
        raise SandboxCommandError(f"Network error contacting ConTree API: {exc}") from exc

    if response.status_code in (401, 403):
        raise SandboxAuthenticationError(f"Authentication failed on ConTree /v1/instances (HTTP {response.status_code}): {response.text}")
    elif response.status_code == 429:
        raise SandboxQuotaExceededError(f"Nebius rate limit or quota exceeded: {response.text}")
    elif response.status_code not in (200, 201, 202):
        raise SandboxCommandError(f"Failed to spawn instance on ConTree (HTTP {response.status_code}): {response.text}")

    data = response.json()
    op_id = data.get("uuid") or data.get("operation_id")
    if not op_id:
        raise SandboxCommandError(f"No operation UUID returned from ConTree: {data}")

    # Poll operation status until completion
    poll_deadline = time.time() + float(cmd_timeout + 30)
    while time.time() < poll_deadline:
        await asyncio.sleep(1.0)
        op_resp = await _send_request(
            method="GET",
            endpoint=f"/v1/operations/{op_id}",
            timeout=10.0,
        )
        if op_resp.status_code != 200:
            continue

        op_data = op_resp.json()
        op_status = op_data.get("status")

        if op_status in ("succeeded", "failed"):
            meta = op_data.get("metadata", {})
            result_meta = meta.get("result", {})
            state_meta = result_meta.get("state", {})

            exit_code = state_meta.get("exit_code", 0 if op_status == "succeeded" else 1)
            stdout = result_meta.get("stdout", {}).get("data", "")
            stderr = result_meta.get("stderr", {}).get("data", "")

            # If snapshot occurred, record the new image snapshot ID for subsequent commands
            new_image = op_data.get("result", {}).get("image") or op_data.get("result", {}).get("image_id")
            if new_image and sandbox_id in _remote_sandboxes:
                _remote_sandboxes[sandbox_id]["snapshot_image_id"] = new_image
                _remote_sandboxes[sandbox_id]["current_image"] = new_image

            duration_ms = round((time.time() - start_t) * 1000.0, 2)
            return CommandResult(
                stdout=stdout if isinstance(stdout, str) else str(stdout),
                stderr=stderr if isinstance(stderr, str) else str(stderr),
                exit_code=int(exit_code),
                duration_ms=duration_ms,
            )

    raise SandboxTimeoutError(f"ConTree operation {op_id} timed out after {cmd_timeout}s")


async def upload_files(sandbox_id: str, files: Dict[str, str]) -> None:
    """
    Upload a mapping of file paths to string contents into the sandbox.

    Args:
        sandbox_id: ID of the running sandbox.
        files: Dictionary mapping file paths to contents.
    """
    # 1. Local isolated sandbox file upload
    if sandbox_id in _local_sandboxes:
        sb_dir = _local_sandboxes[sandbox_id]
        for rel_path, content in files.items():
            dest_file = sb_dir / rel_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            dest_file.write_text(content, encoding="utf-8", errors="replace")
        return

    # 2. Remote ConTree: Stage files into sandbox state for instance attachment
    if sandbox_id in _remote_sandboxes:
        _remote_sandboxes[sandbox_id]["files"].update(files)


async def destroy_sandbox(sandbox_id: str) -> None:
    """
    Clean up and release the sandbox on Nebius AI Cloud or local environment.

    Args:
        sandbox_id: ID of the sandbox to destroy.
    """
    global _active_sandboxes

    # 1. Local teardown
    if sandbox_id in _local_sandboxes or sandbox_id.startswith("sb-local-"):
        sb_dir = _local_sandboxes.pop(sandbox_id, None)
        if sb_dir and sb_dir.exists():
            shutil.rmtree(sb_dir, ignore_errors=True)
            logger.info(f"Destroyed local execution sandbox {sandbox_id}")
        async with _concurrency_lock:
            if _active_sandboxes > 0:
                _active_sandboxes -= 1
        return

    # 2. Remote ConTree teardown
    if sandbox_id in _remote_sandboxes:
        _remote_sandboxes.pop(sandbox_id, None)

    async with _concurrency_lock:
        if _active_sandboxes > 0:
            _active_sandboxes -= 1


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


def reset_sandbox_concurrency_for_testing():
    """Resets active sandbox counter for test isolation."""
    global _active_sandboxes
    _active_sandboxes = 0
