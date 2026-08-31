import React from 'react';
import { render, screen, act } from '@testing-library/react';
import HomePage from '../app/page';

describe('HomePage Component', () => {
  test('renders hero movie title and details', async () => {
    render(<HomePage />);
    const titleElements = await screen.findAllByText('Interstellar');
    expect(titleElements.length).toBeGreaterThan(0);
    expect(
      screen.getByText(
        'Explore this title and see its full details.'
      )
    ).toBeInTheDocument();
  });

  test('renders action buttons in hero section', async () => {
    render(<HomePage />);
    expect(await screen.findByText('Play Now')).toBeInTheDocument();
    expect(screen.getByText('More Info')).toBeInTheDocument();
  });

  test('renders trending movie cards', async () => {
    render(<HomePage />);
    const interstellarElements = await screen.findAllByText('Interstellar');
    expect(interstellarElements.length).toBeGreaterThan(0);
    expect(screen.getByText('Inception')).toBeInTheDocument();
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

  test('renders mood selector tabs and switches mood on click', async () => {
    const { fireEvent } = require('@testing-library/react');
    render(<HomePage />);
    expect(await screen.findByText('Mood & Emotion Carousel')).toBeInTheDocument();
    
    const tenseTabs = screen.getAllByText('Tense & Gripping');
    expect(tenseTabs.length).toBeGreaterThan(0);

    const highAdrenalineTabs = screen.getAllByText('High Adrenaline');
    expect(highAdrenalineTabs.length).toBeGreaterThan(0);

    const highAdrenalineTab = highAdrenalineTabs[0];
    act(() => {
      fireEvent.click(highAdrenalineTab);
    });

    const adrenalineBadges = await screen.findAllByText('High Adrenaline');
    expect(adrenalineBadges.length).toBeGreaterThan(0);
  });

});

