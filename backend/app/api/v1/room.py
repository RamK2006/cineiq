from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.security import HTTPAuthorizationCredentials
from typing import Dict, Literal, Optional, Any, List
from pydantic import BaseModel, ValidationError, Field
import json
import structlog
import uuid
import time
import html
import bcrypt
import asyncio

from app.core.config import settings
from app.core.security import verify_token
from app.db.session import get_redis
from app.core.security import get_current_user
from app.core.metrics import websocket_connected_clients

logger = structlog.get_logger()
router = APIRouter(prefix="/room", tags=["watch-party"])

# --- Memory Fallbacks ---
in_memory_messages: Dict[str, list] = {}
in_memory_meta: Dict[str, dict] = {}
in_memory_state: Dict[str, dict] = {}

ROOM_SIGNALING_REGISTRY: Dict[str, Dict[str, WebSocket]] = {}
ROOM_PRESENCE_REGISTRY: Dict[str, Dict[str, dict]] = {}
ROOM_CHAT_HISTORY: Dict[str, List[dict]] = {}

# --- Schemas ---

class WSMessage(BaseModel):
    type: Literal[
        "play", "pause", "seek", "chat", "submit_passcode", 
        "TRANSFER_HOST", "KICK_USER", "MUTE_USER", "LOCK_ROOM", 
        "UNLOCK_ROOM", "SUBTITLE_TRACK_CHANGED", "reaction",
        "PING", "PONG", "REQUEST_SYNC", "SYNC_TIME", "HOST_ACTION_DENIED"
    ]
    payload: Optional[Any] = None

class CreateRoomRequest(BaseModel):
    passcode: Optional[str] = None

# --- Connection Manager (Distributed Ready) ---

class ConnectionManager:
    def __init__(self):
        # map room_id -> {websocket: user_id}
        self.active_connections: Dict[str, Dict[WebSocket, str]] = {}
        # Background task references for periodic syncs
        self.sync_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, room_id: str, websocket: WebSocket, user_id: str) -> bool:
        room_connections = self.active_connections.get(room_id, {})
        if len(room_connections) >= settings.max_room_participants:
            await websocket.close(code=1008, reason="Room is full")
            logger.info("ws_client_rejected_room_full", room_id=room_id)
            return False

        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
        self.active_connections[room_id][websocket] = user_id
        websocket_connected_clients.inc()
        logger.info("ws_client_connected", room_id=room_id, user_id=user_id)
        
        # Start periodic sync task if this is the first connection
        if len(self.active_connections[room_id]) == 1:
            self.sync_tasks[room_id] = asyncio.create_task(self._periodic_sync_broadcaster(room_id))
            
        return True

    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.active_connections:
            if websocket in self.active_connections[room_id]:
                del self.active_connections[room_id][websocket]
                websocket_connected_clients.dec()
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
                # Cleanup sync task
                if room_id in self.sync_tasks:
                    self.sync_tasks[room_id].cancel()
                    del self.sync_tasks[room_id]
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

    async def _periodic_sync_broadcaster(self, room_id: str):
        """Periodically broadcasts the authoritative server state to ensure clients don't drift."""
        try:
            while True:
                await asyncio.sleep(5) # Broadcast sync every 5 seconds
                if room_id not in self.active_connections:
                    break
                
                # Fetch authoritative state
                redis = get_redis()
                state = None
                if redis:
                    try:
                        state_raw = redis.get(f"room:{room_id}:state")
                        if state_raw:
                            state = json.loads(state_raw)
                    except Exception:
                        pass
                else:
                    state = in_memory_state.get(room_id)
                
                if state:
                    await self.broadcast(room_id, {
                        "type": "SYNC_TIME",
                        "payload": {
                            "server_time": time.time() * 1000, # ms
                            "progress": state.get("progress", 0),
                            "action": state.get("action", "pause"),
                            "state_timestamp": state.get("timestamp", 0) * 1000
                        }
                    })
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Periodic sync broadcaster failed for room {room_id}: {e}")

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

