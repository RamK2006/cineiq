from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import structlog
import uuid

from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/room", tags=["watch-party"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket) -> bool:
        room_connections = self.active_connections.get(room_id, set())
        if len(room_connections) >= settings.max_room_participants:
            await websocket.close(code=1008, reason="Room is full")
            logger.info("ws_client_rejected_room_full", room_id=room_id)
            return False

        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
        self.active_connections[room_id].add(websocket)
        logger.info("ws_client_connected", room_id=room_id)
        return True

    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.active_connections:
            self.active_connections[room_id].discard(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
        logger.info("ws_client_disconnected", room_id=room_id)

    async def broadcast(self, room_id: str, message: dict, sender: WebSocket = None):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                if connection != sender:
                    await connection.send_json(message)

manager = ConnectionManager()

@router.post("/create")
async def create_room():
    """Create a new Watch-Together room."""
    room_id = str(uuid.uuid4())
    return {"room_id": room_id, "status": "created"}

@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    """WebSocket endpoint for real-time room sync."""
    accepted = await manager.connect(room_id, websocket)
    if not accepted:
        return
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # Broadcast sync events (play, pause, seek) to others in room
                await manager.broadcast(room_id, message, sender=websocket)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
        await manager.broadcast(room_id, {"type": "user_left"})
