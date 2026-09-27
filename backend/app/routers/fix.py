"""
Fix Router: Endpoints to request and preview Nemotron-generated remediation patches.
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/fix", tags=["Remediation"])


class FixRequest(BaseModel):
    violation_id: str
    component_path: str


@router.post("")
async def generate_fix(request: FixRequest):
    """Generate a fix using NVIDIA Nemotron Ultra."""
    return {"status": "generating", "violation_id": request.violation_id}
