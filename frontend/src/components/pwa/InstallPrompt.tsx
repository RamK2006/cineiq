'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Download, X } from 'lucide-react';
import { usePWA } from '@/hooks/usePWA';

/**
 * InstallBanner Component
 * Displays a glassmorphic, animated bottom banner prompting the user 
 * to install the CineIQ PWA when the beforeinstallprompt event fires.
 * Respects user dismissal for 7 days to avoid annoyance.
 */
export default function InstallBanner() {
    const { isInstallable, handleInstall } = usePWA();
    const [showBanner, setShowBanner] = useState(false);

    useEffect(() => {
        if (isInstallable) {
            // Check if the user previously dismissed the prompt
            const dismissed = localStorage.getItem('cineiq-install-dismissed');
            const sevenDaysMs = 7 * 24 * 60 * 60 * 1000;

            if (!dismissed || (Date.now() - parseInt(dismissed, 10)) > sevenDaysMs) {
                // Delay showing the banner to not interrupt initial page load UX
                const timer = setTimeout(() => setShowBanner(true), 3000);
                return () => clearTimeout(timer);
            }
        }
    }, [isInstallable]);

    const handleDismiss = () => {
        setShowBanner(false);
        localStorage.setItem('cineiq-install-dismissed', Date.now().toString());
    };

    if (!showBanner || !isInstallable) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ y: 100, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: 100, opacity: 0 }}
                transition={{ type: 'spring', damping: 20, stiffness: 100 }}
                className="fixed bottom-6 left-1/2 z-[100] flex w-[90%] max-w-md -translate-x-1/2 items-center gap-4 rounded-2xl border border-violet-500/30 bg-slate-900/95 p-4 shadow-2xl shadow-violet-900/20 backdrop-blur-md dark:bg-slate-900/95 dark:border-violet-500/30"
            >
                <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-violet-600/20 text-violet-400">
                    <Download size={24} />
                </div>

                <div className="flex-1">
                    <h3 className="text-sm font-semibold text-slate-100 dark:text-slate-100">Install CINEIQ App</h3>
                    <p className="text-xs text-slate-400 dark:text-slate-400">Get faster access and offline movie browsing.</p>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        onClick={handleDismiss}
                        className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-slate-100"
                        aria-label="Dismiss install prompt"
                    >
                        <X size={18} />
                    </button>
                    <button
                        onClick={handleInstall}
                        className="rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-violet-500"
                    >
                        Install
                    </button>
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
