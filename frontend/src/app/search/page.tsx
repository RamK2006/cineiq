import type { Metadata } from 'next';
import SearchClient from './SearchClient';

export const metadata: Metadata = {
  title: 'Search | CineIQ',
  description: 'Find your next favorite movie using AI-powered semantic search.',
  openGraph: {
    title: 'Search | CineIQ',
    description: 'Find your next favorite movie using AI-powered semantic search.',
    type: 'website'
  }
};

export default function SearchPage() {
  return <SearchClient />;
}
