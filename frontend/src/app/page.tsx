import type { Metadata } from 'next';
import HomeClient from './HomeClient';

export const metadata: Metadata = {
  title: 'CineIQ | Discover Movies Together',
  description: 'Discover trending and AI-powered movie recommendations.',
  openGraph: {
    title: 'CineIQ | Discover Movies Together',
    description: 'Discover trending and AI-powered movie recommendations.',
    type: 'website',
    images: ['/default-og.jpg']
  }
};

export default function HomePage() {
  return <HomeClient />;
}
