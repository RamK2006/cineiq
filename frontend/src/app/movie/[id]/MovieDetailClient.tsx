'use client';

import { useEffect, useMemo, useState } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import {
  ArrowLeft,
  CornerDownRight,
  Heart,
  Play,
  Plus,
  Share2,
  ThumbsUp,
} from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import ReviewsSection from './ReviewsSection';

import { ApiError, fetchMovieDetail, MovieDetail } from '@/lib/api';

// Mock Data
const movie = {
  id: '1',
  title: 'Dune: Part Two',
  tagline: 'Long live the fighters.',
  overview: 'Paul Atreides unites with Chani and the Fremen while on a warpath of revenge against the conspirators who destroyed his family.',
  year: '2024',
  runtime: '2h 46m',
  rating: 'PG-13',
  genres: ['Sci-Fi', 'Adventure'],
  director: 'Denis Villeneuve',
  cast: ['Timothée Chalamet', 'Zendaya', 'Rebecca Ferguson', 'Javier Bardem'],
  backdrop: 'https://image.tmdb.org/t/p/original/8rpDcsfLJypbO6vtecsmHLsC88C.jpg',
  dominant_emotion: 'Tense',
  match: 98
};

// Emotional arc data (mock)
const emotionalArc = [
  { time: '0m', tension: 30, awe: 40 },
  { time: '30m', tension: 45, awe: 60 },
  { time: '60m', tension: 80, awe: 50 },
  { time: '90m', tension: 60, awe: 85 },
  { time: '120m', tension: 95, awe: 70 },
  { time: 'Finale', tension: 40, awe: 100 },
];

function formatRuntime(minutes?: number | null) {
  if (!minutes || minutes < 1) return 'Runtime unavailable';
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;
  return hours > 0 ? `${hours}h ${remaining}m` : `${remaining}m`;
}

function MovieSkeleton() {
  return (
    <main aria-busy="true" aria-label="Loading movie details" style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      <div className="skeleton" style={{ height: '70vh', width: '100%', borderRadius: 0 }} />
      <div style={{ padding: '40px 5%', display: 'grid', gap: '18px' }}>
        <div className="skeleton" style={{ height: 46, width: '55%' }} />
        <div className="skeleton" style={{ height: 22, width: '35%' }} />
        <div className="skeleton" style={{ height: 110, width: '100%' }} />
      </div>
    </main>
  );
}

