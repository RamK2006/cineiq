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

// Mock next/image
jest.mock('next/image', () => {
  const React = require('react');
  return function MockImage({ src, alt, ...props }) {
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
    useScroll: () => ({ scrollY: { onChange: jest.fn() } }),
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

