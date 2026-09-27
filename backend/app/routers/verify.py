"""
Verify Router: Endpoints to test patches inside isolated Nebius Sandboxes.
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/verify", tags=["Verification"])


class VerifyRequest(BaseModel):
    patch_id: str
    sandbox_image: str = "node:20"


@router.post("")
async def verify_patch(request: VerifyRequest):
    """Dispatch patch to Nebius Sandbox for axe-core verification."""
    return {"status": "dispatched", "patch_id": request.patch_id}
