import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import MovieDetailClient from '../app/movie/[id]/MovieDetailClient';

describe('MovieDetailPage Component', () => {
  beforeEach(() => {
    global.mockNavigation.resetMocks();
    jest.clearAllMocks();
  });

  test('fetches the movie using the dynamic route id', async () => {
    global.mockNavigation.setParams({ id: '1' });
    render(<MovieDetailClient />);

    expect(screen.getByLabelText('Loading movie details')).toBeInTheDocument();
    expect(await screen.findByText('Dune: Part Two')).toBeInTheDocument();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/movies/1'),
      expect.objectContaining({ method: 'GET' }),
    );
  });

  test('renders dynamic movie metadata returned by the backend', async () => {
    render(<MovieDetailClient />);

    expect(await screen.findByText('83% Match')).toBeInTheDocument();
    expect(screen.getByText('2024')).toBeInTheDocument();
    expect(screen.getByText('PG-13')).toBeInTheDocument();
    expect(screen.getByText('2h 46m')).toBeInTheDocument();
    expect(screen.getByText(/Long live the fighters/)).toBeInTheDocument();
    expect(screen.getByText('Denis Villeneuve')).toBeInTheDocument();
    expect(screen.getByText(/Timothée Chalamet/)).toBeInTheDocument();
  });

  test('renders the chart after the movie loads', async () => {
    render(<MovieDetailClient />);
    await screen.findByText('Dune: Part Two');

    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
    expect(screen.getByTestId('area-chart')).toBeInTheDocument();
    expect(screen.getByTestId('xaxis')).toBeInTheDocument();
    expect(screen.getByTestId('yaxis')).toBeInTheDocument();
    expect(screen.getByTestId('tooltip')).toBeInTheDocument();
  });

  test('all primary action buttons provide feedback', async () => {
    render(<MovieDetailClient />);
    await screen.findByText('Dune: Part Two');

    fireEvent.click(screen.getByRole('button', { name: 'Play movie' }));
    expect(screen.getByRole('status')).toHaveTextContent('Playback is coming soon');

    fireEvent.click(screen.getByRole('button', { name: 'Add to watchlist' }));
    expect(screen.getByRole('status')).toHaveTextContent('Added to your watchlist');

    fireEvent.click(screen.getByRole('button', { name: 'Like this movie' }));
    expect(screen.getByRole('status')).toHaveTextContent('Thanks for rating this movie');

    fireEvent.click(screen.getByRole('button', { name: 'Add to favorites' }));
    expect(screen.getByRole('status')).toHaveTextContent('Added to favourites');
  });

  test('renders a 404 state for an invalid movie id', async () => {
    global.mockNavigation.setParams({ id: 'invalid-id' });
    render(<MovieDetailClient />);

    expect(await screen.findByText('Movie not found')).toBeInTheDocument();
    expect(screen.getByText('404')).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test('renders a 404 state when the backend returns 404', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => ({ detail: 'Movie not found' }),
    });

    render(<MovieDetailClient />);

    expect(await screen.findByText('Movie not found')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByLabelText('Loading movie details')).not.toBeInTheDocument());
  });
});
