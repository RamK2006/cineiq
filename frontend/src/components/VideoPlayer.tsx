'use client';

import React from 'react';
import { SubtitleTrackData } from '@/types/media';

interface VideoPlayerProps {
  isPlaying: boolean;
  progress: number;
  onPlayPause: (playing: boolean) => void;
  onSeek: (progress: number) => void;
  tracks?: SubtitleTrackData[];
  activeTrackId?: string | null;
  onTrackChange?: (trackId: string | null) => void;
  videoUrl?: string;
}

export default function VideoPlayer({
  isPlaying,
  progress,
  onPlayPause,
  onSeek,
  tracks = [],
  activeTrackId,
  onTrackChange,
  videoUrl
}: VideoPlayerProps) {
  return (
    <div className="relative flex h-full w-full items-center justify-center bg-slate-950 text-white">
      {videoUrl ? (
        <video
          src={videoUrl}
          className="h-full w-full object-contain"
          controls={false}
        />
      ) : (
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <div className="mb-4 text-6xl">🎬</div>
          <p className="text-lg font-medium text-slate-300">Watch Party Stream Player</p>
          <p className="mt-1 text-sm text-slate-500">
            {isPlaying ? 'Playing video stream...' : 'Stream is paused'}
          </p>
        </div>
      )}

      {/* Video Overlay Controls */}
      <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between rounded-xl bg-black/60 p-4 backdrop-blur-md">
        <button
          onClick={() => onPlayPause(!isPlaying)}
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-violet-500"
        >
          {isPlaying ? 'Pause' : 'Play'}
        </button>

        <input
          type="range"
          min={0}
          max={100}
          value={progress}
          onChange={(e) => onSeek(Number(e.target.value))}
          className="mx-4 flex-1 accent-violet-500"
        />

        {tracks.length > 0 && onTrackChange && (
          <select
            value={activeTrackId || ''}
            onChange={(e) => onTrackChange(e.target.value || null)}
            className="rounded-lg border border-white/10 bg-slate-900 px-3 py-1.5 text-xs text-white"
          >
            <option value="">Subtitles Off</option>
            {tracks.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label} ({t.language})
              </option>
            ))}
          </select>
        )}
      </div>
    </div>
  );
}
