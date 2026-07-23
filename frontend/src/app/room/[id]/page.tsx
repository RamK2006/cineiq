import type { Metadata } from 'next';
import RoomClient from './RoomClient';

type Props = {
  params: Promise<{ id: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  return {
    title: `Watch Room ${id} | CineIQ`,
    description: `Join watch room ${id} and enjoy collaborative movie watching on CineIQ.`,
    openGraph: {
      title: `Watch Room ${id} | CineIQ`,
      description: `Join watch room ${id} and enjoy collaborative movie watching on CineIQ.`,
      type: 'website',
      images: ['/default-og.jpg']
    }
  };
}

export default function RoomPage() {
  return <RoomClient />;
}
