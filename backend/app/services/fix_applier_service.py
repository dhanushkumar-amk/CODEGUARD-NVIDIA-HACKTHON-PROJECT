"""
Fix Applier Service.
Applies specific ProposedFix patches inside isolated sandboxes branching off
clean baseline environments, ensuring zero cross-test contamination during
automated accessibility verification.
"""
import logging
from pathlib import Path
import shutil
from typing import Any, Dict, Optional

from app.models.schemas import PipelineStage, ProposedFix
from app.services.sandbox_client import (
    CommandResult,
    run_command,
    upload_files,
    SandboxError,
    _local_sandboxes,
)
from app.services.sandbox_orchestrator import (
    get_base_sandbox,
    get_or_create_base_sandbox,
    install_dependencies,
    prepare_verification_sandbox,
)
from app.state import get_scan, track_verification_sandbox

logger = logging.getLogger(__name__)


class FixApplicationError(Exception):
    """Raised when a ProposedFix cannot be safely or accurately applied to a file."""
    pass


async def _notify_applying_fix(
    scan_id: Optional[str],
    fix_id: str,
    fix_index: Optional[int] = None,
    total_fixes: Optional[int] = None,
) -> None:
    """Helper to broadcast WebSocket progress for fix application."""
    if not scan_id:
        return
    try:
        from app.routers.websocket import broadcast_progress

        if fix_index is not None and total_fixes is not None and total_fixes > 0:
            msg = f"Applying fix {fix_index}/{total_fixes} in sandbox..."
            progress = int((fix_index / total_fixes) * 100)
        else:
            msg = f"Applying fix {fix_id} in sandbox..."
            progress = 50

        await broadcast_progress(
            scan_id=scan_id,
            stage=PipelineStage.APPLYING_FIX.value,
            progress=progress,
            message=msg,
            data={"fix_id": fix_id},
        )
    except Exception as exc:
        logger.debug(f"Failed to broadcast fix application progress for scan {scan_id}: {exc}")


async def read_file_from_sandbox(sandbox_id: str, file_path: str) -> str:
    """
    Retrieves the raw content of a file located within a sandbox.
    Uses run_command() to cat the file content back out. Supports standard Linux
    containers (Nebius Cloud node:20) and falls back to Windows 'type' for local development.

    Args:
        sandbox_id: ID of the running sandbox.
        file_path: Relative or absolute path to the file inside the sandbox.

    Returns:
        String content of the file.

    Raises:
        SandboxError: If reading the file fails.
    """
    clean_path = file_path.replace("\\", "/")
    # Standard Linux cat command
    cmd = f'cat "{clean_path}"'
    res: CommandResult = await run_command(sandbox_id, cmd)

    # If running in local Windows test sandbox environment and cat is not recognized
    if res.exit_code != 0 and ("'cat' is not recognized" in res.stderr or "not found" in res.stderr.lower()):
        win_path = file_path.replace("/", "\\")
        res = await run_command(sandbox_id, f'type "{win_path}"')

    if res.exit_code != 0:
        raise SandboxError(f"Failed to read file '{file_path}' from sandbox {sandbox_id}: {res.stderr.strip()}")

    # Normalize Windows cmd.exe 'type' double-carriage return artifact (\r\r\n -> \r\n)
    return res.stdout.replace("\r\r\n", "\r\n")


def _normalize_line(line: str) -> str:
    """Helper to normalize a single line for whitespace-tolerant matching."""
    return line.strip()


