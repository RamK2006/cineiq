import html
import json
import time
import uuid
from typing import Any, Dict, List, Literal, Optional

import bcrypt
import structlog
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.metrics import websocket_connected_clients
from app.core.security import get_current_user, verify_token
from app.db.session import get_redis

logger = structlog.get_logger()
router = APIRouter(prefix="/room", tags=["watch-party"])

# Dynamic type definitions for WebSocket events
MessageType = Literal[
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
    "PING",
    "REQUEST_SYNC",
]


class WSMessage(BaseModel):
    type: MessageType
    payload: Optional[Any] = None




class CreateRoomRequest(BaseModel):
    passcode: Optional[str] = None


# ------------------------------------------------------------------------------
# Redis & Memory Storage Helpers
# ------------------------------------------------------------------------------
in_memory_messages: Dict[str, List[dict]] = {}
in_memory_meta: Dict[str, dict] = {}
in_memory_state: Dict[str, dict] = {}


def get_room_meta(room_id: str) -> Optional[dict]:
    redis = get_redis()
    if redis:
        try:
            data = redis.get(f"room:{room_id}:meta")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning("redis_get_meta_failed", error=str(e))
    return in_memory_meta.get(room_id)


def set_room_meta(room_id: str, meta: dict):
    redis = get_redis()
    if redis:
        try:
            redis.set(f"room:{room_id}:meta", json.dumps(meta))
            redis.expire(f"room:{room_id}:meta", 86400)
            return
        except Exception as e:
            logger.warning("redis_set_meta_failed", error=str(e))
    in_memory_meta[room_id] = meta


def save_chat_message(room_id: str, chat_msg: dict):
    redis = get_redis()
    if redis:
        try:
            key = f"room:{room_id}:messages"
            redis.rpush(key, json.dumps(chat_msg))
            redis.ltrim(key, -100, -1)
            redis.expire(key, 86400)
            return
        except Exception as e:
            logger.error("redis_save_chat_failed", error=str(e))
    
    in_memory_messages.setdefault(room_id, []).append(chat_msg)
    if len(in_memory_messages[room_id]) > 100:
        in_memory_messages[room_id].pop(0)


def get_chat_history(room_id: str, limit: int = 50) -> List[dict]:
    redis = get_redis()
    if redis:
        try:
            raw_history = redis.lrange(f"room:{room_id}:messages", -limit, -1)
            if raw_history:
                return [json.loads(m) for m in raw_history]
        except Exception as e:
            logger.warning("redis_get_history_failed", error=str(e))
    return in_memory_messages.get(room_id, [])[-limit:]


def update_room_playback_state(room_id: str, sync_data: dict):
    redis = get_redis()
    if redis:
        try:
            redis.set(f"room:{room_id}:state", json.dumps(sync_data))
            redis.expire(f"room:{room_id}:state", 86400)
            return
        except Exception as e:
            logger.error("redis_set_state_failed", error=str(e))
    in_memory_state[room_id] = sync_data


def get_room_playback_state(room_id: str) -> Optional[dict]:
    redis = get_redis()
    if redis:
        try:
            state_data = redis.get(f"room:{room_id}:state")
            if state_data:
                return json.loads(state_data)
        except Exception as e:
            logger.error("redis_get_state_failed", error=str(e))
    return in_memory_state.get(room_id)


