'use client';
import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  onRetry?: () => void;
}
interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error('MovieDetail render error:', error, info);

    // Report to monitoring service
    if (typeof window !== 'undefined' && (window as any).Sentry) {
      (window as any).Sentry.captureException(error, {
        contexts: { react: { componentStack: info.componentStack } },
        tags: { location: 'movie-detail-boundary' },
      });
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
    this.props.onRetry?.();
  };

  render() {
    if (this.state.hasError) {
      return (
        <main style={{ minHeight: '100vh', background: 'var(--bg-base)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--space-xl, 40px)' }}>
          <div className="glass-panel" style={{ padding: 'var(--space-xl, 40px)', textAlign: 'center', maxWidth: '480px' }}>
            <h2 style={{ fontSize: 'var(--font-size-xl, 24px)', marginBottom: 'var(--space-sm, 12px)' }}>Something went wrong</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--space-lg, 24px)' }}>
              {this.state.error?.message || 'We couldn\'t load this movie.'}
            </p>
            <button className="btn btn-primary" onClick={this.handleRetry}>
              Retry
            </button>
          </div>
        </main>
      );
    }
    return this.props.children;
  }
}
