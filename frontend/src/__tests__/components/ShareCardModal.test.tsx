import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ShareCardModal from '../../components/ShareCardModal';
import * as htmlToImage from 'html-to-image';

// Mock html-to-image since JSDOM doesn't support canvas drawing natively
jest.mock('html-to-image', () => ({
  toPng: jest.fn().mockResolvedValue('data:image/png;base64,mockbase64data'),
}));

// Mock URL interface
global.URL.createObjectURL = jest.fn();
global.URL.revokeObjectURL = jest.fn();

// Mock fetch for the base64 avatar converter
global.fetch = jest.fn().mockResolvedValue({
  blob: () => Promise.resolve(new Blob(['mock_image'], { type: 'image/png' })),
}) as jest.Mock;

describe('ShareCardModal Component', () => {
  const defaultProps = {
    isOpen: true,
    onClose: jest.fn(),
    userName: 'John Doe',
    userAvatar: 'https://example.com/avatar.jpg',
    moviesWatched: 42,
    radarData: [
      { subject: 'Sci-Fi', A: 100, fullMark: 100 },
      { subject: 'Action', A: 80, fullMark: 100 }
    ],
    primaryGenre: 'Sci-Fi',
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders nothing when isOpen is false', () => {
    render(<ShareCardModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByText('Share Your Taste')).not.toBeInTheDocument();
  });

  it('renders modal contents properly when isOpen is true', () => {
    render(<ShareCardModal {...defaultProps} />);
    
    // Check titles
    expect(screen.getByText('Share Your Taste')).toBeInTheDocument();
    
    // Check injected data
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('#Sci-Fi')).toBeInTheDocument();
    
    // Radar pseudo-elements
    expect(screen.getByText('Action')).toBeInTheDocument();
    expect(screen.getByText('80%')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    render(<ShareCardModal {...defaultProps} />);
    const closeBtn = screen.getByLabelText('Close modal');
    fireEvent.click(closeBtn);
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it('triggers download process properly via html-to-image', async () => {
    render(<ShareCardModal {...defaultProps} />);
    const downloadBtn = screen.getByText('Download Image');
    
    fireEvent.click(downloadBtn);
    
    // Wait for the mock to resolve
    await waitFor(() => {
      expect(htmlToImage.toPng).toHaveBeenCalledTimes(1);
    });
    
    // Wait for fetch of the dataURL (simulated blob creation)
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('data:image/png;base64,mockbase64data');
    });
  });

  it('shows Native Share button when navigator.share is supported', () => {
    // Mock navigator.share
    Object.assign(navigator, {
      share: jest.fn(),
      canShare: jest.fn().mockReturnValue(true)
    });

    render(<ShareCardModal {...defaultProps} />);
    expect(screen.getByText('Share to Story')).toBeInTheDocument();
  });
});
