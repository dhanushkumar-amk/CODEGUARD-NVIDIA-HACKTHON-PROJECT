"""
Scan Router: Endpoints to initiate repository accessibility scans and query violations.
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/scan", tags=["Scanning"])


class ScanRequest(BaseModel):
    repo_url: str
    branch: str = "main"


@router.post("")
async def start_scan(request: ScanRequest):
    """Trigger a new repository accessibility audit."""
    return {"status": "queued", "repo_url": request.repo_url}
