import React from 'react';
import { render, screen } from '@testing-library/react';
import Navigation from '../components/Navigation';

// Define TS interface for custom global mock navigation
interface GlobalMockNavigation {
  setPathname: (path: string) => void;
  resetMocks: () => void;
}

declare global {
  var mockNavigation: GlobalMockNavigation;
}

describe('Navigation Component', () => {
  beforeEach(() => {
    global.mockNavigation.resetMocks();
  });

  test('renders logo and application name', () => {
    render(<Navigation />);
    expect(screen.getByText('CINEIQ')).toBeInTheDocument();
  });

  test('renders all navigation items', () => {
    render(<Navigation />);
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Semantic Search')).toBeInTheDocument();
    expect(screen.getByText('Watch Party')).toBeInTheDocument();
    expect(screen.getByText('Profile')).toBeInTheDocument();
  });

  test('renders Sign In button', () => {
    render(<Navigation />);
    expect(screen.getByText('Sign In')).toBeInTheDocument();
  });

  test('applies active styling to the current route navigation item', () => {
    // Set current path to /search
    global.mockNavigation.setPathname('/search');

    render(<Navigation />);

    const searchLink = screen.getByText('Semantic Search');
    // Check that style/attributes change or simply check the style applies correctly.
    // In Navigation.tsx, isActive sets background: 'rgba(255,255,255,0.1)'
    expect(searchLink).toHaveStyle({
      background: 'rgba(255,255,255,0.1)',
    });

    const homeLink = screen.getByText('Home');
    expect(homeLink).toHaveStyle({
      background: 'transparent',
    });
  });
});
