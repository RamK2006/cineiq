import React from 'react';
import { render, screen, act } from '@testing-library/react';
import HomePage from '../app/page';

describe('HomePage Component', () => {
  test('renders hero movie title and details', () => {
    render(<HomePage />);
    const titleElements = screen.getAllByText('Dune: Part Two');
    expect(titleElements.length).toBe(2);
    expect(titleElements[0]).toBeInTheDocument();
    expect(
      screen.getByText(
        'Paul Atreides unites with Chani and the Fremen while on a warpath of revenge against the conspirators who destroyed his family.'
      )
    ).toBeInTheDocument();
  });

  test('renders action buttons in hero section', () => {
    render(<HomePage />);
    expect(screen.getByText('Play Now')).toBeInTheDocument();
    expect(screen.getByText('More Info')).toBeInTheDocument();
  });

  test('renders all trending movie cards', () => {
    render(<HomePage />);
    
    // We expect the trending movies (Dune, Oppenheimer, Poor Things, Interstellar, Inception, Arrival)
    expect(screen.getByText('Oppenheimer')).toBeInTheDocument();
    expect(screen.getByText('Poor Things')).toBeInTheDocument();
    expect(screen.getByText('Interstellar')).toBeInTheDocument();
    expect(screen.getByText('Inception')).toBeInTheDocument();
    expect(screen.getByText('Arrival')).toBeInTheDocument();
  });

  test('renders animated typing text correctly', () => {
    jest.useFakeTimers();
    render(<HomePage />);

    // Initially, text is typed letter-by-letter. Fast-forward typing timer
    act(() => {
      jest.advanceTimersByTime(2500); // 50ms per character for ~40 characters
    });

    expect(screen.getByText('Discover films that match your soul.')).toBeInTheDocument();
    jest.useRealTimers();
  });
});
