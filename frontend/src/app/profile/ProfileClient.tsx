'use client';

import Image from 'next/image';
import { motion } from 'framer-motion';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import { Settings } from 'lucide-react';
import { useUser } from '@clerk/nextjs';

const tasteData = [
  { subject: 'Sci-Fi', A: 90, fullMark: 100 },
  { subject: 'Action', A: 80, fullMark: 100 },
  { subject: 'Drama', A: 60, fullMark: 100 },
  { subject: 'Comedy', A: 30, fullMark: 100 },
  { subject: 'Thriller', A: 85, fullMark: 100 },
  { subject: 'Horror', A: 40, fullMark: 100 },
];

export default function ProfileClient() {
  const { user, isLoaded } = useUser();

  const userInitials = user?.firstName && user?.lastName 
    ? `${user.firstName[0]}${user.lastName[0]}`.toUpperCase()
    : user?.fullName?.[0]?.toUpperCase() ?? user?.primaryEmailAddress?.emailAddress?.[0]?.toUpperCase() ?? 'U';

  const userName = user?.fullName ?? user?.username ?? user?.primaryEmailAddress?.emailAddress ?? 'User';
  const userSubtitle = user?.primaryEmailAddress?.emailAddress ?? 'Member since 2024';

  return (
    <main style={{ paddingTop: '100px', minHeight: '100vh', padding: '100px 5% 40px' }}>
      <div className="profile-container" style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '40px', maxWidth: '1200px', margin: '0 auto' }}>
        
        {/* Left Col: User Card */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="glass-panel" style={{ padding: '40px 24px', textAlign: 'center', position: 'relative' }}>
            <button aria-label="Open profile settings" style={{ position: 'absolute', top: '20px', right: '20px', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
              <Settings size={20} />
            </button>
            
            {!isLoaded ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div style={{ width: '120px', height: '120px', borderRadius: '50%', marginBottom: '20px', background: 'rgba(255,255,255,0.05)', animation: 'pulse 1.5s infinite' }} />
                <div style={{ width: '150px', height: '24px', borderRadius: '4px', marginBottom: '8px', background: 'rgba(255,255,255,0.05)', animation: 'pulse 1.5s infinite' }} />
                <div style={{ width: '100px', height: '16px', borderRadius: '4px', background: 'rgba(255,255,255,0.05)', animation: 'pulse 1.5s infinite' }} />
              </div>
            ) : (
              <>
                {user?.imageUrl ? (
                  <Image 
                    src={user.imageUrl} 
                    alt={userName}
                    width={120}
                    height={120}
                    style={{ 
                      borderRadius: '50%', 
                      margin: '0 auto 20px', display: 'block', objectFit: 'cover',
                      border: '2px solid var(--accent-secondary)'
                    }}
                  />
                ) : (
                  <div style={{ 
                    width: '120px', height: '120px', borderRadius: '50%', 
                    background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
                    margin: '0 auto 20px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '48px', fontWeight: 700
                  }}>
                    {userInitials}
                  </div>
                )}
                <h2 style={{ fontSize: '28px', marginBottom: '4px' }}>{userName}</h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '15px' }}>{userSubtitle}</p>
              </>
            )}
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '32px', textAlign: 'center' }}>
              <div>
                <div style={{ fontSize: '24px', fontWeight: 700, fontFamily: 'var(--font-display)' }}>342</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Movies Watched</div>
              </div>
              <div>
                <div style={{ fontSize: '24px', fontWeight: 700, fontFamily: 'var(--font-display)' }}>89</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Reviews</div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Col: Analytics */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          <div className="glass-panel" style={{ padding: '32px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <h3 style={{ fontSize: '20px' }}>Taste Profile</h3>
            </div>
            
            <div style={{ height: '300px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={tasteData}>
                  <PolarGrid stroke="rgba(255,255,255,0.1)" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar name="Taste" dataKey="A" stroke="var(--accent-secondary)" fill="var(--accent-secondary)" fillOpacity={0.4} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <p style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '14px', marginTop: '16px' }}>
              Your profile heavily leans towards Sci-Fi and Thrillers with high tension arcs.
            </p>
          </div>

        </div>

      </div>
    </main>
  );
}
