from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Set
import json
import structlog
import uuid
import time

from app.core.config import settings
from app.db.session import get_redis

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
                    try:
                        await connection.send_json(message)
                    except Exception:
                        pass

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
                await websocket.send_json({"type": "sync", "data": json.loads(state_data)})
        except Exception as e:
            logger.error("redis_get_state_failed", error=str(e))
            
    # Notify others
    await manager.broadcast(room_id, {"type": "user_joined", "user": user_id}, sender=websocket)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type")
                
                # Input validation (Issue #27 fallback)
                if msg_type == "chat":
                    text = message.get("data", {}).get("text", "")
                    if not text or len(text) > 500:
                        continue # invalid message
                    
                    message["user"] = user_id
                    await manager.broadcast(room_id, message)
                    
                elif msg_type == "sync":
                    # Broadcast sync events (play, pause, seek) to others in room
                    await manager.broadcast(room_id, message, sender=websocket)
                    
                    # Persist state in redis
                    if redis:
                        try:
                            sync_data = message.get("data", {})
                            sync_data["timestamp"] = time.time()
                            redis.set(f"room:{room_id}:state", json.dumps(sync_data))
                            redis.expire(f"room:{room_id}:state", 86400)
                        except Exception as e:
                            logger.error("redis_set_state_failed", error=str(e))
                            
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
        await manager.broadcast(room_id, {"type": "user_left", "user": user_id})
