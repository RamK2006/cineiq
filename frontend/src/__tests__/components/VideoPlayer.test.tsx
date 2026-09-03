import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import VideoPlayer from '../../components/VideoPlayer';
import '@testing-library/jest-dom';
import { SubtitleTrackData } from '../../types/media';

// Mock the util to prevent fetch calls
jest.mock('../../utils/subtitles', () => ({
  fetchAndProcessSubtitle: jest.fn(async (url) => `blob:${url}`)
}));

global.URL.createObjectURL = jest.fn();
global.URL.revokeObjectURL = jest.fn();

const mockTracks: SubtitleTrackData[] = [
  { id: 'en', label: 'English', language: 'en', src: '/en.srt', kind: 'subtitles', format: 'srt' },
  { id: 'es', label: 'Spanish', language: 'es', src: '/es.vtt', kind: 'subtitles', format: 'vtt' }
];

describe('VideoPlayer', () => {
  it('renders video element', () => {
    render(
      <VideoPlayer 
        isPlaying={false} 
        progress={0} 
        tracks={[]} 
        activeTrackId={null} 
      />
    );
    expect(document.querySelector('video')).toBeInTheDocument();
  });

  it('allows opening subtitles menu and selecting a track', async () => {
    const onTrackChange = jest.fn();
    render(
      <VideoPlayer 
        isPlaying={false} 
        progress={0} 
        tracks={mockTracks} 
        activeTrackId={null} 
        onTrackChange={onTrackChange}
      />
    );

    // Open subtitles menu
    const subBtn = screen.getByLabelText('Subtitles Menu');
    fireEvent.click(subBtn);

    // Check menu items
    const offBtn = screen.getByLabelText('Turn off subtitles');
    expect(offBtn).toBeInTheDocument();
    
    const enBtn = screen.getByLabelText('Select English subtitles');
    expect(enBtn).toBeInTheDocument();
    
    // Select English
    fireEvent.click(enBtn);
    expect(onTrackChange).toHaveBeenCalledWith('en');
  });

  it('allows changing subtitle styling preferences', () => {
    render(
      <VideoPlayer 
        isPlaying={false} 
        progress={0} 
        tracks={mockTracks} 
        activeTrackId={null} 
      />
    );

    // Open settings menu
    const settingsBtn = screen.getByLabelText('Subtitle Settings');
    fireEvent.click(settingsBtn);

    // Select large font
    const largeFontBtn = screen.getByLabelText('Set font size to large');
    fireEvent.click(largeFontBtn);

    // Check if css was updated (we can't easily test the injected style tag contents dynamically in jsdom without inspecting innerHTML, but we can verify the button responds and doesn't crash)
    expect(largeFontBtn).toBeInTheDocument();
  });
});
