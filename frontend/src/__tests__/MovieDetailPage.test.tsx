import React from 'react';
import { render, screen } from '@testing-library/react';
import MovieDetailClient from '../app/movie/[id]/MovieDetailClient';

describe('MovieDetailClient Component', () => {
  test('renders movie details and More Like This section', async () => {
    render(<MovieDetailClient />);
    expect(await screen.findByText(/Interstellar/i)).toBeInTheDocument();
    expect(await screen.findByText('More Like This')).toBeInTheDocument();
  });
});
