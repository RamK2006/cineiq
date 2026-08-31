'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Play, Info } from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';
import { fetchTrendingMovies, fetchMoviesByEmotion } from '../lib/api';
import { MOVIE_CATALOG } from '../lib/catalog';
import Skeleton from '../components/Skeleton';

const BLUR_PLACEHOLDER = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyIDMiPjxyZWN0IHdpZHRoPSIyIiBoZWlnaHQ9IjMiIGZpbGw9IiMxYTFhMmUiLz48L3N2Zz4=";

const MOODS = [
  { id: 'Tense', label: 'Tense & Gripping', color: '#EF4444', icon: '🔥' },
  { id: 'High Adrenaline', label: 'High Adrenaline', color: '#F59E0B', icon: '⚡' },
  { id: 'Mind-Bending', label: 'Mind-Bending Thrills', color: '#8B5CF6', icon: '🌀' },
  { id: 'Awe-Inspiring', label: 'Inspiring Journeys', color: '#3B82F6', icon: '✨' },
  { id: 'Cozy', label: 'Cozy Feel-Good', color: '#10B981', icon: '🍿' },
];

export default function HomePage() {
  const [typedText, setTypedText] = useState('');
  const [hero, setHero] = useState<{ id: string; title: string; backdrop?: string | null; match: string } | null>(null);
  const [trending, setTrending] = useState<{ id: string; title: string; poster?: string | null; match: string }[]>([]);
  const [loading, setLoading] = useState(true);

  // Mood carousel state
  const [activeMood, setActiveMood] = useState('Tense');
  const [moodMovies, setMoodMovies] = useState<{ id: string; title: string; poster?: string | null; match: string }[]>([]);

  const fullText = "Discover films that match your soul.";

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const trendingRes = await fetchTrendingMovies(8);
      if (trendingRes?.movies?.length) {
        const movies = trendingRes.movies.map((movie) => ({
          id: movie.id,
          title: movie.title,
          poster: movie.poster_path,
          match: `${Math.round(movie.match_score * 100)}% Match`,
        }));
        setTrending(movies);
        setHero({
          id: movies[0].id,
          title: movies[0].title,
          backdrop: movies[0].poster,
          match: movies[0].match,
        });
        return;
      }
    } catch (err) {
      console.warn("API unavailable, using embedded catalog:", err);
    }

    // High-res fallback catalog
    const fallback = MOVIE_CATALOG.slice(0, 8).map((m) => ({
      id: m.id,
      title: m.title,
      poster: m.poster_path,
      match: `${Math.round(m.match_score * 100)}% Match`,
    }));
    setTrending(fallback);
    setHero({
      id: fallback[0].id,
      title: fallback[0].title,
      backdrop: MOVIE_CATALOG[0].backdrop_path || fallback[0].poster,
      match: fallback[0].match,
    });
    setLoading(false);
  }, []);

  const loadMoodMovies = useCallback(async (emotion: string) => {
    try {
      const res = await fetchMoviesByEmotion(emotion, 10);
      if (res?.movies?.length) {
        setMoodMovies(
          res.movies.map((m) => ({
            id: m.id,
            title: m.title,
            poster: m.poster_path,
            match: `${Math.round(m.match_score * 100)}% Match`,
          }))
        );
        return;
      }
    } catch (e) {
      // Fallback to filtering local catalog
    }

    const clean = emotion.toLowerCase();
    const fallback = MOVIE_CATALOG.filter(
      (m) =>
        m.dominant_emotion?.toLowerCase().includes(clean) ||
        m.genres.some((g) => g.toLowerCase().includes(clean))
    );
    const finalMatches = (fallback.length ? fallback : MOVIE_CATALOG).slice(0, 10).map((m) => ({
      id: m.id,
      title: m.title,
      poster: m.poster_path,
      match: `${Math.round(m.match_score * 100)}% Match`,
    }));
    setMoodMovies(finalMatches);
  }, []);

  useEffect(() => {
    loadData().finally(() => setLoading(false));
  }, [loadData]);

  useEffect(() => {
    loadMoodMovies(activeMood);
  }, [activeMood, loadMoodMovies]);

  useEffect(() => {
    let i = 0;
    const interval = setInterval(() => {
      if (i <= fullText.length) {
        setTypedText(fullText.slice(0, i));
        i++;
      } else {
        clearInterval(interval);
      }
    }, 50);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <main style={{ padding: '100px 5% 40px', minHeight: '100vh', background: 'var(--bg-base)' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <Skeleton height={350} borderRadius={16} />
          <div style={{ display: 'flex', gap: '16px', overflowX: 'hidden' }}>
            <Skeleton width={180} height={270} borderRadius={12} />
            <Skeleton width={180} height={270} borderRadius={12} />
            <Skeleton width={180} height={270} borderRadius={12} />
            <Skeleton width={180} height={270} borderRadius={12} />
          </div>
        </div>
      </main>
    );
  }

  return (
    <main>
      {/* Hero Section */}
      <section className="hero-section" style={{
        position: 'relative',
        height: '85vh',
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        padding: '0 5%',
        overflow: 'hidden'
      }}>
        {/* Background Image & Gradient */}
        {hero && (
          <>
            <div style={{
              position: 'absolute', inset: 0, zIndex: -1,
              backgroundImage: `url(${hero.backdrop})`,
              backgroundSize: 'cover',
              backgroundPosition: 'center',
              backgroundRepeat: 'no-repeat',
            }} />
            <div style={{
              position: 'absolute', inset: 0, zIndex: -1,
              background: 'linear-gradient(to right, #05050A 20%, transparent 60%), linear-gradient(to top, #05050A 0%, transparent 30%)'
            }} />
          </>
        )}

        {/* Hero Content */}
        {hero && (
          <div className="hero-content" style={{ maxWidth: '600px' }}>
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
            >
              <div style={{ color: 'var(--accent-primary)', fontWeight: 700, letterSpacing: '2px', marginBottom: '16px', fontSize: '14px' }}>
                CINEIQ PREMIERE
              </div>
              <h1 className="hero-title" style={{ fontSize: '72px', marginBottom: '16px', textShadow: '0 4px 24px rgba(0,0,0,0.5)' }}>
                {hero.title}
              </h1>
              
              {/* Typewriter Effect */}
              <div style={{ fontSize: '18px', color: 'var(--text-secondary)', marginBottom: '8px', minHeight: '28px' }}>
                {typedText}<span style={{ opacity: 0.5 }}>|</span>
              </div>
              
              <p style={{ fontSize: '16px', color: '#D4D4D8', marginBottom: '32px', lineHeight: 1.6, textShadow: '0 2px 10px rgba(0,0,0,0.5)' }}>
                Explore this title and see its full details.
              </p>

              <div className="hero-buttons" style={{ display: 'flex', gap: '16px' }}>
                <Link href={`/movie/${hero.id}`} className="btn btn-primary" style={{ padding: '14px 32px', fontSize: '16px' }}>
                  <Play size={20} fill="currentColor" /> Play Now
                </Link>
                <Link href={`/movie/${hero.id}`} className="btn btn-glass" style={{ padding: '14px 32px', fontSize: '16px' }}>
                  <Info size={20} /> More Info
                </Link>
              </div>
            </motion.div>
          </div>
        )}
      </section>

      {/* Top Picks Row */}
      <section className="trending-section" style={{ padding: '0 5%', marginTop: '-80px', position: 'relative', zIndex: 10 }}>
        <h3 style={{ fontSize: '24px', marginBottom: '20px' }}>Top Picks for You</h3>
        <div style={{ display: 'flex', gap: '16px', overflowX: 'auto', paddingBottom: '32px' }}>
          {trending.map((movie, i) => (
            <motion.div
              key={movie.id}
              initial={{ opacity: 0, x: 50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
              style={{ flex: '0 0 auto', width: '220px' }}
            >
              <Link href={`/movie/${movie.id}`}>
                <div className="movie-card">
                  {movie.poster && <Image 
                    src={movie.poster}
                    alt={movie.title}
                    fill
                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                    priority={i < 4}
                    placeholder="blur"
                    blurDataURL={BLUR_PLACEHOLDER}
                    className="movie-poster" 
                  />}
                  <div className="movie-overlay">
                    <div className="movie-title">{movie.title}</div>
                    <div className="movie-meta">
                      <span style={{ color: '#22C55E', fontWeight: 600 }}>{movie.match}</span>
                      <span>TMDB</span>
                    </div>
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Mood & Emotion Carousel Row */}
      <section className="mood-section" style={{ padding: '0 5%', marginTop: '40px', position: 'relative', zIndex: 10 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
            <div>
              <h3 style={{ fontSize: '24px', margin: 0 }}>Mood & Emotion Carousel</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginTop: 4, margin: 0 }}>
                Select how you want to feel right now
              </p>
            </div>
            {/* Interactive Mood Tabs */}
            <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 4 }}>
              {MOODS.map((mood) => {
                const isActive = activeMood === mood.id;
                return (
                  <button
                    key={mood.id}
                    type="button"
                    onClick={() => setActiveMood(mood.id)}
                    style={{
                      padding: '8px 16px',
                      borderRadius: 20,
                      fontSize: 14,
                      fontWeight: 600,
                      cursor: 'pointer',
                      border: `1.5px solid ${isActive ? mood.color : 'rgba(255, 255, 255, 0.15)'}`,
                      background: isActive ? `${mood.color}25` : 'rgba(255, 255, 255, 0.05)',
                      color: isActive ? '#FFFFFF' : 'var(--text-secondary)',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <span>{mood.icon}</span>
                    <span>{mood.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Dynamic Carousel Row */}
        <div style={{ display: 'flex', gap: '16px', overflowX: 'auto', paddingBottom: '32px' }}>
          {moodMovies.map((movie, i) => {
            const currentMoodObj = MOODS.find((m) => m.id === activeMood) || MOODS[0];
            return (
              <motion.div
                key={`${activeMood}-${movie.id}`}
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05, duration: 0.4 }}
                style={{ flex: '0 0 auto', width: '220px' }}
              >
                <Link href={`/movie/${movie.id}`}>
                  <div className="movie-card">
                    {movie.poster && (
                      <Image
                        src={movie.poster}
                        alt={movie.title}
                        fill
                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                        placeholder="blur"
                        blurDataURL={BLUR_PLACEHOLDER}
                        className="movie-poster"
                      />
                    )}
                    <div className="movie-overlay">
                      <div className="movie-title">{movie.title}</div>
                      <div style={{ marginTop: 6, marginBottom: 4 }}>
                        <span
                          style={{
                            padding: '3px 8px',
                            borderRadius: 12,
                            fontSize: 11,
                            fontWeight: 600,
                            background: `${currentMoodObj.color}35`,
                            color: '#FFFFFF',
                            border: `1px solid ${currentMoodObj.color}60`,
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 4,
                          }}
                        >
                          <span>{currentMoodObj.icon}</span>
                          <span>{currentMoodObj.label}</span>
                        </span>
                      </div>
                      <div className="movie-meta">
                        <span style={{ color: '#22C55E', fontWeight: 600 }}>{movie.match}</span>
                        <span>Emotion</span>
                      </div>
                    </div>
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </div>
      </section>
    </main>
  );
}

