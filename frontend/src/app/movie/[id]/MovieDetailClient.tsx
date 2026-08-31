'use client';

import { useCallback, useEffect, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import ReviewsSection from './ReviewsSection';
import { fetchMovie, fetchSimilarMovies, MovieDetail } from '../../../lib/api';
import { findMovieById, MOVIE_CATALOG } from '../../../lib/catalog';

const BLUR_PLACEHOLDER = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyIDMiPjxyZWN0IHdpZHRoPSIyIiBoZWlnaHQ9IjMiIGZpbGw9IiMxYTFhMmUiLz48L3N2Zz4=";

export default function MovieDetailClient() {
  const params = useParams<{ id: string }>();
  const movieId = String(params?.id || '1');
  const [movie, setMovie] = useState<MovieDetail | null>(null);
  const [similarMovies, setSimilarMovies] = useState<{ id: string; title: string; poster?: string | null; match: string }[]>([]);

  const load = useCallback(async () => {
    try {
      const data = await fetchMovie(movieId);
      if (data && data.title) {
        setMovie(data);
      }
    } catch (err) {
      console.warn("API movie fetch error, using catalog:", err);
      const local = findMovieById(movieId) || MOVIE_CATALOG[0];
      setMovie({
        id: local.id,
        title: local.title,
        tagline: local.tagline,
        overview: local.overview,
        year: local.year,
        runtime: local.runtime,
        rating: local.rating,
        genres: local.genres,
        director: local.director,
        cast: local.cast,
        backdrop: local.backdrop_path,
        dominant_emotion: local.dominant_emotion,
        match: Math.round(local.match_score * 100),
        emotional_arc: local.emotional_arc,
      });
    }

    try {
      const simData = await fetchSimilarMovies(movieId, 8);
      if (simData?.movies?.length) {
        setSimilarMovies(
          simData.movies.map((m) => ({
            id: m.id,
            title: m.title,
            poster: m.poster_path,
            match: `${Math.round(m.match_score * 100)}% Match`,
          }))
        );
        return;
      }
    } catch (err) {
      console.warn("API similar movies fetch error, using catalog fallback:", err);
    }

    // Fallback similar movies calculation from local catalog
    const target = findMovieById(movieId) || MOVIE_CATALOG[0];
    const targetGenres = new Set((target.genres || []).map((g) => g.toLowerCase()));
    const candidates = MOVIE_CATALOG.filter((m) => m.id !== movieId);

    const scored = candidates.map((m) => {
      const candGenres = new Set((m.genres || []).map((g) => g.toLowerCase()));
      let intersection = 0;
      targetGenres.forEach((g) => {
        if (candGenres.has(g)) intersection++;
      });
      const union = new Set([...targetGenres, ...candGenres]).size;
      const jaccard = union > 0 ? intersection / union : 0.0;
      const matchScore = round(0.6 * jaccard + 0.4 * m.match_score, 2);
      return { ...m, match_score: matchScore };
    });

    scored.sort((a, b) => b.match_score - a.match_score);

    function round(val: number, decimals: number) {
      return Math.round(val * 100) / 100;
    }

    setSimilarMovies(
      scored.slice(0, 8).map((m) => ({
        id: m.id,
        title: m.title,
        poster: m.poster_path,
        match: `${Math.round(m.match_score * 100)}% Match`,
      }))
    );
  }, [movieId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!movie) {
    return <main aria-busy="true" style={{ minHeight: '100vh', padding: '140px 5%' }}>Loading movie…</main>;
  }

  return (
    <main style={{ minHeight: '100vh', padding: '100px 5% 60px' }}>
      <section className="glass-panel" style={{ padding: 32, display: 'grid', gap: 24 }}>
        {movie.backdrop && (
          <Image
            src={movie.backdrop}
            alt=""
            width={1200}
            height={675}
            priority
            style={{ width: '100%', height: 'auto', borderRadius: 12 }}
          />
        )}
        <h1 style={{ fontSize: 48 }}>{movie.title}</h1>
        <p>{[movie.year, movie.rating, movie.runtime].filter(Boolean).join(' · ')}</p>
        {movie.tagline && <p><em>“{movie.tagline}”</em></p>}
        <p>{movie.overview}</p>
        {movie.genres.length > 0 && <p>{movie.genres.join(' · ')}</p>}
        {(movie.director || movie.cast.length > 0) && (
          <p>
            {movie.director && `Director: ${movie.director}`}
            {movie.director && movie.cast.length > 0 && ' · '}
            {movie.cast.length > 0 && `Cast: ${movie.cast.join(', ')}`}
          </p>
        )}
      </section>
      {movie.emotional_arc.length > 0 && (
        <section className="glass-panel" style={{ marginTop: 24, height: 300, padding: 24 }}>
          <h2>Emotional Journey</h2>
          <ResponsiveContainer width="100%" height="90%">
            <AreaChart data={movie.emotional_arc}>
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Area dataKey="tension" stroke="#E50914" fill="#E5091444" />
              <Area dataKey="awe" stroke="#8B5CF6" fill="#8B5CF644" />
            </AreaChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* More Like This Similar Movies Carousel */}
      {similarMovies.length > 0 && (
        <section className="glass-panel" style={{ marginTop: 24, padding: 24 }}>
          <h2 style={{ fontSize: 24, marginBottom: 16 }}>More Like This</h2>
          <div style={{ display: 'flex', gap: 16, overflowX: 'auto', paddingBottom: 16 }}>
            {similarMovies.map((sim) => (
              <div key={sim.id} style={{ flex: '0 0 auto', width: 180 }}>
                <Link href={`/movie/${sim.id}`}>
                  <div className="movie-card" style={{ height: 260, position: 'relative', borderRadius: 8, overflow: 'hidden' }}>
                    {sim.poster && (
                      <Image
                        src={sim.poster}
                        alt={sim.title}
                        fill
                        sizes="(max-width: 768px) 100vw, 180px"
                        placeholder="blur"
                        blurDataURL={BLUR_PLACEHOLDER}
                        className="movie-poster"
                      />
                    )}
                    <div className="movie-overlay" style={{ padding: 12 }}>
                      <div className="movie-title" style={{ fontSize: 14, fontWeight: 700 }}>{sim.title}</div>
                      <div className="movie-meta" style={{ marginTop: 4 }}>
                        <span style={{ color: '#22C55E', fontWeight: 600, fontSize: 12 }}>{sim.match}</span>
                      </div>
                    </div>
                  </div>
                </Link>
              </div>
            ))}
          </div>
        </section>
      )}

      <ReviewsSection movieId={movieId} />
    </main>
  );
}

