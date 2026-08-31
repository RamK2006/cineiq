import { renderHook, act } from '@testing-library/react';
import { usePushToTalk } from '../../hooks/usePushToTalk';

describe('usePushToTalk', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('initializes with default key', () => {
    const { result } = renderHook(() => usePushToTalk('v'));
    expect(result.current.shortcutKey).toBe('v');
    expect(result.current.isPttActive).toBe(false);
  });

  it('loads saved key from localStorage', () => {
    localStorage.setItem('ptt_shortcut', 'space');
    const { result } = renderHook(() => usePushToTalk('v'));
    expect(result.current.shortcutKey).toBe('space');
  });

  it('changes shortcut and saves to localStorage', () => {
    const { result } = renderHook(() => usePushToTalk('v'));
    
    act(() => {
      result.current.changeShortcut('c');
    });
    
    expect(result.current.shortcutKey).toBe('c');
    expect(localStorage.getItem('ptt_shortcut')).toBe('c');
  });

  it('activates PTT on keydown of matching key', () => {
    const { result } = renderHook(() => usePushToTalk('v'));
    
    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'v' }));
    });
    
    expect(result.current.isPttActive).toBe(true);
  });

  it('deactivates PTT on keyup of matching key', () => {
    const { result } = renderHook(() => usePushToTalk('v'));
    
    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'v' }));
    });
    expect(result.current.isPttActive).toBe(true);
    
    act(() => {
      document.dispatchEvent(new KeyboardEvent('keyup', { key: 'v' }));
    });
    expect(result.current.isPttActive).toBe(false);
  });

  it('ignores other keys', () => {
    const { result } = renderHook(() => usePushToTalk('v'));
    
    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'c' }));
    });
    
    expect(result.current.isPttActive).toBe(false);
  });

  it('ignores keydown if typing in input', () => {
    const { result } = renderHook(() => usePushToTalk('v'));
    
    const input = document.createElement('input');
    document.body.appendChild(input);
    input.focus();
    
    act(() => {
      const event = new KeyboardEvent('keydown', { key: 'v', bubbles: true });
      input.dispatchEvent(event);
    });
    
    expect(result.current.isPttActive).toBe(false);
    
    document.body.removeChild(input);
  });

  it('supports space bar', () => {
    const { result } = renderHook(() => usePushToTalk('space'));
    
    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: ' ' }));
    });
    
    expect(result.current.isPttActive).toBe(true);
  });

  it('resets PTT on window blur', () => {
    const { result } = renderHook(() => usePushToTalk('v'));
    
    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'v' }));
    });
    expect(result.current.isPttActive).toBe(true);
    
    act(() => {
      window.dispatchEvent(new Event('blur'));
    });
    
    expect(result.current.isPttActive).toBe(false);
  });
});
