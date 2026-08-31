'use client';

import { motion } from 'framer-motion';

interface EmojiReactionsProps {
    onReact: (emoji: string) => void;
}

const EMOJIS = ['🍿', '❤️', '😱', '😂', '🔥'];

export default function EmojiReactions({ onReact }: EmojiReactionsProps) {
    return (
        <div className="flex items-center justify-around gap-1">
            {EMOJIS.map((emoji) => (
                <motion.button
                    key={emoji}
                    type="button"
                    onClick={() => onReact(emoji)}
                    whileHover={{ scale: 1.2, y: -2 }}
                    whileTap={{ scale: 0.9 }}
                    className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-800/50 text-xl transition-colors hover:bg-slate-700/80 border border-white/5"
                    aria-label={`React with ${emoji}`}
                >
                    {emoji}
                </motion.button>
            ))}
        </div>
    );
}
