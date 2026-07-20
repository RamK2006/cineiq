'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, useScroll, AnimatePresence } from 'framer-motion';
import { Search, Home, User, Users, Film, Menu, X } from 'lucide-react';
import { useEffect, useState, useRef } from 'react';
import { SignInButton, UserButton, SignedIn, SignedOut } from '@clerk/nextjs';

export default function Navigation() {
  const pathname = usePathname();
  const { scrollY } = useScroll();
  const [isScrolled, setIsScrolled] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const unsubscribe = scrollY.on('change', (latest) => {
      setIsScrolled(latest > 50);
    });
    return () => unsubscribe();
  }, [scrollY]);

  // Lock body scroll when mobile menu is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Close menu on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  // Focus trap
  useEffect(() => {
    if (!isOpen) {
      triggerRef.current?.focus();
      return;
    }

    const menuEl = menuRef.current;
    if (!menuEl) return;

    const focusableSelector = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      const focusableElements = menuEl.querySelectorAll<HTMLElement>(focusableSelector);
      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          lastElement.focus();
          e.preventDefault();
        }
      } else {
        if (document.activeElement === lastElement) {
          firstElement.focus();
          e.preventDefault();
        }
      }
    };

    // Focus the first element initially
    const focusableElements = menuEl.querySelectorAll<HTMLElement>(focusableSelector);
    if (focusableElements.length > 0) {
      focusableElements[0].focus();
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const navItems = [
    { href: '/', label: 'Home', icon: Home },
    { href: '/search', label: 'Semantic Search', icon: Search },
    { href: '/room/demo', label: 'Watch Party', icon: Users },
    { href: '/profile', label: 'Profile', icon: User },
  ];

  // Framer Motion Animation Variants
  const backdropVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1 },
  };

  const drawerVariants = {
    closed: {
      x: '100%',
      transition: {
        type: 'spring',
        stiffness: 400,
        damping: 40,
        staggerChildren: 0.05,
        staggerDirection: -1,
      }
    },
    open: {
      x: 0,
      transition: {
        type: 'spring',
        stiffness: 300,
        damping: 30,
        staggerChildren: 0.08,
        delayChildren: 0.1,
      }
    }
  };

  const itemVariants = {
    closed: { opacity: 0, x: 25 },
    open: { opacity: 1, x: 0 }
  };

  return (
    <>
      <motion.header
        className="nav-header"
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 50,
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

        {/* Desktop Navigation Links */}
        <nav aria-label="Main navigation" className="nav-desktop">
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
        
        {/* Desktop Actions */}
        <div className="nav-desktop-actions" style={{ display: 'flex', alignItems: 'center' }}>
          <SignedOut>
            <SignInButton mode="modal">
              <button className="btn btn-glass navigation-action" style={{ padding: '8px 20px', fontSize: '13px' }}>
                Sign In
              </button>
            </SignInButton>
          </SignedOut>
          <SignedIn>
            <UserButton />
          </SignedIn>
        </div>

        {/* Hamburger Menu Trigger Button */}
        <button
          ref={triggerRef}
          className="nav-mobile-trigger"
          onClick={() => setIsOpen(true)}
          aria-expanded={isOpen}
          aria-controls="mobile-menu-drawer"
          aria-label="Open main menu"
        >
          <Menu size={20} />
        </button>
      </motion.header>

      {/* Mobile Navigation Slide-in Drawer */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              className="nav-mobile-backdrop"
              initial="hidden"
              animate="visible"
              exit="hidden"
              variants={backdropVariants}
              onClick={() => setIsOpen(false)}
            />

            {/* Slide-in Drawer */}
            <motion.div
              id="mobile-menu-drawer"
              ref={menuRef}
              className="nav-mobile-drawer"
              initial="closed"
              animate="open"
              exit="closed"
              variants={drawerVariants}
              role="dialog"
              aria-modal="true"
              aria-label="Mobile navigation menu"
            >
              <div className="nav-drawer-header">
                {/* Logo inside drawer */}
                <Link
                  href="/"
                  className="site-logo"
                  onClick={() => setIsOpen(false)}
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

                {/* Close Button */}
                <button
                  className="nav-drawer-close"
                  onClick={() => setIsOpen(false)}
                  aria-label="Close menu"
                >
                  <X size={18} />
                </button>
              </div>

              {/* Navigation Links in Drawer */}
              <nav aria-label="Mobile navigation" className="nav-drawer-list">
                {navItems.map((item) => {
                  const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                  const Icon = item.icon;
                  return (
                    <motion.div key={item.href} variants={itemVariants}>
                      <Link
                        href={item.href}
                        className={`nav-drawer-link ${isActive ? 'active' : ''}`}
                        onClick={() => setIsOpen(false)}
                        aria-current={isActive ? 'page' : undefined}
                      >
                        <Icon size={18} />
                        <span>{item.label}</span>
                      </Link>
                    </motion.div>
                  );
                })}
              </nav>

              {/* Drawer Footer Actions */}
              <motion.div className="nav-drawer-footer" variants={itemVariants}>
                <SignedOut>
                  <SignInButton mode="modal">
                    <button
                      className="btn btn-glass"
                      onClick={() => setIsOpen(false)}
                    >
                      Sign In
                    </button>
                  </SignInButton>
                </SignedOut>
                <SignedIn>
                  <div onClick={() => setIsOpen(false)} style={{ display: 'flex', justifyContent: 'center' }}>
                    <UserButton />
                  </div>
                </SignedIn>
              </motion.div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
