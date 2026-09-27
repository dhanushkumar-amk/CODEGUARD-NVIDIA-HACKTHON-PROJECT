from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
import httpx

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
    SandboxAuthenticationError,
    SandboxQuotaExceededError,
    SandboxTimeoutError,
)

client = TestClient(app)


@pytest.mark.asyncio
async def test_create_sandbox_missing_key():
    with patch.object(settings, "NEBIUS_SANDBOX_API_KEY", ""):
        with pytest.raises(SandboxAuthenticationError):
            await create_sandbox()


@pytest.mark.asyncio
async def test_create_and_destroy_sandbox():
    mock_resp = httpx.Response(
        status_code=201,
        json={"id": "sb-test-123", "status": "ready", "image": "node:20"},
        request=httpx.Request("POST", "https://api.tokenfactory.nebius.com/v1/sandboxes"),
    )
    mock_del_resp = httpx.Response(
        status_code=204,
        request=httpx.Request("DELETE", "https://api.tokenfactory.nebius.com/v1/sandboxes/sb-test-123"),
    )

    with patch.object(settings, "NEBIUS_SANDBOX_API_KEY", "real-sandbox-key"):
        with patch("app.services.sandbox_client._send_request", side_effect=[mock_resp, mock_del_resp]):
            handle = await create_sandbox()
            assert handle.sandbox_id == "sb-test-123"
            assert handle.id == "sb-test-123"
            assert handle.image == "node:20"

            await destroy_sandbox(handle.sandbox_id)


@pytest.mark.asyncio
async def test_run_command_success():
    mock_resp = httpx.Response(
        status_code=200,
        json={"stdout": "sandbox works\n", "stderr": "", "exit_code": 0, "duration_ms": 42.0},
        request=httpx.Request("POST", "https://api.tokenfactory.nebius.com/v1/sandboxes/sb-1/commands"),
    )

    with patch.object(settings, "NEBIUS_SANDBOX_API_KEY", "real-sandbox-key"):
        with patch("app.services.sandbox_client._send_request", return_value=mock_resp):
            result = await run_command("sb-1", 'echo "sandbox works"')
            assert result.stdout == "sandbox works\n"
            assert result.exit_code == 0
            assert result.duration_ms == 42.0


@pytest.mark.asyncio
async def test_run_command_failing_exit_code_is_not_an_error():
    # A failing test in the sandbox should return CommandResult with exit_code != 0
    mock_resp = httpx.Response(
        status_code=200,
        json={"stdout": "", "stderr": "Test failed\n", "exit_code": 1},
        request=httpx.Request("POST", "https://api.tokenfactory.nebius.com/v1/sandboxes/sb-1/commands"),
    )

    with patch.object(settings, "NEBIUS_SANDBOX_API_KEY", "real-sandbox-key"):
        with patch("app.services.sandbox_client._send_request", return_value=mock_resp):
            result = await run_command("sb-1", "npm test")
            assert result.exit_code == 1
            assert "Test failed" in result.stderr


@pytest.mark.asyncio
async def test_upload_files():
    mock_resp = httpx.Response(
        status_code=200,
        json={"status": "uploaded"},
        request=httpx.Request("POST", "https://api.tokenfactory.nebius.com/v1/sandboxes/sb-1/files"),
    )

    with patch.object(settings, "NEBIUS_SANDBOX_API_KEY", "real-sandbox-key"):
        with patch("app.services.sandbox_client._send_request", return_value=mock_resp):
            await upload_files("sb-1", {"src/index.js": "console.log('hi');"})


@pytest.mark.asyncio
async def test_sandbox_session_guarantees_cleanup():
    mock_handle = SandboxHandle(sandbox_id="sb-clean-1", image="node:20")

    with patch("app.services.sandbox_client.create_sandbox", new_callable=AsyncMock) as mock_create, \
         patch("app.services.sandbox_client.destroy_sandbox", new_callable=AsyncMock) as mock_destroy:
        mock_create.return_value = mock_handle

        with pytest.raises(RuntimeError):
            async with sandbox_session() as sb:
                assert sb.sandbox_id == "sb-clean-1"
                raise RuntimeError("Something failed mid-execution!")

        mock_destroy.assert_awaited_once_with("sb-clean-1")


def test_test_sandbox_echo_endpoint():
    mock_handle = SandboxHandle(sandbox_id="sb-echo-123", image="node:20")
    mock_cmd_result = CommandResult(
        stdout="sandbox works",
        stderr="",
        exit_code=0,
        duration_ms=15.0,
    )

    with patch("app.routers.test_sandbox.run_command", new_callable=AsyncMock) as mock_run, \
         patch("app.routers.test_sandbox.sandbox_session") as mock_session_ctx:

        # Mock the async context manager
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
