import asyncio
import json
import logging
from typing import Dict, List, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("foceye.ws")
router = APIRouter(tags=["Real-time Gaze Telemetry"])


class GazeConnectionManager:
    """
    Manages active WebSocket connections for high-frequency gaze streaming.
    Supports session-based multiplexing (camera tracker -> active session listeners / therapist UI).
    """

    def __init__(self):
        self.active_sessions: Dict[str, Set[WebSocket]] = {}
        self.total_streamed_frames: int = 0

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = set()
        self.active_sessions[session_id].add(websocket)
        logger.info(f"WebSocket client connected to session {session_id}. Active: {len(self.active_sessions[session_id])}")

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_sessions:
            self.active_sessions[session_id].discard(websocket)
            if not self.active_sessions[session_id]:
                del self.active_sessions[session_id]
        logger.info(f"WebSocket client disconnected from session {session_id}")

    async def broadcast_bytes(self, session_id: str, data: bytes, sender: WebSocket):
        self.total_streamed_frames += 1
        if session_id in self.active_sessions:
            for connection in list(self.active_sessions[session_id]):
                if connection != sender:
                    try:
                        await connection.send_bytes(data)
                    except Exception as e:
                        logger.warning(f"Error broadcasting bytes to client: {e}")
                        self.disconnect(session_id, connection)

    async def broadcast_json(self, session_id: str, data: dict, sender: WebSocket):
        self.total_streamed_frames += 1
        if session_id in self.active_sessions:
            for connection in list(self.active_sessions[session_id]):
                if connection != sender:
                    try:
                        await connection.send_json(data)
                    except Exception as e:
                        logger.warning(f"Error broadcasting json to client: {e}")
                        self.disconnect(session_id, connection)


manager = GazeConnectionManager()


@router.get("/api/v1/telemetry/stats", tags=["Real-time Gaze Telemetry"])
async def get_telemetry_stats():
    """
    Returns real-time telemetry server metrics including active rooms and connected observers.
    """
    total_connections = sum(len(conns) for conns in manager.active_sessions.values())
    return {
        "status": "online",
        "active_rooms": len(manager.active_sessions),
        "total_active_connections": total_connections,
        "total_gazepoints_streamed": manager.total_streamed_frames,
        "rooms": [
            {"session_id": sid, "subscribers": len(conns)}
            for sid, conns in manager.active_sessions.items()
        ]
    }


@router.websocket("/ws/gaze/{session_id}")
async def gaze_websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        while True:
            # Receive either binary 32-byte frame or JSON message
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                await manager.broadcast_bytes(session_id, message["bytes"], sender=websocket)
            elif "text" in message and message["text"]:
                try:
                    payload = json.loads(message["text"])
                    # Handle heartbeat ping/pong
                    if isinstance(payload, dict) and payload.get("type") == "ping":
                        await websocket.send_json({"type": "pong", "timestamp": payload.get("timestamp")})
                    else:
                        await manager.broadcast_json(session_id, payload, sender=websocket)
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error on session {session_id}: {e}")
        manager.disconnect(session_id, websocket)
