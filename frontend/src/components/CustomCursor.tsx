'use client';

import { useEffect, useRef, useState } from 'react';

const HOVER_SELECTOR = 'a, button, input, textarea, select, [role="button"], .movie-card';

export default function CustomCursor() {
  const [isEnabled, setIsEnabled] = useState(false);
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);
  const targetPos = useRef({ x: 0, y: 0 });
  const ringPos = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const hasFinePointer = window.matchMedia('(pointer: fine)').matches;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Skip entirely on touch devices and for users who've asked for less motion
    if (!hasFinePointer || prefersReducedMotion) return;

    setIsEnabled(true);
    document.body.classList.add('custom-cursor-active');

    const handleMouseMove = (e: MouseEvent) => {
      targetPos.current = { x: e.clientX, y: e.clientY };
      if (dotRef.current) {
        dotRef.current.style.transform = `translate3d(${e.clientX}px, ${e.clientY}px, 0) translate(-50%, -50%)`;
      }
    };

    const handleMouseOver = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      ringRef.current?.classList.toggle('is-hovering', !!target.closest(HOVER_SELECTOR));
    };

    const handleMouseDown = () => ringRef.current?.classList.add('is-clicking');
    const handleMouseUp = () => ringRef.current?.classList.remove('is-clicking');

    const handleWindowLeave = () => {
      dotRef.current?.style.setProperty('opacity', '0');
      ringRef.current?.style.setProperty('opacity', '0');
    };
    const handleWindowEnter = () => {
      dotRef.current?.style.setProperty('opacity', '1');
      ringRef.current?.style.setProperty('opacity', '1');
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseover', handleMouseOver);
    window.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('mouseleave', handleWindowLeave);
    document.addEventListener('mouseenter', handleWindowEnter);

    // Animate the trailing ring toward the dot's position every frame
    let frameId: number;
    const animateRing = () => {
      ringPos.current.x += (targetPos.current.x - ringPos.current.x) * 0.15;
      ringPos.current.y += (targetPos.current.y - ringPos.current.y) * 0.15;
      if (ringRef.current) {
        ringRef.current.style.transform = `translate3d(${ringPos.current.x}px, ${ringPos.current.y}px, 0) translate(-50%, -50%)`;
      }
      frameId = requestAnimationFrame(animateRing);
    };
    frameId = requestAnimationFrame(animateRing);

    return () => {
      document.body.classList.remove('custom-cursor-active');
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseover', handleMouseOver);
      window.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('mouseleave', handleWindowLeave);
      document.removeEventListener('mouseenter', handleWindowEnter);
      cancelAnimationFrame(frameId);
    };
  }, []);

  if (!isEnabled) return null;

  return (
    <>
      <div ref={dotRef} className="custom-cursor-dot" aria-hidden="true" />
      <div ref={ringRef} className="custom-cursor-ring" aria-hidden="true" />
    </>
  );
}