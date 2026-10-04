"""
CodeGuard Core Pydantic Schemas.
Implements data contracts for violations, remediation patches, sandbox verifications,
audit reports, scan requests, and WebSocket progress messages.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ViolationSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    SERIOUS = "serious"
    MEDIUM = "medium"
    MODERATE = "moderate"
    LOW = "low"
    MINOR = "minor"


class ViolationCategory(str, Enum):
    MISSING_ALT_TEXT = "MISSING_ALT_TEXT"
    UNLABELED_FORM_FIELD = "UNLABELED_FORM_FIELD"
    NON_INTERACTIVE_CLICK = "NON_INTERACTIVE_CLICK"
    EMPTY_LINK_OR_BUTTON = "EMPTY_LINK_OR_BUTTON"
    LOW_CONTRAST = "LOW_CONTRAST"
    HEADING_ORDER = "HEADING_ORDER"
    MISSING_LANDMARK = "MISSING_LANDMARK"
    KEYBOARD_TRAP = "KEYBOARD_TRAP"
    MISSING_LANG = "MISSING_LANG"
    ARIA_MISUSE = "ARIA_MISUSE"
    FOCUS_MANAGEMENT = "FOCUS_MANAGEMENT"
    OTHER = "OTHER"


class PipelineStage(str, Enum):
    INIT = "init"
    CLONING = "cloning"
    PREPARING = "preparing"
    SCANNING = "scanning"
    DIAGNOSING = "diagnosing"
    EXPLAINING = "explaining"
    FIXING = "fixing"
    PREPARING_SANDBOX = "preparing_sandbox"
    APPLYING_FIX = "applying_fix"
    TESTING_ACCESSIBILITY = "testing_accessibility"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    ERROR = "error"


class Violation(BaseModel):
    """Represents an identified accessibility violation."""
    id: str = Field(description="Unique violation identifier (e.g. 'viol_01')")
    file: str = Field(description="Relative repository path to the file")
    line: Optional[int] = Field(default=None, description="Line number of defect")
    type: str = Field(description="WCAG violation rule (e.g. 'color-contrast', 'image-alt')")
    severity: str = Field(default="serious", description="Severity: critical, high, medium, low (or legacy serious/moderate/minor)")
    description: str = Field(description="Human-readable description of defect")
    selector: Optional[str] = Field(default=None, description="DOM or JSX element selector")
    context_snippet: Optional[str] = Field(default=None, description="Offending code snippet")
    source: str = Field(default="rule", description="Detection source: 'rule' or 'llm'")
    wcag_criterion: Optional[str] = Field(default=None, description="WCAG 2.2 Success Criterion (e.g. '1.1.1 Non-text Content')")
    category: ViolationCategory = Field(default=ViolationCategory.OTHER, description="Normalized violation category taxonomy")
    severity_score: Optional[int] = Field(default=None, description="Normalized severity score (1-10), source of truth")
    priority_rank: Optional[int] = Field(default=None, description="Priority rank (1 = highest priority)")


class DiagnosedViolation(Violation):
    """Represents an identified accessibility violation enriched with deep root-cause diagnosis."""
    root_cause: str = Field(description="Plain-English technical explanation of why the defect exists")
    affected_element: str = Field(description="HTML tag, JSX selector, or component affected")
    user_impact: str = Field(description="Plain-English explanation of affected assistive technology users and friction")
    fix_strategy: str = Field(description="Strategic architectural recommendation to resolve the violation")
    confidence: str = Field(default="high", description="Diagnosis confidence level: 'high', 'medium', or 'low'")
    diagnosis_source: str = Field(default="llm", description="Source of diagnosis: 'llm' or 'template'")
    plain_explanation: str = Field(default="", description="Friendly, non-technical plain English explanation for stakeholders")


class ProposedFix(BaseModel):
    """Represents an AI-generated remediation patch."""
    fix_id: str = Field(default="", description="Unique identifier for the fix")
    violation_id: str = Field(description="Referenced violation identifier")
    file: str = Field(default="", description="Relative path to the modified file")
    line_start: Optional[int] = Field(default=None, description="Start line of the modified code block (1-indexed)")
    line_end: Optional[int] = Field(default=None, description="End line of the modified code block (1-indexed)")
    original_lines: str = Field(default="", description="Original code block before patch")
    fixed_lines: str = Field(default="", description="Remediated code block after patch")
    diff: str = Field(default="", description="Unified git diff string")
    explanation_of_change: str = Field(default="", description="Detailed explanation of how the fix resolves the violation")
    confidence: str = Field(default="high", description="Fix confidence level: 'high', 'medium', or 'low'")
    status: str = Field(default="proposed", description="Fix status: 'proposed' or 'failed'")
    failure_reason: Optional[str] = Field(default=None, description="Detailed reason if fix generation or validation failed")
    # Backward compatibility aliases
    explanation: Optional[str] = Field(default="", description="Legacy explanation field")
    original_code: Optional[str] = Field(default=None, description="Legacy original code alias")
    remediated_code: Optional[str] = Field(default=None, description="Legacy remediated code alias")

    def model_post_init(self, __context: Any) -> None:
        if not self.explanation and self.explanation_of_change:
            self.explanation = self.explanation_of_change
        elif not self.explanation_of_change and self.explanation:
            self.explanation_of_change = self.explanation
        if not self.original_code and self.original_lines:
            self.original_code = self.original_lines
        if not self.remediated_code and self.fixed_lines:
            self.remediated_code = self.fixed_lines


class VerificationResult(BaseModel):
    """Outcome of sandbox verification using axe-core and project test suite."""
    fix_id: str = Field(description="Identifier of the tested fix")
    violation_id: Optional[str] = Field(default=None, description="Identifier of the tested violation")
    axe_score_before: float = Field(description="Axe score before fix (0-100)")
    axe_score_after: float = Field(description="Axe score after fix (0-100)")
    tests_passed: bool = Field(description="Whether regression test suite passed")
    violations_resolved: bool = Field(default=True, description="Whether targeted defect was resolved")
    verified: bool = Field(description="Whether fix is verified clean with 0 regressions")
    sandbox_id: Optional[str] = Field(default=None, description="Nebius sandbox container ID")
    sandbox_logs: Optional[str] = Field(default=None, description="Execution logs from sandbox")


class ScanReport(BaseModel):
    """Comprehensive accessibility audit and verification report."""
    scan_id: str = Field(description="Unique scan job identifier")
    repo_url: str = Field(description="Repository URL that was audited")
    branch: str = Field(default="main", description="Git branch audited")
    violations: List[Violation] = Field(default_factory=list, description="List of detected violations")
    fixes: List[ProposedFix] = Field(default_factory=list, description="List of synthesized fixes")
    verification_results: List[VerificationResult] = Field(
        default_factory=list, description="List of sandbox verification results"
    )
    overall_score_before: float = Field(description="Baseline repository accessibility score (0-100)")
    overall_score_after: float = Field(description="Post-remediation accessibility score (0-100)")
    summary: Optional[Dict[str, Any]] = Field(default=None, description="Violation taxonomy summary counts")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Completion timestamp")
    status: str = Field(default="completed", description="Scan execution status")


class ScanRequest(BaseModel):
    """Request payload to initiate a new repository scan."""
    repo_url: str = Field(description="URL of the remote Git repository")
    branch: Optional[str] = Field(default="main", description="Git branch to clone and audit")


class ScanStartResponse(BaseModel):
    """Response returned upon successfully enqueuing a scan."""
    scan_id: str = Field(description="Unique identifier for the initiated scan")
    status: str = Field(default="queued", description="Initial scan status")
    message: str = Field(default="Scan initiated successfully", description="Status message")
    repo_url: Optional[str] = Field(default=None, description="Cloned repository URL")
    branch: Optional[str] = Field(default=None, description="Cloned branch")
    file_count: Optional[int] = Field(default=None, description="Number of discovered frontend UI files")
    framework: Optional[str] = Field(default=None, description="Detected frontend framework (e.g. React, Next.js, Vue)")
    scannable_files: Optional[List[str]] = Field(default=None, description="List of scannable UI file paths")
    batch_count: Optional[int] = Field(default=None, description="Number of extracted code chunks ready for LLM scanning")


class WebSocketMessage(BaseModel):
    """Schema for messages streamed over the WebSocket progress endpoint."""
    stage: str = Field(description="Current pipeline stage (init, cloning, scanning, fixing, verifying, completed, error)")
    progress: int = Field(ge=0, le=100, description="Progress percentage (0-100)")
    message: str = Field(description="Status message for user display")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Optional payload data")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of the event")
