import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import CinemaOverlay, { Reaction } from '../../components/CinemaOverlay';
import '@testing-library/jest-dom';

describe('CinemaOverlay', () => {
  beforeAll(() => {
    window.HTMLElement.prototype.scrollIntoView = jest.fn();
  });

  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  const defaultProps = {
    isFullscreen: true,
    messages: [{ user: 'Alice', text: 'Hello!' }],
    chatInput: '',
    setChatInput: jest.fn(),
    handleChat: jest.fn((e) => e.preventDefault()),
    currentUserId: 'me',
    isMuted: false,
    reactions: [],
    onSendReaction: jest.fn(),
    isChatVisible: true,
    setChatVisible: jest.fn()
  };

  it('renders chat overlay when fullscreen', () => {
    render(<CinemaOverlay {...defaultProps} />);
    expect(screen.getByText('Room Chat')).toBeInTheDocument();
    expect(screen.getByText('Hello!')).toBeInTheDocument();
  });

  it('does not render when not fullscreen', () => {
    const { container } = render(<CinemaOverlay {...defaultProps} isFullscreen={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('auto-hides chat after inactivity', () => {
    render(<CinemaOverlay {...defaultProps} />);
    expect(screen.getByText('Room Chat')).toBeInTheDocument();

    act(() => {
      jest.advanceTimersByTime(3500);
    });

    expect(screen.queryByText('Room Chat')).not.toBeInTheDocument();
  });

  it('reveals chat on mouse move', () => {
    render(<CinemaOverlay {...defaultProps} />);
    
    act(() => {
      jest.advanceTimersByTime(3500);
    });
    expect(screen.queryByText('Room Chat')).not.toBeInTheDocument();

    act(() => {
      fireEvent.mouseMove(document);
    });
    expect(screen.getByText('Room Chat')).toBeInTheDocument();
  });

  it('keeps chat visible while typing', () => {
    render(<CinemaOverlay {...defaultProps} />);
    const input = screen.getByPlaceholderText('Type a message...');
    
    act(() => {
      fireEvent.focus(input);
    });
    
    act(() => {
      jest.advanceTimersByTime(3500);
    });
    
    // Chat should still be visible because input is focused
    expect(screen.getByText('Room Chat')).toBeInTheDocument();
    
    act(() => {
      fireEvent.blur(input);
      jest.advanceTimersByTime(3500);
    });
    
    // Now it hides
    expect(screen.queryByText('Room Chat')).not.toBeInTheDocument();
  });

  it('renders emoji reactions', () => {
    const reactions: Reaction[] = [{ id: '1', emoji: '❤️', timestamp: Date.now() }];
    render(<CinemaOverlay {...defaultProps} reactions={reactions} />);
    
    expect(screen.getAllByText('❤️').length).toBeGreaterThan(0);
  });

  it('calls onSendReaction when reaction button is clicked', () => {
    render(<CinemaOverlay {...defaultProps} />);
    const btn = screen.getByLabelText('React with 😂');
    
    fireEvent.click(btn);
    expect(defaultProps.onSendReaction).toHaveBeenCalledWith('😂');
  });

  it('hides chat when close button is clicked', () => {
    render(<CinemaOverlay {...defaultProps} />);
    const hideBtn = screen.getByLabelText('Hide chat overlay');
    
    fireEvent.click(hideBtn);
    expect(defaultProps.setChatVisible).toHaveBeenCalledWith(false);
  });
});
