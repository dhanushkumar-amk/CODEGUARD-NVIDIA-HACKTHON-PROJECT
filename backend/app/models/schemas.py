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
    SERIOUS = "serious"
    MODERATE = "moderate"
    MINOR = "minor"


class PipelineStage(str, Enum):
    INIT = "init"
    CLONING = "cloning"
    SCANNING = "scanning"
    FIXING = "fixing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    ERROR = "error"


class Violation(BaseModel):
    """Represents an identified accessibility violation."""
    id: str = Field(description="Unique violation identifier (e.g. 'viol_01')")
    file: str = Field(description="Relative repository path to the file")
    line: Optional[int] = Field(default=None, description="Line number of defect")
    type: str = Field(description="WCAG violation rule (e.g. 'color-contrast', 'image-alt')")
    severity: str = Field(default="serious", description="Severity: critical, serious, moderate, minor")
    description: str = Field(description="Human-readable description of defect")
    selector: Optional[str] = Field(default=None, description="DOM or JSX element selector")
    context_snippet: Optional[str] = Field(default=None, description="Offending code snippet")


class ProposedFix(BaseModel):
    """Represents an AI-generated remediation patch."""
    fix_id: str = Field(default="", description="Unique identifier for the fix")
    violation_id: str = Field(description="Referenced violation identifier")
    diff: str = Field(description="Unified git diff string")
    explanation: str = Field(description="Detailed explanation of how the fix resolves the violation")
    original_code: Optional[str] = Field(default=None, description="Original code before patch")
    remediated_code: Optional[str] = Field(default=None, description="Remediated code after patch")


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


class WebSocketMessage(BaseModel):
    """Schema for messages streamed over the WebSocket progress endpoint."""
    stage: str = Field(description="Current pipeline stage (init, cloning, scanning, fixing, verifying, completed, error)")
    progress: int = Field(ge=0, le=100, description="Progress percentage (0-100)")
    message: str = Field(description="Status message for user display")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Optional payload data")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of the event")
