/** @type {import('next').NextConfig} */

const defaultApiUrl =
  process.env.NODE_ENV === 'production'
    ? '/api/v1'
    : 'http://localhost:8001';

const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'image.tmdb.org',
        pathname: '/t/p/**',
      },
    ],
  },
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL || defaultApiUrl,
  },
};

module.exports = nextConfig;