def hash_passcode(passcode: str) -> str:
    return bcrypt.hashpw(passcode.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_passcode(passcode: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(passcode.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ------------------------------------------------------------------------------
# Centralized Connection Manager
# ------------------------------------------------------------------------------
class RoomManager:
    def __init__(self):
        # room_id -> { websocket: {"user_id": str, "username": str, "avatar": str} }
        self.active_connections: Dict[str, Dict[WebSocket, dict]] = {}

    async def connect(
        self, room_id: str, websocket: WebSocket, user_id: str, username: str = "Guest", avatar: str = ""
    ) -> bool:
        room_connections = self.active_connections.setdefault(room_id, {})
        if len(room_connections) >= settings.max_room_participants:
            await websocket.close(code=1008, reason="Room capacity full")
            logger.info("ws_client_rejected_room_full", room_id=room_id, user_id=user_id)
            return False

        await websocket.accept()
        room_connections[websocket] = {
            "user_id": user_id,
            "username": username,
            "avatar": avatar or f"https://ui-avatars.com/api/?name={username}&background=random",
        }
        websocket_connected_clients.inc()
        logger.info("ws_client_connected", room_id=room_id, user_id=user_id)
        return True

    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.active_connections:
            if websocket in self.active_connections[room_id]:
                del self.active_connections[room_id][websocket]
                websocket_connected_clients.dec()
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
                in_memory_messages.pop(room_id, None)
                in_memory_state.pop(room_id, None)
        logger.info("ws_client_disconnected", room_id=room_id)

    async def broadcast(self, room_id: str, message: dict, sender: Optional[WebSocket] = None):
        if room_id not in self.active_connections:
            return
        stale_connections = []
        payload = json.dumps(message)
        for connection in list(self.active_connections[room_id].keys()):
            if connection != sender:
                try:
                    await connection.send_text(payload)
                except Exception as e:
                    logger.error("ws_broadcast_error", error=str(e))
                    stale_connections.append(connection)

        for conn in stale_connections:
            self.disconnect(room_id, conn)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error("ws_send_error", error=str(e))

    def get_participants(self, room_id: str) -> List[dict]:
        if room_id in self.active_connections:
            return [
                {
                    "userId": info["user_id"],
                    "username": info["username"],
                    "avatar": info["avatar"],
                }
                for info in self.active_connections[room_id].values()
            ]
        return []

    def get_user_ids(self, room_id: str) -> List[str]:
        if room_id in self.active_connections:
            return [info["user_id"] for info in self.active_connections[room_id].values()]
        return []

    def get_websocket_for_user(self, room_id: str, user_id: str) -> Optional[WebSocket]:
        if room_id in self.active_connections:
            for ws, info in self.active_connections[room_id].items():
                if info["user_id"] == user_id:
                    return ws
        return None


manager = RoomManager()


# ------------------------------------------------------------------------------
# REST Endpoints
# ------------------------------------------------------------------------------
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
    update_room_playback_state(room_id, initial_state)

    return {"room_id": room_id, "status": "created"}


# ------------------------------------------------------------------------------
# WebRTC Mesh Signaling Endpoint
# ------------------------------------------------------------------------------
@router.websocket("/ws/mesh/{room_id}/{user_id}")
async def room_websocket_signaling_endpoint(
    websocket: WebSocket,
    room_id: str,
    user_id: str,
    username: str = "Guest",
    avatar: str = "",
):
    """Endpoint for WebRTC peer-to-peer mesh signaling and lightweight state updates."""
    accepted = await manager.connect(room_id, websocket, user_id, username, avatar)
    if not accepted:
        return

    # Send hydration payload
    await manager.send_personal_message(
        {
            "type": "ROOM_HYDRATION",
            "data": {
                "members": manager.get_participants(room_id),
                "history": get_chat_history(room_id),
            },
        },
        websocket,
    )

    # Broadcast presence and signaling connections
    await manager.broadcast(
        room_id,
        {
            "type": "USER_JOINED",
            "data": {"userId": user_id, "username": username, "avatar": avatar},
        },
        sender=websocket,
    )
    await manager.broadcast(
        room_id, {"type": "peer-joined", "peerId": user_id}, sender=websocket
    )

    try:
        while True:
            raw_data = await websocket.receive_text()
            packet = json.loads(raw_data)
            event_type = packet.get("type")

            if event_type in ["offer", "answer", "ice-candidate"]:
                await manager.broadcast(
                    room_id,
                    {
                        "type": event_type,
                        "senderId": user_id,
                        "data": packet.get("data"),
                    },
                    sender=websocket,
                )

    except WebSocketDisconnect:
        logger.info(f"[MESH DISCONNECT] User {user_id} disconnected from room {room_id}")
    finally:
        manager.disconnect(room_id, websocket)
        await manager.broadcast(room_id, {"type": "USER_LEFT", "data": {"userId": user_id}})
        await manager.broadcast(room_id, {"type": "peer-left", "peerId": user_id})


# ------------------------------------------------------------------------------
# Core Watch Party Control WebSocket Endpoint
# ------------------------------------------------------------------------------
@router.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket, room_id: str, token: str = Query(None)
):
    """WebSocket endpoint for real-time video playback synchronization and room chat."""
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return

    try:
        payload = await verify_token(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008, reason="User ID missing from token")
            return
    except Exception:
        await websocket.close(code=1008, reason="Authentication failed")
        return

    meta = get_room_meta(room_id)
    if not meta:
        meta = {
            "host_id": user_id,
            "is_locked": False,
            "passcode_hash": None,
            "muted_users": [],
        }
        set_room_meta(room_id, meta)

    if not await manager.connect(room_id, websocket, user_id):
        return

    is_host = meta["host_id"] == user_id

    # Handle passcode gatekeeping for locked rooms
    if meta["is_locked"] and not is_host:
        await manager.send_personal({"type": "PASSCODE_REQUIRED"}, websocket)
        try:
            verified = False
            while not verified:
                data = await websocket.receive_text()
                message_dict = json.loads(data)
                if message_dict.get("type") == "submit_passcode":
                    passcode = message_dict.get("payload", {}).get("passcode", "")
                    if meta["passcode_hash"] and verify_passcode(
                        passcode, meta["passcode_hash"]
                    ):
                        verified = True
                        await manager.send_personal({"type": "PASSCODE_ACCEPTED"}, websocket)
                    else:
                        await manager.send_personal({"type": "PASSCODE_REJECTED"}, websocket)
                else:
                    await manager.send_personal_message(
                        {"error": "Passcode required to join"}, websocket
                    )
        except (WebSocketDisconnect, Exception):
            manager.disconnect(room_id, websocket)
            return

    # Hydrate connecting user with initial room state
    state_data = get_room_playback_state(room_id)
    if state_data:
        await manager.send_personal_message({"type": "sync", "payload": state_data}, websocket)

    await manager.send_personal_message(
        {"type": "history", "payload": get_chat_history(room_id)}, websocket
    )
    await manager.send_personal_message(
        {
            "type": "room_state",
            "payload": {
                "host_id": meta["host_id"],
                "participants": manager.get_user_ids(room_id),
                "is_locked": meta["is_locked"],
                "muted_users": meta.get("muted_users", []),
            },
        },
        websocket,
    )

    # Notify existing members of new entry
    await manager.broadcast(
        room_id, {"type": "user_joined", "user": user_id}, sender=websocket
    )

    try:
        while True:
            data = await websocket.receive_text()
            current_server_time = time.time()

            try:
                msg = WSMessage(**json.loads(data))
                msg_type, payload = msg.type, msg.payload or {}

                # NTP Clock Calibration
                if msg_type == "PING":
                    client_t1 = payload.get("client_t1") if isinstance(payload, dict) else None
                    await manager.send_personal_message(
                        {
                            "type": "PONG",
                            "client_t1": client_t1,
                            "server_t2": current_server_time,
                            "server_t3": time.time(),
                        },
                        websocket,
                    )
                    continue

                elif msg_type == "REQUEST_SYNC":
                    current_state = get_room_playback_state(room_id) or {}
                    await manager.send_personal_message(
                        {"type": "sync", "payload": current_state}, websocket
                    )
                    continue

                # Chat Processing
                elif msg_type == "chat":
                    current_meta = get_room_meta(room_id)
                    if current_meta and user_id in current_meta.get("muted_users", []):
                        await manager.send_personal_message(
                            {"error": "You are muted"}, websocket
                        )
                        continue

                    text = payload.get("text", "") if isinstance(payload, dict) else str(payload)
                    text = html.escape(text.strip())
                    if not text or len(text) > 500:
                        continue

                    chat_msg = {
                        "user": user_id,
                        "text": text,
                        "timestamp": current_server_time,
                    }
                    save_chat_message(room_id, chat_msg)

                    await manager.broadcast(
                        room_id,
                        {
                            "type": "chat",
                            "user": user_id,
                            "payload": {"text": text, "timestamp": chat_msg["timestamp"]},
                        },
                    )

                # Playback State Synchronization
                elif msg_type in ("play", "pause", "seek", "SUBTITLE_TRACK_CHANGED"):
                    sync_data = payload if isinstance(payload, dict) else {}
                    existing = get_room_playback_state(room_id) or {}

                    if msg_type != "SUBTITLE_TRACK_CHANGED":
                        sync_data["action"] = msg_type
                    else:
                        sync_data["action"] = existing.get("action", "pause")
                        sync_data["progress"] = existing.get("progress", 0)
                        sync_data["activeTrackId"] = payload.get("trackId")

                    sync_data["timestamp"] = current_server_time
                    update_room_playback_state(room_id, sync_data)

                    await manager.broadcast(
                        room_id, validated_msg.model_dump(), sender=websocket
                    )

                # Volatile Reaction Handling
                elif msg_type == "reaction":
                    await manager.broadcast(
                        room_id,
                        {"type": "reaction", "user": user_id, "payload": payload},
                    )

                # Host Moderation Controls
                elif msg_type in (
                    "TRANSFER_HOST",
                    "KICK_USER",
                    "MUTE_USER",
                    "LOCK_ROOM",
                    "UNLOCK_ROOM",
                ):
                    current_meta = get_room_meta(room_id)
                    if not current_meta or current_meta["host_id"] != user_id:
                        await manager.send_personal({"error": "Only host can perform actions"}, websocket)
                        continue

                    if msg_type == "TRANSFER_HOST":
                        target_id = payload.get("user_id")
                        if target_id and target_id in manager.get_user_ids(room_id):
                            current_meta["host_id"] = target_id
                            set_room_meta(room_id, current_meta)
                            await manager.broadcast(
                                room_id,
                                {
                                    "type": "TRANSFER_HOST",
                                    "payload": {"host_id": target_id},
                                },
                            )

                    elif msg_type == "KICK_USER":
                        target_id = payload.get("user_id")
                        if target_id and target_id != user_id:
                            target_ws = manager.get_websocket_for_user(room_id, target_id)
                            if target_ws:
                                await manager.send_personal_message(
                                    {
                                        "type": "USER_KICKED",
                                        "payload": {"reason": "Kicked by host"},
                                    },
                                    target_ws,
                                )
                                await target_ws.close(code=4000, reason="Kicked by host")
                                manager.disconnect(room_id, target_ws)
                                await manager.broadcast(
                                    room_id, {"type": "user_left", "user": target_id}
                                )

                    elif msg_type == "MUTE_USER":
                        target_id = payload.get("user_id")
                        is_muted = payload.get("muted", True)
                        if target_id and target_id in manager.get_user_ids(room_id):
                            muted_set = set(current_meta.get("muted_users", []))
                            if is_muted:
                                muted_set.add(target_id)
                            else:
                                muted_set.discard(target_id)
                            current_meta["muted_users"] = list(muted_set)
                            set_room_meta(room_id, current_meta)

                            event_name = "USER_MUTED" if is_muted else "USER_UNMUTED"
                            await manager.broadcast(
                                room_id, {"type": event_name, "user": target_id}
                            )

                    elif msg_type == "LOCK_ROOM":
                        current_meta["is_locked"] = True
                        set_room_meta(room_id, current_meta)
                        await manager.broadcast(room_id, {"type": "ROOM_LOCKED"})

                    elif msg_type == "UNLOCK_ROOM":
                        current_meta["is_locked"] = False
                        set_room_meta(room_id, current_meta)
                        await manager.broadcast(room_id, {"type": "ROOM_UNLOCKED"})

            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {"error": "Invalid JSON format"}, websocket
                )
            except ValidationError as e:
                await manager.send_personal_message(
                    {"error": "Invalid message schema", "details": e.errors()}, websocket
                )

    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
        await manager.broadcast(room_id, {"type": "user_left", "user": user_id})
