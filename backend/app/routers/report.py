"""
Report Router: Endpoints to retrieve full accessibility audit and verification reports.
"""
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import ScanReport
from app.services.aggregator_service import build_scan_report
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
    Returns the real aggregated report from build_scan_report().
    """
    scan = get_scan(scan_id)
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan report not found for scan_id: {scan_id}",
        )

    # Return cached report if available, otherwise dynamically build it
    report = scan.get("report")
    if not report or not getattr(report, "unified_records", None):
        try:
            report = build_scan_report(scan_id)
        except Exception as exc:
            # If report is already present, fallback
            if not report:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error compiling scan report: {str(exc)}",
                )

    return report
