if (process.env.NODE_ENV !== 'production') {
  process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
}

/** @type {import('next').NextConfig} */

const defaultApiUrl =
  process.env.NODE_ENV === 'production'
    ? '/api/v1'
    : 'http://localhost:8001';

const nextConfig = {
  reactStrictMode: true,
  images: {
    unoptimized: process.env.NODE_ENV !== 'production',
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