# --- Signaling Endpoints (Mesh/WebRTC) ---
# ... Keeping existing mesh logic for VoiceChat ...
async def broadcast_to_room_peers(room_id: str, sender_id: str, message: dict):
    if room_id in ROOM_SIGNALING_REGISTRY:
        for peer_id, client_ws in list(ROOM_SIGNALING_REGISTRY[room_id].items()):
            if peer_id != sender_id:
                try:
                    await client_ws.send_text(json.dumps(message))
                except Exception:
                    pass

async def broadcast_to_room(room_id: str, message: dict, exclude_user_id: Optional[str] = None):
    if room_id in ROOM_PRESENCE_REGISTRY:
        payload = json.dumps(message)
        for uid, client in list(ROOM_PRESENCE_REGISTRY[room_id].items()):
            if exclude_user_id is None or uid != exclude_user_id:
                try:
                    await client["ws"].send_text(payload)
                except Exception:
                    pass

@router.websocket("/ws/room/{room_id}/{user_id}")
@router.websocket("/ws/mesh/{room_id}/{user_id}")
async def room_websocket_signaling_endpoint(
    websocket: WebSocket, room_id: str, user_id: str, username: str = "Guest", avatar: str = ""
):
    await websocket.accept()
    if room_id not in ROOM_SIGNALING_REGISTRY:
        ROOM_SIGNALING_REGISTRY[room_id] = {}
    if len(ROOM_SIGNALING_REGISTRY[room_id]) >= 4:
        await websocket.close(code=4001, reason="Watch Party room mesh capacity full.")
        return
    ROOM_SIGNALING_REGISTRY[room_id][user_id] = websocket
    if room_id not in ROOM_PRESENCE_REGISTRY:
        ROOM_PRESENCE_REGISTRY[room_id] = {}
    if room_id not in ROOM_CHAT_HISTORY:
        ROOM_CHAT_HISTORY[room_id] = []
    ROOM_PRESENCE_REGISTRY[room_id][user_id] = {"ws": websocket, "username": username, "avatar": avatar}

    current_members = [{"userId": uid, "username": meta["username"], "avatar": meta["avatar"]} for uid, meta in ROOM_PRESENCE_REGISTRY[room_id].items()]
    await websocket.send_text(json.dumps({"type": "ROOM_HYDRATION", "data": {"members": current_members, "history": ROOM_CHAT_HISTORY[room_id]}}))
    await broadcast_to_room(room_id, {"type": "USER_JOINED", "data": {"userId": user_id, "username": username, "avatar": avatar}}, exclude_user_id=user_id)
    await broadcast_to_room_peers(room_id, user_id, {"type": "peer-joined", "peerId": user_id})

    try:
        while True:
            raw_data = await websocket.receive_text()
            packet = json.loads(raw_data)
            event_type = packet.get("type")
            if event_type == "CHAT_MESSAGE":
                data_obj = packet.get("data", {})
                msg_payload = {"userId": user_id, "username": username, "text": data_obj.get("text", packet.get("text", "")), "timestamp": data_obj.get("timestamp", "")}
                ROOM_CHAT_HISTORY[room_id].append(msg_payload)
                if len(ROOM_CHAT_HISTORY[room_id]) > 50: ROOM_CHAT_HISTORY[room_id].pop(0)
                await broadcast_to_room(room_id, {"type": "CHAT_MESSAGE", "data": msg_payload})
            elif event_type == "EMOJI_REACTION":
                data_obj = packet.get("data", {})
                await broadcast_to_room(room_id, {"type": "EMOJI_REACTION", "data": {"userId": user_id, "emoji": data_obj.get("emoji", packet.get("emoji", "🍿"))}})
            elif event_type in ["offer", "answer", "ice-candidate"]:
                await broadcast_to_room_peers(room_id, user_id, {"type": event_type, "senderId": user_id, "data": packet.get("data")})
    except WebSocketDisconnect:
        pass
    finally:
        if room_id in ROOM_SIGNALING_REGISTRY and user_id in ROOM_SIGNALING_REGISTRY[room_id]: del ROOM_SIGNALING_REGISTRY[room_id][user_id]
        if room_id in ROOM_PRESENCE_REGISTRY and user_id in ROOM_PRESENCE_REGISTRY[room_id]: del ROOM_PRESENCE_REGISTRY[room_id][user_id]
        await broadcast_to_room(room_id, {"type": "USER_LEFT", "data": {"userId": user_id}})
        await broadcast_to_room_peers(room_id, user_id, {"type": "peer-left", "peerId": user_id})


