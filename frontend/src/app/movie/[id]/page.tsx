import type { Metadata } from 'next';
import MovieDetailClient from './MovieDetailClient';

type Props = {
  params: Promise<{ id: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  return {
    title: `Movie ${id} | CineIQ`,
    description: `View details for movie ${id} on CineIQ.`,
    openGraph: {
      title: `Movie ${id} | CineIQ`,
      description: `View details for movie ${id} on CineIQ.`,
      type: 'video.movie',
      images: ['/default-og.jpg']
    }
  };
}

export default function MovieDetailPage() {
  return <MovieDetailClient />;
}
