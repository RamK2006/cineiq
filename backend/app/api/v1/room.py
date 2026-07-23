from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Set, Literal, Optional, Any
from pydantic import BaseModel, ValidationError
import json
import structlog
import uuid
import time

from app.core.config import settings
from app.db.session import get_redis

logger = structlog.get_logger()
router = APIRouter(prefix="/room", tags=["watch-party"])

class WSMessage(BaseModel):
    type: Literal["play", "pause", "seek", "chat"]
    payload: Optional[Any] = None

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
            stale_connections = []
            for connection in self.active_connections[room_id]:
                if connection != sender:
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        logger.error("ws_broadcast_error", error=str(e))
                        stale_connections.append(connection)
            for conn in stale_connections:
                self.disconnect(room_id, conn)

manager = ConnectionManager()

@router.post("/create")
async def create_room():
    """Create a new Watch-Together room."""
    room_id = str(uuid.uuid4())
    # Initialize room state in Redis
    redis = get_redis()
    if redis:
        try:
            redis.set(f"room:{room_id}:state", json.dumps({"action": "pause", "progress": 0, "timestamp": time.time()}))
            redis.expire(f"room:{room_id}:state", 86400) # Expire in 24 hours
        except Exception as e:
            logger.error("redis_set_state_failed", error=str(e))
    return {"room_id": room_id, "status": "created"}

@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, token: str = Query(None)):
    """WebSocket endpoint for real-time room sync."""
    # Basic token validation check (Issue #20 placeholder fallback)
    if not token and not (not settings.clerk_secret_key or "REPLACE" in settings.clerk_secret_key):
        await websocket.close(code=1008, reason="Authentication required")
        return
    
    # Mock user for now since full auth is bypassed if no valid token validation exists
    # Normally we'd decode the JWT token using get_jwks() from security.py here.
    user_id = token if token else f"user_{str(uuid.uuid4())[:8]}"

    accepted = await manager.connect(room_id, websocket)
    if not accepted:
        return
    
    redis = get_redis()
    
    # Send current state
    if redis:
        try:
            state_data = redis.get(f"room:{room_id}:state")
            if state_data:
                await websocket.send_json({"type": "sync", "payload": json.loads(state_data)})
        except Exception as e:
            logger.error("redis_get_state_failed", error=str(e))
            
    # Notify others
    await manager.broadcast(room_id, {"type": "user_joined", "user": user_id}, sender=websocket)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_dict = json.loads(data)
                validated_msg = WSMessage(**message_dict)
                msg_type = validated_msg.type
                payload = validated_msg.payload or {}
                
                # Input validation
                if msg_type == "chat":
                    text = payload.get("text", "") if isinstance(payload, dict) else str(payload)
                    if not text or len(text) > 500:
                        continue # invalid message
                    
                    broadcast_msg = validated_msg.dict()
                    broadcast_msg["user"] = user_id
                    await manager.broadcast(room_id, broadcast_msg)
                    
                elif msg_type in ("play", "pause", "seek"):
                    # Broadcast sync events (play, pause, seek) to others in room
                    await manager.broadcast(room_id, validated_msg.dict(), sender=websocket)
                    
                    # Persist state in redis
                    if redis:
                        try:
                            sync_data = payload if isinstance(payload, dict) else {}
                            sync_data["action"] = msg_type
                            sync_data["timestamp"] = time.time()
                            redis.set(f"room:{room_id}:state", json.dumps(sync_data))
                            redis.expire(f"room:{room_id}:state", 86400)
                        except Exception as e:
                            logger.error("redis_set_state_failed", error=str(e))
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})
            except ValidationError as e:
                await websocket.send_json({"error": "Invalid message schema", "details": e.errors()})
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
        await manager.broadcast(room_id, {"type": "user_left", "user": user_id})
