"""
Unit tests for Test Runner Service (Phase 21).
Covers test command detection, test file discovery, pass/fail execution,
timeout handling and hung process cleanup, and test count parsing.
"""
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from app.models.schemas import TestRunResult
from app.services.sandbox_client import CommandResult, SandboxTimeoutError
from app.services.test_runner_service import (
    detect_test_command,
    has_test_files,
    parse_test_counts,
    run_test_suite,
)


@pytest.fixture
def temp_repo(tmp_path: Path):
    """Fixture providing a temporary repo directory structure."""
    return tmp_path


class TestDetectTestCommand:
    def test_finds_test_script(self, temp_repo: Path):
        pkg = temp_repo / "package.json"
        pkg.write_text(json.dumps({"scripts": {"test": "jest", "build": "tsc"}}), encoding="utf-8")
        assert detect_test_command(str(temp_repo)) == "npm test"

    def test_finds_test_unit_script(self, temp_repo: Path):
        pkg = temp_repo / "package.json"
        pkg.write_text(json.dumps({"scripts": {"test:unit": "vitest run"}}), encoding="utf-8")
        assert detect_test_command(str(temp_repo)) == "npm run test:unit"

    def test_finds_test_ci_script(self, temp_repo: Path):
        pkg = temp_repo / "package.json"
        pkg.write_text(json.dumps({"scripts": {"test:ci": "jest --ci"}}), encoding="utf-8")
        assert detect_test_command(str(temp_repo)) == "npm run test:ci"

    def test_priority_order_prefers_test_over_unit(self, temp_repo: Path):
        pkg = temp_repo / "package.json"
        pkg.write_text(
            json.dumps({"scripts": {"test": "jest", "test:unit": "vitest", "test:ci": "jest --ci"}}),
            encoding="utf-8",
        )
        assert detect_test_command(str(temp_repo)) == "npm test"

    def test_returns_none_when_no_package_json(self, temp_repo: Path):
        assert detect_test_command(str(temp_repo)) is None

    def test_returns_none_when_no_test_script_exists(self, temp_repo: Path):
        pkg = temp_repo / "package.json"
        pkg.write_text(json.dumps({"scripts": {"build": "vite build", "start": "node server.js"}}), encoding="utf-8")
        assert detect_test_command(str(temp_repo)) is None

    def test_ignores_npm_init_placeholder(self, temp_repo: Path):
        pkg = temp_repo / "package.json"
        pkg.write_text(
            json.dumps({"scripts": {"test": 'echo "Error: no test specified" && exit 1'}}),
            encoding="utf-8",
        )
        assert detect_test_command(str(temp_repo)) is None


class TestHasTestFiles:
    def test_finds_test_js_file(self, temp_repo: Path):
        src = temp_repo / "src"
        src.mkdir()
        (src / "app.test.js").write_text("// test", encoding="utf-8")
        assert has_test_files(str(temp_repo)) is True

    def test_finds_spec_tsx_file(self, temp_repo: Path):
        src = temp_repo / "src"
        src.mkdir()
        (src / "Header.spec.tsx").write_text("// spec", encoding="utf-8")
        assert has_test_files(str(temp_repo)) is True

    def test_finds_tests_directory(self, temp_repo: Path):
        tests_dir = temp_repo / "__tests__"
        tests_dir.mkdir()
        (tests_dir / "helper.js").write_text("// helper", encoding="utf-8")
        assert has_test_files(str(temp_repo)) is True

    def test_returns_false_when_no_tests(self, temp_repo: Path):
        src = temp_repo / "src"
        src.mkdir()
        (src / "App.tsx").write_text("export default function App() {}", encoding="utf-8")
        assert has_test_files(str(temp_repo)) is False


