'use client';

import { useCallback, useEffect, useState } from 'react';
import Image from 'next/image';
import { useParams } from 'next/navigation';
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import ErrorState from '../../../components/ErrorState';
import ReviewsSection from './ReviewsSection';
import { fetchMovie, MovieDetail } from '../../../lib/api';

export default function MovieDetailClient() {
  const params = useParams<{ id: string }>();
  const movieId = String(params.id);
  const [movie, setMovie] = useState<MovieDetail | null>(null);
  const [error, setError] = useState('');
  const load = useCallback(async () => {
    try { setError(''); setMovie(await fetchMovie(movieId)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Movie details are unavailable.'); }
  }, [movieId]);
  useEffect(() => { void load(); }, [load]);
  if (error) return <ErrorState title="Movie unavailable" message={error} onRetry={() => void load()} />;
  if (!movie) return <main aria-busy="true" style={{ minHeight: '100vh', padding: '140px 5%' }}>Loading movie…</main>;
  return <main style={{ minHeight: '100vh', padding: '100px 5% 60px' }}>
    <section className="glass-panel" style={{ padding: 32, display: 'grid', gap: 24 }}>
      {movie.backdrop && <Image src={movie.backdrop} alt="" width={1200} height={675} priority style={{ width: '100%', height: 'auto', borderRadius: 12 }} />}
      <h1 style={{ fontSize: 48 }}>{movie.title}</h1>
      <p>{[movie.year, movie.rating, movie.runtime].filter(Boolean).join(' · ')}</p>
      {movie.tagline && <p><em>“{movie.tagline}”</em></p>}
      <p>{movie.overview}</p>
      {movie.genres.length > 0 && <p>{movie.genres.join(' · ')}</p>}
      {(movie.director || movie.cast.length > 0) && <p>{movie.director && `Director: ${movie.director}`}{movie.director && movie.cast.length > 0 && ' · '}{movie.cast.length > 0 && `Cast: ${movie.cast.join(', ')}`}</p>}
    </section>
    {movie.emotional_arc.length > 0 && <section className="glass-panel" style={{ marginTop: 24, height: 300, padding: 24 }}><h2>Emotional Journey</h2><ResponsiveContainer width="100%" height="90%"><AreaChart data={movie.emotional_arc}><XAxis dataKey="time" /><YAxis /><Tooltip /><Area dataKey="tension" stroke="#E50914" fill="#E5091444" /><Area dataKey="awe" stroke="#8B5CF6" fill="#8B5CF644" /></AreaChart></ResponsiveContainer></section>}
    <ReviewsSection movieId={movieId} />
  </main>;
}
