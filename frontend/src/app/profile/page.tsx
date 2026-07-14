'use client';

import { motion } from 'framer-motion';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import { Settings, Edit2 } from 'lucide-react';

const tasteData = [
  { subject: 'Sci-Fi', A: 90, fullMark: 100 },
  { subject: 'Action', A: 80, fullMark: 100 },
  { subject: 'Drama', A: 60, fullMark: 100 },
  { subject: 'Comedy', A: 30, fullMark: 100 },
  { subject: 'Thriller', A: 85, fullMark: 100 },
  { subject: 'Horror', A: 40, fullMark: 100 },
];

export default function ProfilePage() {
  return (
    <main style={{ paddingTop: '100px', minHeight: '100vh', padding: '100px 5% 40px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '40px', maxWidth: '1200px', margin: '0 auto' }}>
        
        {/* Left Col: User Card */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="glass-panel" style={{ padding: '40px 24px', textAlign: 'center', position: 'relative' }}>
            <button aria-label="Open profile settings" style={{ position: 'absolute', top: '20px', right: '20px', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
              <Settings size={20} />
            </button>
            
            <div style={{ 
              width: '120px', height: '120px', borderRadius: '50%', 
              background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
              margin: '0 auto 20px', display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '48px', fontWeight: 700
            }}>
              J
            </div>
            <h2 style={{ fontSize: '28px', marginBottom: '4px' }}>John Doe</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '15px' }}>Member since 2024</p>
            
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
