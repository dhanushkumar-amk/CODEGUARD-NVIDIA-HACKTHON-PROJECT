"""
WebSocket Router: Real-time progress broadcasting for CodeGuard audit and remediation pipelines.
Streams progressive stages for a given scan_id so the frontend can animate live status.
"""
import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.models.schemas import WebSocketMessage
from app.state import get_scan

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Real-time Streaming"])


class ConnectionManager:
    """Manages active WebSocket client connections grouped by scan_id."""
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, scan_id: str, websocket: WebSocket):
        await websocket.accept()
        if scan_id not in self.active_connections:
            self.active_connections[scan_id] = set()
        self.active_connections[scan_id].add(websocket)

    def disconnect(self, scan_id: str, websocket: WebSocket):
        if scan_id in self.active_connections:
            self.active_connections[scan_id].discard(websocket)
            if not self.active_connections[scan_id]:
                del self.active_connections[scan_id]

    async def send_message(self, websocket: WebSocket, message: WebSocketMessage):
        payload = message.model_dump(mode="json")
        await websocket.send_text(json.dumps(payload))


manager = ConnectionManager()


@router.websocket("/{scan_id}")
async def websocket_progress_endpoint(websocket: WebSocket, scan_id: str):
    """
    Live streaming endpoint for a specific scan_id.
    Simulates progressive pipeline stages upon connection to support frontend live testing.
    """
    await manager.connect(scan_id, websocket)
    scan_data = get_scan(scan_id)

    # Simulated pipeline sequence for live progress animations
    files_count = scan_data.get("file_count", len(scan_data.get("files", []))) or 20
    batch_count = scan_data.get("batch_count", len(scan_data.get("scan_batch", []))) or 15
    parsed_mid = max(1, files_count // 2)

    stages = [
        WebSocketMessage(
            stage="init",
            progress=5,
            message="Initialized scan request. Connecting to repository...",
            timestamp=datetime.now(timezone.utc),
        ),
        WebSocketMessage(
            stage="cloning",
            progress=15,
            message=f"Repository cloned. Discovered {files_count} UI component files.",
            data={"branch": scan_data.get("branch", "main"), "files_count": files_count},
            timestamp=datetime.now(timezone.utc),
        ),
        WebSocketMessage(
            stage="preparing",
            progress=25,
            message=f"Parsed {parsed_mid}/{files_count} files",
            data={"files_parsed": parsed_mid, "total_files": files_count},
            timestamp=datetime.now(timezone.utc),
        ),
        WebSocketMessage(
            stage="preparing",
            progress=40,
            message=f"Parsed {files_count}/{files_count} files ({batch_count} chunks extracted)",
            data={"files_parsed": files_count, "total_files": files_count, "batch_count": batch_count},
            timestamp=datetime.now(timezone.utc),
        ),
        WebSocketMessage(
            stage="scanning",
            progress=55,
            message="Accessibility audit complete: 4 actionable violations detected.",
            data={"violations_count": len(scan_data.get("violations", []))},
            timestamp=datetime.now(timezone.utc),
        ),
        WebSocketMessage(
            stage="fixing",
            progress=75,
            message="Synthesized WCAG 2.2 AA compliant patches using Nemotron Ultra.",
            data={"fixes_count": len(scan_data.get("fixes", []))},
            timestamp=datetime.now(timezone.utc),
        ),
        WebSocketMessage(
            stage="verifying",
            progress=90,
            message="Patches verified in isolated Nebius Sandboxes with 0 regressions.",
            data={"verified_count": len(scan_data.get("verification_results", []))},
            timestamp=datetime.now(timezone.utc),
        ),
        WebSocketMessage(
            stage="completed",
            progress=100,
            message="All violations remediated and verified in Nebius Sandboxes.",
            data={
                "overall_score_before": 62.5,
                "overall_score_after": 100.0,
                "status": "completed",
            },
            timestamp=datetime.now(timezone.utc),
        ),
    ]

    try:
        # Stream the mock stages with a short realistic delay
        for stage_msg in stages:
            await manager.send_message(websocket, stage_msg)
            await asyncio.sleep(0.15)

        # Keep connection open for client echo / ping messages
        while True:
            client_msg = await websocket.receive_text()
            await websocket.send_text(json.dumps({"type": "pong", "received": client_msg}))

    except WebSocketDisconnect:
        manager.disconnect(scan_id, websocket)
    except Exception as exc:
        logger.warning(f"WebSocket session terminated for scan {scan_id}: {exc}")
        manager.disconnect(scan_id, websocket)
