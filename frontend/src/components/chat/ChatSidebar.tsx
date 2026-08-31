'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, X, Send, ShieldAlert } from 'lucide-react';
import EmojiReactions from './EmojiReactions';

interface Message {
    user: string;
    userId?: string;
    text: string;
    timestamp: string;
}

interface Participant {
    userId: string;
    username: string;
    avatar: string;
}

interface ChatSidebarProps {
    messages: Message[];
    participants: Participant[];
    currentUserId: string;
    chatInput: string;
    setChatInput: (val: string) => void;
    onSendMessage: (e: React.FormEvent) => void;
    isMuted: boolean;
    connectionStatus: 'connecting' | 'connected' | 'disconnected';
    onClose?: () => void;
    isFullscreen?: boolean;
}

export default function ChatSidebar({
    messages,
    participants,
    currentUserId,
    chatInput,
    setChatInput,
    onSendMessage,
    isMuted,
    connectionStatus,
    onClose,
    isFullscreen = false,
}: ChatSidebarProps) {
    const chatScrollRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        chatScrollRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    return (
        <motion.aside
            initial={{ x: 320, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 320, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className={`glass-panel room-sidebar flex flex-col border-l border-white/10 bg-slate-900/90 backdrop-blur-md ${isFullscreen ? 'h-full' : 'absolute top-20 right-5 bottom-5 w-80 rounded-xl'
                }`}
            style={{ zIndex: 50 }}
        >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/10 p-4">
                <div className="flex items-center gap-2">
                    <Users size={18} className="text-violet-400" />
                    <span className="font-semibold text-sm text-slate-100">
                        Room Chat ({participants.length})
                    </span>
                </div>
                {onClose && (
                    <button
                        onClick={onClose}
                        className="rounded-full p-1.5 text-slate-400 hover:bg-white/10 hover:text-white transition-colors"
                        aria-label="Close chat"
                    >
                        <X size={16} />
                    </button>
                )}
            </div>

            {/* Participants Pills */}
            <div className="border-b border-white/10 p-3">
                <div className="flex flex-wrap gap-2">
                    {participants.map((p) => (
                        <div
                            key={p.userId}
                            className="group relative flex items-center gap-2 rounded-full bg-slate-800/80 px-3 py-1.5 border border-white/5"
                            title={p.username}
                        >
                            <div className="relative">
                                <img
                                    src={p.avatar || `https://ui-avatars.com/api/?name=${p.username}&background=random`}
                                    alt={p.username}
                                    className="h-6 w-6 rounded-full object-cover"
                                />
                                {/* Online status ring */}
                                <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full border-2 border-slate-800 bg-emerald-500" />
                                1
                            </div>
                            <span className="text-xs font-medium text-slate-200">
                                {p.userId === currentUserId ? 'You' : p.username}
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
                {messages.length === 0 ? (
                    <div className="flex h-full flex-col items-center justify-center text-center text-slate-500">
                        <p className="text-sm">No messages yet.</p>
                        <p className="text-xs mt-1">Be the first to say hello!</p>
                    </div>
                ) : (
                    messages.map((m, i) => {
                        const isMe = m.userId === currentUserId || m.user === currentUserId;
                        return (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}
                            >
                                <div
                                    className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${isMe
                                            ? 'bg-violet-600/90 text-white rounded-br-md'
                                            : 'bg-slate-800/80 text-slate-100 rounded-bl-md border border-white/5'
                                        }`}
                                >
                                    {!isMe && (
                                        <div className="mb-1 flex items-center gap-2">
                                            <span className="text-xs font-semibold text-violet-300">
                                                @{m.user || 'Guest'}
                                            </span>
                                            {m.timestamp && (
                                                <span className="text-[10px] text-slate-500">{m.timestamp}</span>
                                            )}
                                        </div>
                                    )}
                                    <p className="text-sm leading-relaxed break-words">{m.text}</p>
                                </div>
                            </motion.div>
                        );
                    })
                )}
                <div ref={chatScrollRef} />
            </div>

            {/* Quick Emoji Reactions */}
            <div className="border-t border-white/10 bg-slate-900/50 p-2">
                <EmojiReactions onReact={(emoji) => {
                    // Handled by parent via WS, but we can trigger local optimistically if needed
                }} />
            </div>

            {/* Input Area */}
            <form onSubmit={onSendMessage} className="border-t border-white/10 p-4">
                <div className="relative flex items-center gap-2">
                    <input
                        type="text"
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        placeholder={isMuted ? "You are muted by host" : "Type a message..."}
                        className="flex-1 rounded-xl border border-white/10 bg-slate-800/50 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={connectionStatus !== 'connected' || isMuted}
                        maxLength={500}
                    />
                    <button
                        type="submit"
                        disabled={!chatInput.trim() || connectionStatus !== 'connected' || isMuted}
                        className="rounded-xl bg-violet-600 p-2.5 text-white transition-colors hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed"
                        aria-label="Send message"
                    >
                        <Send size={18} />
                    </button>
                </div>
                {isMuted && (
                    <div className="mt-2 flex items-center gap-1.5 text-xs text-red-400">
                        <ShieldAlert size={12} />
                        <span>You have been muted by the room host.</span>
                    </div>
                )}
            </form>
        </motion.aside>
    );
}
