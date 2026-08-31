from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.security import HTTPAuthorizationCredentials
from typing import Dict, Literal, Optional, Any, List
from pydantic import BaseModel, ValidationError
import json
import structlog
import uuid
import time
import html
import bcrypt

from app.core.config import settings
from app.core.security import verify_token, get_current_user
from app.db.session import get_redis
from app.core.metrics import websocket_connected_clients

logger = structlog.get_logger()
router = APIRouter(prefix="/room", tags=["watch-party"])

# In-memory storage fallbacks
in_memory_messages: Dict[str, list] = {}
in_memory_meta: Dict[str, dict] = {}
in_memory_state: Dict[str, dict] = {}

ROOM_SIGNALING_REGISTRY: Dict[str, Dict[str, WebSocket]] = {}
ROOM_PRESENCE_REGISTRY: Dict[str, Dict[str, dict]] = {}
ROOM_CHAT_HISTORY: Dict[str, List[dict]] = {}


class WSMessage(BaseModel):
    type: Literal[
        "play",
        "pause",
        "seek",
        "chat",
        "submit_passcode",
        "TRANSFER_HOST",
        "KICK_USER",
        "MUTE_USER",
        "LOCK_ROOM",
        "UNLOCK_ROOM",
        "SUBTITLE_TRACK_CHANGED",
        "reaction",
    ]
    payload: Optional[Any] = None


