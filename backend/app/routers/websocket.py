"""
WebSocket Router: Real-time progress broadcasting for active scans, generation, and sandbox runs.
"""
import logging
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Real-time Updates"])


class ConnectionManager:
    """Manages active WebSocket client connections."""
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/ws/progress")
async def websocket_progress_endpoint(websocket: WebSocket):
    """Client connection for streaming pipeline progress updates."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo ping / pong
            await websocket.send_json({"type": "ack", "received": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