export default function MovieDetailClient() {
  const params = useParams<{ id: string | string[] }>();
  const router = useRouter();
  const id = Array.isArray(params.id) ? params.id[0] : params.id;
  const [movie, setMovie] = useState<MovieDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const { scrollY } = useScroll();

  const y1 = useTransform(scrollY, [0, 500], [0, 200]);
  const opacity = useTransform(scrollY, [0, 300], [1, 0]);
  const scale = useTransform(scrollY, [0, 300], [1, 1.05]);

  const releaseYear = useMemo(
    () => (movie?.release_date ? movie.release_date.slice(0, 4) : 'Year unavailable'),
    [movie?.release_date],
  );

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(null), 2400);
  };

  useEffect(() => {
    let active = true;

    async function loadMovie() {
      if (!id || !/^\d+$/.test(id)) {
        setNotFound(true);
        setLoading(false);
        return;
      }

      setLoading(true);
      setNotFound(false);
      setError(null);

      try {
        const result = await fetchMovieDetail(id);
        if (active) setMovie(result);
      } catch (fetchError) {
        if (!active) return;
        if (fetchError instanceof ApiError && fetchError.status === 404) {
          setNotFound(true);
        } else {
          setError(fetchError instanceof Error ? fetchError.message : 'Unable to load movie details');
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    loadMovie();
    return () => {
      active = false;
    };
  }, [id]);

  const handleShare = async () => {
    if (!movie) return;
    if (navigator.share) {
      try {
        await navigator.share({ title: movie.title, url: window.location.href });
        showToast('Share sheet opened');
      } catch {
        // User cancellation does not need an error state.
      }
      return;
    }

    await navigator.clipboard.writeText(window.location.href);
    showToast('Link copied to clipboard');
  };

  if (loading) return <MovieSkeleton />;

  if (notFound) {
    return (
      <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 24, background: 'var(--bg-base)' }}>
        <section className="glass-panel" style={{ maxWidth: 560, padding: 40, textAlign: 'center' }}>
          <div style={{ fontSize: 72, fontWeight: 800, color: 'var(--accent-primary)' }}>404</div>
          <h1 style={{ marginTop: 8 }}>Movie not found</h1>
          <p style={{ color: 'var(--text-secondary)', margin: '12px 0 24px' }}>
            The TMDB movie ID is invalid or the movie is no longer available.
          </p>
          <button className="btn btn-primary" onClick={() => router.push('/')}>
            <ArrowLeft size={18} /> Back home
          </button>
        </section>
      </main>
    );
  }

  if (error || !movie) {
    return (
      <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 24, background: 'var(--bg-base)' }}>
        <section className="glass-panel" style={{ maxWidth: 560, padding: 40, textAlign: 'center' }}>
          <h1>Unable to load movie</h1>
          <p style={{ color: 'var(--text-secondary)', margin: '12px 0 24px' }}>{error}</p>
          <button className="btn btn-primary" onClick={() => window.location.reload()}>
            Try again
          </button>
        </section>
      </main>
    );
  }

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      {toast && (
        <div role="status" aria-live="polite" style={{ position: 'fixed', zIndex: 50, right: 24, top: 88, padding: '12px 18px', borderRadius: 12, background: 'rgba(20,20,35,0.96)', border: '1px solid rgba(255,255,255,0.14)', boxShadow: '0 12px 35px rgba(0,0,0,0.35)' }}>
          {toast}
        </div>
      )}

      <div style={{ height: '70vh', position: 'relative', overflow: 'hidden' }}>
        <motion.div style={{ position: 'absolute', inset: 0, backgroundImage: movie.backdrop_path ? `url(${movie.backdrop_path})` : 'linear-gradient(135deg, #181826, #09090f)', backgroundSize: 'cover', backgroundPosition: 'top center', y: y1, scale }} />
        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, var(--bg-base) 0%, rgba(0,0,0,0.2) 60%)' }} />

        <motion.div className="glass-panel" style={{ opacity, position: 'absolute', bottom: 40, left: '5%', right: '5%', padding: 40, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <h1 style={{ fontSize: 'clamp(38px, 6vw, 64px)', textShadow: '0 4px 20px rgba(0,0,0,0.5)' }}>{movie.title}</h1>
          <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 16, fontSize: 15, color: '#E4E4E7', fontWeight: 500 }}>
            <span style={{ color: '#22C55E', fontWeight: 700 }}>{Math.round(movie.match_score * 100)}% Match</span>
            <span>{releaseYear}</span>
            <span style={{ padding: '2px 8px', border: '1px solid rgba(255,255,255,0.2)', borderRadius: 4 }}>{movie.certification || 'Not rated'}</span>
            <span>{formatRuntime(movie.runtime)}</span>
            <span>{movie.vote_average.toFixed(1)}/10 TMDB</span>
          </div>

          <div style={{ display: 'flex', gap: 16, marginTop: 8, flexWrap: 'wrap' }}>
            <button className="btn btn-primary" aria-label="Play movie" onClick={() => showToast('Playback is coming soon')}>
              <Play size={20} fill="currentColor" /> Play
            </button>
            <button className="btn btn-glass" style={{ padding: 12, borderRadius: '50%' }} aria-label="Add to watchlist" onClick={() => showToast('Added to your watchlist')}><Plus size={20} /></button>
            <button className="btn btn-glass" style={{ padding: 12, borderRadius: '50%' }} aria-label="Like this movie" onClick={() => showToast('Thanks for rating this movie')}><ThumbsUp size={20} /></button>
            <button className="btn btn-glass" style={{ padding: 12, borderRadius: '50%' }} aria-label="Add to favorites" onClick={() => showToast('Added to favourites')}><Heart size={20} /></button>
            <button className="btn btn-glass" style={{ padding: 12, borderRadius: '50%' }} aria-label="Share movie" onClick={handleShare}><Share2 size={20} /></button>
          </div>
        </motion.div>
      </div>

      <div style={{ padding: '40px 5%', display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(260px, 1fr)', gap: 40 }}>
        <div>
          {movie.tagline && <h3 style={{ fontSize: 24, marginBottom: 16, fontStyle: 'italic', color: 'var(--text-secondary)' }}>&ldquo;{movie.tagline}&rdquo;</h3>}
          <p style={{ fontSize: 18, color: 'var(--text-primary)', lineHeight: 1.7, marginBottom: 40 }}>{movie.overview || 'No overview is available for this movie.'}</p>

          <h3 style={{ fontSize: 20, marginBottom: 24 }}>Emotional Journey</h3>
          <div className="glass-panel" style={{ padding: 24, height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={emotionalArc} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: 'rgba(20,20,35,0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                <Area type="monotone" dataKey="tension" stroke="#E50914" fillOpacity={0.16} fill="#E50914" strokeWidth={2} />
                <Area type="monotone" dataKey="awe" stroke="#8B5CF6" fillOpacity={0.14} fill="#8B5CF6" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div><div style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 8 }}>Cast</div><div style={{ color: 'var(--text-primary)', fontSize: 15 }}>{movie.cast.length ? movie.cast.map((member) => member.name).join(', ') : 'Cast unavailable'}</div></div>
          <div><div style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 8 }}>Director</div><div style={{ color: 'var(--text-primary)', fontSize: 15 }}>{movie.director || 'Director unavailable'}</div></div>
          <div><div style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 8 }}>Genres</div><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>{movie.genres.length ? movie.genres.map((genre) => <span key={genre} style={{ background: 'rgba(255,255,255,0.1)', padding: '4px 12px', borderRadius: 999, fontSize: 13 }}>{genre}</span>) : <span>Genres unavailable</span>}</div></div>
          <div className="glass-panel" style={{ padding: 20, marginTop: 20 }}><div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}><CornerDownRight size={20} color="var(--accent-secondary)" /><span style={{ fontWeight: 600 }}>CineIQ Match</span></div><div style={{ fontSize: 24, fontFamily: 'var(--font-display)', color: 'var(--accent-primary)', fontWeight: 700 }}>{Math.round(movie.match_score * 100)}%</div></div>
        </div>
      </div>
      <ReviewsSection movieId={String(params.id ?? movie.id)} />
    </main>
  );
}