class TestParseTestCounts:
    def test_parses_jest_output(self):
        output = """
PASS src/App.test.tsx
Tests:       3 passed, 1 failed, 4 total
Snapshots:   0 total
Time:        1.234 s
"""
        passed, failed = parse_test_counts(output)
        assert passed == 3
        assert failed == 1

    def test_parses_all_passed_jest(self):
        output = """
PASS src/App.test.tsx
Tests:       5 passed, 5 total
Snapshots:   0 total
Time:        0.82 s
"""
        passed, failed = parse_test_counts(output)
        assert passed == 5
        assert failed == 0

    def test_parses_node_test_runner_output(self):
        output = """
ℹ tests 4
ℹ suites 0
ℹ pass 3
ℹ fail 1
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 42.12
"""
        passed, failed = parse_test_counts(output)
        assert passed == 3
        assert failed == 1

    def test_parses_mocha_output(self):
        output = "  4 passing (15ms)\n  1 failing"
        passed, failed = parse_test_counts(output)
        assert passed == 4
        assert failed == 1

    def test_returns_none_when_unmatched(self):
        passed, failed = parse_test_counts("Some non-test output string")
        assert passed is None
        assert failed is None


@pytest.mark.asyncio
class TestRunTestSuite:
    async def test_no_test_command_returns_no_tests_found(self, temp_repo: Path):
        result = await run_test_suite("sb_123", str(temp_repo))
        assert result.status == "no_tests_found"
        assert result.passed is None
        assert result.passed_count is None
        assert result.failed_count is None

    async def test_passing_test_run(self, temp_repo: Path):
        pkg = temp_repo / "package.json"
        pkg.write_text(json.dumps({"scripts": {"test": "jest"}}), encoding="utf-8")

        mock_cmd_result = CommandResult(
            stdout="PASS src/Header.test.js\nTests: 2 passed, 2 total\n",
            stderr="",
            exit_code=0,
            duration_ms=450.0,
        )

        with patch("app.services.test_runner_service.run_command", new=AsyncMock(return_value=mock_cmd_result)) as mock_run:
            res: TestRunResult = await run_test_suite("sb_test", str(temp_repo))
            assert res.status == "passed"
            assert res.passed is True
            assert res.passed_count == 2
            assert res.failed_count == 0
            assert "PASS src/Header.test.js" in res.raw_output
            mock_run.assert_called_once_with(sandbox_id="sb_test", command="npm test", timeout=60)

    async def test_failing_test_run_captures_output(self, temp_repo: Path):
        pkg = temp_repo / "package.json"
        pkg.write_text(json.dumps({"scripts": {"test": "jest"}}), encoding="utf-8")

        mock_cmd_result = CommandResult(
            stdout="FAIL src/Header.test.js\nTests: 1 passed, 1 failed, 2 total\n",
            stderr="AssertionError: Expected true to be false",
            exit_code=1,
            duration_ms=510.0,
        )

        with patch("app.services.test_runner_service.run_command", new=AsyncMock(return_value=mock_cmd_result)):
            res: TestRunResult = await run_test_suite("sb_test", str(temp_repo))
            assert res.status == "failed"
            assert res.passed is False
            assert res.passed_count == 1
            assert res.failed_count == 1
            assert "AssertionError" in res.raw_output

    async def test_timeout_returns_timeout_and_kills_process(self, temp_repo: Path):
        pkg = temp_repo / "package.json"
        pkg.write_text(json.dumps({"scripts": {"test": "jest"}}), encoding="utf-8")

        # First run_command call raises SandboxTimeoutError, second call is the kill command
        mock_run = AsyncMock()
        mock_run.side_effect = [
            SandboxTimeoutError("Timed out after 10s"),
            CommandResult(stdout="killed", stderr="", exit_code=0, duration_ms=10.0),
        ]

        with patch("app.services.test_runner_service.run_command", new=mock_run):
            res: TestRunResult = await run_test_suite("sb_test", str(temp_repo), timeout=10)
            assert res.status == "timeout"
            assert res.passed is None
            assert "timed out" in res.raw_output.lower()

            # Confirm kill command was dispatched
            assert mock_run.call_count == 2
            kill_call = mock_run.call_args_list[1]
            assert "pkill" in kill_call[1]["command"] or "taskkill" in kill_call[1]["command"]
