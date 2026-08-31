import { useState, useEffect, useCallback } from 'react';

export function usePushToTalk(defaultKey: string = 'v') {
  const [shortcutKey, setShortcutKey] = useState<string>(defaultKey);
  const [isPttActive, setIsPttActive] = useState<boolean>(false);

  // Load persisted shortcut if available
  useEffect(() => {
    try {
      const savedKey = localStorage.getItem('ptt_shortcut');
      if (savedKey) {
        setShortcutKey(savedKey);
      }
    } catch (e) {
      // Ignore localStorage errors
    }
  }, []);

  const changeShortcut = useCallback((key: string) => {
    const lowerKey = key.toLowerCase();
    setShortcutKey(lowerKey);
    try {
      localStorage.setItem('ptt_shortcut', lowerKey);
    } catch (e) {
      // Ignore localStorage errors
    }
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || (e.target as HTMLElement).isContentEditable) {
        return;
      }
      
      const targetKey = shortcutKey === 'space' ? ' ' : shortcutKey;

      if (e.key.toLowerCase() === targetKey && !e.repeat) {
        setIsPttActive(true);
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const targetKey = shortcutKey === 'space' ? ' ' : shortcutKey;
      if (e.key.toLowerCase() === targetKey) {
        setIsPttActive(false);
      }
    };

    const handleBlur = () => {
      setIsPttActive(false);
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('keyup', handleKeyUp);
    window.addEventListener('blur', handleBlur);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('keyup', handleKeyUp);
      window.removeEventListener('blur', handleBlur);
    };
  }, [shortcutKey]);

  return { isPttActive, shortcutKey, changeShortcut };
}
