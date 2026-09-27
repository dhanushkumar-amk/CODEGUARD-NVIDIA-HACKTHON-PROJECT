"""
Business Logic Services Package.
Exposes clients and orchestration services for LLM inference, sandboxing, git, scanning, remediation, and reporting.
"""
from app.services.llm_client import (
    call_nemotron,
    call_nemotron_fast,
    get_total_cost_so_far,
    get_token_usage_stats,
    reset_cost_tracker,
)
from app.services.sandbox_client import (
    create_sandbox,
    destroy_sandbox,
    run_command,
    sandbox_session,
    upload_files,
)
from app.services.git_service import (
    clone_repo,
    find_frontend_files,
    cleanup_repo,
    get_repo_metadata,
    GitServiceError,
    InvalidRepoUrlError,
    RepoTooLargeError,
    RepoNotFoundError,
    CloneFailedError,
)
from app.services.scanner_service import (
    read_file_safe,
    extract_relevant_markup,
    chunk_large_file,
    prepare_scan_batch,
)
from app.services.fixer_service import generate_remediation_patch
from app.services.verifier_service import verify_patch_in_sandbox
from app.services.report_service import generate_compliance_report

__all__ = [
    "call_nemotron",
    "call_nemotron_fast",
    "get_total_cost_so_far",
    "get_token_usage_stats",
    "reset_cost_tracker",
    "create_sandbox",
    "destroy_sandbox",
    "run_command",
    "sandbox_session",
    "upload_files",
    "clone_repo",
    "find_frontend_files",
    "cleanup_repo",
    "get_repo_metadata",
    "GitServiceError",
    "InvalidRepoUrlError",
    "RepoTooLargeError",
    "RepoNotFoundError",
    "CloneFailedError",
    "read_file_safe",
    "extract_relevant_markup",
    "chunk_large_file",
    "prepare_scan_batch",
    "generate_remediation_patch",
    "verify_patch_in_sandbox",
    "generate_compliance_report",
]
