"""
Test Runner Service for Sandboxes.
Detects, executes, and evaluates test suites inside isolated verification sandboxes
to safeguard against code regressions during automated remediation.
"""
import json
import logging
import os
from pathlib import Path
import re
import time
from typing import Optional, Tuple

from app.models.schemas import TestRunResult
from app.services.sandbox_client import (
    CommandResult,
    SandboxTimeoutError,
    run_command,
)

logger = logging.getLogger(__name__)

# Common test script names in priority order
COMMON_TEST_SCRIPTS = ["test", "test:unit", "test:ci"]

# File extensions / patterns indicating test files
TEST_FILE_PATTERNS = [
    r"\.test\.[jt]sx?$",
    r"\.spec\.[jt]sx?$",
]
TEST_DIR_PATTERNS = ["__tests__", "tests"]


def detect_test_command(repo_path: str) -> Optional[str]:
    """
    Reads package.json's "scripts" section in priority order:
    "test", "test:unit", "test:ci".
    
    Returns:
        "npm test" if script is literally named "test"
        "npm run <script>" for other matched scripts (e.g. "npm run test:unit")
        None if no recognizable test script exists
    """
    pkg_path = Path(repo_path) / "package.json"
    if not pkg_path.is_file():
        return None

    try:
        with open(pkg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        logger.warning(f"Failed to parse package.json at {pkg_path}: {exc}")
        return None

    scripts = data.get("scripts", {})
    if not isinstance(scripts, dict):
        return None

    for script_name in COMMON_TEST_SCRIPTS:
        cmd = scripts.get(script_name)
        if cmd and isinstance(cmd, str):
            # Check if it's the standard empty npm init placeholder:
            # 'echo "Error: no test specified" && exit 1'
            if "no test specified" in cmd.lower():
                logger.info(f"Ignoring placeholder test script '{script_name}': {cmd}")
                continue

            if script_name == "test":
                return "npm test"
            return f"npm run {script_name}"

    return None


def has_test_files(repo_path: str) -> bool:
    """
    Sanity cross-check: scans the repository directory to see if it contains
    any *.test.*, *.spec.*, or __tests__/ files.
    """
    root = Path(repo_path)
    if not root.is_dir():
        return False

    ignored_dirs = {"node_modules", ".git", "dist", "build", ".next", ".turbo"}

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored directories
        dirnames[:] = [d for d in dirnames if d not in ignored_dirs]

        current_dir_name = Path(dirpath).name
        if any(td in current_dir_name for td in TEST_DIR_PATTERNS):
            if filenames:
                return True

        for fn in filenames:
            for pattern in TEST_FILE_PATTERNS:
                if re.search(pattern, fn, re.IGNORECASE):
                    return True

    return False


def parse_test_counts(output: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Best-effort extraction of passed and failed test counts from test runner stdout/stderr.
    Supports Jest, Vitest, Node Test Runner, and Mocha styles.
    
    Returns:
        (passed_count, failed_count)
    """
    if not output:
        return None, None

    passed_count: Optional[int] = None
    failed_count: Optional[int] = None

    # Pattern 1: Jest / Vitest summary lines
    # "Tests:       2 passed, 1 failed, 3 total"
    # "Tests:       4 passed, 4 total"
    # "Tests:       1 failed, 1 total"
    jest_tests_m = re.search(r"Tests:\s*(.+)", output, re.IGNORECASE)
    if jest_tests_m:
        segment = jest_tests_m.group(1)
        pass_m = re.search(r"(\d+)\s+passed", segment, re.IGNORECASE)
        fail_m = re.search(r"(\d+)\s+failed", segment, re.IGNORECASE)
        if pass_m:
            passed_count = int(pass_m.group(1))
        if fail_m:
            failed_count = int(fail_m.group(1))
        if passed_count is not None or failed_count is not None:
            return passed_count, (failed_count or 0 if passed_count else failed_count)

    # Pattern 2: Node built-in test runner (TAP / spec reporter)
    # "ℹ pass 3" / "ℹ fail 1"
    node_pass_m = re.search(r"ℹ\s+pass\s+(\d+)", output, re.IGNORECASE)
    node_fail_m = re.search(r"ℹ\s+fail\s+(\d+)", output, re.IGNORECASE)
    if node_pass_m or node_fail_m:
        if node_pass_m:
            passed_count = int(node_pass_m.group(1))
        if node_fail_m:
            failed_count = int(node_fail_m.group(1))
        return passed_count, (failed_count or 0 if passed_count else failed_count)

    # Pattern 3: Mocha style
    # "5 passing (12ms)"
    # "2 failing"
    mocha_pass_m = re.search(r"(\d+)\s+passing", output, re.IGNORECASE)
    mocha_fail_m = re.search(r"(\d+)\s+failing", output, re.IGNORECASE)
    if mocha_pass_m or mocha_fail_m:
        if mocha_pass_m:
            passed_count = int(mocha_pass_m.group(1))
        if mocha_fail_m:
            failed_count = int(mocha_fail_m.group(1))
        return passed_count, (failed_count or 0 if passed_count else failed_count)

    # Pattern 4: Generic "X passed, Y failed" anywhere in text
    generic_pass_m = re.search(r"(\d+)\s+passed", output, re.IGNORECASE)
    generic_fail_m = re.search(r"(\d+)\s+failed", output, re.IGNORECASE)
    if generic_pass_m:
        passed_count = int(generic_pass_m.group(1))
    if generic_fail_m:
        failed_count = int(generic_fail_m.group(1))

    return passed_count, failed_count


async def run_test_suite(
    sandbox_id: str,
    repo_path: str,
    timeout: int = 60,
) -> TestRunResult:
    """
    Executes the project's test suite inside the specified sandbox container.
    Guarantees that test execution never breaks the scan/verification pipeline.
    
    Args:
        sandbox_id: Running sandbox container ID.
        repo_path: Local path to the repository (used to inspect package.json).
        timeout: Maximum seconds to wait for tests to complete before aborting.
        
    Returns:
        TestRunResult with status ('passed', 'failed', 'timeout', 'no_tests_found', 'error'),
        pass/fail boolean, counts, raw stdout/stderr, and duration.
    """
    cmd = detect_test_command(repo_path)
    if not cmd:
        logger.info(f"No test command detected for repo at {repo_path}. Skipping test suite.")
        return TestRunResult(
            status="no_tests_found",
            passed=None,
            passed_count=None,
            failed_count=None,
            raw_output="",
            duration_seconds=0.0,
        )

    # Sanity check: command found but no test files found
    test_files_exist = has_test_files(repo_path)
    if not test_files_exist:
        logger.warning(
            f"Test command '{cmd}' detected in package.json, but no test files "
            f"(*.test.*, *.spec.*, __tests__/) were found in {repo_path}. "
            "Proceeding with test execution but flagging as suspicious."
        )

    logger.info(f"Running test command '{cmd}' in sandbox {sandbox_id} with timeout={timeout}s")
    start_time = time.time()

    try:
        result: CommandResult = await run_command(
            sandbox_id=sandbox_id,
            command=cmd,
            timeout=timeout,
        )
        duration = round(time.time() - start_time, 2)
        raw_output = f"{result.stdout}\n{result.stderr}".strip()

        passed_count, failed_count = parse_test_counts(raw_output)

        if result.exit_code == 0:
            return TestRunResult(
                status="passed",
                passed=True,
                passed_count=passed_count,
                failed_count=failed_count or 0,
                raw_output=raw_output,
                duration_seconds=duration,
            )
        else:
            return TestRunResult(
                status="failed",
                passed=False,
                passed_count=passed_count or 0,
                failed_count=failed_count if failed_count is not None else 1,
                raw_output=raw_output,
                duration_seconds=duration,
            )

    except SandboxTimeoutError as exc:
        duration = round(time.time() - start_time, 2)
        logger.warning(f"Test suite execution timed out after {timeout}s in sandbox {sandbox_id}: {exc}")

        # Kill hung processes inside the sandbox so they don't consume resources
        try:
            kill_cmd = "pkill -f node || taskkill /f /im node.exe || true"
            await run_command(sandbox_id=sandbox_id, command=kill_cmd, timeout=5)
        except Exception as kill_err:
            logger.debug(f"Process cleanup attempted after timeout in {sandbox_id}: {kill_err}")

        return TestRunResult(
            status="timeout",
            passed=None,
            passed_count=None,
            failed_count=None,
            raw_output=f"Test run timed out after {timeout}s",
            duration_seconds=duration,
        )

    except Exception as exc:
        duration = round(time.time() - start_time, 2)
        logger.error(f"Error executing test suite in sandbox {sandbox_id}: {exc}", exc_info=True)
        return TestRunResult(
            status="error",
            passed=None,
            passed_count=None,
            failed_count=None,
            raw_output=f"Error executing test suite: {str(exc)}",
            duration_seconds=duration,
        )
