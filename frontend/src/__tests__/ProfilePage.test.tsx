import React from 'react';
import { render, screen } from '@testing-library/react';
import ProfilePage from '../app/profile/page';

describe('ProfilePage Component', () => {
  test('renders user profile card with user name and details', () => {
    render(<ProfilePage />);
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Member since 2024')).toBeInTheDocument();
  });

  test('renders watched movies and reviews statistics', () => {
    render(<ProfilePage />);
    
    // Check watched count
    expect(screen.getByText('342')).toBeInTheDocument();
    expect(screen.getByText('Movies Watched')).toBeInTheDocument();

    // Check reviews count
    expect(screen.getByText('89')).toBeInTheDocument();
    expect(screen.getByText('Reviews')).toBeInTheDocument();
  });

  test('renders taste profile description and radar chart elements', () => {
    render(<ProfilePage />);
    
    expect(screen.getByText('Taste Profile')).toBeInTheDocument();
    expect(
      screen.getByText('Your profile heavily leans towards Sci-Fi and Thrillers with high tension arcs.')
    ).toBeInTheDocument();

    // Verify all radar chart mock components are rendered in the document
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
    expect(screen.getByTestId('radar-chart')).toBeInTheDocument();
    expect(screen.getByTestId('polar-grid')).toBeInTheDocument();
    expect(screen.getByTestId('polar-angle-axis')).toBeInTheDocument();
    expect(screen.getByTestId('polar-radius-axis')).toBeInTheDocument();
    expect(screen.getByTestId('radar')).toBeInTheDocument();
  });
});
