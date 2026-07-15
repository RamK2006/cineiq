import React from 'react';
import { render, screen, act } from '@testing-library/react';
import HomePage from '../app/page';

describe('HomePage Component', () => {
  test('renders hero movie title and details', async () => {
    render(<HomePage />);
    const titleElements = await screen.findAllByText('Dune: Part Two');
    expect(titleElements.length).toBe(2);
    expect(titleElements[0]).toBeInTheDocument();
    expect(
      screen.getByText(
        'Discover this trending cinema title recommended for you by CineIQ.'
      )
    ).toBeInTheDocument();
  });

  test('renders action buttons in hero section', async () => {
    render(<HomePage />);
    expect(await screen.findByText('Play Now')).toBeInTheDocument();
    expect(screen.getByText('More Info')).toBeInTheDocument();
  });

  test('renders all trending movie cards', async () => {
    render(<HomePage />);
    
    // We expect the trending movies (Dune, Oppenheimer, Poor Things, Interstellar, Inception, Arrival)
    expect(await screen.findByText('Oppenheimer')).toBeInTheDocument();
    expect(screen.getByText('Poor Things')).toBeInTheDocument();
    expect(screen.getByText('Interstellar')).toBeInTheDocument();
    expect(screen.getByText('Inception')).toBeInTheDocument();
    expect(screen.getByText('Arrival')).toBeInTheDocument();
  });

  test('renders animated typing text correctly', async () => {
    jest.useFakeTimers();
    render(<HomePage />);

    // Wait for mock data fetch to complete and hide the skeleton loader
    await act(async () => {
      await Promise.resolve(); 
    });

    // Fast-forward typing timer
    act(() => {
      jest.advanceTimersByTime(2500); // 50ms per character for ~40 characters
    });

    expect(screen.getByText('Discover films that match your soul.')).toBeInTheDocument();
    jest.useRealTimers();
  });
});
