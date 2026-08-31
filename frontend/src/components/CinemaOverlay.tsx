import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Smile, MessageSquareOff, MessageSquare } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export interface Reaction {
  id: string;
  emoji: string;
  timestamp: number;
}

export interface CinemaOverlayProps {
  isFullscreen: boolean;
  messages: { user: string; text: string }[];
  chatInput: string;
  setChatInput: (val: string) => void;
  handleChat: (e: React.FormEvent) => void;
  currentUserId: string;
  isMuted: boolean;
  reactions: Reaction[];
  onSendReaction: (emoji: string) => void;
  isChatVisible: boolean;
  setChatVisible: (visible: boolean) => void;
}

export default function CinemaOverlay({
  isFullscreen,
  messages,
  chatInput,
  setChatInput,
  handleChat,
  currentUserId,
  isMuted,
  reactions,
  onSendReaction,
  isChatVisible,
  setChatVisible
}: CinemaOverlayProps) {
  const [isActive, setIsActive] = useState(true);
  const isFocusedRef = useRef(false);
  const inactivityTimer = useRef<NodeJS.Timeout | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const resetInactivity = useCallback(() => {
    setIsActive(true);
    if (inactivityTimer.current) clearTimeout(inactivityTimer.current);
    inactivityTimer.current = setTimeout(() => {
      if (!isFocusedRef.current) {
        setIsActive(false);
      }
    }, 3000);
  }, []);

  useEffect(() => {
    resetInactivity();
    return () => {
      if (inactivityTimer.current) clearTimeout(inactivityTimer.current);
    };
  }, [resetInactivity]);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  useEffect(() => {
    const handleMouseMove = () => resetInactivity();
    document.addEventListener('mousemove', handleMouseMove);
    return () => document.removeEventListener('mousemove', handleMouseMove);
  }, [resetInactivity]);

  if (!isFullscreen) return null;

  return (
    <div 
      ref={overlayRef}
      className="cinema-overlay" 
      style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 100, overflow: 'hidden' }}
    >
      {/* Reactions Overlay */}
      <AnimatePresence>
        {reactions.map((r) => (
          <motion.div
            key={r.id}
            initial={{ opacity: 0, y: 50, x: Math.random() * 20 - 10, scale: 0.5 }}
            animate={{ opacity: [0, 1, 1, 0], y: -200 - Math.random() * 100, x: Math.random() * 40 - 20, scale: [0.5, 1.2, 1] }}
            exit={{ opacity: 0 }}
            transition={{ duration: 2.5, ease: 'easeOut' }}
            style={{
              position: 'absolute',
              bottom: '120px',
              right: '340px',
              fontSize: '28px',
              pointerEvents: 'none',
              zIndex: 110,
              userSelect: 'none'
            }}
            aria-hidden="true"
          >
            {r.emoji}
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Floating Chat Panel */}
      <AnimatePresence>
        {isChatVisible && isActive && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.3 }}
            style={{
              position: 'absolute',
              bottom: '80px',
              right: '20px',
              width: '320px',
              height: '400px',
              maxHeight: '60vh',
              background: 'rgba(17, 24, 39, 0.75)',
              backdropFilter: 'blur(10px)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '16px',
              display: 'flex',
              flexDirection: 'column',
              pointerEvents: 'auto',
              boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
              zIndex: 120
            }}
            onMouseEnter={resetInactivity}
          >
            {/* Chat Header */}
            <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 600, color: 'white', fontSize: '14px' }}>Room Chat</span>
              <button 
                onClick={() => setChatVisible(false)}
                style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
                aria-label="Hide chat overlay"
              >
                <MessageSquareOff size={16} />
              </button>
            </div>

            {/* Chat Messages */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {messages.map((m, i) => (
                <div key={i} style={{ background: m.user === currentUserId ? 'rgba(229,9,20,0.2)' : 'rgba(255,255,255,0.1)', padding: '8px 12px', borderRadius: '12px', alignSelf: m.user === currentUserId ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '2px' }}>{m.user === currentUserId ? 'You' : m.user}</div>
                  <div style={{ fontSize: '13px', color: 'white', wordBreak: 'break-word' }}>{m.text}</div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {/* Quick Reactions */}
            <div style={{ padding: '8px 16px', display: 'flex', gap: '12px', justifyContent: 'center', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
               {['👍', '😂', '😮', '❤️', '🔥'].map(emoji => (
                 <button
                   key={emoji}
                   onClick={() => { onSendReaction(emoji); resetInactivity(); }}
                   style={{ background: 'transparent', border: 'none', fontSize: '20px', cursor: 'pointer', transition: 'transform 0.1s' }}
                   className="reaction-btn"
                   aria-label={`React with ${emoji}`}
                 >
                   {emoji}
                 </button>
               ))}
            </div>

            {/* Chat Input */}
            <form onSubmit={(e) => { handleChat(e); resetInactivity(); }} style={{ padding: '12px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
              <div style={{ display: 'flex', gap: '8px', position: 'relative' }}>
                <input 
                  type="text" 
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onFocus={() => { isFocusedRef.current = true; resetInactivity(); }}
                  onBlur={() => { isFocusedRef.current = false; resetInactivity(); }}
                  placeholder={isMuted ? "You are muted" : "Type a message..."}
                  aria-label="Cinema chat message"
                  style={{ padding: '10px 40px 10px 16px', fontSize: '13px', width: '100%', background: isMuted ? 'rgba(255,0,0,0.1)' : 'rgba(0,0,0,0.3)', color: 'white', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '20px', outline: 'none' }}
                  disabled={isMuted}
                />
                <button type="submit" disabled={isMuted || !chatInput.trim()} style={{ position: 'absolute', right: '4px', top: '4px', bottom: '4px', width: '32px', background: 'var(--accent-primary)', border: 'none', borderRadius: '50%', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: chatInput.trim() ? 'pointer' : 'default', opacity: chatInput.trim() ? 1 : 0.5 }}>
                  <Send size={14} />
                </button>
              </div>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
      <style jsx>{`
        .reaction-btn:hover { transform: scale(1.2); }
      `}</style>
    </div>
  );
}
