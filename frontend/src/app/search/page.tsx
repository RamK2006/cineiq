'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Mic, Sparkles } from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';
interface MovieItem {
  id: string;
  title: string;
  poster_path: string | null;
  release_date?: string | null;
  overview?: string;
  match_score?: number;
}

const BLUR_PLACEHOLDER = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyIDMiPjxyZWN0IHdpZHRoPSIyIiBoZWlnaHQ9IjMiIGZpbGw9IiMxYTFhMmUiLz48L3N2Zz4=";

export default function SemanticSearchPage() {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [results, setResults] = useState<MovieItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    setIsSearching(true);
    setError(null);
    setResults([]);
    setHasSearched(true);

    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1';
      const res = await fetch(`${backendUrl}/search/semantic?q=${encodeURIComponent(query)}&limit=10`);
      
      if (!res.ok) {
        throw new Error('Failed to fetch search results');
      }

      const data = await res.json();
      // The backend returns { results: [...] } or just [...]
      setResults(data.results || data || []);
    } catch (err: any) {
      console.error("Search error:", err);
      setError("The recommendation engine timed out or encountered an error. Please check your connection and try again.");
    } finally {
      setIsSearching(false);
    }
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
              aria-label="Search for movies by description"
              style={{ flex: 1, background: 'transparent', border: 'none', color: 'white', fontSize: '18px', outline: 'none' }}
            />
            <button 
              type="button"
              onClick={() => setIsListening(!isListening)}
              aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
              style={{ background: isListening ? 'rgba(229, 9, 20, 0.1)' : 'transparent', border: 'none', padding: '12px', borderRadius: '50%', cursor: 'pointer', color: isListening ? 'var(--accent-primary)' : 'var(--text-muted)', transition: 'all 0.2s' }}
            >
              <Mic size={24} style={isListening ? { animation: 'pulse 1.5s infinite' } : {}} />
            </button>
            <button type="submit" className="btn btn-primary" style={{ margin: '0 8px' }} disabled={isSearching}>
              {isSearching ? 'Searching...' : 'Search'}
            </button>
          </div>
        </motion.form>

        {/* Results Section */}
        {isSearching ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '20px 0' }}>
            {[1, 2, 3].map(i => (
              <div key={i} className="glass-panel" style={{ display: 'flex', padding: '16px', gap: '20px', height: '152px' }}>
                <div className="skeleton" style={{ width: '80px', height: '120px', borderRadius: '8px', flexShrink: 0 }} />
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '12px' }}>
                  <div className="skeleton" style={{ width: '60%', height: '24px', borderRadius: '4px' }} />
                  <div className="skeleton" style={{ width: '90%', height: '14px', borderRadius: '4px' }} />
                  <div className="skeleton" style={{ width: '80%', height: '14px', borderRadius: '4px' }} />
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div style={{ textAlign: 'center', padding: '40px 20px', background: 'rgba(229, 9, 20, 0.1)', borderRadius: '16px', border: '1px solid rgba(229, 9, 20, 0.2)' }}>
            <h3 style={{ color: '#E50914', marginBottom: '8px' }}>Search Failure</h3>
            <p style={{ color: 'var(--text-secondary)' }}>{error}</p>
            <button onClick={handleSearch} className="btn btn-primary" style={{ marginTop: '16px' }}>Retry Search</button>
          </div>
        ) : (hasSearched && results.length === 0) ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '16px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
            <Search size={48} color="var(--text-muted)" style={{ margin: '0 auto 16px', opacity: 0.5 }} />
            <h3 style={{ fontSize: '24px', marginBottom: '8px' }}>No Movie Recommendations</h3>
            <p style={{ color: 'var(--text-secondary)', maxWidth: '400px', margin: '0 auto 24px' }}>
              We couldn&apos;t find any films matching &quot;{query}&quot;. Try adjusting your description.
            </p>
            <button onClick={() => setQuery('')} className="btn btn-secondary">Clear Search</button>
          </div>
        ) : results.length > 0 ? (
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
                      {movie.poster_path ? (
                        <Image 
                          src={movie.poster_path.startsWith('http') ? movie.poster_path : `https://image.tmdb.org/t/p/w500${movie.poster_path}`}
                          alt={movie.title} 
                          width={80}
                          height={120}
                          placeholder="blur"
                          blurDataURL={BLUR_PLACEHOLDER}
                          style={{ borderRadius: '8px', objectFit: 'cover', flexShrink: 0 }} 
                        />
                      ) : (
                        <div style={{ width: '80px', height: '120px', borderRadius: '8px', background: 'var(--surface-color)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <Search size={24} color="var(--text-muted)" />
                        </div>
                      )}
                      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div>
                            <h4 style={{ fontSize: '20px', marginBottom: '4px' }}>{movie.title} {movie.release_date && <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>({movie.release_date.split('-')[0]})</span>}</h4>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.5, maxWidth: '90%', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                              {movie.overview || "No description available."}
                            </p>
                          </div>
                          {movie.match_score !== undefined && (
                            <div style={{ background: 'rgba(34, 197, 94, 0.1)', color: '#22C55E', padding: '4px 12px', borderRadius: '999px', fontSize: '13px', fontWeight: 600 }}>
                              {Math.round(movie.match_score * 100)}% Match
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </Link>
                </motion.div>
                ))}
            </div>
          </motion.div>
        ) : null}

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
