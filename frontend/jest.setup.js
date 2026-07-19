import '@testing-library/jest-dom';

// Mock matchMedia (required for responsive libraries and Clerk components if any)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // Deprecated
    removeListener: jest.fn(), // Deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock ResizeObserver
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock next/navigation
const mockPush = jest.fn();
const mockReplace = jest.fn();
const mockPrefetch = jest.fn();
const mockBack = jest.fn();
let mockPathname = '/';
let mockParams = { id: '1' };

jest.mock('next/navigation', () => ({
  usePathname: () => mockPathname,
  useParams: () => mockParams,
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    prefetch: mockPrefetch,
    back: mockBack,
  }),
}));

global.mockNavigation = {
  push: mockPush,
  replace: mockReplace,
  prefetch: mockPrefetch,
  back: mockBack,
  setPathname: (path) => { mockPathname = path; },
  setParams: (params) => { mockParams = params; },
  resetMocks: () => {
    mockPush.mockClear();
    mockReplace.mockClear();
    mockPrefetch.mockClear();
    mockBack.mockClear();
    mockPathname = '/';
    mockParams = { id: '1' };
  }
};

// Mock global fetch for API calls in test environments
global.fetch = jest.fn().mockImplementation((url) => {
  if (url.includes('/recommend/trending')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        algorithm: 'trending',
        movies: [
          {
            id: '1',
            title: 'Dune: Part Two',
            poster_path: 'https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2JGqpTd4p.jpg',
            vote_average: 8.3,
            genres: ['Sci-Fi', 'Adventure'],
            match_score: 0.98
          }
        ]
      })
    });
  }
  if (url.includes('/recommend/personalized')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        algorithm: 'personalized',
        movies: [
          { id: '1', title: 'Dune: Part Two', poster_path: 'https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2JGqpTd4p.jpg', vote_average: 8.3, genres: ['Sci-Fi'], match_score: 0.98 },
          { id: '2', title: 'Oppenheimer', poster_path: 'https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg', vote_average: 8.9, genres: ['Drama'], match_score: 0.98 },
          { id: '3', title: 'Poor Things', poster_path: 'https://image.tmdb.org/t/p/w500/kCGlIMHnOm8PhcbTi03XQ5VGe1T.jpg', vote_average: 8.0, genres: ['Comedy'], match_score: 0.98 },
          { id: '4', title: 'Interstellar', poster_path: 'https://image.tmdb.org/t/p/w500/gEU2QlsE1ZEbKU01E8XgK31rGfQ.jpg', vote_average: 8.6, genres: ['Sci-Fi'], match_score: 0.98 },
          { id: '5', title: 'Inception', poster_path: 'https://image.tmdb.org/t/p/w500/oYuLEt3zVCKqA3F0B7I2G0kE7Y.jpg', vote_average: 8.8, genres: ['Sci-Fi'], match_score: 0.98 },
          { id: '6', title: 'Arrival', poster_path: 'https://image.tmdb.org/t/p/w500/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg', vote_average: 8.0, genres: ['Sci-Fi'], match_score: 0.98 }
        ]
      })
    });
  }
  return Promise.reject(new Error('Unknown Endpoint'));
});

// Mock next/image
jest.mock('next/image', () => {
  const React = require('react');
  return function MockImage({ src, alt, fill, sizes, priority, placeholder, blurDataURL, ...props }) {
    // eslint-disable-next-line @next/next/no-img-element
    return React.createElement('img', { src, alt, ...props });
  };
});

// Mock framer-motion
jest.mock('framer-motion', () => {
  const React = require('react');
  const actual = jest.requireActual('framer-motion');
  
  const customMotion = new Proxy(
    {},
    {
      get: (_target, key) => {
        return React.forwardRef(({ children, ...props }, ref) => {
          const cleanProps = { ...props };
          const motionProps = [
            'initial', 'animate', 'exit', 'transition', 'variants', 
            'whileHover', 'whileTap', 'whileInView', 'viewport'
          ];
          motionProps.forEach(prop => delete cleanProps[prop]);
          return React.createElement(key, { ...cleanProps, ref }, children);
        });
      },
    }
  );

  return {
    ...actual,
    motion: customMotion,
    AnimatePresence: ({ children }) => children,
    useScroll: () => ({ scrollY: { onChange: jest.fn(), on: jest.fn(() => jest.fn()) } }),
    useTransform: () => {},
  };
});

// Mock recharts
jest.mock('recharts', () => {
  const React = require('react');
  return {
    ResponsiveContainer: ({ children }) => React.createElement('div', { 'data-testid': 'responsive-container' }, children),
    AreaChart: ({ children }) => React.createElement('div', { 'data-testid': 'area-chart' }, children),
    Area: () => React.createElement('div', { 'data-testid': 'area' }),
    XAxis: () => React.createElement('div', { 'data-testid': 'xaxis' }),
    YAxis: () => React.createElement('div', { 'data-testid': 'yaxis' }),
    Tooltip: () => React.createElement('div', { 'data-testid': 'tooltip' }),
    RadarChart: ({ children }) => React.createElement('div', { 'data-testid': 'radar-chart' }, children),
    PolarGrid: () => React.createElement('div', { 'data-testid': 'polar-grid' }),
    PolarAngleAxis: () => React.createElement('div', { 'data-testid': 'polar-angle-axis' }),
    PolarRadiusAxis: () => React.createElement('div', { 'data-testid': 'polar-radius-axis' }),
    Radar: () => React.createElement('div', { 'data-testid': 'radar' }),
  };
});

// Mock Clerk
jest.mock('@clerk/nextjs', () => {
  const React = require('react');
  return {
    ClerkProvider: ({ children }) => React.createElement('div', { 'data-testid': 'clerk-provider' }, children),
    SignedIn: ({ children }) => null,
    SignedOut: ({ children }) => children,
    SignInButton: ({ children }) => children,
    UserButton: () => React.createElement('div', { 'data-testid': 'user-button' }),
    useUser: () => ({
      isLoaded: true,
      isSignedIn: true,
      user: {
        fullName: 'John Doe',
        primaryEmailAddress: null,
        imageUrl: null,
      },
    }),
  };
});


