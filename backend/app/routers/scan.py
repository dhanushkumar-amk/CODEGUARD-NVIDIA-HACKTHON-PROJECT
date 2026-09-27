"""
Scan Router: Endpoints to initiate repository accessibility audits and check scan status.
"""
from fastapi import APIRouter, status
from app.models.schemas import ScanRequest, ScanStartResponse
from app.state import create_scan, get_scan

router = APIRouter(tags=["Scanning"])


@router.post(
    "/start",
    response_model=ScanStartResponse,
    status_code=status.HTTP_200_OK,
    summary="Start a new repository scan",
)
async def start_scan(request: ScanRequest) -> ScanStartResponse:
    """
    Initiate an accessibility audit for the specified repository URL.
    Returns a unique scan_id to subscribe to progress events.
    """
    scan_id = create_scan(repo_url=request.repo_url, branch=request.branch or "main")
    return ScanStartResponse(
        scan_id=scan_id,
        status="queued",
        message="Scan initiated and queued for orchestration",
    )


@router.get(
    "/{scan_id}",
    summary="Get scan metadata and status",
)
async def get_scan_status(scan_id: str):
    """Retrieve metadata and high-level progress for a given scan_id."""
    scan = get_scan(scan_id)
    return {
        "scan_id": scan_id,
        "repo_url": scan.get("repo_url"),
        "branch": scan.get("branch"),
        "status": scan.get("status"),
        "progress": scan.get("progress", 100),
    }
