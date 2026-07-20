import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export default function ErrorState({
  title = 'Something Went Wrong',
  message = 'An unexpected error occurred while loading content. Please try again.',
  onRetry,
  className = '',
}: ErrorStateProps) {
  return (
    <div
      className={`glass-panel ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '40px 24px',
        maxWidth: '480px',
        margin: '20px auto',
        border: '1px solid rgba(229, 9, 20, 0.2)', // Accent primary border glow
        borderRadius: '16px',
        boxShadow: '0 8px 32px rgba(229, 9, 20, 0.05)',
      }}
      data-testid="error-state"
    >
      <div
        style={{
          background: 'rgba(229, 9, 20, 0.1)',
          padding: '16px',
          borderRadius: '50%',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <AlertTriangle size={36} color="var(--accent-primary)" />
      </div>

      <h3
        style={{
          fontSize: '20px',
          fontWeight: 700,
          color: 'var(--text-primary)',
          marginBottom: '10px',
          fontFamily: 'var(--font-display)',
        }}
      >
        {title}
      </h3>

      <p
        style={{
          fontSize: '14px',
          color: 'var(--text-secondary)',
          lineHeight: 1.5,
          marginBottom: '24px',
          maxWidth: '320px',
        }}
      >
        {message}
      </p>

      {onRetry && (
        <button
          onClick={onRetry}
          className="btn btn-primary"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 20px',
            fontSize: '14px',
          }}
          data-testid="retry-button"
        >
          <RefreshCw size={16} /> Try Again
        </button>
      )}
    </div>
  );
}
