import { useEffect } from 'react';
import { usePathname } from 'next/navigation';

export function useScrollRestoration() {
  const pathname = usePathname();

  useEffect(() => {
    const handleScroll = () => {
      try {
        sessionStorage.setItem(`scroll-${pathname}`, String(window.scrollY));
      } catch {}
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [pathname]);

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(`scroll-${pathname}`);
      if (saved) {
        const y = parseInt(saved, 10);
        if (!isNaN(y) && y > 0) requestAnimationFrame(() => window.scrollTo(0, y));
      }
    } catch {}
  }, [pathname]);
}
