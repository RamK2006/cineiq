import '@testing-library/jest-dom';

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
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
  useSearchParams: () => new URLSearchParams(),
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
  setPathname: (path) => {
    mockPathname = path;
  },
  setParams: (params) => {
    mockParams = params;
  },
  resetMocks: () => {
    mockPush.mockClear();
    mockReplace.mockClear();
    mockPrefetch.mockClear();
    mockBack.mockClear();
    mockPathname = '/';
    mockParams = { id: '1' };
  },
};

// Mock global fetch
global.fetch = jest.fn().mockImplementation((url) => {
  if (url.includes('/profile/stats')) {
    return Promise.resolve({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: () =>
        Promise.resolve({
          movies_watched: 12,
          reviews: 4,
          top_genres: [
            { genre: 'Science Fiction', score: 100 },
            { genre: 'Adventure', score: 80 },
            { genre: 'Drama', score: 60 },
          ],
        }),
    });
  }

  if (url.includes('/movies/')) {
    return Promise.resolve({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: () =>
        Promise.resolve({
          id: '1',
          title: 'Dune: Part Two',
          tagline: 'Long live the fighters.',
          overview: 'Paul Atreides unites with Chani and the Fremen.',
          release_date: '2024-02-27',
          runtime: 166,
          certification: 'PG-13',
          genres: ['Science Fiction', 'Adventure'],
          director: 'Denis Villeneuve',
          cast: [
            {
              id: 1,
              name: 'Timothée Chalamet',
              character: 'Paul Atreides',
            },
          ],
          backdrop_path:
            'https://image.tmdb.org/t/p/original/backdrop.jpg',
          poster_path:
            'https://image.tmdb.org/t/p/w500/poster.jpg',
          vote_average: 8.3,
          match_score: 0.83,
        }),
    });
  }

  if (url.includes('/recommend/trending')) {
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          algorithm: 'trending',
          movies: [],
        }),
    });
  }

  if (url.includes('/recommend/personalized')) {
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          algorithm: 'personalized',
          movies: [],
        }),
    });
  }

  return Promise.reject(new Error('Unknown Endpoint'));
});

// Mock next/image
jest.mock('next/image', () => {
  const React = require('react');

  return function MockImage({
    src,
    alt,
    fill,
    sizes,
    priority,
    placeholder,
    blurDataURL,
    ...props
  }) {
    return React.createElement('img', {
      src,
      alt,
      ...props,
    });
  };
});

// Mock framer-motion
jest.mock('framer-motion', () => {
  const React = require('react');
  const actual = jest.requireActual('framer-motion');

  const customMotion = new Proxy(
    {},
    {
      get: (_target, key) =>
        React.forwardRef(({ children, ...props }, ref) => {
          const cleanProps = { ...props };
          const motionProps = [
            'initial',
            'animate',
            'exit',
            'transition',
            'variants',
            'whileHover',
            'whileTap',
            'whileInView',
            'viewport',
          ];

          motionProps.forEach((prop) => {
            delete cleanProps[prop];
          });

          return React.createElement(
            key,
            { ...cleanProps, ref },
            children,
          );
        }),
    },
  );

  return {
    ...actual,
    motion: customMotion,
    AnimatePresence: ({ children }) => children,
    useScroll: () => ({
      scrollY: {
        onChange: jest.fn(),
        on: jest.fn(() => jest.fn()),
      },
    }),
    useTransform: () => {},
  };
});

// Mock recharts
jest.mock('recharts', () => {
  const React = require('react');

  return {
    ResponsiveContainer: ({ children }) =>
      React.createElement(
        'div',
        { 'data-testid': 'responsive-container' },
        children,
      ),
    AreaChart: ({ children }) =>
      React.createElement(
        'div',
        { 'data-testid': 'area-chart' },
        children,
      ),
    Area: () =>
      React.createElement('div', {
        'data-testid': 'area',
      }),
    XAxis: () =>
      React.createElement('div', {
        'data-testid': 'xaxis',
      }),
    YAxis: () =>
      React.createElement('div', {
        'data-testid': 'yaxis',
      }),
    Tooltip: () =>
      React.createElement('div', {
        'data-testid': 'tooltip',
      }),
    RadarChart: ({ children }) =>
      React.createElement(
        'div',
        { 'data-testid': 'radar-chart' },
        children,
      ),
    PolarGrid: () =>
      React.createElement('div', {
        'data-testid': 'polar-grid',
      }),
    PolarAngleAxis: () =>
      React.createElement('div', {
        'data-testid': 'polar-angle-axis',
      }),
    PolarRadiusAxis: () =>
      React.createElement('div', {
        'data-testid': 'polar-radius-axis',
      }),
    Radar: () =>
      React.createElement('div', {
        'data-testid': 'radar',
      }),
  };
});

// Mock Clerk hooks as configurable Jest mocks
const mockOpenUserProfile = jest.fn();
const mockGetToken = jest.fn().mockResolvedValue('test-token');

const mockUseUser = jest.fn(() => ({
  isLoaded: true,
  isSignedIn: true,
  user: {
    fullName: 'Jane Cinema',
    firstName: 'Jane',
    lastName: 'Cinema',
    primaryEmailAddress: {
      emailAddress: 'jane@example.com',
    },
    imageUrl: null,
  },
}));

const mockUseClerk = jest.fn(() => ({
  openUserProfile: mockOpenUserProfile,
}));

const mockUseAuth = jest.fn(() => ({
  isLoaded: true,
  isSignedIn: true,
  userId: 'user_test_123',
  sessionId: 'session_test_123',
  getToken: mockGetToken,
}));

jest.mock('@clerk/nextjs', () => {
  const React = require('react');

  return {
    ClerkProvider: ({ children }) =>
      React.createElement(
        'div',
        { 'data-testid': 'clerk-provider' },
        children,
      ),
    SignedIn: ({ children }) => children,
    SignedOut: () => null,
    SignInButton: ({ children }) => children,
    UserButton: () =>
      React.createElement('div', {
        'data-testid': 'user-button',
      }),
    useUser: mockUseUser,
    useClerk: mockUseClerk,
    useAuth: mockUseAuth,
  };
});
