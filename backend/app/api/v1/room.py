from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.security import HTTPAuthorizationCredentials
from typing import Dict, Set, Literal, Optional, Any, List
from pydantic import BaseModel, ValidationError
import json
import structlog
import uuid
import time
import html
import bcrypt

from app.core.config import settings
from app.core.security import verify_token
from app.db.session import get_redis
from app.core.security import get_current_user
from app.core.metrics import websocket_connected_clients

logger = structlog.get_logger()
router = APIRouter(prefix="/room", tags=["watch-party"])

# In-memory fallback
in_memory_messages: Dict[str, list] = {}
in_memory_meta: Dict[str, dict] = {}
in_memory_state: Dict[str, dict] = {}

class WSMessage(BaseModel):
    type: Literal["play", "pause", "seek", "chat", "submit_passcode", "TRANSFER_HOST", "KICK_USER", "MUTE_USER", "LOCK_ROOM", "UNLOCK_ROOM"]
    payload: Optional[Any] = None

class CreateRoomRequest(BaseModel):
    passcode: Optional[str] = None

class ConnectionManager:
    def __init__(self):
        # map room_id -> {websocket: user_id}
        self.active_connections: Dict[str, Dict[WebSocket, str]] = {}

    async def connect(self, room_id: str, websocket: WebSocket, user_id: str) -> bool:
        room_connections = self.active_connections.get(room_id, {})
        if len(room_connections) >= settings.max_room_participants:
            await websocket.close(code=1008, reason="Room is full")
            logger.info("ws_client_rejected_room_full", room_id=room_id)
            return False

        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
        self.active_connections[room_id].add(websocket)
        websocket_connected_clients.inc()
        logger.info("ws_client_connected", room_id=room_id)
        return True

    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.active_connections:
            if websocket in self.active_connections[room_id]:
                self.active_connections[room_id].discard(websocket)
                websocket_connected_clients.dec()
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

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error("ws_send_error", error=str(e))

    def get_participants(self, room_id: str) -> List[str]:
        if room_id in self.active_connections:
            return list(self.active_connections[room_id].values())
        return []

    def get_websocket_for_user(self, room_id: str, user_id: str) -> Optional[WebSocket]:
        if room_id in self.active_connections:
            for ws, uid in self.active_connections[room_id].items():
                if uid == user_id:
                    return ws
        return None

manager = ConnectionManager()

def get_room_meta(room_id: str) -> Optional[dict]:
    redis = get_redis()
    if redis:
        try:
            data = redis.get(f"room:{room_id}:meta")
            if data:
                return json.loads(data)
        except Exception:
            pass
    return in_memory_meta.get(room_id)

def set_room_meta(room_id: str, meta: dict):
    redis = get_redis()
    if redis:
        try:
            redis.set(f"room:{room_id}:meta", json.dumps(meta))
            redis.expire(f"room:{room_id}:meta", 86400)
        except Exception:
            pass
    else:
        in_memory_meta[room_id] = meta

