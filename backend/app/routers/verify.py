"""
Verify Router: Endpoints to inspect sandbox verification results and regression test statuses.
"""
from typing import List
from fastapi import APIRouter
from app.models.schemas import VerificationResult
from app.state import get_scan

router = APIRouter(tags=["Verification"])


@router.get(
    "/{scan_id}",
    response_model=List[VerificationResult],
    summary="Get sandbox verification results for a scan",
)
async def get_verification_results(scan_id: str) -> List[VerificationResult]:
    """
    Retrieve verification results confirming that synthesized patches passed axe-core
    checks and existing regression test suites inside Nebius sandboxes.
    """
    scan = get_scan(scan_id)
    return scan.get("verification_results", [])
