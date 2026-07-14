'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Mic, Sparkles } from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';

export default function SemanticSearchPage() {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [isListening, setIsListening] = useState(false);

  // Mock results
  const results = [
    { id: '1', title: 'Arrival', year: '2016', match: 94, poster: 'https://image.tmdb.org/t/p/w500/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg', desc: 'A linguist works with the military to communicate with alien lifeforms.' },
    { id: '2', title: 'Interstellar', year: '2014', match: 89, poster: 'https://image.tmdb.org/t/p/w500/gEU2QlsE1ZEbKU01E8XgK31rGfQ.jpg', desc: 'A team of explorers travel through a wormhole in space in an attempt to ensure humanity\'s survival.' },
    { id: '3', title: 'Contact', year: '1997', match: 82, poster: 'https://image.tmdb.org/t/p/w500/bT2B1xQx7M4zZ2E2A6eO7FhIbbB.jpg', desc: 'Dr. Ellie Arroway finds conclusive radio proof of extraterrestrial intelligence.' }
  ];

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;
    setIsSearching(true);
    setTimeout(() => setIsSearching(false), 1200); // Simulate network delay
  };

  return (
    <main style={{ paddingTop: '100px', minHeight: '100vh', padding: '100px 5% 40px' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
          >
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'rgba(139, 92, 246, 0.1)', color: 'var(--accent-secondary)', padding: '6px 16px', borderRadius: '999px', fontSize: '13px', fontWeight: 600, marginBottom: '16px' }}>
              <Sparkles size={14} /> AI-Powered Search
            </div>
            <h1 style={{ fontSize: '48px', marginBottom: '16px' }}>Describe what you want to watch</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '18px' }}>
              Don&apos;t know the title? Just describe the plot, mood, or characters.
            </p>
          </motion.div>
        </div>

        {/* Search Bar */}
        <motion.form 
          onSubmit={handleSearch}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          style={{ position: 'relative', marginBottom: '40px' }}
        >
          <div className="glass-panel" style={{ display: 'flex', alignItems: 'center', padding: '8px', borderRadius: '999px' }}>
            <Search size={24} color="var(--text-muted)" style={{ margin: '0 16px' }} />
            <input 
              type="text" 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder='e.g., "A dark sci-fi movie about aliens and time travel"'
              style={{ flex: 1, background: 'transparent', border: 'none', color: 'white', fontSize: '18px', outline: 'none' }}
            />
            <button 
              type="button"
              onClick={() => setIsListening(!isListening)}
              style={{ background: isListening ? 'rgba(229, 9, 20, 0.1)' : 'transparent', border: 'none', padding: '12px', borderRadius: '50%', cursor: 'pointer', color: isListening ? 'var(--accent-primary)' : 'var(--text-muted)', transition: 'all 0.2s' }}
            >
              <Mic size={24} style={isListening ? { animation: 'pulse 1.5s infinite' } : {}} />
            </button>
            <button type="submit" className="btn btn-primary" style={{ margin: '0 8px' }}>
              Search
            </button>
          </div>
        </motion.form>

        {/* Results */}
        {isSearching ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <div className="skeleton" style={{ width: '100%', height: '140px', borderRadius: '16px', marginBottom: '16px' }} />
            <div className="skeleton" style={{ width: '100%', height: '140px', borderRadius: '16px', marginBottom: '16px' }} />
          </div>
        ) : query && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            <h3 style={{ fontSize: '20px', marginBottom: '24px', color: 'var(--text-secondary)' }}>
              Top Semantic Matches
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {results.map((movie, i) => (
                <motion.div
                  key={movie.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                >
                  <Link href={`/movie/${movie.id}`}>
                    <div className="glass-panel" style={{ display: 'flex', padding: '16px', gap: '20px', cursor: 'pointer', transition: 'transform 0.2s' }} onMouseOver={e => e.currentTarget.style.transform = 'scale(1.02)'} onMouseOut={e => e.currentTarget.style.transform = 'scale(1)'}>
                      <Image src={movie.poster} alt={movie.title} width={80} height={120} style={{ borderRadius: '8px', objectFit: 'cover' }} />
                      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div>
                            <h4 style={{ fontSize: '20px', marginBottom: '4px' }}>{movie.title} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>({movie.year})</span></h4>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.5, maxWidth: '90%' }}>{movie.desc}</p>
                          </div>
                          <div style={{ background: 'rgba(34, 197, 94, 0.1)', color: '#22C55E', padding: '4px 12px', borderRadius: '999px', fontSize: '13px', fontWeight: 600 }}>
                            {movie.match}% Match
                          </div>
                        </div>
                      </div>
                    </div>
                  </Link>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

      </div>
      <style jsx global>{`
        @keyframes pulse {
          0% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.1); opacity: 0.7; }
          100% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </main>
  );
}
