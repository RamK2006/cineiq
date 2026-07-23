import { ThemeProvider } from 'next-themes'
import type { Metadata } from 'next';
import './globals.css';
import Navigation from '@/components/Navigation';
import CustomCursor from '@/components/CustomCursor';
import { ClerkProvider } from '@clerk/nextjs';

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

    <html lang="en" suppressHydrationWarning>
      <body>
        <ClerkProvider>
          <ThemeProvider attribute="data-theme">
            <Navigation />
            <CustomCursor />
            <a href="#main-content" className="skip-link">Skip to main content</a>   
            <div id="main-content">
              {children}
            </div>
          </ThemeProvider>
        </ClerkProvider>
      </body>
    </html>
  );
         
}