# --- State Endpoints ---

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
    
    state_payload = json.dumps({"action": "pause", "progress": 0, "timestamp": time.time()})
    redis = get_redis()
    if redis:
        try:
            redis.set(f"room:{room_id}:state", state_payload)
            redis.expire(f"room:{room_id}:state", 86400)
        except Exception as e:
            logger.error("redis_set_state_failed", error=str(e))
    else:
        in_memory_state[room_id] = {"action": "pause", "progress": 0, "timestamp": time.time()}

    set_room_meta(room_id, meta)
    return {"room_id": room_id, "status": "created"}

@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, token: str = Query(None)):
    """WebSocket endpoint for real-time authoritative room sync."""
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

    meta = get_room_meta(room_id)
    if not meta:
        meta = {"host_id": user_id, "is_locked": False, "passcode_hash": None, "muted_users": []}
        set_room_meta(room_id, meta)
        
    accepted = await manager.connect(room_id, websocket, user_id)
    if not accepted:
        return

    redis = get_redis()
    is_host = meta["host_id"] == user_id

    # Handle room locking
    if meta["is_locked"] and not is_host:
        await manager.send_personal_message({"type": "PASSCODE_REQUIRED"}, websocket)
        verified = False
        try:
            while not verified:
                data = await websocket.receive_text()
                message_dict = json.loads(data)
                if message_dict.get("type") == "submit_passcode":
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

    # Send current state
    if redis:
        try:
            state_data = redis.get(f"room:{room_id}:state")
            if state_data:
                await websocket.send_json({"type": "sync", "payload": json.loads(state_data)})
        except Exception: pass
    else:
        state_data = in_memory_state.get(room_id)
        if state_data:
            await websocket.send_json({"type": "sync", "payload": state_data})

    # Send Chat History
    history = []
    if redis:
        try:
            raw_history = redis.lrange(f"room:{room_id}:messages", -50, -1)
            if raw_history: history = [json.loads(m) for m in raw_history]
        except Exception: pass
    else:
        history = in_memory_messages.get(room_id, [])[-50:]
    await websocket.send_json({"type": "history", "payload": history})
        
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
                
                # Re-fetch meta to ensure we have latest host_id
                current_meta = get_room_meta(room_id) or meta
                is_currently_host = current_meta["host_id"] == user_id
                
                # --- NTP Clock Sync ---
                if msg_type == "PING":
                    # Respond with PONG to allow client to calculate RTT & clock offset
                    client_time = payload.get("client_time", 0)
                    await manager.send_personal_message({
                        "type": "PONG",
                        "payload": {
                            "client_time": client_time,
                            "server_time": time.time() * 1000
                        }
                    }, websocket)
                    continue

                elif msg_type == "REQUEST_SYNC":
                    # Client requesting immediate authoritative state
                    auth_state = None
                    if redis:
                        try:
                            st = redis.get(f"room:{room_id}:state")
                            if st: auth_state = json.loads(st)
                        except Exception: pass
                    else:
                        auth_state = in_memory_state.get(room_id)
                        
                    if auth_state:
                        await manager.send_personal_message({
                            "type": "SYNC_TIME",
                            "payload": {
                                "server_time": time.time() * 1000,
                                "progress": auth_state.get("progress", 0),
                                "action": auth_state.get("action", "pause"),
                                "state_timestamp": auth_state.get("timestamp", 0) * 1000
                            }
                        }, websocket)
                    continue

                # --- Playback Controls (Host Only) ---
                elif msg_type in ("play", "pause", "seek", "SUBTITLE_TRACK_CHANGED"):
                    if not is_currently_host:
                        await manager.send_personal_message({
                            "type": "HOST_ACTION_DENIED",
                            "error": "Only the host can control playback."
                        }, websocket)
                        continue
                        
                    # Calculate new state
                    sync_data = payload if isinstance(payload, dict) else {}
                    sync_data["action"] = msg_type
                    sync_data["timestamp"] = time.time()
                    
                    if redis:
                        try:
                            redis.set(f"room:{room_id}:state", json.dumps(sync_data))
                            redis.expire(f"room:{room_id}:state", 86400)
                        except Exception: pass
                    else:
                        in_memory_state[room_id] = sync_data

                    # Broadcast the action and the authoritative state
                    # We broadcast action directly for quick client response
                    broadcast_msg = validated_msg.model_dump()
                    # Add authoritative server time for syncing
                    broadcast_msg["payload"]["server_time"] = time.time() * 1000
                    await manager.broadcast(room_id, broadcast_msg, sender=websocket)
                    # We could also trigger a SYNC_TIME here, but the above is enough
                    
                # --- Chat ---
                elif msg_type == "chat":
                    if user_id in current_meta.get("muted_users", []):
                        await manager.send_personal_message({"error": "You are muted"}, websocket)
                        continue

                    text = payload.get("text", "") if isinstance(payload, dict) else str(payload)
                    text = html.escape(text.strip())
                    if not text or len(text) > 500:
                        continue
                    
                    chat_msg = {"user": user_id, "text": text, "timestamp": time.time()}
                    
                    try:
                        if redis:
                            key = f"room:{room_id}:messages"
                            redis.rpush(key, json.dumps(chat_msg))
                            redis.ltrim(key, -100, -1)
                            redis.expire(key, 86400)
                        else:
                            if room_id not in in_memory_messages: in_memory_messages[room_id] = []
                            in_memory_messages[room_id].append(chat_msg)
                            if len(in_memory_messages[room_id]) > 100: in_memory_messages[room_id].pop(0)
                    except Exception: pass
                    
                    await manager.broadcast(room_id, {"type": "chat", "user": user_id, "payload": {"text": text, "timestamp": chat_msg["timestamp"]}}, sender=websocket)
                    
                elif msg_type == "reaction":
                    await manager.broadcast(room_id, {"type": "reaction", "user": user_id, "payload": payload}, sender=websocket)
                    
                # --- Host Moderation Actions ---
                elif msg_type in ("TRANSFER_HOST", "KICK_USER", "MUTE_USER", "LOCK_ROOM", "UNLOCK_ROOM"):
                    if not is_currently_host:
                        await manager.send_personal_message({"error": "Only host can perform this action"}, websocket)
                        continue
                    
                    if msg_type == "TRANSFER_HOST":
                        target_id = payload.get("user_id")
                        if target_id and target_id in manager.get_participants(room_id):
                            current_meta["host_id"] = target_id
                            set_room_meta(room_id, current_meta)
                            await manager.broadcast(room_id, {"type": "TRANSFER_HOST", "payload": {"host_id": target_id}}, sender=websocket)
                            await manager.send_personal_message({"type": "TRANSFER_HOST", "payload": {"host_id": target_id}}, websocket)

                    elif msg_type == "KICK_USER":
                        target_id = payload.get("user_id")
                        if target_id and target_id != user_id and target_id in manager.get_participants(room_id):
                            target_ws = manager.get_websocket_for_user(room_id, target_id)
                            if target_ws:
                                await manager.send_personal_message({"type": "USER_KICKED", "payload": {"reason": "Kicked by host"}}, target_ws)
                                await target_ws.close(code=4000, reason="Kicked by host")
                                manager.disconnect(room_id, target_ws)
                                await manager.broadcast(room_id, {"type": "user_left", "user": target_id}, sender=websocket)
                            
                    elif msg_type == "MUTE_USER":
                        target_id = payload.get("user_id")
                        is_muted = payload.get("muted", True)
                        if target_id and target_id in manager.get_participants(room_id):
                            muted_set = set(current_meta.get("muted_users", []))
                            if is_muted: muted_set.add(target_id)
                            else: muted_set.discard(target_id)
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