def hash_passcode(passcode: str) -> str:
    return bcrypt.hashpw(passcode.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_passcode(passcode: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(passcode.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

@router.post("/create")
async def create_room(req: Optional[CreateRoomRequest] = None, current_user: str = Depends(get_current_user)):
    """Create a new Watch-Together room."""
    room_id = str(uuid.uuid4())
    passcode_hash = hash_passcode(req.passcode) if req and req.passcode else None
    
    meta = {
        "host_id": current_user,
        "is_locked": bool(passcode_hash),
        "passcode_hash": passcode_hash,
        "muted_users": []
    }
    
    redis = get_redis()
    if redis:
        try:
            redis.set(f"room:{room_id}:state", json.dumps({"action": "pause", "progress": 0, "timestamp": time.time()}))
            redis.expire(f"room:{room_id}:state", 86400)
        except Exception as e:
            logger.error("redis_set_state_failed", error=str(e))
    else:
        in_memory_state[room_id] = {"action": "pause", "progress": 0, "timestamp": time.time()}

    set_room_meta(room_id, meta)
    
    return {"room_id": room_id, "status": "created"}

@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, token: str = Query(None)):
    """WebSocket endpoint for real-time room sync."""
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return

    try:
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        payload = await verify_token(credentials)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008, reason="User ID not found in token")
            return
    except Exception as e:
        logger.warning("ws_auth_failed", error=str(e))
        await websocket.close(code=1008, reason="Authentication failed")
        return

    # Check if room exists
    meta = get_room_meta(room_id)
    if not meta:
        # For backward compatibility, create dynamically if not found
        meta = {
            "host_id": user_id,
            "is_locked": False,
            "passcode_hash": None,
            "muted_users": []
        }
        set_room_meta(room_id, meta)
        
    accepted = await manager.connect(room_id, websocket, user_id)
    if not accepted:
        return

    is_host = meta["host_id"] == user_id
    redis = get_redis()

    if meta["is_locked"] and not is_host:
        await manager.send_personal_message({"type": "PASSCODE_REQUIRED"}, websocket)
        verified = False
        try:
            while not verified:
                data = await websocket.receive_text()
                message_dict = json.loads(data)
                msg_type = message_dict.get("type")
                if msg_type == "submit_passcode":
                    passcode = message_dict.get("payload", {}).get("passcode", "")
                    if meta["passcode_hash"] and verify_passcode(passcode, meta["passcode_hash"]):
                        verified = True
                        await manager.send_personal_message({"type": "PASSCODE_ACCEPTED"}, websocket)
                    else:
                        await manager.send_personal_message({"type": "PASSCODE_REJECTED"}, websocket)
                else:
                    await manager.send_personal_message({"error": "Passcode required to join"}, websocket)
        except WebSocketDisconnect:
            manager.disconnect(room_id, websocket)
            return
        except Exception:
            manager.disconnect(room_id, websocket)
            return

    # User is verified or host. Send initial state.
    # Send current state
    if redis:
        try:
            state_data = redis.get(f"room:{room_id}:state")
            if state_data:
                await websocket.send_json({"type": "sync", "payload": json.loads(state_data)})
        except Exception as e:
            logger.error("redis_get_state_failed", error=str(e))
    else:
        state_data = in_memory_state.get(room_id)
        if state_data:
            await websocket.send_json({"type": "sync", "payload": state_data})

    # Send chat history
    try:
        history = []
        if redis:
            raw_history = redis.lrange(f"room:{room_id}:messages", -50, -1)
            if raw_history:
                history = [json.loads(m) for m in raw_history]
        else:
            history = in_memory_messages.get(room_id, [])[-50:]
        
        await websocket.send_json({"type": "history", "payload": history})
    except Exception as e:
        logger.error("chat_history_fetch_failed", error=str(e))
            
    # Send current participants and host
    await websocket.send_json({
        "type": "room_state",
        "payload": {
            "host_id": meta["host_id"],
            "participants": manager.get_participants(room_id),
            "is_locked": meta["is_locked"],
            "muted_users": meta["muted_users"]
        }
    })

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
                    current_meta = get_room_meta(room_id)
                    if current_meta and user_id in current_meta.get("muted_users", []):
                        await manager.send_personal_message({"error": "You are muted"}, websocket)
                        continue

                    text = payload.get("text", "") if isinstance(payload, dict) else str(payload)
                    text = html.escape(text.strip())
                    if not text or len(text) > 500:
                        continue
                    
                    chat_msg = {
                        "user": user_id,
                        "text": text,
                        "timestamp": time.time()
                    }
                    
                    try:
                        if redis:
                            key = f"room:{room_id}:messages"
                            redis.rpush(key, json.dumps(chat_msg))
                            redis.ltrim(key, -100, -1)
                            redis.expire(key, 86400)
                        else:
                            if room_id not in in_memory_messages:
                                in_memory_messages[room_id] = []
                            in_memory_messages[room_id].append(chat_msg)
                            if len(in_memory_messages[room_id]) > 100:
                                in_memory_messages[room_id].pop(0)
                    except Exception as e:
                        logger.error("redis_save_chat_failed", error=str(e))
                    
                    broadcast_msg = {
                        "type": "chat",
                        "user": user_id,
                        "payload": {"text": text, "timestamp": chat_msg["timestamp"]}
                    }
                    await manager.broadcast(room_id, broadcast_msg, sender=websocket)
                    
                elif msg_type in ("play", "pause", "seek"):
                    await manager.broadcast(room_id, validated_msg.model_dump(), sender=websocket)
                    
                    if redis:
                        try:
                            sync_data = payload if isinstance(payload, dict) else {}
                            sync_data["action"] = msg_type
                            sync_data["timestamp"] = time.time()
                            redis.set(f"room:{room_id}:state", json.dumps(sync_data))
                            redis.expire(f"room:{room_id}:state", 86400)
                        except Exception as e:
                            logger.error("redis_set_state_failed", error=str(e))
                    else:
                        sync_data = payload if isinstance(payload, dict) else {}
                        sync_data["action"] = msg_type
                        sync_data["timestamp"] = time.time()
                        in_memory_state[room_id] = sync_data

                # Host Moderation Actions
                elif msg_type in ("TRANSFER_HOST", "KICK_USER", "MUTE_USER", "LOCK_ROOM", "UNLOCK_ROOM"):
                    current_meta = get_room_meta(room_id)
                    if not current_meta or current_meta["host_id"] != user_id:
                        await manager.send_personal_message({"error": "Only host can perform this action"}, websocket)
                        continue
                    
                    if msg_type == "TRANSFER_HOST":
                        target_id = payload.get("user_id")
                        if target_id and target_id in manager.get_participants(room_id):
                            current_meta["host_id"] = target_id
                            set_room_meta(room_id, current_meta)
                            await manager.broadcast(room_id, {"type": "TRANSFER_HOST", "payload": {"host_id": target_id}}, sender=websocket)
                            await manager.send_personal_message({"type": "TRANSFER_HOST", "payload": {"host_id": target_id}}, websocket)
                        else:
                            await manager.send_personal_message({"error": "Invalid user"}, websocket)

                    elif msg_type == "KICK_USER":
                        target_id = payload.get("user_id")
                        if target_id and target_id != user_id and target_id in manager.get_participants(room_id):
                            target_ws = manager.get_websocket_for_user(room_id, target_id)
                            if target_ws:
                                await manager.send_personal_message({"type": "USER_KICKED", "payload": {"reason": "Kicked by host"}}, target_ws)
                                await target_ws.close(code=4000, reason="Kicked by host")
                                manager.disconnect(room_id, target_ws)
                                await manager.broadcast(room_id, {"type": "user_left", "user": target_id}, sender=websocket)
                        else:
                            await manager.send_personal_message({"error": "Invalid user to kick"}, websocket)
                            
                    elif msg_type == "MUTE_USER":
                        target_id = payload.get("user_id")
                        is_muted = payload.get("muted", True)
                        if target_id and target_id in manager.get_participants(room_id):
                            muted_set = set(current_meta.get("muted_users", []))
                            if is_muted:
                                muted_set.add(target_id)
                            else:
                                muted_set.discard(target_id)
                            current_meta["muted_users"] = list(muted_set)
                            set_room_meta(room_id, current_meta)
                            broadcast_event = "USER_MUTED" if is_muted else "USER_UNMUTED"
                            await manager.broadcast(room_id, {"type": broadcast_event, "user": target_id}, sender=websocket)
                            await manager.send_personal_message({"type": broadcast_event, "user": target_id}, websocket)
                            
                    elif msg_type == "LOCK_ROOM":
                        current_meta["is_locked"] = True
                        set_room_meta(room_id, current_meta)
                        await manager.broadcast(room_id, {"type": "ROOM_LOCKED"}, sender=websocket)
                        await manager.send_personal_message({"type": "ROOM_LOCKED"}, websocket)

                    elif msg_type == "UNLOCK_ROOM":
                        current_meta["is_locked"] = False
                        set_room_meta(room_id, current_meta)
                        await manager.broadcast(room_id, {"type": "ROOM_UNLOCKED"}, sender=websocket)
                        await manager.send_personal_message({"type": "ROOM_UNLOCKED"}, websocket)
                        
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})
            except ValidationError as e:
                await websocket.send_json({"error": "Invalid message schema", "details": e.errors()})
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
        await manager.broadcast(room_id, {"type": "user_left", "user": user_id})
