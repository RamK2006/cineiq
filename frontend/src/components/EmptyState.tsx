import React from 'react';
import { Film } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
  icon?: React.ReactNode;
}

export default function EmptyState({
  title = 'No Results Found',
  description = 'Try adjusting your filters or search keywords to find what you are looking for.',
  actionLabel,
  onAction,
  className = '',
  icon,
}: EmptyStateProps) {
  return (
    <div
      className={`glass-panel ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '48px 32px',
        maxWidth: '520px',
        margin: '20px auto',
        borderRadius: '16px',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
      }}
      data-testid="empty-state"
    >
      <div
        style={{
          background: 'rgba(255, 255, 255, 0.05)',
          padding: '20px',
          borderRadius: '50%',
          marginBottom: '24px',
          color: 'var(--text-muted)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {icon || <Film size={40} color="var(--text-muted)" />}
      </div>

      <h3
        style={{
          fontSize: '22px',
          fontWeight: 600,
          color: 'var(--text-primary)',
          marginBottom: '12px',
          fontFamily: 'var(--font-display)',
        }}
      >
        {title}
      </h3>

      <p
        style={{
          fontSize: '15px',
          color: 'var(--text-secondary)',
          lineHeight: 1.6,
          marginBottom: '28px',
          maxWidth: '360px',
        }}
      >
        {description}
      </p>

      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="btn btn-primary"
          style={{
            padding: '12px 24px',
            fontSize: '14px',
            fontWeight: 600,
          }}
          data-testid="empty-state-action"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
