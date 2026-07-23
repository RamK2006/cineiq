'use client';

import { Film, Home, Search } from 'lucide-react';
import Link from 'next/link';
import { motion } from 'framer-motion';

export default function NotFound() {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '120px 20px 40px 20px',
      background: 'radial-gradient(circle at center, #0B0B1E 0%, #05050A 100%)',
    }}>
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 15 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="glass-panel"
        style={{
          maxWidth: '550px',
          width: '100%',
          padding: '40px',
          textAlign: 'center',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: 'var(--glass-shadow)',
        }}
      >
        <div style={{
          width: '80px',
          height: '80px',
          background: 'rgba(139, 92, 246, 0.1)', // Discovery purple theme background
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 24px auto',
          border: '1px solid rgba(139, 92, 246, 0.25)',
          boxShadow: '0 0 30px rgba(139, 92, 246, 0.2)',
        }}>
          <Film size={36} color="var(--accent-secondary)" />
        </div>

        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontSize: '64px',
          fontWeight: 800,
          lineHeight: 1,
          marginBottom: '8px',
          color: '#FFFFFF',
          letterSpacing: '-0.04em',
        }}>
          404
        </h1>

        <h2 style={{
          fontFamily: 'var(--font-display)',
          fontSize: '24px',
          fontWeight: 600,
          marginBottom: '16px',
          color: '#FFFFFF',
        }}>
          Scene Not Found
        </h2>

        <p style={{
          color: 'var(--text-secondary)',
          fontSize: '16px',
          marginBottom: '36px',
          lineHeight: 1.6,
        }}>
          The page you are looking for has been cut from the final release or moved to a different screen.
        </p>

        <div style={{
          display: 'flex',
          gap: '16px',
          justifyContent: 'center',
          flexWrap: 'wrap',
        }}>
          <Link href="/" className="btn btn-primary" style={{
            padding: '12px 28px',
            fontSize: '15px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
          }}>
            <Home size={16} />
            Go Home
          </Link>

          <Link href="/search" className="btn btn-glass" style={{
            padding: '12px 28px',
            fontSize: '15px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
          }}>
            <Search size={16} />
            Find Movies
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
