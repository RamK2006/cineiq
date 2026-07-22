import type { Metadata } from 'next';
import './globals.css';
import Navigation from '@/components/Navigation';
import CustomCursor from '@/components/CustomCursor';import { ClerkProvider } from '@clerk/nextjs';

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
<body>
          <CustomCursor />
          <Navigation />          <a href="#main-content" className="skip-link">Skip to main content</a>
          <div id="main-content">
            {children}
          </div>
        </body>
      </html>
    </ClerkProvider>
  );
}
