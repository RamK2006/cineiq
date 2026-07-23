import type { Metadata } from 'next';
import './globals.css';
import Navigation from '@/components/Navigation';
import { ThemeProvider } from '@/context/ThemeContext';
import { ClerkProvider } from '@clerk/nextjs';
import CustomCursor from '@/components/CustomCursor';
import ScrollToTopButton from '@/components/ScrollToTopButton';

export const metadata: Metadata = {
  title: 'CINEIQ | Discover Movies Together',
  description: 'AI-powered movie recommendations and social discovery platform.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || 'pk_test_Y2luZWlxLmNsZXJrLmFjY291bnRzLmRldiQ';

  return (
    <ClerkProvider publishableKey={publishableKey}>
      <html lang="en">
        <head>
          <script
            dangerouslySetInnerHTML={{
              __html: `
                (function () {
                  try {
                    var stored = localStorage.getItem('cineiq-theme');
                    var theme = stored || (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
                    document.documentElement.setAttribute('data-theme', theme);
                  } catch (e) {}
                })();
              `,
            }}
          />
        </head>
        <body>
          <ThemeProvider>
            <Navigation />
            <a href="#main-content" className="skip-link">Skip to main content</a>
            <div id="main-content">
              {children}
            </div>
          </ThemeProvider>
          <CustomCursor />
          <ScrollToTopButton />
        </body>
      </html>
    </ClerkProvider>
  );
}
