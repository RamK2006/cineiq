import React from 'react';
import { render, screen } from '@testing-library/react';
import MovieDetailPage from '../app/movie/[id]/page';

describe('MovieDetailPage Component', () => {
  beforeEach(() => {
    global.mockNavigation.resetMocks();
  });

  test('renders movie title, rating, runtime, and match score', () => {
    render(<MovieDetailPage />);
    
    expect(screen.getByText('Dune: Part Two')).toBeInTheDocument();
    expect(screen.getByText('98% Match')).toBeInTheDocument();
    expect(screen.getByText('2024')).toBeInTheDocument();
    expect(screen.getByText('PG-13')).toBeInTheDocument();
    expect(screen.getByText('2h 46m')).toBeInTheDocument();
  });

  test('renders movie overview and tagline', () => {
    render(<MovieDetailPage />);
    
    // Tagline in quotes
    expect(screen.getByText('"Long live the fighters."')).toBeInTheDocument();
    expect(
      screen.getByText(
        'Paul Atreides unites with Chani and the Fremen while on a warpath of revenge against the conspirators who destroyed his family.'
      )
    ).toBeInTheDocument();
  });

  test('renders movie metadata details like director and cast', () => {
    render(<MovieDetailPage />);
    
    // Check Director
    expect(screen.getByText('Denis Villeneuve')).toBeInTheDocument();
    
    // Check Cast members using regex to match substrings inside the joined cast string
    expect(screen.getByText(/Timothée Chalamet/)).toBeInTheDocument();
    expect(screen.getByText(/Zendaya/)).toBeInTheDocument();
    expect(screen.getByText(/Rebecca Ferguson/)).toBeInTheDocument();
    expect(screen.getByText(/Javier Bardem/)).toBeInTheDocument();
  });

  test('renders mock emotional arc chart elements', () => {
    render(<MovieDetailPage />);
    
    // ResponsiveContainer, AreaChart, XAxis, YAxis, Tooltip, and Area elements should render (mocked)
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
    expect(screen.getByTestId('area-chart')).toBeInTheDocument();
    expect(screen.getByTestId('xaxis')).toBeInTheDocument();
    expect(screen.getByTestId('yaxis')).toBeInTheDocument();
    expect(screen.getByTestId('tooltip')).toBeInTheDocument();
  });

  test('renders movie action buttons (Play, Add to List, etc.)', () => {
    render(<MovieDetailPage />);
    expect(screen.getByText(/Play/)).toBeInTheDocument();
  });
});
