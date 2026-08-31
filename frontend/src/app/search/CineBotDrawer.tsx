'use client';

import { useRef, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, X, Bot, Film } from 'lucide-react';
import Image from 'next/image';
import { CineBotMessage } from '@/lib/cinebot';

interface CineBotDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  messages: CineBotMessage[];
  input: string;
  isLoading: boolean;
  onInputChange: (value: string) => void;
  onSendMessage: (e: React.FormEvent) => void;
}

export default function CineBotDrawer({
  isOpen,
  onClose,
  messages,
  input,
  isLoading,
  onInputChange,
  onSendMessage,
}: CineBotDrawerProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="fixed right-0 top-0 z-50 h-full w-full max-w-md border-l border-white/10 bg-slate-900/95 shadow-2xl backdrop-blur-xl dark:bg-slate-900/95 flex flex-col"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-white/10 p-4">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-violet-600/20 text-violet-400">
                <Bot size={18} />
              </div>
              <h2 className="font-semibold text-slate-100">CineBot Assistant</h2>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-slate-100"
              aria-label="Close CineBot"
            >
              <X size={20} />
            </button>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
            {messages.map((msg, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`max-w-[90%] rounded-2xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-violet-600 text-white rounded-br-md'
                      : 'bg-slate-800/80 text-slate-100 rounded-bl-md border border-white/5'
                  }`}
                >
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                </div>

                {/* Movie Recommendations Cards */}
                {msg.role === 'assistant' && msg.recommendations && msg.recommendations.length > 0 && (
                  <div className="mt-3 flex w-full flex-col gap-3">
                    {msg.recommendations.map((movie) => (
                      <a
                        key={movie.id}
                        href={`/movie/${movie.id}`}
                        className="group flex gap-3 rounded-xl border border-white/10 bg-slate-800/50 p-3 transition-colors hover:bg-slate-800 hover:border-violet-500/50"
                      >
                        <div className="relative h-16 w-12 flex-shrink-0 overflow-hidden rounded-md bg-slate-700">
                          {movie.poster_path ? (
                            <Image
                              src={movie.poster_path.startsWith('http') ? movie.poster_path : `https://image.tmdb.org/t/p/w92${movie.poster_path}`}
                              alt={movie.title}
                              fill
                              className="object-cover"
                            />
                          ) : (
                            <Film className="absolute inset-0 m-auto h-6 w-6 text-slate-500" />
                          )}
                        </div>
                        <div className="flex flex-1 flex-col justify-center">
                          <h4 className="text-sm font-semibold text-slate-100 group-hover:text-violet-400 transition-colors">
                            {movie.title}
                          </h4>
                          <p className="mt-1 text-xs text-slate-400 line-clamp-2">{movie.reasoning}</p>
                        </div>
                      </a>
                    ))}
                  </div>
                )}
              </motion.div>
            ))}

            {/* Typing Indicator */}
            {isLoading && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-start gap-2">
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-violet-600/20 text-violet-400">
                  <Bot size={16} />
                </div>
                <div className="rounded-2xl rounded-bl-md border border-white/5 bg-slate-800/80 px-4 py-3">
                  <div className="flex gap-1">
                    <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: '0ms' }} />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: '150ms' }} />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </motion.div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <form onSubmit={onSendMessage} className="border-t border-white/10 bg-slate-900/95 p-4 backdrop-blur-xl">
            <div className="relative flex items-center gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => onInputChange(e.target.value)}
                placeholder="Ask for a movie recommendation..."
                className="flex-1 rounded-xl border border-white/10 bg-slate-800/50 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 disabled:opacity-50"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="rounded-xl bg-violet-600 p-3 text-white transition-colors hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Send message"
              >
                <Send size={18} />
              </button>
            </div>
          </form>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
