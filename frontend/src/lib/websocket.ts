/**
 * Centralized WebSocket management utility for Watch Party rooms.
 * Handles connection lifecycle, automatic reconnection, and typed message routing.
 */

export type WSMessageType =
    | 'ROOM_HYDRATION'
    | 'USER_JOINED'
    | 'USER_LEFT'
    | 'CHAT_MESSAGE'
    | 'EMOJI_REACTION'
    | 'peer-joined'
    | 'peer-left'
    | 'offer'
    | 'answer'
    | 'ice-candidate'
    | 'play'
    | 'pause'
    | 'seek'
    | 'chat'
    | 'reaction'
    | 'user_joined'
    | 'user_left'
    | 'sync'
    | 'PASSCODE_REQUIRED'
    | 'PASSCODE_REJECTED'
    | 'PASSCODE_ACCEPTED'
    | 'room_state'
    | 'history'
    | 'TRANSFER_HOST'
    | 'USER_KICKED'
    | 'USER_MUTED'
    | 'USER_UNMUTED'
    | 'ROOM_LOCKED'
    | 'ROOM_UNLOCKED';

export interface WSMessage {
    type: WSMessageType;
    data?: any;
    payload?: any;
    user?: string;
    peerId?: string;
    senderId?: string;
    error?: string;
}

export class RoomWebSocket {
    private ws: WebSocket | null = null;
    private roomId: string;
    private userId: string;
    private token: string | null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 2000;
    private messageHandlers: Map<WSMessageType, ((data: any) => void)[]> = new Map();
    private isManualClose = false;

    constructor(roomId: string, userId: string, token: string | null = null) {
        this.roomId = roomId;
        this.userId = userId;
        this.token = token;
    }

    public connect(username: string = 'Guest', avatar: string = '') {
        if (this.ws?.readyState === WebSocket.OPEN) return;

        this.isManualClose = false;
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const configuredUrl = process.env.NEXT_PUBLIC_WS_URL;

        let wsUrl = `${protocol}//${host}/ws/room/${this.roomId}/${this.userId}?username=${encodeURIComponent(username)}&avatar=${encodeURIComponent(avatar)}`;

        if (configuredUrl) {
            const wsBase = configuredUrl.replace(/\/$/, '');
            wsUrl = `${wsBase}/room/ws/room/${this.roomId}/${this.userId}?username=${encodeURIComponent(username)}&avatar=${encodeURIComponent(avatar)}`;
        }

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log(`[WS] Connected to room ${this.roomId}`);
            this.reconnectAttempts = 0;
        };

        this.ws.onmessage = (event) => {
            try {
                const message: WSMessage = JSON.parse(event.data);
                const handlers = this.messageHandlers.get(message.type) || [];
                handlers.forEach(handler => handler(message.data || message.payload || message));
            } catch (err) {
                console.error('[WS] Failed to parse message:', err);
            }
        };

        this.ws.onclose = (event) => {
            console.log(`[WS] Disconnected from room ${this.roomId}`, event.code);
            if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                console.log(`[WS] Reconnecting in ${this.reconnectDelay}ms...`);
                setTimeout(() => this.connect(username, avatar), this.reconnectDelay);
                this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 10000);
            }
        };

        this.ws.onerror = (error) => {
            console.error('[WS] Error:', error);
        };
    }

    public send(type: WSMessageType, data?: any) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type, data }));
        } else {
            console.warn('[WS] Cannot send message, socket not open');
        }
    }

    public on(type: WSMessageType, handler: (data: any) => void) {
        if (!this.messageHandlers.has(type)) {
            this.messageHandlers.set(type, []);
        }
        this.messageHandlers.get(type)!.push(handler);
    }

    public off(type: WSMessageType, handler: (data: any) => void) {
        const handlers = this.messageHandlers.get(type);
        if (handlers) {
            this.messageHandlers.set(type, handlers.filter(h => h !== handler));
        }
    }

    public close() {
        this.isManualClose = true;
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}
