'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, useScroll, useTransform } from 'framer-motion';
import { Search, Home, User, Users, Film } from 'lucide-react';
import { useEffect, useState } from 'react';

export default function Navigation() {
  const pathname = usePathname();
  const { scrollY } = useScroll();
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const unsubscribe = scrollY.on("change", (latest) => {
      setIsScrolled(latest > 50);
    });
    return () => unsubscribe();
  }, [scrollY]);

  const navItems = [
    { href: '/', label: 'Home', icon: Home },
    { href: '/search', label: 'Semantic Search', icon: Search },
    { href: '/room/demo', label: 'Watch Party', icon: Users },
    { href: '/profile', label: 'Profile', icon: User },
  ];

  return (
    <motion.header
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 50,
        padding: '20px 40px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: isScrolled ? 'rgba(5, 5, 10, 0.85)' : 'transparent',
        backdropFilter: isScrolled ? 'blur(20px)' : 'none',
        borderBottom: isScrolled ? '1px solid rgba(255,255,255,0.05)' : '1px solid transparent',
        transition: 'all 0.3s ease',
      }}
    >
      <Link
        href="/"
        className="site-logo"
        aria-label="CineIQ home"
        style={{ display: 'flex', alignItems: 'center', gap: '10px' }}
      >
        <div style={{
          width: '32px', height: '32px',
          background: 'var(--accent-primary)',
          borderRadius: '8px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 0 20px rgba(229, 9, 20, 0.5)'
        }}>
          <Film size={18} color="white" />
        </div>
        <span style={{ fontFamily: 'var(--font-display)', fontSize: '20px', fontWeight: 800, letterSpacing: '2px' }}>
          CINEIQ
        </span>
      </Link>

      <nav aria-label="Main navigation" style={{ display: 'flex', gap: '8px' }}>
        {navItems.map((item) => {
          const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className="navigation-link"
              aria-current={isActive ? 'page' : undefined}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                borderRadius: '999px',
                fontFamily: 'var(--font-display)',
                fontSize: '14px',
                fontWeight: isActive ? 600 : 500,
                color: isActive ? 'white' : 'var(--text-secondary)',
                background: isActive ? 'rgba(255,255,255,0.1)' : 'transparent',
                transition: 'all 0.2s',
              }}
            >
              <Icon size={16} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      
      <div>
        <button className="btn btn-glass navigation-action" style={{ padding: '8px 20px', fontSize: '13px' }}>
          Sign In
        </button>
      </div>
    </motion.header>
  );
}