class CreateRoomRequest(BaseModel):
    passcode: Optional[str] = None


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[WebSocket, str]] = {}

    async def connect(self, room_id: str, websocket: WebSocket, user_id: str) -> bool:
        room_connections = self.active_connections.get(room_id, {})
        if len(room_connections) >= settings.max_room_participants:
            await websocket.close(code=1008, reason="Room is full")
            logger.info("ws_client_rejected_room_full", room_id=room_id)
            return False

        await websocket.accept()
        self.active_connections.setdefault(room_id, {})[websocket] = user_id
        websocket_connected_clients.inc()
        logger.info("ws_client_connected", room_id=room_id)
        return True

    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.active_connections:
            if websocket in self.active_connections[room_id]:
                del self.active_connections[room_id][websocket]
                websocket_connected_clients.dec()
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
        logger.info("ws_client_disconnected", room_id=room_id)

    async def broadcast(self, room_id: str, message: dict, sender: Optional[WebSocket] = None):
        if room_id not in self.active_connections:
            return
        
        stale = []
        payload = message
        for connection in self.active_connections[room_id]:
            if connection != sender:
                try:
                    await connection.send_json(payload)
                except Exception as e:
                    logger.error("ws_broadcast_error", error=str(e))
                    stale.append(connection)
        for conn in stale:
            self.disconnect(room_id, conn)

    async def send_personal(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error("ws_send_error", error=str(e))

    def get_participants(self, room_id: str) -> List[str]:
        return list(self.active_connections.get(room_id, {}).values())

    def get_user_socket(self, room_id: str, user_id: str) -> Optional[WebSocket]:
        for ws, uid in self.active_connections.get(room_id, {}).items():
            if uid == user_id:
                return ws
        return None


manager = ConnectionManager()


# Helper Utilities
def get_room_meta(room_id: str) -> Optional[dict]:
    redis = get_redis()
    if redis:
        try:
            if data := redis.get(f"room:{room_id}:meta"):
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
            return
        except Exception:
            pass
    in_memory_meta[room_id] = meta


async def broadcast_mesh(room_id: str, sender_id: str, message: dict):
    if room_id in ROOM_SIGNALING_REGISTRY:
        payload = json.dumps(message)
        for peer_id, client_ws in list(ROOM_SIGNALING_REGISTRY[room_id].items()):
            if peer_id != sender_id:
                try:
                    await client_ws.send_text(payload)
                except Exception as e:
                    logger.error(f"Signaling dispatch failed to {peer_id}: {str(e)}")


async def broadcast_presence(room_id: str, message: dict, exclude_id: Optional[str] = None):
    if room_id in ROOM_PRESENCE_REGISTRY:
        payload = json.dumps(message)
        for uid, client in list(ROOM_PRESENCE_REGISTRY[room_id].items()):
            if exclude_id is None or uid != exclude_id:
                try:
                    await client["ws"].send_text(payload)
                except Exception as e:
                    logger.error(f"Presence broadcast failed in {room_id}: {str(e)}")


@router.post("/create")
async def create_room(req: Optional[CreateRoomRequest] = None, current_user: str = Depends(get_current_user)):
    room_id = str(uuid.uuid4())
    passcode_hash = bcrypt.hashpw(req.passcode.encode("utf-8"), bcrypt.gensalt()).decode("utf-8") if req and req.passcode else None

    meta = {
        "host_id": current_user,
        "is_locked": bool(passcode_hash),
        "passcode_hash": passcode_hash,
        "muted_users": [],
    }
    set_room_meta(room_id, meta)

    initial_state = {"action": "pause", "progress": 0, "timestamp": time.time()}
    redis = get_redis()
    if redis:
        try:
            redis.set(f"room:{room_id}:state", json.dumps(initial_state))
            redis.expire(f"room:{room_id}:state", 86400)
        except Exception as e:
            logger.error("redis_set_state_failed", error=str(e))
    else:
        in_memory_state[room_id] = initial_state

    return {"room_id": room_id, "status": "created"}


@router.websocket("/ws/room/{room_id}/{user_id}")
@router.websocket("/ws/mesh/{room_id}/{user_id}")
async def room_websocket_signaling_endpoint(
    websocket: WebSocket, room_id: str, user_id: str, username: str = "Guest", avatar: str = ""
):
    await websocket.accept()

    ROOM_SIGNALING_REGISTRY.setdefault(room_id, {})
    if len(ROOM_SIGNALING_REGISTRY[room_id]) >= 4:
        await websocket.close(code=4001, reason="Watch Party room mesh capacity full.")
        return

    ROOM_SIGNALING_REGISTRY[room_id][user_id] = websocket
    ROOM_PRESENCE_REGISTRY.setdefault(room_id, {})
    
    avatar_url = avatar or f"https://ui-avatars.com/api/?name={username}&background=random"
    ROOM_PRESENCE_REGISTRY[room_id][user_id] = {"ws": websocket, "username": username, "avatar": avatar_url}

    current_members = [
        {"userId": uid, "username": meta["username"], "avatar": meta["avatar"]}
        for uid, meta in ROOM_PRESENCE_REGISTRY[room_id].items()
    ]

    redis = get_redis()
    recent_history = []
    if redis:
        try:
            if raw := redis.lrange(f"room:{room_id}:messages", -50, -1):
                recent_history = [json.loads(m) for m in raw]
        except Exception:
            pass
    if not recent_history:
        recent_history = ROOM_CHAT_HISTORY.get(room_id, [])[-50:]

    await websocket.send_text(json.dumps({
        "type": "ROOM_HYDRATION",
        "data": {"members": current_members, "history": recent_history}
    }))

    await broadcast_presence(room_id, {"type": "USER_JOINED", "data": {"userId": user_id, "username": username, "avatar": avatar_url}}, exclude_id=user_id)
    await broadcast_mesh(room_id, user_id, {"type": "peer-joined", "peerId": user_id})

    try:
        while True:
            packet = json.loads(await websocket.receive_text())
            event_type = packet.get("type")

            if event_type == "CHAT_MESSAGE":
                data_obj = packet.get("data", {})
                msg_payload = {
                    "userId": user_id,
                    "username": username,
                    "text": data_obj.get("text", packet.get("text", "")),
                    "timestamp": data_obj.get("timestamp", "") or time.strftime("%H:%M", time.gmtime()),
                }

                if redis:
                    try:
                        key = f"room:{room_id}:messages"
                        redis.rpush(key, json.dumps(msg_payload))
                        redis.ltrim(key, -50, -1)
                        redis.expire(key, 86400)
                    except Exception:
                        ROOM_CHAT_HISTORY.setdefault(room_id, []).append(msg_payload)
                else:
                    ROOM_CHAT_HISTORY.setdefault(room_id, []).append(msg_payload)

                await broadcast_presence(room_id, {"type": "CHAT_MESSAGE", "data": msg_payload})

            elif event_type == "EMOJI_REACTION":
                emoji = packet.get("data", {}).get("emoji", packet.get("emoji", "🍿"))
                await broadcast_presence(room_id, {"type": "EMOJI_REACTION", "data": {"userId": user_id, "emoji": emoji}})

            elif event_type in ["offer", "answer", "ice-candidate"]:
                await broadcast_mesh(room_id, user_id, {"type": event_type, "senderId": user_id, "data": packet.get("data")})

    except WebSocketDisconnect:
        logger.info(f"Signaling disconnect: {user_id}")
    finally:
        if room_id in ROOM_SIGNALING_REGISTRY:
            ROOM_SIGNALING_REGISTRY[room_id].pop(user_id, None)
            if not ROOM_SIGNALING_REGISTRY[room_id]:
                del ROOM_SIGNALING_REGISTRY[room_id]

        if room_id in ROOM_PRESENCE_REGISTRY:
            ROOM_PRESENCE_REGISTRY[room_id].pop(user_id, None)
            if not ROOM_PRESENCE_REGISTRY[room_id]:
                del ROOM_PRESENCE_REGISTRY[room_id]

        await broadcast_presence(room_id, {"type": "USER_LEFT", "data": {"userId": user_id}})
        await broadcast_mesh(room_id, user_id, {"type": "peer-left", "peerId": user_id})


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, token: str = Query(None)):
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return

    try:
        payload = await verify_token(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008, reason="User ID missing in token")
            return
    except Exception:
        await websocket.close(code=1008, reason="Authentication failed")
        return

    meta = get_room_meta(room_id) or {
        "host_id": user_id,
        "is_locked": False,
        "passcode_hash": None,
        "muted_users": [],
    }
    set_room_meta(room_id, meta)

    if not await manager.connect(room_id, websocket, user_id):
        return

    is_host = (meta["host_id"] == user_id)
    redis = get_redis()

    if meta["is_locked"] and not is_host:
        await manager.send_personal({"type": "PASSCODE_REQUIRED"}, websocket)
        try:
            verified = False
            while not verified:
                msg = json.loads(await websocket.receive_text())
                if msg.get("type") == "submit_passcode":
                    passcode = msg.get("payload", {}).get("passcode", "")
                    if meta["passcode_hash"] and bcrypt.checkpw(passcode.encode(), meta["passcode_hash"].encode()):
                        verified = True
                        await manager.send_personal({"type": "PASSCODE_ACCEPTED"}, websocket)
                    else:
                        await manager.send_personal({"type": "PASSCODE_REJECTED"}, websocket)
                else:
                    await manager.send_personal({"error": "Passcode required"}, websocket)
        except Exception:
            manager.disconnect(room_id, websocket)
            return

    # Send Initial Sync Payload
    if redis:
        if state := redis.get(f"room:{room_id}:state"):
            await manager.send_personal({"type": "sync", "payload": json.loads(state)}, websocket)
    elif state := in_memory_state.get(room_id):
        await manager.send_personal({"type": "sync", "payload": state}, websocket)

    # Send Chat History
    history = []
    if redis:
        if raw := redis.lrange(f"room:{room_id}:messages", -50, -1):
            history = [json.loads(m) for m in raw]
    else:
        history = in_memory_messages.get(room_id, [])[-50:]
    await manager.send_personal({"type": "history", "payload": history}, websocket)

    # Room State & Notifications
    await manager.send_personal({
        "type": "room_state",
        "payload": {
            "host_id": meta["host_id"],
            "participants": manager.get_participants(room_id),
            "is_locked": meta["is_locked"],
            "muted_users": meta["muted_users"],
        }
    }, websocket)

    await manager.broadcast(room_id, {"type": "user_joined", "user": user_id}, sender=websocket)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = WSMessage(**json.loads(data))
                msg_type, payload = msg.type, msg.payload or {}

                if msg_type == "chat":
                    if user_id in get_room_meta(room_id).get("muted_users", []):
                        await manager.send_personal({"error": "You are muted"}, websocket)
                        continue

                    text = html.escape(str(payload.get("text", "") if isinstance(payload, dict) else payload).strip())
                    if not text or len(text) > 500:
                        continue

                    chat_msg = {"user": user_id, "text": text, "timestamp": time.time()}
                    if redis:
                        key = f"room:{room_id}:messages"
                        redis.rpush(key, json.dumps(chat_msg))
                        redis.ltrim(key, -100, -1)
                        redis.expire(key, 86400)
                    else:
                        in_memory_messages.setdefault(room_id, []).append(chat_msg)

                    await manager.broadcast(room_id, {"type": "chat", "user": user_id, "payload": chat_msg})

                elif msg_type == "reaction":
                    await manager.broadcast(room_id, {"type": "reaction", "user": user_id, "payload": payload}, sender=websocket)

                elif msg_type in ("play", "pause", "seek", "SUBTITLE_TRACK_CHANGED"):
                    await manager.broadcast(room_id, msg.model_dump(), sender=websocket)
                    sync_data = payload if isinstance(payload, dict) else {}
                    sync_data["action"] = msg_type
                    sync_data["timestamp"] = time.time()
                    
                    if redis:
                        redis.set(f"room:{room_id}:state", json.dumps(sync_data))
                        redis.expire(f"room:{room_id}:state", 86400)
                    else:
                        in_memory_state[room_id] = sync_data

                elif msg_type in ("TRANSFER_HOST", "KICK_USER", "MUTE_USER", "LOCK_ROOM", "UNLOCK_ROOM"):
                    current_meta = get_room_meta(room_id)
                    if not current_meta or current_meta["host_id"] != user_id:
                        await manager.send_personal({"error": "Only host can perform actions"}, websocket)
                        continue

                    if msg_type == "TRANSFER_HOST" and (target_id := payload.get("user_id")) in manager.get_participants(room_id):
                        current_meta["host_id"] = target_id
                        set_room_meta(room_id, current_meta)
                        await manager.broadcast(room_id, {"type": "TRANSFER_HOST", "payload": {"host_id": target_id}})

                    elif msg_type == "KICK_USER" and (target_id := payload.get("user_id")) and target_id != user_id:
                        if target_ws := manager.get_user_socket(room_id, target_id):
                            await manager.send_personal({"type": "USER_KICKED"}, target_ws)
                            await target_ws.close(code=4000, reason="Kicked by host")
                            manager.disconnect(room_id, target_ws)
                            await manager.broadcast(room_id, {"type": "user_left", "user": target_id})

                    elif msg_type == "MUTE_USER" and (target_id := payload.get("user_id")):
                        muted_set = set(current_meta.get("muted_users", []))
                        if payload.get("muted", True):
                            muted_set.add(target_id)
                        else:
                            muted_set.discard(target_id)
                        current_meta["muted_users"] = list(muted_set)
                        set_room_meta(room_id, current_meta)
                        ev = "USER_MUTED" if payload.get("muted", True) else "USER_UNMUTED"
                        await manager.broadcast(room_id, {"type": ev, "user": target_id})

                    elif msg_type in ("LOCK_ROOM", "UNLOCK_ROOM"):
                        current_meta["is_locked"] = (msg_type == "LOCK_ROOM")
                        set_room_meta(room_id, current_meta)
                        await manager.broadcast(room_id, {"type": msg_type})

            except json.JSONDecodeError:
                await manager.send_personal({"error": "Invalid JSON"}, websocket)
            except ValidationError as e:
                await manager.send_personal({"error": "Invalid message schema", "details": e.errors()}, websocket)

    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
        await manager.broadcast(room_id, {"type": "user_left", "user": user_id})
