import type { Metadata } from 'next';
import ProfileClient from './ProfileClient';

export const metadata: Metadata = {
  title: 'Your Profile | CineIQ',
  description: 'View your taste profile, movie recommendations, and watch history.',
  openGraph: {
    title: 'Your Profile | CineIQ',
    description: 'View your taste profile, movie recommendations, and watch history.',
    type: 'profile',
    images: ['/default-og.jpg']
  }
};

export default function ProfilePage() {
  return <ProfileClient />;
}
