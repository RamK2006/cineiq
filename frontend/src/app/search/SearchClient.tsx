'use client';

import { useState, useEffect, Suspense } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Mic, Search, Sparkles, Filter, X } from 'lucide-react';
import EmptyState from '../../components/EmptyState';
import { apiRequest } from '../../lib/api';
import { searchCatalog } from '../../lib/catalog';

type Result = { id: string; title: string; overview: string; poster_path?: string | null; similarity_score: number };

const AVAILABLE_GENRES = [
  'Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary', 
  'Drama', 'Family', 'Fantasy', 'History', 'Horror', 'Music', 'Mystery', 
  'Romance', 'Science Fiction', 'Thriller', 'War', 'Western'
];

function SearchContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Result[] | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  
  // Filter state
  const [showFilters, setShowFilters] = useState(false);
  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const [minRating, setMinRating] = useState<number>(0);
  const [yearFrom, setYearFrom] = useState<number | ''>('');
  const [yearTo, setYearTo] = useState<number | ''>('');
  const [sortBy, setSortBy] = useState<string>('popularity');

  // Initialize from URL
  useEffect(() => {
    const q = searchParams.get('q') || '';
    const genre = searchParams.getAll('genre');
    const minRatingParam = searchParams.get('min_rating');
    const yearFromParam = searchParams.get('year_from');
    const yearToParam = searchParams.get('year_to');
    const sortByParam = searchParams.get('sort_by');

    if (q) setQuery(q);
    if (genre.length > 0) setSelectedGenres(genre);
    if (minRatingParam) setMinRating(parseFloat(minRatingParam));
    if (yearFromParam) setYearFrom(parseInt(yearFromParam));
    if (yearToParam) setYearTo(parseInt(yearToParam));
    if (sortByParam) setSortBy(sortByParam);

    if (q || genre.length > 0 || minRatingParam || yearFromParam || yearToParam) {
      executeSearch(q, genre, minRatingParam, yearFromParam, yearToParam, sortByParam);
    }
  }, [searchParams]);

  const toggleGenre = (genre: string) => {
    setSelectedGenres(prev => 
      prev.includes(genre) ? prev.filter(g => g !== genre) : [...prev, genre]
    );
  };

  async function executeSearch(
    q: string, 
    genres: string[], 
    rating: string | null, 
    yFrom: string | null, 
    yTo: string | null,
    sort: string | null
  ) {
    setIsSearching(true);
    setResults(null);

    try {
      const params = new URLSearchParams();
      if (q) params.append('q', q);
      genres.forEach(g => params.append('genres', g));
      if (rating) params.append('min_rating', rating);
      if (yFrom) params.append('year_from', yFrom);
      if (yTo) params.append('year_to', yTo);
      if (sort) params.append('sort_by', sort);

      const response = (await apiRequest(`/search/semantic?${params.toString()}`)) as {
        results: Result[];
      };
      if (response && response.results) {
        setResults(response.results);
        setIsSearching(false);
        return;
      }
    } catch (cause) {
      console.warn('API search failed, falling back to local search engine:', cause);
    }

    // Local catalog search fallback
    const localMatches = searchCatalog(q).map((m) => ({
      id: m.id,
      title: m.title,
      overview: m.overview,
      poster_path: m.poster_path,
      similarity_score: m.match_score,
    }));
    setResults(localMatches);
    setIsSearching(false);
  }

  function handleSearch(event: React.FormEvent) {
    event.preventDefault();
    if (!query.trim() && selectedGenres.length === 0 && !yearFrom && !yearTo && minRating === 0) return;
    
    const params = new URLSearchParams();
    if (query.trim()) params.append('q', query.trim());
    selectedGenres.forEach(g => params.append('genre', g));
    if (minRating > 0) params.append('min_rating', minRating.toString());
    if (yearFrom) params.append('year_from', yearFrom.toString());
    if (yearTo) params.append('year_to', yearTo.toString());
    if (sortBy !== 'popularity') params.append('sort_by', sortBy);

    router.push(`/search?${params.toString()}`);
  }

  return (
    <main style={{ minHeight: '100vh', padding: '100px 5% 40px' }}>
      <div style={{ maxWidth: 800, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{ color: 'var(--accent-secondary)', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <Sparkles size={16} /> AI-Powered Search
          </div>
          <h1 style={{ fontSize: 48, marginTop: 8 }}>Describe what you want to watch</h1>
        </div>
        
        <form onSubmit={handleSearch} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="glass-panel" style={{ display: 'flex', padding: 8, gap: 8 }}>
            <Search aria-hidden size={24} style={{ alignSelf: 'center', marginLeft: 8 }} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              aria-label="Search for movies by description or title"
              placeholder="Describe a movie, mood, or plot (e.g. Nolan space adventure)"
              className="search-input"
              style={{ flex: 1 }}
            />
            <button 
              type="button" 
              onClick={() => setShowFilters(!showFilters)}
              className={`btn ${showFilters ? 'btn-primary' : 'btn-glass'}`}
              style={{ padding: '8px 12px' }}
              title="Toggle Filters"
            >
              <Filter size={20} />
            </button>
            <button type="button" aria-label="Voice search is not available" disabled title="Voice search requires browser speech recognition" style={{ padding: '8px' }}>
              <Mic size={22} />
            </button>
            <button type="submit" className="btn btn-primary" disabled={isSearching}>
              {isSearching ? 'Searching…' : 'Search'}
            </button>
          </div>

          {showFilters && (
            <div className="glass-panel" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ fontSize: 18, margin: 0 }}>Advanced Filters</h3>
                <button type="button" onClick={() => setShowFilters(false)} style={{ background: 'transparent', border: 'none', color: 'white', cursor: 'pointer' }}>
                  <X size={20} />
                </button>
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: 8, fontSize: 14, color: 'var(--text-secondary)' }}>Genres</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {AVAILABLE_GENRES.map(genre => (
                    <button
                      key={genre}
                      type="button"
                      onClick={() => toggleGenre(genre)}
                      style={{
                        padding: '6px 12px',
                        borderRadius: 16,
                        fontSize: 14,
                        border: `1px solid ${selectedGenres.includes(genre) ? 'var(--accent-primary)' : 'rgba(255,255,255,0.2)'}`,
                        background: selectedGenres.includes(genre) ? 'var(--accent-primary)' : 'transparent',
                        color: 'white',
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                      }}
                    >
                      {genre}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                <div>
                  <label style={{ display: 'block', marginBottom: 8, fontSize: 14, color: 'var(--text-secondary)' }}>
                    Minimum Rating: {minRating > 0 ? `${minRating}+` : 'Any'}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="10"
                    step="0.5"
                    value={minRating}
                    onChange={(e) => setMinRating(parseFloat(e.target.value))}
                    style={{ width: '100%', accentColor: 'var(--accent-primary)' }}
                  />
                </div>
                
                <div>
                  <label style={{ display: 'block', marginBottom: 8, fontSize: 14, color: 'var(--text-secondary)' }}>Sort By</label>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 8,
                      background: 'rgba(255,255,255,0.1)',
                      border: '1px solid rgba(255,255,255,0.2)',
                      color: 'white',
                      outline: 'none'
                    }}
                  >
                    <option value="popularity" style={{ color: 'black' }}>Popularity</option>
                    <option value="rating" style={{ color: 'black' }}>Highest Rated</option>
                    <option value="release_date" style={{ color: 'black' }}>Newest</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: 8, fontSize: 14, color: 'var(--text-secondary)' }}>Release Year Range</label>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  <input
                    type="number"
                    placeholder="From (e.g. 1990)"
                    value={yearFrom}
                    onChange={(e) => setYearFrom(e.target.value ? parseInt(e.target.value) : '')}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      borderRadius: 8,
                      background: 'rgba(255,255,255,0.1)',
                      border: '1px solid rgba(255,255,255,0.2)',
                      color: 'white'
                    }}
                  />
                  <span>to</span>
                  <input
                    type="number"
                    placeholder="To (e.g. 2024)"
                    value={yearTo}
                    onChange={(e) => setYearTo(e.target.value ? parseInt(e.target.value) : '')}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      borderRadius: 8,
                      background: 'rgba(255,255,255,0.1)',
                      border: '1px solid rgba(255,255,255,0.2)',
                      color: 'white'
                    }}
                  />
                </div>
              </div>
            </div>
          )}
        </form>

        <section style={{ marginTop: 32 }}>
          {results?.length === 0 && (
            <EmptyState title="No matches" description="No catalogue results matched that search." />
          )}
          {results && results.length > 0 && (
            <div style={{ display: 'grid', gap: 16 }}>
              {results.map((movie) => (
                <Link
                  href={`/movie/${movie.id}`}
                  key={movie.id}
                  className="glass-panel search-result-item"
                >
                  {movie.poster_path && (
                    <Image
                      src={movie.poster_path}
                      alt=""
                      width={80}
                      height={120}
                      style={{ borderRadius: 8, objectFit: 'cover' }}
                    />
                  )}
                  <div>
                    <h2 style={{ fontSize: 20 }}>{movie.title}</h2>
                    <p style={{ color: 'var(--text-secondary)', fontSize: 14, margin: '6px 0 10px' }}>
                      {movie.overview}
                    </p>
                    <span style={{ color: '#22C55E', fontWeight: 600, fontSize: 13 }}>
                      {Math.round(movie.similarity_score * 100)}% match
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

export default function SemanticSearchPage() {
  return (
    <Suspense fallback={<div style={{ textAlign: 'center', padding: '100px', color: 'white' }}>Loading search...</div>}>
      <SearchContent />
    </Suspense>
  );
}
