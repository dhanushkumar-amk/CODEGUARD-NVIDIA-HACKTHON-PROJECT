"""
WebSocket Router: Real-time progress broadcasting for CodeGuard audit and remediation pipelines.
Streams progressive stages for a given scan_id so the frontend can animate live status.
"""
import asyncio
from datetime import datetime
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
    stages = [
        WebSocketMessage(
            stage="init",
            progress=5,
            message="Initialized scan request. Connecting to repository...",
            timestamp=datetime.utcnow(),
        ),
        WebSocketMessage(
            stage="cloning",
            progress=15,
            message="Repository cloned. Discovered 18 UI component files.",
            data={"branch": scan_data.get("branch", "main"), "files_count": 18},
            timestamp=datetime.utcnow(),
        ),
        WebSocketMessage(
            stage="scanning",
            progress=40,
            message="Accessibility audit complete: 4 actionable violations detected.",
            data={"violations_count": len(scan_data.get("violations", []))},
            timestamp=datetime.utcnow(),
        ),
        WebSocketMessage(
            stage="fixing",
            progress=65,
            message="Synthesized WCAG 2.2 AA compliant patches using Nemotron Ultra.",
            data={"fixes_count": len(scan_data.get("fixes", []))},
            timestamp=datetime.utcnow(),
        ),
        WebSocketMessage(
            stage="verifying",
            progress=85,
            message="Patches verified in isolated Nebius Sandboxes with 0 regressions.",
            data={"verified_count": len(scan_data.get("verification_results", []))},
            timestamp=datetime.utcnow(),
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
            timestamp=datetime.utcnow(),
        ),
    ]

    try:
        # Stream the mock stages with a short realistic delay
        for stage_msg in stages:
            await manager.send_message(websocket, stage_msg)
            await asyncio.sleep(0.3)

        # Keep connection open for client echo / ping messages
        while True:
            client_msg = await websocket.receive_text()
            await websocket.send_text(json.dumps({"type": "pong", "received": client_msg}))

    except WebSocketDisconnect:
        manager.disconnect(scan_id, websocket)
    except Exception as exc:
        logger.warning(f"WebSocket session terminated for scan {scan_id}: {exc}")
        manager.disconnect(scan_id, websocket)
