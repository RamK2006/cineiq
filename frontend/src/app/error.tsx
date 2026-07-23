'use client';

import { useEffect } from 'react';
import { AlertTriangle, RotateCcw, Home } from 'lucide-react';
import Link from 'next/link';
import { motion } from 'framer-motion';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error details to the console as required
    console.error('CineIQ Application Error:', error);
  }, [error]);

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '120px 20px 40px 20px',
      background: 'radial-gradient(circle at center, #100808 0%, #05050A 100%)',
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
          border: '1px solid rgba(229, 9, 20, 0.15)', // Custom red accent border for error state
          boxShadow: '0 8px 32px rgba(229, 9, 20, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
        }}
      >
        <div style={{
          width: '80px',
          height: '80px',
          background: 'rgba(229, 9, 20, 0.1)',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 24px auto',
          border: '1px solid rgba(229, 9, 20, 0.25)',
          boxShadow: '0 0 30px rgba(229, 9, 20, 0.2)',
        }}>
          <AlertTriangle size={36} color="var(--accent-primary)" />
        </div>

        <h2 style={{
          fontFamily: 'var(--font-display)',
          fontSize: '32px',
          fontWeight: 800,
          marginBottom: '12px',
          color: '#FFFFFF',
          letterSpacing: '-0.02em',
        }}>
          System Malfunction
        </h2>

        <p style={{
          color: 'var(--text-secondary)',
          fontSize: '16px',
          marginBottom: '32px',
          lineHeight: 1.6,
        }}>
          An unexpected error occurred during the projection. We couldn&apos;t retrieve the reel for this page.
        </p>

        {error.message && (
          <div style={{
            background: 'rgba(0, 0, 0, 0.3)',
            border: '1px solid rgba(255, 255, 255, 0.05)',
            borderRadius: 'var(--radius-md)',
            padding: '16px',
            marginBottom: '32px',
            textAlign: 'left',
            fontFamily: 'monospace',
            fontSize: '13px',
            color: 'rgba(255, 255, 255, 0.7)',
            overflowX: 'auto',
            maxHeight: '120px',
          }}>
            <span style={{ color: 'var(--accent-primary)', fontWeight: 'bold' }}>Error:</span> {error.message}
          </div>
        )}

        <div style={{
          display: 'flex',
          gap: '16px',
          justifyContent: 'center',
        }}>
          <button
            onClick={() => reset()}
            className="btn btn-primary"
            style={{
              padding: '12px 28px',
              fontSize: '15px',
            }}
          >
            <RotateCcw size={16} />
            Try Again
          </button>
          
          <Link href="/" className="btn btn-glass" style={{
            padding: '12px 28px',
            fontSize: '15px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
          }}>
            <Home size={16} />
            Go Home
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
