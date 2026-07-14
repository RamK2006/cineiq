'use client';

import { motion, useScroll, useTransform } from 'framer-motion';
import { Play, Plus, ThumbsUp, Heart, Share2, CornerDownRight } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useParams } from 'next/navigation' ;

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
  { time: '0m', tension: 30, awe: 40, action: 10 },
  { time: '30m', tension: 45, awe: 60, action: 20 },
  { time: '60m', tension: 80, awe: 50, action: 75 },
  { time: '90m', tension: 60, awe: 85, action: 40 },
  { time: '120m', tension: 95, awe: 70, action: 90 },
  { time: '150m', tension: 100, awe: 95, action: 100 },
  { time: '166m', tension: 40, awe: 100, action: 20 },
];

export default function MovieDetailPage() {
   const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: movie.title,
          url: window.location.href,
        });
      } catch (error) {
        console.error('Error sharing:',error);
      }
    } else {
      navigator.clipboard.writeText(window.location.href);
      alert('Link copied to clipboard!');
    }
  };

  const params = useParams();
  const { scrollY } = useScroll();
  
  // Parallax effects
  const y1 = useTransform(scrollY, [0, 500], [0, 200]);
  const opacity = useTransform(scrollY, [0, 300], [1, 0]);
  const scale = useTransform(scrollY, [0, 300], [1, 1.05]);

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
            <button
              className="btn btn-glass"
              style={{ padding: '12px', borderRadius: '50%' }}
              aria-label="Share movie"
              onClick={handleShare}
            >
              <Share2 size={20} /> 
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
