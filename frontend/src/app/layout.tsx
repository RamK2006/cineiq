import type { Metadata } from 'next';
import './globals.css';
import Navigation from '@/components/Navigation';

export const metadata: Metadata = {
  title: 'CINEIQ | Discover Movies Together',
  description: 'AI-powered movie recommendations and social discovery platform.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Navigation />
        <a href="#main-content" className="skip-link">Skip to main content</a>
        <div id="main-content">
          {children}
        </div>
      </body>
    </html>
  );
}
