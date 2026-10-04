"""
Unit tests for Sandbox Orchestrator service (Phase 17).
Covers:
- get_or_create_base_sandbox reusing existing sandbox for same scan_id without re-provisioning
- install_dependencies detecting yarn.lock vs package-lock.json / npm
- cleanup_scan_sandboxes destroying all base and verification sandboxes
- failed npm install returning a clear CommandResult without throwing
- file collection correctly ignoring node_modules, .git, and binaries
"""
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from app.config import settings
from app.services.sandbox_client import (
    CommandResult,
    SandboxHandle,
    SandboxCommandError,
    SandboxTimeoutError,
)
from app.services.sandbox_orchestrator import (
    cleanup_scan_sandboxes,
    collect_repo_files,
    get_or_create_base_sandbox,
    install_dependencies,
    prepare_verification_sandbox,
)
from app.state import (
    create_scan,
    get_base_sandbox,
    get_scan,
    get_scan_sandboxes,
    track_base_sandbox,
    track_verification_sandbox,
)


@pytest.mark.asyncio
async def test_get_or_create_base_sandbox_reuses_existing(tmp_path: Path):
    """Ensure get_or_create_base_sandbox returns the SAME sandbox_id on repeat calls for the same scan_id."""
    scan_id = create_scan("https://github.com/example/test-repo")
    (tmp_path / "package.json").write_text('{"name": "test"}', encoding="utf-8")

    mock_handle = SandboxHandle(sandbox_id="sb-base-test-1", image=settings.NEBIUS_SANDBOX_DEFAULT_IMAGE)
    mock_install_res = CommandResult(stdout="installed", stderr="", exit_code=0, duration_ms=100.0)

    with patch("app.services.sandbox_orchestrator.create_sandbox", new_callable=AsyncMock) as mock_create, \
         patch("app.services.sandbox_orchestrator.upload_files", new_callable=AsyncMock) as mock_upload, \
         patch("app.services.sandbox_orchestrator.install_dependencies", new_callable=AsyncMock) as mock_install:

        mock_create.return_value = mock_handle
        mock_install.return_value = mock_install_res

        # First call: provisions, uploads repo files, and installs
        sb_id_1 = await get_or_create_base_sandbox(repo_path=str(tmp_path), scan_id=scan_id)
        assert sb_id_1 == "sb-base-test-1"
        assert mock_create.call_count == 1
        assert mock_upload.call_count == 1
        assert mock_install.call_count == 1

        # Second call with same scan_id: returns existing without recreating
        sb_id_2 = await get_or_create_base_sandbox(repo_path=str(tmp_path), scan_id=scan_id)
        assert sb_id_2 == "sb-base-test-1"
        assert mock_create.call_count == 1  # Not called again
        assert mock_upload.call_count == 1  # Not called again
        assert mock_install.call_count == 1  # Not called again


