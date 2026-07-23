import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import Skeleton from '../components/Skeleton';
import ErrorState from '../components/ErrorState';
import EmptyState from '../components/EmptyState';
import { Sparkles } from 'lucide-react';

describe('Skeleton Component', () => {
  test('renders default rectangle skeleton', () => {
    render(<Skeleton />);
    const el = screen.getByTestId('skeleton');
    expect(el).toBeInTheDocument();
    expect(el).toHaveClass('skeleton');
    expect(el.style.borderRadius).toBe('12px');
  });

  test('applies variant shapes correctly', () => {
    const { rerender } = render(<Skeleton variant="circle" />);
    expect(screen.getByTestId('skeleton').style.borderRadius).toBe('50%');

    rerender(<Skeleton variant="text" />);
    expect(screen.getByTestId('skeleton').style.borderRadius).toBe('4px');
  });

  test('applies custom dimensions and classes', () => {
    render(<Skeleton width={150} height={40} className="custom-class" />);
    const el = screen.getByTestId('skeleton');
    expect(el).toHaveClass('custom-class');
    expect(el.style.width).toBe('150px');
    expect(el.style.height).toBe('40px');
  });
});

describe('ErrorState Component', () => {
  test('renders error state with default texts', () => {
    render(<ErrorState />);
    expect(screen.getByText('Something Went Wrong')).toBeInTheDocument();
    expect(
      screen.getByText('An unexpected error occurred while loading content. Please try again.')
    ).toBeInTheDocument();
  });

  test('renders custom title and message text', () => {
    render(<ErrorState title="Fail" message="Unable to connect to database" />);
    expect(screen.getByText('Fail')).toBeInTheDocument();
    expect(screen.getByText('Unable to connect to database')).toBeInTheDocument();
  });

  test('triggers callback when retry button is clicked', () => {
    const mockRetry = jest.fn();
    render(<ErrorState onRetry={mockRetry} />);
    const retryBtn = screen.getByTestId('retry-button');
    fireEvent.click(retryBtn);
    expect(mockRetry).toHaveBeenCalledTimes(1);
  });
});

describe('EmptyState Component', () => {
  test('renders empty state default values', () => {
    render(<EmptyState />);
    expect(screen.getByText('No Results Found')).toBeInTheDocument();
    expect(
      screen.getByText('Try adjusting your filters or search keywords to find what you are looking for.')
    ).toBeInTheDocument();
  });

  test('renders empty state custom title, desc, and icon', () => {
    render(
      <EmptyState
        title="Empty Box"
        description="Nothing here"
        icon={<span data-testid="custom-icon">✨</span>}
      />
    );
    expect(screen.getByText('Empty Box')).toBeInTheDocument();
    expect(screen.getByText('Nothing here')).toBeInTheDocument();
    expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
  });

  test('triggers callback action when action button is clicked', () => {
    const mockAction = jest.fn();
    render(<EmptyState actionLabel="Reload" onAction={mockAction} />);
    const actionBtn = screen.getByTestId('empty-state-action');
    fireEvent.click(actionBtn);
    expect(mockAction).toHaveBeenCalledTimes(1);
  });
});
