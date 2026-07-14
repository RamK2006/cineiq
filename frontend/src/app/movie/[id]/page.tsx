'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { motion, useScroll, useTransform } from 'framer-motion';
import { Play, Plus, ThumbsUp, Heart, CornerDownRight } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import ErrorBoundary from '@/components/ErrorBoundary';

interface Movie {
  id: string;
  title: string;
  tagline: string;
  overview: string;
  year: string;
  runtime: string;
  rating: string;
  genres: string[];
  director: string;
  cast: string[];
  backdrop: string;
  dominant_emotion: string;
  match: number;
}

interface EmotionalArcPoint {
  time: string;
  tension: number;
  awe: number;
  action: number;
}

function MovieDetailContent() {
  const params = useParams();
  const movieId = params?.id as string;

  const [movie, setMovie] = useState<Movie | null>(null);
  const [emotionalArc, setEmotionalArc] = useState<EmotionalArcPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMovie = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/movies/${movieId}`);
      if (!res.ok) {
        throw new Error(
          res.status === 404
            ? 'This movie could not be found.'
            : res.status === 429
            ? 'Too many requests right now. Please try again shortly.'
            : `Failed to load movie (status ${res.status}).`
        );
      }
      const data = await res.json();
      setMovie(data.movie);
      setEmotionalArc(data.emotionalArc ?? []);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Something went wrong loading this movie.'
      );
    } finally {
      setLoading(false);
    }
  }, [movieId]);

  useEffect(() => {
    fetchMovie();
  }, [fetchMovie]);

  const { scrollY } = useScroll();
  const y1 = useTransform(scrollY, [0, 500], [0, 200]);
  const opacity = useTransform(scrollY, [0, 300], [1, 0]);
  const scale = useTransform(scrollY, [0, 300], [1, 1.05]);

  if (loading) {
    return (
      <main style={{ minHeight: '100vh', background: 'var(--bg-base)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-secondary)', fontSize: '16px' }}>Loading movie…</div>
      </main>
    );
  }

  if (error || !movie) {
    return (
      <main style={{ minHeight: '100vh', background: 'var(--bg-base)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px' }}>
        <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', maxWidth: '480px' }}>
          <h2 style={{ fontSize: '24px', marginBottom: '12px' }}>Couldn&apos;t load this movie</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
            {error || 'Please try again.'}
          </p>
          <button className="btn btn-primary" onClick={fetchMovie}>
            Retry
          </button>
        </div>
      </main>
    );
  }

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>

      {/* Hero Parallax */}
      <div style={{ height: '70vh', position: 'relative', overflow: 'hidden' }}>
        <motion.div style={{
          position: 'absolute', inset: 0,
          backgroundImage: `url(${movie.backdrop})`,
          backgroundSize: 'cover',
          backgroundPosition: 'top center',
          y: y1,
          scale,
        }} />
        <div style={{
          position: 'absolute', inset: 0,
          background: 'linear-gradient(to top, var(--bg-base) 0%, transparent 60%)'
        }} />

        <motion.div className="glass-panel" style={{
          opacity,
          position: 'absolute', bottom: '40px', left: '5%', right: '5%',
          padding: '40px', display: 'flex', flexDirection: 'column', gap: '16px'
        }}>
          <h1 style={{ fontSize: '56px', textShadow: '0 4px 20px rgba(0,0,0,0.5)' }}>{movie.title}</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '15px', color: '#E4E4E7', fontWeight: 500 }}>
            <span style={{ color: '#22C55E', fontWeight: 700 }}>{movie.match}% Match</span>
            <span>{movie.year}</span>
            <span style={{ padding: '2px 8px', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '4px' }}>{movie.rating}</span>
            <span>{movie.runtime}</span>
          </div>

          <div style={{ display: 'flex', gap: '16px', marginTop: '8px' }}>
            <button className="btn btn-primary" aria-label="Play movie">
              <Play size={20} fill="currentColor" /> Play
            </button>
            <button className="btn btn-glass" style={{ padding: '12px', borderRadius: '50%' }} aria-label="Add to watchlist">
              <Plus size={20} />
            </button>
            <button className="btn btn-glass" style={{ padding: '12px', borderRadius: '50%' }} aria-label="Like this movie">
              <ThumbsUp size={20} />
            </button>
            <button className="btn btn-glass" style={{ padding: '12px', borderRadius: '50%' }} aria-label="Add to favorites">
              <Heart size={20} />
            </button>
          </div>
        </motion.div>
      </div>

      {/* Content Grid */}
      <div style={{ padding: '40px 5%', display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '40px' }}>

        {/* Left Col: Overview & Emotional Arc */}
        <div>
          <h3 style={{ fontSize: '24px', marginBottom: '16px', fontStyle: 'italic', color: 'var(--text-secondary)' }}>
            &ldquo;{movie.tagline}&rdquo;
          </h3>
          <p style={{ fontSize: '18px', color: 'var(--text-primary)', lineHeight: 1.7, marginBottom: '40px' }}>
            {movie.overview}
          </p>

          <h3 style={{ fontSize: '20px', marginBottom: '24px' }}>Emotional Journey</h3>
          <div className="glass-panel" style={{ padding: '24px', height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={emotionalArc} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorTension" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#E50914" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#E50914" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorAwe" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ background: 'rgba(20,20,35,0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                  itemStyle={{ fontSize: '13px' }}
                />
                <Area type="monotone" dataKey="tension" stroke="#E50914" fillOpacity={1} fill="url(#colorTension)" strokeWidth={2} />
                <Area type="monotone" dataKey="awe" stroke="#8B5CF6" fillOpacity={1} fill="url(#colorAwe)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right Col: Metadata */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div>
            <div style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '8px' }}>Cast</div>
            <div style={{ color: 'var(--text-primary)', fontSize: '15px' }}>{movie.cast.join(', ')}</div>
          </div>
          <div>
            <div style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '8px' }}>Director</div>
            <div style={{ color: 'var(--text-primary)', fontSize: '15px' }}>{movie.director}</div>
          </div>
          <div>
            <div style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '8px' }}>Genres</div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {movie.genres.map(g => (
                <span key={g} style={{ background: 'rgba(255,255,255,0.1)', padding: '4px 12px', borderRadius: '999px', fontSize: '13px' }}>
                  {g}
                </span>
              ))}
            </div>
          </div>
          <div className="glass-panel" style={{ padding: '20px', marginTop: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <CornerDownRight size={20} color="var(--accent-secondary)" />
              <span style={{ fontWeight: 600 }}>Dominant Emotion</span>
            </div>
            <div style={{ fontSize: '24px', fontFamily: 'var(--font-display)', color: 'var(--accent-primary)', fontWeight: 700 }}>
              {movie.dominant_emotion}
            </div>
          </div>
        </div>

      </div>
    </main>
  );
}

export default function MovieDetailPage() {
  return (
    <ErrorBoundary>
      <MovieDetailContent />
    </ErrorBoundary>
  );
}