def apply_fix_to_file(original_content: str, fix: ProposedFix) -> str:
    """
    Takes the full original file content and a ProposedFix.
    Performs a safe find-and-replace: locates fix.original_lines within
    original_content (allowing minor whitespace-only differences, matching the
    tolerance in validate_fix_output) and replaces it with fix.fixed_lines.

    Args:
        original_content: Full text content of the target file.
        fix: ProposedFix object containing original_lines and fixed_lines.

    Returns:
        Updated full file content with the fix safely applied.

    Raises:
        FixApplicationError: If original_lines cannot be located in original_content.
    """
    orig_snippet = fix.original_lines or fix.original_code or ""
    fixed_snippet = fix.fixed_lines or fix.remediated_code or ""

    if not orig_snippet.strip():
        raise FixApplicationError(f"ProposedFix '{fix.fix_id}' has empty original_lines.")

    # 1. Exact character-for-character match
    if orig_snippet in original_content:
        return original_content.replace(orig_snippet, fixed_snippet, 1)

    # 2. Line ending normalization match (\r\n vs \n)
    orig_c_norm = original_content.replace("\r\n", "\n")
    orig_s_norm = orig_snippet.replace("\r\n", "\n")
    fixed_s_norm = fixed_snippet.replace("\r\n", "\n")

    if orig_s_norm in orig_c_norm:
        patched = orig_c_norm.replace(orig_s_norm, fixed_s_norm, 1)
        if "\r\n" in original_content:
            patched = patched.replace("\n", "\r\n")
        return patched

    # 3. Line-by-line whitespace & indentation tolerant search
    file_lines = original_content.splitlines()
    target_lines = [l for l in orig_s_norm.splitlines() if l.strip()]
    if not target_lines:
        raise FixApplicationError(f"ProposedFix '{fix.fix_id}' target lines are empty.")

    target_norm = [_normalize_line(l) for l in target_lines]

    match_start = -1
    match_end = -1

    for i in range(len(file_lines)):
        matched_indices = []
        target_idx = 0
        for j in range(i, len(file_lines)):
            line_stripped = _normalize_line(file_lines[j])
            if not line_stripped:
                # Allow empty lines within code blocks
                continue
            if line_stripped == target_norm[target_idx]:
                matched_indices.append(j)
                target_idx += 1
                if target_idx == len(target_norm):
                    match_start = matched_indices[0]
                    match_end = matched_indices[-1]
                    break
            else:
                break
        if match_start != -1:
            break

    if match_start == -1:
        file_desc = fix.file or "target file"
        raise FixApplicationError(
            f"Could not locate original code snippet in '{file_desc}'.\n"
            f"Expected snippet:\n{orig_snippet}\n"
            f"Target file has {len(file_lines)} lines."
        )

    # Detect indentation of the matched start line in the file
    matched_orig_first_line = file_lines[match_start]
    leading_indent = matched_orig_first_line[: len(matched_orig_first_line) - len(matched_orig_first_line.lstrip())]

    # Prepare replacement lines
    replacement_lines = fixed_s_norm.splitlines()
    if replacement_lines:
        first_rep_indent = replacement_lines[0][: len(replacement_lines[0]) - len(replacement_lines[0].lstrip())]
        if not first_rep_indent and leading_indent:
            replacement_lines = [leading_indent + l if l.strip() else l for l in replacement_lines]

    # Assemble new file content
    new_file_lines = file_lines[:match_start] + replacement_lines + file_lines[match_end + 1 :]
    separator = "\r\n" if "\r\n" in original_content else "\n"
    new_content = separator.join(new_file_lines)

    if (original_content.endswith("\n") or original_content.endswith("\r\n")) and not new_content.endswith(separator):
        new_content += separator

    return new_content


async def create_fix_verification_sandbox(
    base_sandbox_id: str,
    repo_path: str,
    fix: ProposedFix,
    scan_id: str,
) -> str:
    """
    Creates an isolated verification sandbox branching off the baseline state,
    applies the ProposedFix patch, and uploads the patched file.

    ARCHITECTURE NOTE ON SANDBOX CLONING / FORKING:
    Nebius AI Cloud Sandbox API currently exposes REST primitives for provisioning
    fresh containers (/sandboxes), command execution, and file uploading, but does not
    natively support a live snapshot/clone-from-container endpoint.
    To ensure strict test isolation with zero cross-test contamination between fixes:
    1. A fresh sandbox container is provisioned via prepare_verification_sandbox().
    2. For local test environments, node_modules from base_sandbox_id is copied directly
       to the new sandbox directory to avoid redundant 15-30s npm installs.
    3. For remote environments, dependencies are cleanly installed in the new sandbox.
    4. The target file is read from the sandbox, patched via apply_fix_to_file(), and
       uploaded back, leaving all other files in a clean, reproducible state.

    Args:
        base_sandbox_id: ID of the clean baseline sandbox.
        repo_path: Path to the local repository clone.
        fix: ProposedFix to be verified.
        scan_id: Associated scan identifier.

    Returns:
        The new verification sandbox_id.

    Raises:
        FixApplicationError: If the fix cannot be applied.
        SandboxError: If container operations fail.
    """
    # 1. Provision fresh verification sandbox container
    new_sandbox_id = await prepare_verification_sandbox(
        repo_path=repo_path,
        scan_id=scan_id,
        fix_id=fix.fix_id,
    )

    # 2. Dependency optimization: copy installed node_modules from base sandbox if local
    copied_local = False
    if base_sandbox_id in _local_sandboxes and new_sandbox_id in _local_sandboxes:
        base_dir = _local_sandboxes[base_sandbox_id]
        new_dir = _local_sandboxes[new_sandbox_id]
        base_modules = base_dir / "node_modules"
        new_modules = new_dir / "node_modules"
        if base_modules.exists() and not new_modules.exists():
            try:
                shutil.copytree(base_modules, new_modules, symlinks=True)
                copied_local = True
                logger.debug(f"Copied node_modules from base sandbox {base_sandbox_id} to {new_sandbox_id}")
            except Exception as exc:
                logger.warning(f"Failed to copy node_modules locally: {exc}")

    if not copied_local:
        install_res = await install_dependencies(
            sandbox_id=new_sandbox_id,
            repo_path=repo_path,
            scan_id=scan_id,
        )
        if install_res.exit_code != 0:
            logger.warning(
                f"Dependency installation in verification sandbox {new_sandbox_id} completed with code {install_res.exit_code}"
            )

    # 3. Read target file from the newly prepared sandbox
    target_file = fix.file
    original_content = await read_file_from_sandbox(new_sandbox_id, target_file)

    # 4. Safely apply the fix patch to the content
    patched_content = apply_fix_to_file(original_content, fix)

    # 5. Write the patched file back into the sandbox via upload_files
    await upload_files(new_sandbox_id, {target_file: patched_content})
    logger.info(f"Successfully applied fix {fix.fix_id} to '{target_file}' in sandbox {new_sandbox_id}")

    # Track in state under verification_sandbox_ids
    track_verification_sandbox(scan_id=scan_id, sandbox_id=new_sandbox_id, fix_id=fix.fix_id)

    return new_sandbox_id


