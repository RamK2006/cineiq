'use client';

import { useState, useEffect, useRef } from 'react';
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

  // Mock participants
  const participants = ['You', 'Alex', 'Sarah'];

  useEffect(() => {
    // Scaffold WebSocket connection
    // TODO: Replace with actual WebSocket connection when backend is ready
    return () => {
      // Cleanup WebSocket connection on unmount
    };
  }, [roomId]);

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
    // In real app, emit WS event here
  };

  const handleChat = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput) return;
    setMessages(prev => [...prev, { user: 'You', text: chatInput }]);
    setChatInput('');
  };

  return (
    <main style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#000' }}>
      {/* Video Area */}
      <div style={{ flex: 1, position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
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
          
          <div style={{ flex: 1, height: '4px', background: 'rgba(255,255,255,0.2)', borderRadius: '2px', cursor: 'pointer' }}>
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
            <span style={{ fontWeight: 600, fontSize: '14px' }}>Room Participants</span>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            {participants.map(p => (
              <div key={p} style={{ background: 'rgba(255,255,255,0.1)', padding: '4px 10px', borderRadius: '999px', fontSize: '12px' }}>
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
              style={{ padding: '10px 16px', fontSize: '14px' }}
            />
          </div>
        </form>

      </div>
    </main>
  );
}
