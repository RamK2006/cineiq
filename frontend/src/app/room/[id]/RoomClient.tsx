'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Pause, Maximize, Volume2, Users, Lock, Unlock, LogOut, MessageSquare, X } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth, useUser } from '@clerk/nextjs';
import VideoPlayer from '@/components/VideoPlayer';
import CinemaOverlay, { Reaction } from '@/components/CinemaOverlay';
import { SubtitleTrackData } from '@/types/media';
import VoiceMeshOverlay from '@/components/VoiceMeshOverlay';
import { usePushToTalk } from '@/hooks/usePushToTalk';
import { VoiceStatus } from '@/hooks/useAudioAnalyzer';
import ChatSidebar from '@/components/chat/ChatSidebar';
import { RoomWebSocket, WSMessage } from '@/lib/websocket';

export default function RoomClient() {
  const params = useParams();
  const router = useRouter();
  const roomId = params.id as string;
  const { user } = useUser();
  const { getToken } = useAuth();

  const currentUserId = user?.id || 'unknown';
  const userName = user?.fullName ?? user?.username ?? user?.primaryEmailAddress?.emailAddress ?? 'You';
  const userAvatar = user?.imageUrl || '';

  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [messages, setMessages] = useState<{ user: string; userId?: string; text: string; timestamp: string }[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [members, setMembers] = useState<{ userId: string; username: string; avatar: string }[]>([]);
  const [reactions, setReactions] = useState<Reaction[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');

  // Moderation state
  const [hostId, setHostId] = useState<string | null>(null);
  const [mutedUsers, setMutedUsers] = useState<string[]>([]);
  const [isLocked, setIsLocked] = useState(false);
  const [showPasscodeModal, setShowPasscodeModal] = useState(false);
  const [passcodeInput, setPasscodeInput] = useState('');
  const [passcodeError, setPasscodeError] = useState('');
  const [kicked, setKicked] = useState(false);
  const [activeTrackId, setActiveTrackId] = useState<string | null>(null);
  
  const availableTracks: SubtitleTrackData[] = [
    { id: 'en', label: 'English', language: 'en', src: '/subtitles/en.srt', kind: 'subtitles', format: 'srt' },
    { id: 'es', label: 'Spanish', language: 'es', src: '/subtitles/es.vtt', kind: 'subtitles', format: 'vtt' }
  ];
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const expectedDisconnect = useRef<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isChatVisible, setChatVisible] = useState(true);

  const roomVideoAreaRef = useRef<HTMLDivElement>(null);


  // WebRTC Voice Mesh state
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [peerStreams, setPeerStreams] = useState<Map<string, MediaStream>>(new Map());
  const [cameraActive, setCameraActive] = useState(true);
  const [micActive, setMicActive] = useState(false);
  const [voiceStates, setVoiceStates] = useState<Record<string, VoiceStatus>>({});
  const { isPttActive, shortcutKey, changeShortcut } = usePushToTalk('v');

  const wsRef = useRef<RoomWebSocket | null>(null);

  const triggerFloatingEmoji = useCallback((emoji: string) => {
    const id = String(Date.now() + Math.random());
    setReactions(prev => [...prev, { id, emoji, timestamp: Date.now() }]);
    setTimeout(() => {
      setReactions(prev => prev.filter(r => r.id !== id));
    }, 2000);
  }, []);


  const handleSendReaction = useCallback((emoji: string) => {
    if (wsRef.current) {
      wsRef.current.send('EMOJI_REACTION', { emoji });
    }
    triggerFloatingEmoji(emoji);
  }, [triggerFloatingEmoji]);

  const connectWebSocket = useCallback(async () => {
    if (kicked) return;
    const token = await getToken();
    if (!token) {
      setConnectionStatus('disconnected');
      return;
    }

    const ws = new RoomWebSocket(roomId, currentUserId, token);
    wsRef.current = ws;

    ws.on('ROOM_HYDRATION', (data) => {
      if (data?.members) setMembers(data.members);
      if (data?.history) {
        setMessages(data.history.map((m: any) => ({
          user: m.username || m.userId || 'Guest',
          userId: m.userId,
          text: m.text || '',
          timestamp: m.timestamp || ''
        })));
      }
    });

    ws.on('USER_JOINED', (data) => {
      if (data?.userId) {
        setMembers(prev => [...prev.filter(m => m.userId !== data.userId), data]);
        setMessages(prev => [...prev, { user: 'System', text: `${data.username} joined the room`, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
      }
    });

    ws.on('USER_LEFT', (data) => {
      if (data?.userId) {
        setMembers(prev => prev.filter(m => m.userId !== data.userId));
        // Find username for system message if possible, otherwise generic
        setMessages(prev => [...prev, { user: 'System', text: `A participant left the room`, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
      }
    });

    ws.on('CHAT_MESSAGE', (data) => {
      if (data) {
        setMessages(prev => [...prev, {
          user: data.username || data.userId || 'Guest',
          userId: data.userId,
          text: data.text || '',
          timestamp: data.timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
      }
    });

    ws.on('EMOJI_REACTION', (data) => {
      if (data?.emoji) triggerFloatingEmoji(data.emoji);
    });

    ws.on('room_state', (payload) => {
      setHostId(payload.host_id);
      setIsLocked(payload.is_locked);
      setMutedUsers(payload.muted_users || []);
    });

    ws.on('sync', (payload) => {
      if (payload?.action === 'play') setIsPlaying(true);
      else if (payload?.action === 'pause') setIsPlaying(false);
      if (payload?.progress !== undefined) setProgress(payload.progress);
    });

    ws.on('USER_KICKED', () => {
      setKicked(true);
      ws.close();
      setTimeout(() => router.push('/'), 3000);
    });

    ws.on('USER_MUTED', (data) => {
      if (data?.user) setMutedUsers(prev => prev.includes(data.user) ? prev : [...prev, data.user]);
    });

    ws.on('USER_UNMUTED', (data) => {
      if (data?.user) setMutedUsers(prev => prev.filter(u => u !== data.user));
    });

    ws.on('ROOM_LOCKED', () => setIsLocked(true));
    ws.on('ROOM_UNLOCKED', () => setIsLocked(false));
    ws.on('PASSCODE_REQUIRED', () => { setShowPasscodeModal(true); setPasscodeError(''); });
    ws.on('PASSCODE_REJECTED', () => setPasscodeError('Incorrect passcode'));
    ws.on('PASSCODE_ACCEPTED', () => { setShowPasscodeModal(false); setPasscodeError(''); });


    // Connect the underlying WebSocket
    ws.connect(userName, userAvatar);
    setConnectionStatus('connected');
  }, [roomId, currentUserId, getToken, kicked, router, userName, userAvatar, triggerFloatingEmoji]);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connectWebSocket]);

  const emitSync = useCallback((action: 'play' | 'pause' | 'seek', newProgress?: number) => {
    if (wsRef.current) {
      wsRef.current.send(action, { progress: newProgress !== undefined ? newProgress : progress });
    }
  }, [progress]);


  const handlePlayPause = useCallback(() => {
    const newIsPlaying = !isPlaying;
    setIsPlaying(newIsPlaying);
    emitSync(newIsPlaying ? 'play' : 'pause');
  }, [isPlaying, emitSync]);

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const newProgress = Math.min(100, Math.max(0, (x / rect.width) * 100));
    setProgress(newProgress);
    emitSync('seek', newProgress);
  };

  const handleChat = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || mutedUsers.includes(currentUserId)) return;

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (wsRef.current) {
      wsRef.current.send('CHAT_MESSAGE', { text: chatInput, timestamp });
    }
    setChatInput('');
  };

  const submitPasscode = (e: React.FormEvent) => {
    e.preventDefault();
    if (!passcodeInput.trim() || !wsRef.current) return;
    wsRef.current.send('submit_passcode', { passcode: passcodeInput });
  };

  const toggleLock = () => {
    if (wsRef.current) {
      wsRef.current.send(isLocked ? 'UNLOCK_ROOM' : 'LOCK_ROOM');
    }
  };

  const handleTrackChange = (trackId: string | null) => {
    setActiveTrackId(trackId);
    if (wsRef.current) {
      wsRef.current.send('SUBTITLE_TRACK_CHANGED', { track_id: trackId });
    }
  };

  const isHost = currentUserId === hostId;

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      roomVideoAreaRef.current?.requestFullscreen().catch(err => console.error(`Fullscreen error: ${err.message}`));
    } else {
      document.exitFullscreen();
    }
  }, []);

  useEffect(() => {
    const handleFullscreenChange = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  const handleVoiceStatusChange = useCallback((peerId: string, status: VoiceStatus) => {
    setVoiceStates(prev => {
      if (prev[peerId] === status) return prev;
      return { ...prev, [peerId]: status };
    });
  }, []);

  if (kicked) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-black text-white">
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-8 text-center">
          <LogOut size={48} className="mx-auto mb-4 text-red-500" />
          <h2 className="mb-2 text-2xl font-semibold">You were removed from this room</h2>
          <p className="text-slate-400">Redirecting to home...</p>
        </div>
      </div>
    );
  }

  return (
    <main className="relative flex h-screen flex-col bg-black" ref={roomVideoAreaRef}>
      {/* Floating Animated Reaction Container */}
      <div className="pointer-events-none absolute bottom-24 right-80 z-50 flex flex-col gap-2">
        {reactions.map((r) => (
          <motion.span
            key={r.id}
            initial={{ opacity: 1, y: 0, scale: 0.8 }}
            animate={{ opacity: 0, y: -100, scale: 1.5 }}
            transition={{ duration: 1.8, ease: "easeOut" }}
            className="block text-center text-4xl"
          >
            {r.emoji}
          </motion.span>
        ))}
      </div>

      {/* Passcode Modal Overlay */}
      <AnimatePresence>
        {showPasscodeModal && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm"
          >
            <div className="w-full max-w-md rounded-2xl border border-white/10 bg-slate-900 p-8">
              <h2 className="mb-4 flex items-center gap-2 text-xl font-semibold text-white">
                <Lock size={20} /> Private Room
              </h2>
              <p className="mb-6 text-sm text-slate-400">This room is locked. Please enter the passcode to join.</p>
              <form onSubmit={submitPasscode}>
                <input
                  type="password"
                  value={passcodeInput}
                  onChange={(e) => setPasscodeInput(e.target.value)}
                  placeholder="Enter passcode"
                  className="mb-4 w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white placeholder-slate-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                  autoFocus
                />
                {passcodeError && <div className="mb-4 text-sm text-red-400">{passcodeError}</div>}
                <div className="flex gap-3">
                  <button type="button" onClick={() => router.push('/')} className="flex-1 rounded-xl border border-white/20 bg-transparent px-4 py-3 text-white transition-colors hover:bg-white/5">
                    Cancel
                  </button>
                  <button type="submit" className="flex-1 rounded-xl bg-violet-600 px-4 py-3 font-semibold text-white transition-colors hover:bg-violet-500">
                    Join Room
                  </button>
                </div>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Video Area */}

      <div className="relative flex flex-1 items-center justify-center overflow-hidden bg-black">
        {!isFullscreen && (
          <div className="absolute left-5 top-5 z-50 flex items-center gap-2 rounded-full bg-black/50 px-3 py-1.5">
            <div className={`h-2 w-2 rounded-full ${connectionStatus === 'connected' ? 'bg-emerald-500' : connectionStatus === 'connecting' ? 'bg-amber-500' : 'bg-red-500'}`} />
            <span className="text-xs capitalize text-white">{connectionStatus}</span>
          </div>
        )}

        {isHost && !isFullscreen && (
          <div className="absolute left-32 top-5 z-50">
            <button onClick={toggleLock} className="flex items-center gap-2 rounded-full bg-black/50 px-3 py-1.5 text-xs text-white transition-colors hover:bg-black/70">
              {isLocked ? <Lock size={14} /> : <Unlock size={14} />}
              {isLocked ? 'Room Locked' : 'Room Unlocked'}
            </button>
          </div>
        )}

        {!showPasscodeModal && (
          <>
            <VideoPlayer
              isPlaying={isPlaying}
              progress={progress}
              onPlayPause={(playing: boolean) => { setIsPlaying(playing); emitSync(playing ? 'play' : 'pause'); }}
              onSeek={(p: number) => { setProgress(p); emitSync('seek', p); }}
              tracks={availableTracks}
              activeTrackId={activeTrackId}
              onTrackChange={handleTrackChange}
            />

            <div className="absolute right-80 top-5 z-50 max-w-xs">
              <VoiceMeshOverlay
                localStream={localStream}
                peerStreams={peerStreams}
                cameraActive={cameraActive}
                micActive={micActive || isPttActive}
                onToggleCamera={() => setCameraActive(!cameraActive)}
                onToggleMic={() => setMicActive(!micActive)}
                onSelectDevice={async () => { }}
                onVoiceStatusChange={handleVoiceStatusChange}
                shortcutKey={shortcutKey}
                onChangeShortcut={changeShortcut}
              />
            </div>

            {!isPlaying && !showPasscodeModal && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                <motion.button
                  whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}
                  onClick={handlePlayPause} aria-label="Play video"
                  className="flex h-20 w-20 items-center justify-center rounded-full bg-violet-600 shadow-[0_0_30px_rgba(124,58,237,0.5)] transition-colors hover:bg-violet-500"
                >
                  <Play size={40} fill="white" className="ml-1 text-white" />
                </motion.button>
              </div>
            )}

            <CinemaOverlay
              isFullscreen={isFullscreen}
              messages={messages}
              chatInput={chatInput}
              setChatInput={setChatInput}
              handleChat={handleChat}
              currentUserId={currentUserId}
              isMuted={mutedUsers.includes(currentUserId)}
              reactions={reactions}
              onSendReaction={handleSendReaction}
              isChatVisible={isChatVisible}
              setChatVisible={setChatVisible}
            />

            {/* Video Controls Bottom Bar */}
            <div className="glass-panel absolute bottom-5 left-5 right-5 z-50 flex items-center gap-5 rounded-xl border border-white/10 bg-black/60 px-5 py-4 transition-all duration-300" style={{ right: isFullscreen ? '1.25rem' : '21rem' }}>
              <button onClick={handlePlayPause} aria-label={isPlaying ? 'Pause' : 'Play'} className="text-white hover:text-violet-400">
                {isPlaying ? <Pause size={24} fill="white" /> : <Play size={24} fill="white" />}
              </button>
              <div onClick={handleSeek} className="flex-1 h-1.5 cursor-pointer rounded-full bg-white/20">
                <div style={{ width: `${progress}%` }} className="h-full rounded-full bg-violet-600 transition-all duration-100" />
              </div>
              <span className="font-mono text-sm text-slate-300">00:00 / 02:45:00</span>
              <button aria-label="Volume" className="text-white hover:text-violet-400"><Volume2 size={20} /></button>
              <button onClick={toggleFullscreen} aria-label="Fullscreen" className="text-white hover:text-violet-400"><Maximize size={20} /></button>
            </div>
          </>
        )}
      </div>

      {/* Chat Sidebar Component */}
      <AnimatePresence>
        {isChatVisible && !showPasscodeModal && (
          <ChatSidebar
            messages={messages}
            participants={members}
            currentUserId={currentUserId}
            chatInput={chatInput}
            setChatInput={setChatInput}
            onSendMessage={handleChat}
            isMuted={mutedUsers.includes(currentUserId)}
            connectionStatus={connectionStatus}
            onClose={() => setChatVisible(false)}
            isFullscreen={isFullscreen}
          />
        )}
      </AnimatePresence>

      {/* Toggle Chat Button (when hidden) */}
      {!isChatVisible && !showPasscodeModal && (
        <button
          onClick={() => setChatVisible(true)}
          className="absolute right-5 top-24 z-50 rounded-xl border border-white/10 bg-slate-900/80 p-3 text-white backdrop-blur-md transition-colors hover:bg-slate-800"
          aria-label="Open chat"
        >
          <MessageSquare size={20} />
        </button>
      )}
    </main>
  );
}
