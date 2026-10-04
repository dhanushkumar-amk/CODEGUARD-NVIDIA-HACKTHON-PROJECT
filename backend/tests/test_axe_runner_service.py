"""
Unit tests for Axe Runner Service (Phase 19).
Covers:
- Valid JSON output from run-axe-check.js is parsed correctly into expected dict shape
- Malformed or empty stdout returns {"error": ..., "score": None} without raising
- Timeout during command execution is caught and returns a clear error result
- get_axe_score_for_sandbox convenience wrapper returns float or None
- ensure_playwright_installed caches repeated checks
"""
from unittest.mock import AsyncMock, patch
import pytest

from app.services.axe_runner_service import (
    ensure_playwright_installed,
    get_axe_score_for_sandbox,
    run_axe_check,
    _playwright_installed_sandboxes,
)
from app.services.sandbox_client import CommandResult, SandboxTimeoutError


@pytest.mark.asyncio
async def test_run_axe_check_parses_valid_json():
    """Ensure valid JSON payload emitted by run-axe-check.js is parsed cleanly."""
    mock_axe_json = """
    {
        "violations": [
            {
                "id": "image-alt",
                "impact": "critical",
                "description": "Images must have alternate text",
                "nodes": [{"html": "<img src='logo.png'>", "target": ["img"]}]
            },
            {
                "id": "color-contrast",
                "impact": "serious",
                "description": "Elements must meet minimum color contrast ratio",
                "nodes": [{"html": "<button>Click</button>", "target": ["button"]}]
            }
        ],
        "passes": 18,
        "incomplete": 1,
        "url_tested": "http://localhost:5173",
        "score": 90.0
    }
    """

    with patch("app.services.axe_runner_service.upload_files", new_callable=AsyncMock) as mock_upload, \
         patch("app.services.axe_runner_service.run_command", new_callable=AsyncMock) as mock_run:

        mock_run.return_value = CommandResult(
            stdout=mock_axe_json,
            stderr="",
            exit_code=0,
            duration_ms=2500.0,
        )

        res = await run_axe_check(sandbox_id="sb-axe-valid", timeout=30)

        assert res["score"] == 90.0
        assert res["passes"] == 18
        assert res["incomplete"] == 1
        assert len(res["violations"]) == 2
        assert res["url_tested"] == "http://localhost:5173"
        assert "error" not in res or res["error"] is None


@pytest.mark.asyncio
async def test_run_axe_check_handles_malformed_stdout():
    """Ensure malformed non-JSON stdout returns an error dictionary instead of crashing."""
    with patch("app.services.axe_runner_service.upload_files", new_callable=AsyncMock), \
         patch("app.services.axe_runner_service.run_command", new_callable=AsyncMock) as mock_run:

        mock_run.return_value = CommandResult(
            stdout="Some unexpected non-JSON Node traceback or text",
            stderr="ReferenceError: foo is not defined",
            exit_code=1,
            duration_ms=100.0,
        )

        res = await run_axe_check(sandbox_id="sb-axe-malformed")

        assert res["score"] is None
        assert "error" in res
        assert "JSON decode error" in res["error"] or "error" in res


@pytest.mark.asyncio
async def test_run_axe_check_handles_empty_stdout():
    """Ensure completely empty stdout returns clear error without raising."""
    with patch("app.services.axe_runner_service.upload_files", new_callable=AsyncMock), \
         patch("app.services.axe_runner_service.run_command", new_callable=AsyncMock) as mock_run:

        mock_run.return_value = CommandResult(
            stdout="",
            stderr="Process killed",
            exit_code=137,
            duration_ms=50.0,
        )

        res = await run_axe_check(sandbox_id="sb-axe-empty")

        assert res["score"] is None
        assert res["error"] == "Process killed"


@pytest.mark.asyncio
async def test_run_axe_check_handles_timeout_gracefully():
    """Ensure SandboxTimeoutError is caught and converted to an error dictionary."""
    with patch("app.services.axe_runner_service.upload_files", new_callable=AsyncMock), \
         patch("app.services.axe_runner_service.run_command", new_callable=AsyncMock) as mock_run:

        mock_run.side_effect = SandboxTimeoutError("Command execution timed out after 60s")

        res = await run_axe_check(sandbox_id="sb-axe-timeout", timeout=60)

        assert res["score"] is None
        assert "timed out" in res["error"].lower()


@pytest.mark.asyncio
async def test_get_axe_score_for_sandbox():
    """Ensure get_axe_score_for_sandbox returns the numeric score or None on failure."""
    with patch("app.services.axe_runner_service.run_axe_check", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = {"score": 75.5, "violations": []}
        score = await get_axe_score_for_sandbox("sb-test")
        assert score == 75.5

        mock_check.return_value = {"error": "server_failed_to_start", "score": None}
        score_err = await get_axe_score_for_sandbox("sb-test-err")
        assert score_err is None


@pytest.mark.asyncio
async def test_ensure_playwright_installed_caches_check():
    """Ensure ensure_playwright_installed caches previously verified sandboxes to skip re-running commands."""
    _playwright_installed_sandboxes.clear()

    with patch("app.services.axe_runner_service.run_command", new_callable=AsyncMock) as mock_run:
        # 1. Package check returns ready
        mock_run.side_effect = [
            CommandResult(stdout="ready\n", stderr="", exit_code=0),  # pkg check
            CommandResult(stdout="chromium downloaded\n", stderr="", exit_code=0),  # browser install
        ]

        ready1 = await ensure_playwright_installed("sb-cache-test")
        assert ready1 is True
        assert mock_run.call_count == 2

        # 2. Second call for same sandbox: uses cache, 0 extra run_command calls
        ready2 = await ensure_playwright_installed("sb-cache-test")
        assert ready2 is True
        assert mock_run.call_count == 2
