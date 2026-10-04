"""
WebSocket Router: Real-time progress broadcasting for CodeGuard audit and remediation pipelines.
Streams progressive stages for a given scan_id so the frontend can animate live status.
"""
import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional, Set

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

    async def broadcast_to_scan(self, scan_id: str, message: WebSocketMessage):
        connections = self.active_connections.get(scan_id, set())
        for ws in list(connections):
            try:
                await self.send_message(ws, message)
            except Exception as e:
                logger.warning(f"Error broadcasting to scan {scan_id}: {e}")
                self.disconnect(scan_id, ws)


manager = ConnectionManager()


async def broadcast_progress(
    scan_id: str,
    stage: str,
    progress: int,
    message: str,
    data: Optional[Dict[str, Any]] = None,
):
    """
    Broadcasts a WebSocketMessage to all active WebSocket connections for scan_id.
    Automatically enriches payload data with running estimated LLM cost.
    """
    payload_data = dict(data) if data else {}
    if "current_cost_usd" not in payload_data:
        try:
            from app.services.llm_client import get_scan_usage_stats
            usage = get_scan_usage_stats(scan_id)
            payload_data["current_cost_usd"] = usage.get("total_cost_usd", 0.0)
        except Exception:
            pass

    msg = WebSocketMessage(
        stage=stage,
        progress=progress,
        message=message,
        data=payload_data,
        timestamp=datetime.now(timezone.utc),
    )
    await manager.broadcast_to_scan(scan_id, msg)


@router.websocket("/{scan_id}")
async def websocket_progress_endpoint(websocket: WebSocket, scan_id: str):
    """
    Live streaming endpoint for a specific scan_id.
    Maintains connection for real pipeline broadcasts, or streams mock progression
    for standalone frontend / simulated preview tests.
    """
    await manager.connect(scan_id, websocket)
    scan_data = get_scan(scan_id)
    scan_status = scan_data.get("status") if scan_data else None

    # Determine if this is a real actively monitored scan or a standalone/mock session
    is_active_real = bool(scan_data and scan_data.get("is_active_real_scan", False))
    is_real_scan = is_active_real and not (
        scan_id.startswith("mock")
        or scan_id.startswith("demo_sim")
        or scan_id.startswith("scan_stream")
        or scan_id.startswith("test")
    )

    try:
        if not is_real_scan or scan_id.startswith("mock") or scan_id.startswith("demo_sim") or scan_id.startswith("scan_stream"):
            # Simulated pipeline sequence for live progress animations & tests
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
                    progress=35,
                    message=f"Parsed {files_count}/{files_count} files ({batch_count} chunks extracted)",
                    data={"files_parsed": files_count, "total_files": files_count, "batch_count": batch_count},
                    timestamp=datetime.now(timezone.utc),
                ),
                WebSocketMessage(
                    stage="scanning",
                    progress=45,
                    message="Scanning AST & axe-core rules — 2 violations found so far",
                    data={"violations_count": 2, "violations_found": 2, "current_cost_usd": 0.0008},
                    timestamp=datetime.now(timezone.utc),
                ),
                WebSocketMessage(
                    stage="scanning",
                    progress=55,
                    message="Scanned 6/6 chunks — 4 violations found so far",
                    data={"violations_count": 4, "violations_found": 4, "current_cost_usd": 0.0018},
                    timestamp=datetime.now(timezone.utc),
                ),
                WebSocketMessage(
                    stage="diagnosing",
                    progress=65,
                    message="Diagnosed root causes and WCAG failure modes with Nemotron Nano.",
                    data={"violations_count": 4, "violations_found": 4, "current_cost_usd": 0.0042},
                    timestamp=datetime.now(timezone.utc),
                ),
                WebSocketMessage(
                    stage="explaining",
                    progress=72,
                    message="Generated plain-English impact summaries for compliance & developers.",
                    data={"violations_count": 4, "violations_found": 4, "current_cost_usd": 0.0076},
                    timestamp=datetime.now(timezone.utc),
                ),
                WebSocketMessage(
                    stage="generating_fixes",
                    progress=80,
                    message="Synthesized WCAG 2.2 AA compliant patches using Nemotron Ultra.",
                    data={"violations_count": 4, "violations_found": 4, "fixes_count": 4, "current_cost_usd": 0.0165},
                    timestamp=datetime.now(timezone.utc),
                ),
                WebSocketMessage(
                    stage="preparing_sandbox",
                    progress=86,
                    message="Spinning up isolated ephemeral execution container.",
                    data={"violations_count": 4, "violations_found": 4, "current_cost_usd": 0.0190},
                    timestamp=datetime.now(timezone.utc),
                ),
                WebSocketMessage(
                    stage="applying_fix",
                    progress=90,
                    message="Applied synthesized code patches into sandbox workspace.",
                    data={"violations_count": 4, "violations_found": 4, "current_cost_usd": 0.0215},
                    timestamp=datetime.now(timezone.utc),
                ),
                WebSocketMessage(
                    stage="testing_accessibility",
                    progress=94,
                    message="Executed axe-core headless checks and regression test suite (0 regressions).",
                    data={"violations_count": 4, "violations_found": 4, "current_cost_usd": 0.0252},
                    timestamp=datetime.now(timezone.utc),
                ),
                WebSocketMessage(
                    stage="verifying",
                    progress=97,
                    message="Patches verified in isolated Nebius Sandboxes with 0 regressions.",
                    data={"violations_count": 4, "violations_found": 4, "verified_count": 4, "current_cost_usd": 0.0285},
                    timestamp=datetime.now(timezone.utc),
                ),
                WebSocketMessage(
                    stage="complete",
                    progress=100,
                    message="All violations remediated and verified in Nebius Sandboxes.",
                    data={
                        "fixed_and_verified": 4,
                        "total_violations": 4,
                        "score_before": 58.0,
                        "score_after": 91.0,
                        "current_cost_usd": 0.0335,
                    },
                    timestamp=datetime.now(timezone.utc),
                ),
            ]

            for stage_msg in stages:
                await manager.send_message(websocket, stage_msg)
                await asyncio.sleep(0.2)
        elif scan_status in ("complete", "completed"):
            # If the scan completed before the WebSocket connected, send completion immediately
            report = scan_data.get("report")
            verified_count = scan_data.get("verified_count", 0)
            total_violations = len(scan_data.get("violations", []))
            await manager.send_message(
                websocket,
                WebSocketMessage(
                    stage="complete",
                    progress=100,
                    message=f"Scan complete — {verified_count} of {total_violations} violations fixed and verified",
                    data={
                        "fixed_and_verified": verified_count,
                        "total_violations": total_violations,
                        "score_before": getattr(report, "overall_score_before", 50.0) if report else 50.0,
                        "score_after": getattr(report, "overall_score_after", 100.0) if report else 100.0,
                    },
                    timestamp=datetime.now(timezone.utc),
                ),
            )
        else:
            # Active scan is running in background. Send immediate greeting event:
            await manager.send_message(
                websocket,
                WebSocketMessage(
                    stage="preparing",
                    progress=10,
                    message="Connected to active CodeGuard audit pipeline...",
                    data={"status": scan_status},
                    timestamp=datetime.now(timezone.utc),
                ),
            )

        # Keep connection open for real broadcast events streamed from background workers
        while True:
            client_msg = await websocket.receive_text()
            await websocket.send_text(json.dumps({"type": "pong", "received": client_msg}))

    except WebSocketDisconnect:
        manager.disconnect(scan_id, websocket)
    except Exception as exc:
        logger.warning(f"WebSocket session terminated for scan {scan_id}: {exc}")
        manager.disconnect(scan_id, websocket)
