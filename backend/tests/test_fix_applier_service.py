"""
Unit tests for Fix Applier Service (Phase 18).
Covers:
- apply_fix_to_file correctly replaces matching content
- apply_fix_to_file tolerates minor whitespace differences (line endings, trailing spaces, indentation)
- apply_fix_to_file raises FixApplicationError when original_lines is not found
- A failed fix application correctly sets status="failed" without crashing the pipeline
- read_file_from_sandbox properly fetches and decodes sandbox file content
"""
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from app.models.schemas import ProposedFix
from app.services.fix_applier_service import (
    apply_and_prepare_fix,
    apply_fix_to_file,
    create_fix_verification_sandbox,
    read_file_from_sandbox,
    FixApplicationError,
)
from app.services.sandbox_client import CommandResult, SandboxError
from app.state import create_scan, get_scan


def test_apply_fix_to_file_replaces_exact_match():
    """Ensure exact matching lines are replaced cleanly without touching surrounding code."""
    original_code = (
        'import React from "react";\n'
        '\n'
        'export function Header() {\n'
        '  return (\n'
        '    <header>\n'
        '      <img src="/logo.svg" className="h-8" />\n'
        '    </header>\n'
        '  );\n'
        '}\n'
    )

    fix = ProposedFix(
        fix_id="fix_test_01",
        violation_id="viol_01",
        file="src/components/Header.tsx",
        original_lines='      <img src="/logo.svg" className="h-8" />',
        fixed_lines='      <img src="/logo.svg" alt="Company Logo" className="h-8" />',
    )

    result = apply_fix_to_file(original_code, fix)
    assert '<img src="/logo.svg" alt="Company Logo" className="h-8" />' in result
    assert '<img src="/logo.svg" className="h-8" />' not in result
    assert 'export function Header() {' in result


def test_apply_fix_to_file_tolerates_whitespace_differences():
    """Ensure matching succeeds when indentation or line-ending whitespace differs slightly."""
    original_code = (
        'export function Button() {\n'
        '    return (\n'
        '        <button onClick={handleClick}>\n'
        '            Click me\n'
        '        </button>\n'
        '    );\n'
        '}\n'
    )

    # Fix provided with different indentation (2 spaces instead of 8) and extra trailing spaces
    fix = ProposedFix(
        fix_id="fix_test_02",
        violation_id="viol_02",
        file="src/components/Button.tsx",
        original_lines='  <button onClick={handleClick}>  \n    Click me  \n  </button>',
        fixed_lines='  <button onClick={handleClick} aria-label="Submit Form">\n    Click me\n  </button>',
    )

    result = apply_fix_to_file(original_code, fix)
    assert 'aria-label="Submit Form"' in result
    assert 'export function Button() {' in result


def test_apply_fix_to_file_raises_error_when_original_lines_not_found():
    """Ensure FixApplicationError is raised when the target snippet is absent."""
    original_code = (
        'export function Card() {\n'
        '  return <div>Clean card</div>;\n'
        '}\n'
    )

    fix = ProposedFix(
        fix_id="fix_test_missing",
        violation_id="viol_03",
        file="src/components/Card.tsx",
        original_lines='<input id="missing-input" type="text" />',
        fixed_lines='<input id="missing-input" type="text" aria-label="Username" />',
    )

    with pytest.raises(FixApplicationError) as exc_info:
        apply_fix_to_file(original_code, fix)

    assert "Could not locate original code snippet" in str(exc_info.value)


@pytest.mark.asyncio
async def test_failed_fix_application_sets_status_failed_without_crashing():
    """Ensure apply_and_prepare_fix records status='failed' on error without throwing unhandled exceptions."""
    scan_id = create_scan("https://github.com/example/fail-repo")

    fix = ProposedFix(
        fix_id="fix_fail_01",
        violation_id="viol_04",
        file="src/components/Nonexistent.tsx",
        original_lines='<p>Old</p>',
        fixed_lines='<p>New</p>',
    )

    with patch("app.services.fix_applier_service.get_or_create_base_sandbox", new_callable=AsyncMock) as mock_base, \
         patch("app.services.fix_applier_service.create_fix_verification_sandbox", new_callable=AsyncMock) as mock_create:

        mock_base.return_value = "sb-base-dummy"
        mock_create.side_effect = FixApplicationError("Could not locate original snippet in file")

        res = await apply_and_prepare_fix(
            fix=fix,
            repo_path="/tmp/dummy",
            scan_id=scan_id,
        )

        assert res["status"] == "failed"
        assert res["sandbox_id"] is None
        assert "Patch location mismatch" in res["error"]
        assert fix.status == "failed"
        assert fix.failure_reason is not None


@pytest.mark.asyncio
async def test_read_file_from_sandbox():
    """Ensure read_file_from_sandbox calls cat command and returns decoded content."""
    with patch("app.services.fix_applier_service.run_command", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = CommandResult(
            stdout="<header>test content</header>",
            stderr="",
            exit_code=0,
            duration_ms=15.0,
        )

        content = await read_file_from_sandbox("sb-test-read", "src/Header.tsx")
        assert content == "<header>test content</header>"
        mock_run.assert_called_once()
        cmd_called = mock_run.call_args[0][1]
        assert 'cat "src/Header.tsx"' in cmd_called
