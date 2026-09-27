"""
Report Router: Endpoints to retrieve audit reports and compliance scores.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/report", tags=["Reports"])


@router.get("/{scan_id}")
async def get_report(scan_id: str):
    """Retrieve full compliance report for a completed scan."""
    return {"scan_id": scan_id, "score_before": 65, "score_after": 100}
