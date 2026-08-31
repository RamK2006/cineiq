'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Pause, Maximize, Volume2, Users, MoreVertical, Lock, Unlock, LogOut } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth, useUser } from '@clerk/nextjs';
import VoiceMeshOverlay from '@/components/VoiceMeshOverlay';


export default function RoomClient() {
  const params = useParams();
  const router = useRouter();
  const roomId = params.id as string;
  
  const { user } = useUser();
  const { getToken } = useAuth();
  
  // Use user.id for unique identification, fallback to name
  const currentUserId = user?.id || 'unknown';
  const userName = user?.fullName ?? user?.username ?? user?.primaryEmailAddress?.emailAddress ?? 'You';

  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [messages, setMessages] = useState<{user: string, text: string}[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [participants, setParticipants] = useState<string[]>([currentUserId]);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  
  // Moderation state
  const [hostId, setHostId] = useState<string | null>(null);
  const [mutedUsers, setMutedUsers] = useState<string[]>([]);
  const [isLocked, setIsLocked] = useState(false);
  const [showPasscodeModal, setShowPasscodeModal] = useState(false);
  const [passcodeInput, setPasscodeInput] = useState('');
  const [passcodeError, setPasscodeError] = useState('');
  const [kicked, setKicked] = useState(false);
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const expectedDisconnect = useRef<boolean>(false);

  // Realtime WebRTC Voice Mesh state & refs
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [peerStreams, setPeerStreams] = useState<Map<string, MediaStream>>(new Map());
  const [cameraActive, setCameraActive] = useState(true);
  const [micActive, setMicActive] = useState(true);

  const meshWsRef = useRef<WebSocket | null>(null);
  const peersRef = useRef<Map<string, RTCPeerConnection>>(new Map());
  const localUserIdRef = useRef<string>(user?.id || `user_${Math.floor(Math.random() * 10000)}`);

  const initializeMeshWebSocket = useCallback((stream: MediaStream | null) => {
    if (typeof window === 'undefined') return;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const configuredUrl = process.env.NEXT_PUBLIC_WS_URL;
    let wsUrl = `${protocol}//${host}/ws/room/${roomId}/${localUserIdRef.current}`;
    if (configuredUrl) {
      const wsBase = configuredUrl.replace(/\/$/, '');
      wsUrl = `${wsBase}/room/ws/room/${roomId}/${localUserIdRef.current}`;
    }

    meshWsRef.current = new WebSocket(wsUrl);

    meshWsRef.current.onmessage = async (event) => {
      try {
        const message = JSON.parse(event.data);
        const { type, peerId, senderId, data } = message;

        switch (type) {
          case 'peer-joined':
            createNewPeerConnection(peerId, stream, true);
            break;
          case 'offer':
            const pcOffer = createNewPeerConnection(senderId, stream, false);
            await pcOffer.setRemoteDescription(new RTCSessionDescription(data));
            const answer = await pcOffer.createAnswer();
            await pcOffer.setLocalDescription(answer);
            meshWsRef.current?.send(JSON.stringify({ type: 'answer', data: answer }));
            break;
          case 'answer':
            const pcAnswer = peersRef.current.get(senderId);
            await pcAnswer?.setRemoteDescription(new RTCSessionDescription(data));
            break;
          case 'ice-candidate':
            const pcCandidate = peersRef.current.get(senderId);
            await pcCandidate?.addIceCandidate(new RTCIceCandidate(data));
            break;
          case 'peer-left':
            removePeer(peerId);
            break;
        }
      } catch (err) {
        console.error("WebRTC mesh signaling frame parse error:", err);
      }
    };
  }, [roomId]);

  const createNewPeerConnection = useCallback((targetPeerId: string, stream: MediaStream | null, initiateOffer: boolean) => {
    if (peersRef.current.has(targetPeerId)) {
      peersRef.current.get(targetPeerId)?.close();
    }

    const pc = new RTCPeerConnection({
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
      ]
    });

    peersRef.current.set(targetPeerId, pc);

    if (stream) {
      stream.getTracks().forEach(track => pc.addTrack(track, stream));
    }

    pc.onicecandidate = (e) => {
      if (e.candidate) {
        meshWsRef.current?.send(JSON.stringify({ type: 'ice-candidate', data: e.candidate }));
      }
    };

    pc.ontrack = (e) => {
      if (e.streams && e.streams[0]) {
        setPeerStreams(prev => {
          const next = new Map(prev);
          next.set(targetPeerId, e.streams[0]);
          return next;
        });
      }
    };

    if (initiateOffer) {
      pc.createOffer().then(async (offer) => {
        await pc.setLocalDescription(offer);
        meshWsRef.current?.send(JSON.stringify({ type: 'offer', data: offer }));
      }).catch(err => console.error("Error creating RTC offer:", err));
    }

    return pc;
  }, []);

  const removePeer = useCallback((targetPeerId: string) => {
    const pc = peersRef.current.get(targetPeerId);
    if (pc) {
      pc.close();
      peersRef.current.delete(targetPeerId);
    }
    setPeerStreams(prev => {
      const next = new Map(prev);
      next.delete(targetPeerId);
      return next;
    });
  }, []);

  useEffect(() => {
    let currentStream: MediaStream | null = null;
    if (typeof navigator !== 'undefined' && navigator.mediaDevices?.getUserMedia) {
      navigator.mediaDevices.getUserMedia({ video: true, audio: true })
        .then((stream) => {
          currentStream = stream;
          setLocalStream(stream);
          initializeMeshWebSocket(stream);
        })
        .catch((err) => {
          console.warn("Media capture fallback:", err);
          initializeMeshWebSocket(null);
        });
    } else {
      initializeMeshWebSocket(null);
    }

    const handleBeforeUnload = () => {
      meshWsRef.current?.close();
      peersRef.current.forEach(pc => pc.close());
      currentStream?.getTracks().forEach(track => track.stop());
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      meshWsRef.current?.close();
      peersRef.current.forEach(pc => pc.close());
      currentStream?.getTracks().forEach(track => track.stop());
    };
  }, [roomId, initializeMeshWebSocket]);

  const toggleCamera = () => {
    if (localStream) {
      localStream.getVideoTracks().forEach(track => {
        track.enabled = !cameraActive;
      });
      setCameraActive(!cameraActive);
    }
  };

  const toggleMic = () => {
    if (localStream) {
      localStream.getAudioTracks().forEach(track => {
        track.enabled = !micActive;
      });
      setMicActive(!micActive);
    }
  };

  const handleSelectDevice = async (kind: 'videoinput' | 'audioinput', deviceId: string) => {
    try {
      const constraints: MediaStreamConstraints = {};
      if (kind === 'videoinput') constraints.video = { deviceId: { exact: deviceId } };
      if (kind === 'audioinput') constraints.audio = { deviceId: { exact: deviceId } };

      const newStream = await navigator.mediaDevices.getUserMedia(constraints);
      const newTrack = kind === 'videoinput' ? newStream.getVideoTracks()[0] : newStream.getAudioTracks()[0];
      
      if (newTrack && localStream) {
        const oldTrack = kind === 'videoinput' ? localStream.getVideoTracks()[0] : localStream.getAudioTracks()[0];
        if (oldTrack) {
          localStream.removeTrack(oldTrack);
          oldTrack.stop();
        }
        localStream.addTrack(newTrack);

        peersRef.current.forEach((pc) => {
          const sender = pc.getSenders().find(s => s.track?.kind === (kind === 'videoinput' ? 'video' : 'audio'));
          if (sender) {
            sender.replaceTrack(newTrack);
          }
        });
      }
    } catch (err) {
      console.error("Failed to switch media device:", err);
    }
  };


  const connectWebSocket = useCallback(async () => {
    if (expectedDisconnect.current) return;
    const token = await getToken();
    if (!token) { setConnectionStatus('disconnected'); return; }
    const configuredUrl = process.env.NEXT_PUBLIC_WS_URL;
    const wsBase = configuredUrl || `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/api/v1`;
    const wsUrl = `${wsBase.replace(/\/$/, '')}/room/ws/${encodeURIComponent(roomId)}?token=${encodeURIComponent(token)}`;
    
    console.log(`Connecting to WS room: ${roomId}`);
    setConnectionStatus('connecting');
    
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('Connected to WS');
      setConnectionStatus('connected');
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
    };

    ws.current.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.error && showPasscodeModal) {
            setPasscodeError(message.error);
            return;
        }
        
        switch (message.type) {
          case 'PASSCODE_REQUIRED':
            setShowPasscodeModal(true);
            setPasscodeError('');
            break;
          case 'PASSCODE_REJECTED':
            setPasscodeError('Incorrect passcode');
            break;
          case 'PASSCODE_ACCEPTED':
            setShowPasscodeModal(false);
            setPasscodeError('');
            break;
          case 'room_state':
            setHostId(message.payload.host_id);
            setParticipants(message.payload.participants);
            setIsLocked(message.payload.is_locked);
            setMutedUsers(message.payload.muted_users || []);
            break;
          case 'play':
            setIsPlaying(true);
            if (message.payload?.progress !== undefined) setProgress(message.payload.progress);
            break;
          case 'pause':
            setIsPlaying(false);
            if (message.payload?.progress !== undefined) setProgress(message.payload.progress);
            break;
          case 'seek':
            if (message.payload?.progress !== undefined) setProgress(message.payload.progress);
            break;
          case 'history':
            const historyMessages = message.payload || [];
            setMessages(historyMessages.map((msg: any) => ({
              user: msg.user || 'Unknown',
              text: msg.text || ''
            })));
            break;
          case 'chat':
            setMessages(prev => [...prev, { user: message.user || 'Unknown', text: message.payload?.text || '' }]);
            break;
          case 'user_joined':
            setParticipants(prev => {
               if (!prev.includes(message.user)) return [...prev, message.user];
               return prev;
            });
            setMessages(prev => [...prev, { user: 'System', text: `${message.user} joined the room` }]);
            break;
          case 'user_left':
            setParticipants(prev => prev.filter(p => p !== message.user));
            setMessages(prev => [...prev, { user: 'System', text: `${message.user} left the room` }]);
            break;
          case 'sync':
            if (message.payload?.action === 'play') setIsPlaying(true);
            else if (message.payload?.action === 'pause') setIsPlaying(false);
            if (message.payload?.progress !== undefined) setProgress(message.payload.progress);
            break;
          case 'TRANSFER_HOST':
            setHostId(message.payload.host_id);
            break;
          case 'USER_KICKED':
            setKicked(true);
            expectedDisconnect.current = true;
            if (ws.current) ws.current.close();
            setTimeout(() => {
                router.push('/');
            }, 3000);
            break;
          case 'USER_MUTED':
            setMutedUsers(prev => prev.includes(message.user) ? prev : [...prev, message.user]);
            break;
          case 'USER_UNMUTED':
            setMutedUsers(prev => prev.filter(u => u !== message.user));
            break;
          case 'ROOM_LOCKED':
            setIsLocked(true);
            break;
          case 'ROOM_UNLOCKED':
            setIsLocked(false);
            break;
        }
      } catch (err) {
        console.error('Failed to parse WS message', err);
      }
    };

    ws.current.onclose = (event) => {
      console.log('Disconnected from WS', event.code);
      setConnectionStatus('disconnected');
      if (!expectedDisconnect.current && !kicked) {
        reconnectTimeout.current = setTimeout(connectWebSocket, 3000);
      }
    };
    
    ws.current.onerror = (error) => {
      console.error('WS Error:', error);
      ws.current?.close();
    };
  }, [getToken, roomId, kicked, router, showPasscodeModal]);

  useEffect(() => {
    void connectWebSocket();
    return () => {
      expectedDisconnect.current = true;
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      if (ws.current) ws.current.close();
    };
  }, [connectWebSocket]);

  const emitSync = (action: 'play' | 'pause' | 'seek', newProgress?: number) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: action,
        payload: {
          progress: newProgress !== undefined ? newProgress : progress
        }
      }));
    }
  };

  const handlePlayPause = () => {
    const newIsPlaying = !isPlaying;
    setIsPlaying(newIsPlaying);
    emitSync(newIsPlaying ? 'play' : 'pause');
  };
  
  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const newProgress = Math.min(100, Math.max(0, (x / rect.width) * 100));
    setProgress(newProgress);
    emitSync('seek', newProgress);
  };

  const handleChat = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    if (mutedUsers.includes(currentUserId)) return;
    
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'chat',
        payload: { text: chatInput }
      }));
      setChatInput('');
    }
  };

  const submitPasscode = (e: React.FormEvent) => {
      e.preventDefault();
      if (!passcodeInput.trim()) return;
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
          ws.current.send(JSON.stringify({
              type: 'submit_passcode',
              payload: { passcode: passcodeInput }
          }));
      }
  };

  const toggleLock = () => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
          ws.current.send(JSON.stringify({
              type: isLocked ? 'UNLOCK_ROOM' : 'LOCK_ROOM'
          }));
      }
  };
  
  const isHost = currentUserId === hostId;

  if (kicked) {
      return (
          <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: '#000', color: 'white' }}>
              <div style={{ background: 'rgba(239, 68, 68, 0.2)', border: '1px solid #ef4444', padding: '24px', borderRadius: '12px', textAlign: 'center' }}>
                  <LogOut size={48} color="#ef4444" style={{ margin: '0 auto 16px' }} />
                  <h2 style={{ fontSize: '24px', marginBottom: '8px' }}>You were removed from this room</h2>
                  <p style={{ color: 'var(--text-secondary)' }}>Redirecting to home...</p>
              </div>
          </div>
      );
  }

  return (
    <main className="room-container" style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#000' }}>
      
      {/* Passcode Modal Overlay */}
      <AnimatePresence>
        {showPasscodeModal && (
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{ position: 'fixed', inset: 0, zIndex: 100, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(5px)' }}
          >
            <div style={{ background: '#111827', padding: '32px', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.1)', width: '100%', maxWidth: '400px' }}>
                <h2 style={{ fontSize: '20px', color: 'white', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Lock size={20} /> Private Room
                </h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px' }}>This room is locked. Please enter the passcode to join.</p>
                <form onSubmit={submitPasscode}>
                    <input 
                        type="password" 
                        value={passcodeInput}
                        onChange={(e) => setPasscodeInput(e.target.value)}
                        placeholder="Enter passcode"
                        className="input-glass"
                        style={{ width: '100%', padding: '12px 16px', fontSize: '16px', marginBottom: '16px', background: 'rgba(255,255,255,0.05)', color: 'white', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                        autoFocus
                    />
                    {passcodeError && <div style={{ color: '#ef4444', fontSize: '14px', marginBottom: '16px' }}>{passcodeError}</div>}
                    <div style={{ display: 'flex', gap: '12px' }}>
                        <button type="button" onClick={() => router.push('/')} style={{ flex: 1, padding: '12px', background: 'transparent', color: 'white', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '8px', cursor: 'pointer' }}>Cancel</button>
                        <button type="submit" style={{ flex: 1, padding: '12px', background: 'var(--accent-primary)', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 600 }}>Join Room</button>
                    </div>
                </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Video Area */}
      <div className="room-video-area" style={{ flex: 1, position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
        
        {/* Connection Status Indicator */}
        <div style={{ position: 'absolute', top: 20, left: 20, zIndex: 50, display: 'flex', alignItems: 'center', gap: 8, background: 'rgba(0,0,0,0.5)', padding: '6px 12px', borderRadius: 20 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: connectionStatus === 'connected' ? '#10b981' : connectionStatus === 'connecting' ? '#f59e0b' : '#ef4444' }} />
          <span style={{ fontSize: 12, color: 'white', textTransform: 'capitalize' }}>{connectionStatus}</span>
        </div>
        
        {isHost && (
            <div style={{ position: 'absolute', top: 20, left: 140, zIndex: 50 }}>
                <button onClick={toggleLock} style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(0,0,0,0.5)', padding: '6px 12px', borderRadius: 20, color: 'white', border: 'none', cursor: 'pointer' }}>
                    {isLocked ? <Lock size={14} /> : <Unlock size={14} />}
                    <span style={{ fontSize: 12 }}>{isLocked ? 'Room Locked' : 'Room Unlocked'}</span>
                </button>
            </div>
        )}

        {/* Floating Voice Mesh Peer Overlay */}
        <div style={{ position: 'absolute', top: 20, right: 340, zIndex: 50, maxWidth: '320px' }}>
          <VoiceMeshOverlay
            localStream={localStream}
            peerStreams={peerStreams}
            cameraActive={cameraActive}
            micActive={micActive}
            onToggleCamera={toggleCamera}
            onToggleMic={toggleMic}
            onSelectDevice={handleSelectDevice}
          />
        </div>


        <div style={{ width: '100%', height: '100%', display: 'grid', placeItems: 'center', background: '#111827', color: 'var(--text-secondary)' }}>
          No licensed playback source is configured for this room.
        </div>
        
        {/* Play/Pause Overlay animation */}
        {!isPlaying && !showPasscodeModal && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.4)' }}>
            <motion.button 
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={handlePlayPause}
              aria-label="Play video"
              style={{ background: 'var(--accent-primary)', border: 'none', width: '80px', height: '80px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', boxShadow: '0 0 30px rgba(229,9,20,0.5)' }}
            >
              <Play size={40} fill="white" color="white" style={{ marginLeft: '6px' }} />
            </motion.button>
          </div>
        )}

        {/* Video Controls Bottom Bar */}
        <div className="glass-panel room-video-controls" style={{ position: 'absolute', bottom: '20px', left: '20px', right: '320px', padding: '16px', display: 'flex', alignItems: 'center', gap: '20px' }}>
          <button onClick={handlePlayPause} aria-label={isPlaying ? 'Pause video' : 'Play video'} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}>
            {isPlaying ? <Pause size={24} fill="white" /> : <Play size={24} fill="white" />}
          </button>
          
          <div onClick={handleSeek} style={{ flex: 1, height: '4px', background: 'rgba(255,255,255,0.2)', borderRadius: '2px', cursor: 'pointer' }}>
            <div style={{ width: `${progress}%`, height: '100%', background: 'var(--accent-primary)', borderRadius: '2px', transition: 'width 0.1s' }} />
          </div>

          <span style={{ fontFamily: 'var(--font-body)', fontSize: '14px' }}>00:00 / 02:45:00</span>
          
          <button aria-label="Adjust volume" style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}>
            <Volume2 size={20} />
          </button>
          <button aria-label="Toggle fullscreen" style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}>
            <Maximize size={20} />
          </button>
        </div>
      </div>

      {/* Right Sidebar: Chat & Participants */}
      <div className="glass-panel room-sidebar" style={{ position: 'absolute', top: '80px', right: '20px', bottom: '20px', width: '320px', display: 'flex', flexDirection: 'column', border: '1px solid rgba(255,255,255,0.1)' }}>
        
        {/* Participants */}
        <div style={{ padding: '16px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <Users size={16} color="var(--accent-secondary)" />
            <span style={{ fontWeight: 600, fontSize: '14px' }}>Room Participants ({participants.length})</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '150px', overflowY: 'auto' }}>
            {participants.map(p => (
              <ParticipantItem key={p} userId={p} isHost={isHost} roomHostId={hostId} isMuted={mutedUsers.includes(p)} currentUserId={currentUserId} ws={ws.current} />
            ))}
          </div>
        </div>

        {/* Chat Messages */}
        <div style={{ flex: 1, padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {messages.map((m, i) => (
            <div key={i} style={{ background: m.user === currentUserId ? 'rgba(229,9,20,0.1)' : 'rgba(255,255,255,0.05)', padding: '10px 14px', borderRadius: '12px', alignSelf: m.user === currentUserId ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '2px' }}>{m.user === currentUserId ? 'You' : m.user}</div>
              <div style={{ fontSize: '14px', wordBreak: 'break-word' }}>{m.text}</div>
            </div>
          ))}
        </div>

        {/* Chat Input */}
        <form onSubmit={handleChat} style={{ padding: '16px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input 
              type="text" 
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              placeholder={mutedUsers.includes(currentUserId) ? "You are muted" : "Type a message..."}
              aria-label="Chat message"
              className="input-glass"
              style={{ padding: '10px 16px', fontSize: '14px', width: '100%', background: mutedUsers.includes(currentUserId) ? 'rgba(255,0,0,0.1)' : undefined }}
              disabled={connectionStatus !== 'connected' || mutedUsers.includes(currentUserId)}
            />
          </div>
        </form>

      </div>
    </main>
  );
}

// Subcomponent for participant to isolate dropdown state
function ParticipantItem({ userId, isHost, roomHostId, isMuted, currentUserId, ws }: { userId: string, isHost: boolean, roomHostId: string | null, isMuted: boolean, currentUserId: string, ws: WebSocket | null }) {
    const [showMenu, setShowMenu] = useState(false);
    
    const isThisUserHost = userId === roomHostId;
    const isMe = userId === currentUserId;

    const handleAction = (action: string) => {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        ws.send(JSON.stringify({
            type: action,
            payload: { user_id: userId, muted: !isMuted } // payload reused
        }));
        setShowMenu(false);
    };

    return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 10px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px', position: 'relative' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '13px', color: 'white', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '140px' }}>
                    {userId} {isMe && '(You)'}
                </span>
                {isThisUserHost && <span style={{ fontSize: '10px', background: 'var(--accent-primary)', padding: '2px 6px', borderRadius: '4px', color: 'white' }}>Host</span>}
                {isMuted && <Volume2 size={12} color="#ef4444" />}
            </div>
            
            {isHost && !isMe && (
                <div style={{ position: 'relative' }}>
                    <button onClick={() => setShowMenu(!showMenu)} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                        <MoreVertical size={16} />
                    </button>
                    {showMenu && (
                        <div style={{ position: 'absolute', right: 0, top: '100%', background: '#1f2937', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '4px', zIndex: 10, minWidth: '120px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }}>
                            <button onClick={() => handleAction('TRANSFER_HOST')} style={{ width: '100%', textAlign: 'left', padding: '8px 12px', background: 'transparent', border: 'none', color: 'white', cursor: 'pointer', fontSize: '13px', borderRadius: '4px' }} className="menu-btn">Make Host</button>
                            <button onClick={() => handleAction('MUTE_USER')} style={{ width: '100%', textAlign: 'left', padding: '8px 12px', background: 'transparent', border: 'none', color: 'white', cursor: 'pointer', fontSize: '13px', borderRadius: '4px' }} className="menu-btn">{isMuted ? 'Unmute' : 'Mute'}</button>
                            <button onClick={() => handleAction('KICK_USER')} style={{ width: '100%', textAlign: 'left', padding: '8px 12px', background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '13px', borderRadius: '4px' }} className="menu-btn">Remove</button>
                        </div>
                    )}
                </div>
            )}
            
            {showMenu && <div style={{ position: 'fixed', inset: 0, zIndex: 9 }} onClick={() => setShowMenu(false)} />}
            
            <style jsx>{`
                .menu-btn:hover { background: rgba(255,255,255,0.1) !important; }
            `}</style>
        </div>
    );
}
