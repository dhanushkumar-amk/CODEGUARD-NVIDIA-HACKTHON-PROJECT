"""
Business Logic Services Package.
Exposes clients and orchestration services for LLM inference, sandboxing, git, scanning, remediation, and reporting.
"""
from app.services.llm_client import (
    call_nemotron,
    call_nemotron_fast,
    call_nemotron_ultra,
    call_with_escalation,
    get_total_cost_so_far,
    get_cost_breakdown,
    get_token_usage_stats,
    get_scan_usage_stats,
    reset_cost_tracker,
    UltraBudgetExceededError,
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
from app.services.detector_service import (
    rule_based_precheck,
    build_detection_prompt,
    detect_violations_in_chunk,
    detect_violations,
)
from app.services.classifier_service import (
    normalize_category,
    calculate_severity_score,
    map_score_to_severity_label,
    classify_violations,
    summarize_violations,
)
from app.services.diagnosis_service import (
    get_surrounding_context,
    build_diagnosis_prompt,
    get_templated_diagnosis,
    diagnose_violation,
    diagnose_all,
)
from app.services.explainer_service import (
    build_explanation_prompt,
    generate_explanation,
    generate_all_explanations,
    truncate_at_sentence_boundary,
)
from app.services.fixer_service import (
    get_fix_context,
    build_fix_prompt,
    validate_fix_output,
    generate_fix,
    generate_all_fixes,
    generate_remediation_patch,
)
from app.services.verifier_service import verify_patch_in_sandbox
from app.services.sandbox_orchestrator import (
    prepare_verification_sandbox,
    install_dependencies,
    get_or_create_base_sandbox,
    cleanup_scan_sandboxes,
    collect_repo_files,
)
from app.services.report_service import generate_compliance_report

__all__ = [
    "call_nemotron",
    "call_nemotron_fast",
    "call_nemotron_ultra",
    "call_with_escalation",
    "get_total_cost_so_far",
    "get_cost_breakdown",
    "get_token_usage_stats",
    "get_scan_usage_stats",
    "reset_cost_tracker",
    "UltraBudgetExceededError",
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
    "rule_based_precheck",
    "build_detection_prompt",
    "detect_violations_in_chunk",
    "detect_violations",
    "normalize_category",
    "calculate_severity_score",
    "map_score_to_severity_label",
    "classify_violations",
    "summarize_violations",
    "get_surrounding_context",
    "build_diagnosis_prompt",
    "get_templated_diagnosis",
    "diagnose_violation",
    "diagnose_all",
    "build_explanation_prompt",
    "generate_explanation",
    "generate_all_explanations",
    "truncate_at_sentence_boundary",
    "get_fix_context",
    "build_fix_prompt",
    "validate_fix_output",
    "generate_fix",
    "generate_all_fixes",
    "generate_remediation_patch",
    "verify_patch_in_sandbox",
    "prepare_verification_sandbox",
    "install_dependencies",
    "get_or_create_base_sandbox",
    "cleanup_scan_sandboxes",
    "collect_repo_files",
    "generate_compliance_report",
]
