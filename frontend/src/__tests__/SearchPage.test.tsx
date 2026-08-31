import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import SemanticSearchPage from '../app/search/page';

describe('SemanticSearchPage Component', () => {
  test('renders page title and header badge', () => {
    render(<SemanticSearchPage />);
    expect(screen.getByText('Describe what you want to watch')).toBeInTheDocument();
    expect(screen.getByText(/AI-Powered Search/)).toBeInTheDocument();
  });


  test('allows typing in search input and displays suggestions', async () => {
    render(<SemanticSearchPage />);
    const input = screen.getByLabelText('Search for movies by description or title') as HTMLInputElement;
    
    act(() => {
      fireEvent.change(input, { target: { value: 'Inter' } });
    });
    expect(input.value).toBe('Inter');

    const suggestion = await screen.findByRole('listbox');
    expect(suggestion).toBeInTheDocument();
  });

  test('supports keyboard navigation (ArrowDown / Escape) on suggestions popover', async () => {
    render(<SemanticSearchPage />);
    const input = screen.getByLabelText('Search for movies by description or title') as HTMLInputElement;

    act(() => {
      fireEvent.change(input, { target: { value: 'Inter' } });
    });

    const listbox = await screen.findByRole('listbox');
    expect(listbox).toBeInTheDocument();

    act(() => {
      fireEvent.keyDown(input, { key: 'ArrowDown' });
    });

    const options = screen.getAllByRole('option');
    expect(options[0]).toHaveAttribute('aria-selected', 'true');

    act(() => {
      fireEvent.keyDown(input, { key: 'Escape' });
    });

    await waitFor(() => {
      expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    });
  });
});

