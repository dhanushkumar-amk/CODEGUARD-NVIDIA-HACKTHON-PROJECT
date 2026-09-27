"""
Report Router: Endpoints to retrieve full accessibility audit and verification reports.
"""
from fastapi import APIRouter
from app.models.schemas import ScanReport
from app.state import get_scan

router = APIRouter(tags=["Reports"])


@router.get(
    "/{scan_id}",
    response_model=ScanReport,
    summary="Get complete audit report and compliance score",
)
async def get_scan_report(scan_id: str) -> ScanReport:
    """
    Retrieve comprehensive report containing before/after compliance scores,
    all identified violations, synthesized patches, and sandbox test results.
    """
    scan = get_scan(scan_id)
    return scan.get("report")
