'use client';

import { useState, useEffect } from 'react';

/**
 * Extended Event interface for the beforeinstallprompt event
 * which is not natively typed in standard TypeScript DOM libraries.
 */
interface BeforeInstallPromptEvent extends Event {
    prompt: () => Promise<void>;
    userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

/**
 * Custom hook to manage PWA installation logic.
 * Tracks whether the app is installable, already installed, 
 * and provides a handler to trigger the native install prompt.
 */
export function usePWA() {
    const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
    const [isInstalled, setIsInstalled] = useState(false);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            // Check if the app is already running in standalone mode (installed)
            setIsInstalled(window.matchMedia('(display-mode: standalone)').matches);

            const handler = (e: Event) => {
                e.preventDefault();
                setDeferredPrompt(e as BeforeInstallPromptEvent);
            };

            window.addEventListener('beforeinstallprompt', handler);

            // Listen for the appinstalled event to update state
            const handleInstalled = () => {
                setIsInstalled(true);
                setDeferredPrompt(null);
            };
            window.addEventListener('appinstalled', handleInstalled);

            return () => {
                window.removeEventListener('beforeinstallprompt', handler);
                window.removeEventListener('appinstalled', handleInstalled);
            };
        }
    }, []);

    const handleInstall = async () => {
        if (!deferredPrompt) return;

        // Trigger the native browser install prompt
        deferredPrompt.prompt();

        // Wait for the user to respond to the prompt
        const { outcome } = await deferredPrompt.userChoice;
        if (outcome === 'accepted') {
            console.log('User accepted the CineIQ install prompt');
        } else {
            console.log('User dismissed the CineIQ install prompt');
        }

        // Clear the deferredPrompt as it can only be used once
        setDeferredPrompt(null);
    };

    return {
        isInstallable: !!deferredPrompt && !isInstalled,
        isInstalled,
        handleInstall,
        deferredPrompt,
    };
}
