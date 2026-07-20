'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Play, Pause, Maximize, Volume2, Users, MessageSquare } from 'lucide-react';
import { useParams } from 'next/navigation';

export default function WatchRoomPage() {
  const params = useParams();
  const roomId = params.id as string;
  
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [messages, setMessages] = useState<{user: string, text: string}[]>([
    { user: 'System', text: 'Welcome to the Watch Party!' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [participants, setParticipants] = useState<string[]>(['You']);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const userIdRef = useRef<string | null>(null);

  const connectWebSocket = useCallback(() => {
    // Basic fallback for token 
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') || '' : '';
    // Normally would use env var for WS URL, using hardcoded local as per issue details
    const wsUrl = `ws://localhost:8001/api/v1/room/ws/${roomId}${token ? `?token=${token}` : ''}`;
    
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
        if (message.type === 'sync') {
          if (message.data.action === 'play') {
            setIsPlaying(true);
          } else if (message.data.action === 'pause') {
            setIsPlaying(false);
          }
          if (message.data.progress !== undefined) {
            setProgress(message.data.progress);
          }
        } else if (message.type === 'chat') {
          setMessages(prev => [...prev, { user: message.user || 'Unknown', text: message.data.text }]);
        } else if (message.type === 'user_joined') {
          if (!userIdRef.current) userIdRef.current = message.user; // capture our ID if it's the first time
          setParticipants(prev => {
             if (!prev.includes(message.user)) return [...prev, message.user];
             return prev;
          });
          setMessages(prev => [...prev, { user: 'System', text: `${message.user} joined the room` }]);
        } else if (message.type === 'user_left') {
          setParticipants(prev => prev.filter(p => p !== message.user));
          setMessages(prev => [...prev, { user: 'System', text: `${message.user} left the room` }]);
        }
      } catch (err) {
        console.error('Failed to parse WS message', err);
      }
    };

    ws.current.onclose = () => {
      console.log('Disconnected from WS');
      setConnectionStatus('disconnected');
      // Auto-reconnect after 3 seconds
      reconnectTimeout.current = setTimeout(connectWebSocket, 3000);
    };
    
    ws.current.onerror = (error) => {
      console.error('WS Error:', error);
      ws.current?.close();
    };
  }, [roomId]);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      if (ws.current) ws.current.close();
    };
  }, [connectWebSocket]);

  const emitSync = (action: string, newProgress?: number) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'sync',
        data: {
          action,
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
    emitSync(isPlaying ? 'play' : 'pause', newProgress);
  };

  const handleChat = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'chat',
        data: { text: chatInput }
      }));
      setMessages(prev => [...prev, { user: 'You', text: chatInput }]);
      setChatInput('');
    }
  };

  return (
    <main style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#000' }}>
      {/* Video Area */}
      <div style={{ flex: 1, position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
        
        {/* Connection Status Indicator */}
        <div style={{ position: 'absolute', top: 20, left: 20, zIndex: 50, display: 'flex', alignItems: 'center', gap: 8, background: 'rgba(0,0,0,0.5)', padding: '6px 12px', borderRadius: 20 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: connectionStatus === 'connected' ? '#10b981' : connectionStatus === 'connecting' ? '#f59e0b' : '#ef4444' }} />
          <span style={{ fontSize: 12, color: 'white', textTransform: 'capitalize' }}>{connectionStatus}</span>
        </div>

        {/* Placeholder Video */}
        <div style={{ width: '100%', height: '100%', backgroundImage: 'url(https://image.tmdb.org/t/p/original/8rpDcsfLJypbO6vtecsmHLsC88C.jpg)', backgroundSize: 'cover', backgroundPosition: 'center', filter: isPlaying ? 'none' : 'brightness(0.6)' }} />
        
        {/* Play/Pause Overlay animation */}
        {!isPlaying && (
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
        <div className="glass-panel" style={{ position: 'absolute', bottom: '20px', left: '20px', right: '320px', padding: '16px', display: 'flex', alignItems: 'center', gap: '20px' }}>
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
      <div className="glass-panel" style={{ position: 'absolute', top: '80px', right: '20px', bottom: '20px', width: '280px', display: 'flex', flexDirection: 'column', border: '1px solid rgba(255,255,255,0.1)' }}>
        
        {/* Participants */}
        <div style={{ padding: '16px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <Users size={16} color="var(--accent-secondary)" />
            <span style={{ fontWeight: 600, fontSize: '14px' }}>Room Participants ({participants.length})</span>
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {participants.map(p => (
              <div key={p} style={{ background: 'rgba(255,255,255,0.1)', padding: '4px 10px', borderRadius: '999px', fontSize: '12px', whiteSpace: 'nowrap' }}>
                {p}
              </div>
            ))}
          </div>
        </div>

        {/* Chat Messages */}
        <div style={{ flex: 1, padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {messages.map((m, i) => (
            <div key={i} style={{ background: m.user === 'You' ? 'rgba(229,9,20,0.1)' : 'rgba(255,255,255,0.05)', padding: '10px 14px', borderRadius: '12px', alignSelf: m.user === 'You' ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '2px' }}>{m.user}</div>
              <div style={{ fontSize: '14px' }}>{m.text}</div>
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
              placeholder="Type a message..."
              aria-label="Chat message"
              className="input-glass"
              style={{ padding: '10px 16px', fontSize: '14px', width: '100%' }}
              disabled={connectionStatus !== 'connected'}
            />
          </div>
        </form>

      </div>
    </main>
  );
}