async def apply_and_prepare_fix(
    fix: ProposedFix,
    repo_path: str,
    scan_id: str,
    base_sandbox_id: Optional[str] = None,
    fix_index: Optional[int] = None,
    total_fixes: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Orchestrates applying a ProposedFix inside an isolated verification sandbox.
    Broadcasts WebSocket progress notifications.
    Catches application and sandbox errors gracefully, returning structured status
    without crashing the overall audit pipeline.

    Args:
        fix: ProposedFix instance.
        repo_path: Path to the local repository clone.
        scan_id: Associated scan identifier.
        base_sandbox_id: Optional existing clean baseline sandbox ID.
        fix_index: Optional current fix index for progress reporting (e.g. 3).
        total_fixes: Optional total fixes count for progress reporting (e.g. 8).

    Returns:
        Dict: {"sandbox_id": str | None, "fix_id": str, "status": "applied" | "failed", "error": str | None}
    """
    await _notify_applying_fix(
        scan_id=scan_id,
        fix_id=fix.fix_id,
        fix_index=fix_index,
        total_fixes=total_fixes,
    )

    resolved_base_id = base_sandbox_id or get_base_sandbox(scan_id)
    if not resolved_base_id:
        try:
            resolved_base_id = await get_or_create_base_sandbox(repo_path=repo_path, scan_id=scan_id)
        except Exception as exc:
            err_msg = f"Failed to initialize base sandbox: {exc}"
            logger.error(err_msg, exc_info=True)
            fix.status = "failed"
            fix.failure_reason = err_msg
            return {
                "sandbox_id": None,
                "fix_id": fix.fix_id,
                "status": "failed",
                "error": err_msg,
            }

    try:
        sandbox_id = await create_fix_verification_sandbox(
            base_sandbox_id=resolved_base_id,
            repo_path=repo_path,
            fix=fix,
            scan_id=scan_id,
        )
        return {
            "sandbox_id": sandbox_id,
            "fix_id": fix.fix_id,
            "status": "applied",
            "error": None,
        }
    except FixApplicationError as exc:
        err_msg = f"Patch location mismatch or invalid target: {exc}"
        logger.warning(f"Fix {fix.fix_id} application error: {err_msg}")
        fix.status = "failed"
        fix.failure_reason = err_msg
        return {
            "sandbox_id": None,
            "fix_id": fix.fix_id,
            "status": "failed",
            "error": err_msg,
        }
    except Exception as exc:
        err_msg = f"Unexpected error applying fix in sandbox: {exc}"
        logger.error(f"Fix {fix.fix_id} unexpected failure: {err_msg}", exc_info=True)
        fix.status = "failed"
        fix.failure_reason = err_msg
        return {
            "sandbox_id": None,
            "fix_id": fix.fix_id,
            "status": "failed",
            "error": err_msg,
        }
