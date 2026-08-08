'use client';

import { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { Mic, Search, Sparkles } from 'lucide-react';
import EmptyState from '../../components/EmptyState';
import ErrorState from '../../components/ErrorState';
import { apiRequest } from '../../lib/api';

type Result = { id: string; title: string; overview: string; poster_path?: string | null; similarity_score: number };

export default function SemanticSearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Result[] | null>(null);
  const [error, setError] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  async function handleSearch(event: React.FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    setIsSearching(true); setError(''); setResults(null);
    try {
      const response = await apiRequest(`/search/semantic?q=${encodeURIComponent(query.trim())}`) as { results: Result[] };
      setResults(response.results);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Search is unavailable.');
    } finally { setIsSearching(false); }
  }

  return <main style={{ minHeight: '100vh', padding: '100px 5% 40px' }}>
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: 40 }}>
        <div style={{ color: 'var(--accent-secondary)' }}><Sparkles size={14} /> AI-Powered Search</div>
        <h1 style={{ fontSize: 48 }}>Describe what you want to watch</h1>
      </div>
      <form onSubmit={handleSearch} className="glass-panel" style={{ display: 'flex', padding: 8, gap: 8 }}>
        <Search aria-hidden size={24} />
        <input value={query} onChange={(event) => setQuery(event.target.value)} aria-label="Search for movies by description or title" placeholder="Describe a movie, mood, or plot" className="search-input" style={{ flex: 1 }} />
        <button type="button" aria-label="Voice search is not available" disabled title="Voice search requires browser speech recognition"><Mic size={22} /></button>
        <button type="submit" className="btn btn-primary" disabled={isSearching}>{isSearching ? 'Searching…' : 'Search'}</button>
      </form>
      <section style={{ marginTop: 32 }}>
        {error && <ErrorState title="Search unavailable" message={error} onRetry={() => { void handleSearch(new Event('submit') as unknown as React.FormEvent); }} />}
        {results?.length === 0 && <EmptyState title="No matches" description="No catalogue results matched that search." />}
        {results && results.length > 0 && <div style={{ display: 'grid', gap: 16 }}>
          {results.map((movie) => <Link href={`/movie/${movie.id}`} key={movie.id} className="glass-panel" style={{ display: 'flex', padding: 16, gap: 20 }}>
            {movie.poster_path && <Image src={movie.poster_path} alt="" width={80} height={120} style={{ borderRadius: 8, objectFit: 'cover' }} />}
            <div><h2>{movie.title}</h2><p>{movie.overview}</p><span>{Math.round(movie.similarity_score * 100)}% match</span></div>
          </Link>)}
        </div>}
      </section>
    </div>
  </main>;
}
