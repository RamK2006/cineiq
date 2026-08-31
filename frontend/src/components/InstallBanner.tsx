'use client';

import React, { useEffect, useState } from 'react';

export default function InstallBanner() {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Register Service Worker for offline asset & page caching
    if ('serviceWorker' in navigator && process.env.NODE_ENV === 'production') {
      navigator.serviceWorker.register('/sw.js').catch((err) => {
        console.warn('PWA Service Worker registration failed:', err);
      });
    }

    const handler = (e: any) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setVisible(true);
    };

    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      setDeferredPrompt(null);
    }
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-50 bg-purple-600 text-white p-4 rounded-xl shadow-2xl flex items-center gap-4 max-w-sm"
      style={{
        position: 'fixed',
        bottom: '16px',
        right: '16px',
        zIndex: 9999,
        background: '#7c3aed',
        color: 'white',
        padding: '16px',
        borderRadius: '12px',
        boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        maxWidth: '380px',
      }}
    >
      <div>
        <h4 className="font-bold text-sm" style={{ fontWeight: 'bold', fontSize: '14px', margin: 0 }}>
          Install CineIQ App
        </h4>
        <p className="text-xs text-purple-200" style={{ fontSize: '12px', color: '#e9d5ff', margin: '4px 0 0' }}>
          Access browse pages and cached movie details offline.
        </p>
      </div>
      <button
        onClick={handleInstall}
        className="bg-white text-purple-700 text-xs font-semibold px-3 py-2 rounded-lg hover:bg-purple-50 transition-colors"
        style={{
          background: 'white',
          color: '#6b21a8',
          fontSize: '12px',
          fontWeight: 600,
          padding: '8px 12px',
          borderRadius: '8px',
          border: 'none',
          cursor: 'pointer',
          whiteSpace: 'nowrap',
        }}
      >
        Install
      </button>
    </div>
  );
}
