from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.services.sandbox_client import (
    create_sandbox,
    run_command,
    upload_files,
    destroy_sandbox,
    sandbox_session,
    SandboxHandle,
    CommandResult,
    SandboxQuotaExceededError,
    SandboxTimeoutError,
    reset_sandbox_concurrency_for_testing,
    _local_sandboxes,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_concurrency():
    reset_sandbox_concurrency_for_testing()
    yield
    reset_sandbox_concurrency_for_testing()


@pytest.mark.asyncio
async def test_create_and_destroy_local_sandbox():
    """Ensure local isolated process sandbox provisions and cleans up without remote API calls."""
    handle = await create_sandbox(image="local")
    assert handle.sandbox_id.startswith("sb-local-")
    assert handle.status == "ready"

    # Test execution in sandbox
    res = await run_command(handle.sandbox_id, "echo hello_sandbox")
    assert "hello_sandbox" in res.stdout
    assert res.exit_code == 0

    await destroy_sandbox(handle.sandbox_id)
    assert handle.sandbox_id not in _local_sandboxes


@pytest.mark.asyncio
async def test_run_command_success():
    """Verify run_command executes cleanly in the provisioned sandbox."""
    handle = await create_sandbox(image="local")
    try:
        result = await run_command(handle.sandbox_id, 'echo "sandbox works"')
        assert "sandbox works" in result.stdout
        assert result.exit_code == 0
        assert result.duration_ms is not None
    finally:
        await destroy_sandbox(handle.sandbox_id)


@pytest.mark.asyncio
async def test_run_command_failing_exit_code_is_not_an_error():
    """A failing process exit code should be returned as exit_code != 0 without raising an exception."""
    handle = await create_sandbox(image="local")
    try:
        result = await run_command(handle.sandbox_id, "exit 1")
        assert result.exit_code == 1
    finally:
        await destroy_sandbox(handle.sandbox_id)


@pytest.mark.asyncio
async def test_upload_files():
    """Verify file upload writes files cleanly into the sandbox directory."""
    handle = await create_sandbox(image="local")
    try:
        await upload_files(handle.sandbox_id, {"src/test.txt": "hello_from_test"})
        sb_dir = _local_sandboxes[handle.sandbox_id]
        test_file = sb_dir / "src" / "test.txt"
        assert test_file.exists()
        assert test_file.read_text(encoding="utf-8") == "hello_from_test"
    finally:
        await destroy_sandbox(handle.sandbox_id)


@pytest.mark.asyncio
async def test_sandbox_session_guarantees_cleanup():
    """Ensure sandbox_session context manager cleans up sandbox even on exception."""
    mock_handle = SandboxHandle(sandbox_id="sb-clean-1", image="node:20-slim")

    with patch("app.services.sandbox_client.create_sandbox", new_callable=AsyncMock) as mock_create, \
         patch("app.services.sandbox_client.destroy_sandbox", new_callable=AsyncMock) as mock_destroy:
        mock_create.return_value = mock_handle

        with pytest.raises(RuntimeError):
            async with sandbox_session() as sb:
                assert sb.sandbox_id == "sb-clean-1"
                raise RuntimeError("Something failed mid-execution!")

        mock_destroy.assert_awaited_once_with("sb-clean-1")


def test_test_sandbox_echo_endpoint():
    """Verify smoke test endpoint /test-sandbox/echo."""
    mock_handle = SandboxHandle(sandbox_id="sb-echo-123", image="node:20-slim")
    mock_cmd_result = CommandResult(
        stdout="sandbox works",
        stderr="",
        exit_code=0,
        duration_ms=15.0,
    )

    with patch("app.routers.test_sandbox.run_command", new_callable=AsyncMock) as mock_run, \
         patch("app.routers.test_sandbox.sandbox_session") as mock_session_ctx:

        mock_session_ctx.return_value.__aenter__.return_value = mock_handle
        mock_session_ctx.return_value.__aexit__.return_value = None
        mock_run.return_value = mock_cmd_result

        response = client.post("/test-sandbox/echo")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["sandbox_id"] == "sb-echo-123"
        assert data["stdout"] == "sandbox works"
        assert data["exit_code"] == 0