@pytest.mark.asyncio
async def test_install_dependencies_detects_yarn_vs_package_lock(tmp_path: Path):
    """Ensure install_dependencies executes 'yarn install' when yarn.lock is present, otherwise 'npm install'."""
    # 1. Test yarn.lock presence
    yarn_dir = tmp_path / "yarn_project"
    yarn_dir.mkdir()
    (yarn_dir / "package.json").write_text('{"name": "yarn-app"}', encoding="utf-8")
    (yarn_dir / "yarn.lock").write_text("# yarn lockfile v1\n", encoding="utf-8")

    with patch("app.services.sandbox_orchestrator.run_command", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = CommandResult(stdout="yarn success", stderr="", exit_code=0, duration_ms=120.0)

        res_yarn = await install_dependencies(sandbox_id="sb-yarn-01", repo_path=str(yarn_dir))
        assert res_yarn.exit_code == 0
        mock_run.assert_called_once_with(
            sandbox_id="sb-yarn-01",
            command="yarn install",
            timeout=settings.NPM_INSTALL_TIMEOUT_SECONDS,
        )

    # 2. Test package-lock.json (npm)
    npm_dir = tmp_path / "npm_project"
    npm_dir.mkdir()
    (npm_dir / "package.json").write_text('{"name": "npm-app"}', encoding="utf-8")
    (npm_dir / "package-lock.json").write_text('{"lockfileVersion": 2}', encoding="utf-8")

    with patch("app.services.sandbox_orchestrator.run_command", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = CommandResult(stdout="npm success", stderr="", exit_code=0, duration_ms=150.0)

        res_npm = await install_dependencies(sandbox_id="sb-npm-01", repo_path=str(npm_dir))
        assert res_npm.exit_code == 0
        mock_run.assert_called_once_with(
            sandbox_id="sb-npm-01",
            command="npm install",
            timeout=settings.NPM_INSTALL_TIMEOUT_SECONDS,
        )


@pytest.mark.asyncio
async def test_cleanup_scan_sandboxes_destroys_all_tracked():
    """Ensure cleanup_scan_sandboxes destroys all base and verification sandboxes associated with scan_id."""
    scan_id = create_scan("https://github.com/example/cleanup-repo")
    track_base_sandbox(scan_id, "sb-base-clean")
    track_verification_sandbox(scan_id, "sb-verify-1", "fix_01")
    track_verification_sandbox(scan_id, "sb-verify-2", "fix_02")

    tracked_before = get_scan_sandboxes(scan_id)
    assert set(tracked_before) == {"sb-base-clean", "sb-verify-1", "sb-verify-2"}

    destroyed = []
    async def mock_destroy(sb_id: str):
        destroyed.append(sb_id)

    with patch("app.services.sandbox_orchestrator.destroy_sandbox", side_effect=mock_destroy):
        await cleanup_scan_sandboxes(scan_id)

    assert set(destroyed) == {"sb-base-clean", "sb-verify-1", "sb-verify-2"}
    assert get_scan_sandboxes(scan_id) == []
    assert get_base_sandbox(scan_id) is None


@pytest.mark.asyncio
async def test_failed_npm_install_returns_clear_result_rather_than_throwing(tmp_path: Path):
    """Ensure a failed npm install returns a CommandResult with error details without raising exceptions."""
    repo_dir = tmp_path / "broken_repo"
    repo_dir.mkdir()
    (repo_dir / "package.json").write_text('{"name": "broken"}', encoding="utf-8")

    # 1. Command exit code != 0 (e.g. dependency resolution conflict)
    with patch("app.services.sandbox_orchestrator.run_command", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = CommandResult(
            stdout="",
            stderr="npm ERR! ERESOLVE unable to resolve dependency tree",
            exit_code=1,
            duration_ms=450.0,
        )

        res = await install_dependencies("sb-broken", repo_path=str(repo_dir))
        assert res.exit_code == 1
        assert "npm ERR! ERESOLVE" in res.stderr

    # 2. Timeout error caught and transformed to clear CommandResult
    with patch("app.services.sandbox_orchestrator.run_command", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = SandboxTimeoutError("Command execution timed out after 180s")

        res_timeout = await install_dependencies("sb-timeout", repo_path=str(repo_dir))
        assert res_timeout.exit_code != 0
        assert "timed out" in res_timeout.stderr.lower()

    # 3. Communication/command error caught and transformed
    with patch("app.services.sandbox_orchestrator.run_command", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = SandboxCommandError("Sandbox container crashed")

        res_err = await install_dependencies("sb-err", repo_path=str(repo_dir))
        assert res_err.exit_code == 1
        assert "Sandbox container crashed" in res_err.stderr


@pytest.mark.asyncio
async def test_prepare_verification_sandbox(tmp_path: Path):
    """Ensure prepare_verification_sandbox spins up a container, uploads code, and tracks it under scan+fix."""
    scan_id = create_scan("https://github.com/example/verification-repo")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "App.tsx").write_text("export default function App() { return <div>Test</div>; }", encoding="utf-8")

    mock_handle = SandboxHandle(sandbox_id="sb-ver-fix-1", image=settings.NEBIUS_SANDBOX_DEFAULT_IMAGE)

    with patch("app.services.sandbox_orchestrator.create_sandbox", new_callable=AsyncMock) as mock_create, \
         patch("app.services.sandbox_orchestrator.upload_files", new_callable=AsyncMock) as mock_upload:

        mock_create.return_value = mock_handle

        sb_id = await prepare_verification_sandbox(
            repo_path=str(tmp_path),
            scan_id=scan_id,
            fix_id="fix_test_42",
        )

        assert sb_id == "sb-ver-fix-1"
        mock_create.assert_called_once_with(image=settings.NEBIUS_SANDBOX_DEFAULT_IMAGE)
        mock_upload.assert_called_once()
        uploaded_files = mock_upload.call_args[1]["files"]
        assert "src/App.tsx" in uploaded_files

        # Verify tracking in state
        scan = get_scan(scan_id)
        assert "sb-ver-fix-1" in scan["verification_sandbox_ids"]
        assert scan["sandbox_map"].get("fix_test_42") == "sb-ver-fix-1"


def test_collect_repo_files_ignores_unwanted_dirs(tmp_path: Path):
    """Ensure collect_repo_files ignores node_modules, .git, build dirs, and binary extensions."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.tsx").write_text("<div />", encoding="utf-8")
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")

    # Ignored directory structures
    (tmp_path / "node_modules" / "react").mkdir(parents=True)
    (tmp_path / "node_modules" / "react" / "index.js").write_text("module.exports = {};", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]", encoding="utf-8")
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "bundle.js").write_text("alert(1);", encoding="utf-8")

    # Ignored binary extension
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    files = collect_repo_files(tmp_path)

    assert "src/index.tsx" in files
    assert "package.json" in files
    assert not any("node_modules" in k for k in files)
    assert not any(".git" in k for k in files)
    assert not any("dist" in k for k in files)
    assert not any(k.endswith(".png") for k in files)
