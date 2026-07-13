import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import SemanticSearchPage from '../app/search/page';

describe('SemanticSearchPage Component', () => {
  test('renders page title and subtitle', () => {
    render(<SemanticSearchPage />);
    expect(screen.getByText('Describe what you want to watch')).toBeInTheDocument();
    expect(screen.getByText("Don't know the title? Just describe the plot, mood, or characters.")).toBeInTheDocument();
  });

  test('allows typing in search input', () => {
    render(<SemanticSearchPage />);
    const input = screen.getByPlaceholderText('e.g., "A dark sci-fi movie about aliens and time travel"') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'sci-fi time travel' } });
    expect(input.value).toBe('sci-fi time travel');
  });

  test('displays search results on submission', async () => {
    render(<SemanticSearchPage />);
    const input = screen.getByPlaceholderText('e.g., "A dark sci-fi movie about aliens and time travel"');

    // Type query
    act(() => {
      fireEvent.change(input, { target: { value: 'space aliens' } });
    });

    const form = input.closest('form')!;

    // Submit form directly
    act(() => {
      fireEvent.submit(form);
    });

    // Wait for results (Arrival, Interstellar, Contact) to be visible (after 1200ms delay)
    const arrivalResult = await screen.findByText('Arrival', {}, { timeout: 3000 });
    expect(arrivalResult).toBeInTheDocument();

    expect(screen.getByText('Interstellar')).toBeInTheDocument();
    expect(screen.getByText('Contact')).toBeInTheDocument();
  });

  test('toggles voice listening state on button click', async () => {
    render(<SemanticSearchPage />);
    
    // Retrieve all buttons on the page and filter the microphone toggle button (the search submit button text is "Search")
    const getListenButton = () => {
      const buttons = screen.getAllByRole('button');
      return buttons.find(b => b.textContent !== 'Search')!;
    };
    
    // Initial: isListening is false, background style is transparent
    expect(getListenButton().getAttribute('style')).toContain('background: transparent');

    act(() => {
      fireEvent.click(getListenButton());
    });

    // Toggled: background style should change to rgba(229, 9, 20, 0.1)
    await waitFor(() => {
      expect(getListenButton().getAttribute('style')).toContain('background: rgba(229, 9, 20, 0.1)');
    });
  });
});
