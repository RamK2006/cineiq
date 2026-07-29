'use client';

import { useEffect, useMemo, useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from 'recharts';
import { AlertCircle, Settings } from 'lucide-react';
import { useAuth, useClerk, useUser } from '@clerk/nextjs';

import { fetchProfileStats, ProfileStats } from '@/lib/api';

const EMPTY_STATS: ProfileStats = {
  movies_watched: 0,
  reviews: 0,
  genre_preferences: [],
};

export default function ProfileClient() {
  const router = useRouter();
  const { user, isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const { openUserProfile } = useClerk();
  const [stats, setStats] = useState<ProfileStats>(EMPTY_STATS);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded) return;

    if (!isSignedIn) {
      router.replace('/sign-in');
      return;
    }

    let cancelled = false;

    async function loadStats() {
      setStatsLoading(true);
      setStatsError(null);

      try {
        const token = await getToken();
        if (!token) throw new Error('Authentication token unavailable');
        const result = await fetchProfileStats(token);
        if (!cancelled) setStats(result);
      } catch {
        if (!cancelled) {
          setStatsError('We could not load your profile statistics.');
          setStats(EMPTY_STATS);
        }
      } finally {
        if (!cancelled) setStatsLoading(false);
      }
    }

    void loadStats();
    return () => {
      cancelled = true;
    };
  }, [getToken, isLoaded, isSignedIn, router]);

  const userName =
    user?.fullName ||
    user?.username ||
    user?.primaryEmailAddress?.emailAddress ||
    'CineIQ member';
  const userEmail = user?.primaryEmailAddress?.emailAddress || 'No email available';
  const userInitials = useMemo(() => {
    const source = user?.fullName || userEmail;
    return source
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toUpperCase() || 'U';
  }, [user?.fullName, userEmail]);

  if (!isLoaded || !isSignedIn) {
    return (
      <main aria-busy="true" style={{ minHeight: '100vh', padding: '140px 5% 40px' }}>
        <div className="glass-panel" style={{ maxWidth: '520px', margin: '0 auto', padding: '40px' }}>
          <div style={{ height: '24px', width: '55%', background: 'rgba(255,255,255,.08)', borderRadius: '8px' }} />
        </div>
      </main>
    );
  }

  const hasTasteProfile = stats.genre_preferences.length > 0;

  return (
    <main style={{ minHeight: '100vh', padding: '100px 5% 40px' }}>
      <div className="profile-container" style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 1fr) minmax(0, 2fr)', gap: '40px', maxWidth: '1200px', margin: '0 auto' }}>
        <section style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="glass-panel" style={{ padding: '40px 24px', textAlign: 'center', position: 'relative' }}>
            <button
              type="button"
              aria-label="Open profile settings"
              onClick={() => openUserProfile()}
              style={{ position: 'absolute', top: '20px', right: '20px', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
            >
              <Settings size={20} />
            </button>

            {user?.imageUrl ? (
              <Image
                src={user.imageUrl}
                alt={`${userName}'s avatar`}
                width={120}
                height={120}
                style={{ borderRadius: '50%', margin: '0 auto 20px', display: 'block', objectFit: 'cover', border: '2px solid var(--accent-secondary)' }}
              />
            ) : (
              <div aria-label={`${userName}'s initials`} style={{ width: '120px', height: '120px', borderRadius: '50%', background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))', margin: '0 auto 20px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '48px', fontWeight: 700 }}>
                {userInitials}
              </div>
            )}

            <h1 style={{ fontSize: '28px', marginBottom: '4px' }}>{userName}</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '15px' }}>{userEmail}</p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '32px' }}>
              <div>
                <div style={{ fontSize: '24px', fontWeight: 700, fontFamily: 'var(--font-display)' }}>{statsLoading ? '—' : stats.movies_watched}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Movies Watched</div>
              </div>
              <div>
                <div style={{ fontSize: '24px', fontWeight: 700, fontFamily: 'var(--font-display)' }}>{statsLoading ? '—' : stats.reviews}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Reviews</div>
              </div>
            </div>
          </div>
        </section>

        <section style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="glass-panel" style={{ padding: '32px' }}>
            <h2 style={{ fontSize: '20px', marginBottom: '24px' }}>Taste Profile</h2>

            {statsError ? (
              <div role="alert" style={{ display: 'flex', gap: '10px', alignItems: 'center', color: 'var(--text-secondary)' }}>
                <AlertCircle size={20} />
                <span>{statsError}</span>
              </div>
            ) : statsLoading ? (
              <div aria-label="Loading taste profile" style={{ height: '300px', borderRadius: '16px', background: 'rgba(255,255,255,.05)' }} />
            ) : hasTasteProfile ? (
              <>
                <div style={{ height: '300px', width: '100%' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={stats.genre_preferences}>
                      <PolarGrid stroke="rgba(255,255,255,0.1)" />
                      <PolarAngleAxis dataKey="genre" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                      <Radar name="Taste" dataKey="score" stroke="var(--accent-secondary)" fill="var(--accent-secondary)" fillOpacity={0.4} />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
                <p style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '14px', marginTop: '16px' }}>
                  Your strongest movie preference is {stats.genre_preferences[0].genre}.
                </p>
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                <h3 style={{ marginBottom: '10px' }}>Complete your profile</h3>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>
                  Watch, rate, or save movies to build your personalised taste chart.
                </p>
                <button type="button" onClick={() => router.push('/')} className="btn-primary">
                  Explore movies
                </button>
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
