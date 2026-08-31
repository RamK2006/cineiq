import { renderHook, act } from '@testing-library/react';
import { useAudioAnalyzer } from '../../hooks/useAudioAnalyzer';

describe('useAudioAnalyzer', () => {
  let mockAudioContext: any;
  let mockSource: any;
  let mockAnalyser: any;

  beforeEach(() => {
    jest.useFakeTimers();

    mockSource = {
      connect: jest.fn(),
      disconnect: jest.fn(),
    };

    mockAnalyser = {
      fftSize: 256,
      connect: jest.fn(),
      disconnect: jest.fn(),
      getFloatTimeDomainData: jest.fn((array: Float32Array) => {
        // Default to silence
        for (let i = 0; i < array.length; i++) array[i] = 0;
      })
    };

    mockAudioContext = {
      state: 'running',
      resume: jest.fn().mockResolvedValue(undefined),
      close: jest.fn().mockResolvedValue(undefined),
      createMediaStreamSource: jest.fn(() => mockSource),
      createAnalyser: jest.fn(() => mockAnalyser),
    };

    (window as any).AudioContext = jest.fn(() => mockAudioContext);
    
    // Mock requestAnimationFrame
    jest.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
      return setTimeout(() => cb(Date.now()), 16) as unknown as number;
    });
    jest.spyOn(window, 'cancelAnimationFrame').mockImplementation((id) => {
      clearTimeout(id);
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
    jest.useRealTimers();
  });

  const createMockStream = (hasAudio: boolean = true) => {
    return {
      getAudioTracks: () => hasAudio ? [{}] : []
    } as unknown as MediaStream;
  };

  it('returns muted if isMuted is true', () => {
    const stream = createMockStream();
    const { result } = renderHook(() => useAudioAnalyzer(stream, true));
    
    expect(result.current).toBe('muted');
  });

  it('returns muted if stream has no audio tracks', () => {
    const stream = createMockStream(false);
    const { result } = renderHook(() => useAudioAnalyzer(stream, false));
    
    expect(result.current).toBe('muted');
  });

  it('initializes and returns active when silent', () => {
    const stream = createMockStream();
    const { result } = renderHook(() => useAudioAnalyzer(stream, false));
    
    expect(result.current).toBe('active');
    
    // Advance timers to trigger analysis loop
    act(() => {
      jest.advanceTimersByTime(100);
    });
    
    expect(result.current).toBe('active');
  });

  it('transitions to speaking when volume exceeds threshold', () => {
    const stream = createMockStream();
    const { result } = renderHook(() => useAudioAnalyzer(stream, false));
    
    expect(result.current).toBe('active');
    
    // Simulate loud audio
    mockAnalyser.getFloatTimeDomainData.mockImplementation((array: Float32Array) => {
      for (let i = 0; i < array.length; i++) array[i] = 1.0;
    });
    
    act(() => {
      // Need 3 frames of speaking to transition
      jest.advanceTimersByTime(16 * 4);
    });
    
    expect(result.current).toBe('speaking');
  });

  it('transitions back to active after silence and release time', () => {
    const stream = createMockStream();
    const { result } = renderHook(() => useAudioAnalyzer(stream, false));
    
    // Simulate loud audio
    mockAnalyser.getFloatTimeDomainData.mockImplementation((array: Float32Array) => {
      for (let i = 0; i < array.length; i++) array[i] = 1.0;
    });
    
    act(() => {
      jest.advanceTimersByTime(16 * 4); // Become speaking
    });
    
    expect(result.current).toBe('speaking');
    
    // Simulate silence
    mockAnalyser.getFloatTimeDomainData.mockImplementation((array: Float32Array) => {
      for (let i = 0; i < array.length; i++) array[i] = 0.0;
    });
    
    act(() => {
      // Need 15 frames of silence to transition back (15 * 16ms = 240ms) + smoothing time
      jest.advanceTimersByTime(16 * 30);
    });
    
    expect(result.current).toBe('active');
  });

  it('cleans up resources on unmount', () => {
    const stream = createMockStream();
    const { unmount } = renderHook(() => useAudioAnalyzer(stream, false));
    
    act(() => {
      unmount();
    });
    
    expect(mockSource.disconnect).toHaveBeenCalled();
    expect(mockAnalyser.disconnect).toHaveBeenCalled();
    expect(mockAudioContext.close).toHaveBeenCalled();
  });
});
