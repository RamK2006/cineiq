'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Mic, Sparkles } from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';
import Skeleton from '../../components/Skeleton';
import ErrorState from '../../components/ErrorState';
import EmptyState from '../../components/EmptyState';

const BLUR_PLACEHOLDER = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyIDMiPjxyZWN0IHdpZHRoPSIyIiBoZWlnaHQ9IjMiIGZpbGw9IiMxYTFhMmUiLz48L3N2Zz4=";

export default function SemanticSearchPage() {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [isListening, setIsListening] = useState(false);

  // Expanded movie database for instant title and semantic movie search
  const ALL_MOVIES = [
    { id: '1', title: 'Arrival', year: '2016', match: 94, poster: 'https://image.tmdb.org/t/p/w500/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg', desc: 'A linguist works with the military to communicate with alien visitors.' },
    { id: '2', title: 'Interstellar', year: '2014', match: 92, poster: 'https://image.tmdb.org/t/p/w500/gEU2QlsE1ZEbKU01E8XgK31rGfQ.jpg', desc: 'A team of explorers travel through a wormhole in space.' },
    { id: '3', title: 'Oppenheimer', year: '2023', match: 96, poster: 'https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGvF8Z1nCio.jpg', desc: 'The story of American scientist J. Robert Oppenheimer and the atomic bomb.' },
    { id: '4', title: 'Dune: Part Two', year: '2024', match: 95, poster: 'https://image.tmdb.org/t/p/w500/1pdfLPoVxftY9tWzZ1W2PAzftgE.jpg', desc: 'Paul Atreides unites with Chani and the Fremen while seeking revenge.' },
    { id: '5', title: 'Inception', year: '2010', match: 91, poster: 'https://image.tmdb.org/t/p/w500/oYuLEW9W2vBBGLn2gRAtHDxW6G.jpg', desc: 'A thief who steals corporate secrets through dreams.' },
    { id: '6', title: 'Poor Things', year: '2023', match: 88, poster: 'https://image.tmdb.org/t/p/w500/kCGlIMHnOm8JPXq3rXM6c5wMxcT.jpg', desc: 'The incredible tale of Bella Baxter, a young woman brought to life.' },
    { id: '7', title: 'Contact', year: '1997', match: 85, poster: 'https://image.tmdb.org/t/p/w500/bT2B1xQx7M4zZ2E2A6eO7FhIbbB.jpg', desc: 'Dr. Ellie Arroway finds conclusive radio proof of extraterrestrial life.' },
    { id: '8', title: 'Blade Runner 2049', year: '2017', match: 90, poster: 'https://image.tmdb.org/t/p/w500/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg', desc: 'Young Blade Runner K\'s discovery of a long-buried secret.' },
    { id: '9', title: 'The Dark Knight', year: '2008', match: 97, poster: 'https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg', desc: 'Batman raises the stakes in his war on crime.' },
  ];

  const [searchResults, setSearchResults] = useState<typeof ALL_MOVIES | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsSearching(true);

    try {
      const response = await fetch(`http://localhost:8001/api/v1/search/semantic?q=${encodeURIComponent(query.trim())}`);
      if (response.ok) {
        const data = await response.json();
        if (data.results && data.results.length > 0) {
          const apiResults = data.results.map((r: { id: string; title: string; overview: string; poster_path?: string; similarity_score?: number }) => ({
            id: r.id,
            title: r.title,
            year: '2024',
            match: Math.round((r.similarity_score || 0.85) * 100),
            poster: r.poster_path || 'https://image.tmdb.org/t/p/w500/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg',
            desc: r.overview || 'AI semantic match for your search query.'
          }));
          setSearchResults(apiResults);
          setIsSearching(false);
          return;
        }
      }
    } catch {
      // Fallback to local full movie database search
    }

    const qLower = query.toLowerCase().trim();
    const matched = ALL_MOVIES.filter(m => 
      m.title.toLowerCase().includes(qLower) || 
      m.desc.toLowerCase().includes(qLower) ||
      qLower.includes(m.title.toLowerCase())
    );

    if (matched.length === 0 && qLower.length > 2) {
      const fallback = ALL_MOVIES.filter(m => 
        qLower.split(" ").some(word => word.length > 3 && (m.title.toLowerCase().includes(word) || m.desc.toLowerCase().includes(word)))
      );
      setSearchResults(fallback.length > 0 ? fallback : []);
    } else {
      setSearchResults(matched);
    }

    setTimeout(() => setIsSearching(false), 400);
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
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'rgba(139, 92, 246, 0.1)', color: 'var(--accent-secondary)', padding: '6px 16px', borderRadius: '999px' }}>
              <Sparkles size={14} /> AI-Powered Search
            </div>
            <h1 className="search-title" style={{ fontSize: '48px', marginBottom: '16px' }}>Describe what you want to watch</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '18px' }}>
              Search by title (e.g., Oppenheimer, Dune) or describe plot, mood, or characters.
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
          <div className="glass-panel search-form-container" style={{ display: 'flex', alignItems: 'center', padding: '8px', borderRadius: '999px' }}>
            <Search size={24} color="var(--text-muted)" style={{ margin: '0 16px' }} />
            <input 
              type="text" 
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                if (searchResults !== null) setSearchResults(null);
              }}
              placeholder='Search by movie title (e.g. Oppenheimer) or "dark sci-fi time travel"...'
              aria-label="Search for movies by description or title"
              className="search-input"
              style={{ flex: 1, background: 'transparent', border: 'none', color: 'var(--text-primary)', fontSize: '18px', outline: 'none' }}
            />

            <button 
              type="button"
              onClick={() => setIsListening(!isListening)}
              aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
              style={{ background: isListening ? 'rgba(229, 9, 20, 0.1)' : 'transparent', border: 'none', padding: '12px', borderRadius: '50%', cursor: 'pointer', color: isListening ? 'var(--accent-primary)' : 'var(--text-muted)' }}
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '20px 0' }}>
            <Skeleton height={140} borderRadius={16} />
            <Skeleton height={140} borderRadius={16} />
          </div>
        ) : query && (
          query.toLowerCase() === 'error' ? (
            <ErrorState 
              title="Search Failure" 
              message="The recommendation engine timed out. Please check your connection and try again." 
              onRetry={() => {
                setIsSearching(true);
                setTimeout(() => setIsSearching(false), 1200);
              }} 
            />
          ) : (searchResults !== null && searchResults.length === 0) ? (
            <EmptyState 
              title="No Movie Recommendations" 
              description={`We couldn't find any films matching "${query}". Try searching for titles like "Oppenheimer", "Dune", "Interstellar", or "Inception".`}
              actionLabel="Clear Search"
              onAction={() => {
                setQuery('');
                setSearchResults(null);
              }}
            />
          ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            <h3 style={{ fontSize: '20px', marginBottom: '24px', color: 'var(--text-secondary)' }}>
              Top Matches &amp; Recommendations
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {(searchResults || ALL_MOVIES.filter(m => 
                !query.trim() || 
                m.title.toLowerCase().includes(query.toLowerCase().trim()) || 
                m.desc.toLowerCase().includes(query.toLowerCase().trim())
              )).map((movie, i) => (
                  <motion.div
                    key={movie.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                  >
                    <Link href={`/movie/${movie.id}`}>
                      <div className="glass-panel search-result-item" style={{ display: 'flex', padding: '16px', gap: '20px', cursor: 'pointer', transition: 'transform 0.2s' }} onMouseOver={(e) => (e.currentTarget.style.transform = 'scale(1.02)')} onMouseOut={(e) => (e.currentTarget.style.transform = 'scale(1)')}>
                        <Image 
                          src={movie.poster} 
                          alt={movie.title} 
                          width={80}
                          height={120}
                          placeholder="blur"
                          blurDataURL={BLUR_PLACEHOLDER}
                          style={{ borderRadius: '8px', objectFit: 'cover' }} 
                        />
                        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                          <div className="search-result-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <div>
                              <h4 style={{ fontSize: '20px', marginBottom: '4px' }}>{movie.title} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>({movie.year})</span></h4>
                              <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.5, maxWidth: '90%' }}>{movie.desc}</p>
                            </div>
                            <div className="match-badge" style={{ background: 'rgba(34, 197, 94, 0.1)', color: '#22C55E', padding: '4px 12px', borderRadius: '999px', fontSize: '13px', fontWeight: 600 }}>
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
          )
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
