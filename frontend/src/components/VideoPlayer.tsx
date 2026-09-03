'use client';

import React, { useRef, useEffect, useState } from 'react';
import { SubtitleTrackData, SubtitlePreferences, SubtitleFontSize, SubtitleBackgroundOpacity } from '../types/media';
import { fetchAndProcessSubtitle } from '../utils/subtitles';
import { Settings, Subtitles, Check } from 'lucide-react';

export interface VideoPlayerProps {
  isPlaying: boolean;
  progress: number; // 0 to 100
  onPlayPause?: (playing: boolean) => void;
  onSeek?: (progress: number) => void;
  tracks?: SubtitleTrackData[];
  activeTrackId?: string | null;
  onTrackChange?: (trackId: string | null) => void;
  videoUrl?: string;
}

const DEFAULT_PREFS: SubtitlePreferences = {
  fontSize: 'medium',
  backgroundOpacity: 'medium',
};

export default function VideoPlayer({
  isPlaying,
  progress,
  onPlayPause,
  onSeek,
  tracks = [],
  activeTrackId = null,
  onTrackChange,
  videoUrl
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [processedTracks, setProcessedTracks] = useState<(SubtitleTrackData & { objectUrl: string })[]>([]);
  const [prefs, setPrefs] = useState<SubtitlePreferences>(DEFAULT_PREFS);
  const [showSettings, setShowSettings] = useState(false);
  const [showSubtitlesMenu, setShowSubtitlesMenu] = useState(false);
  const settingsButtonRef = useRef<HTMLButtonElement>(null);
  const subtitlesButtonRef = useRef<HTMLButtonElement>(null);

  // Sync isPlaying to the actual video element
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlaying) {
      if (video.paused) {
        video.play().catch(e => console.warn('Play interrupted:', e));
      }
    } else {
      if (!video.paused) {
        video.pause();
      }
    }
  }, [isPlaying]);

  // Sync progress to actual video element ONLY when it differs significantly
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !video.duration) return;

    const currentProgress = (video.currentTime / video.duration) * 100;
    if (Math.abs(currentProgress - progress) > 1) {
      video.currentTime = (progress / 100) * video.duration;
    }
  }, [progress]);

  // Load subtitle tracks and convert them to blob URLs
  useEffect(() => {
    let mounted = true;
    const objectUrlsToRevoke: string[] = [];

    const loadTracks = async () => {
      const loaded: (SubtitleTrackData & { objectUrl: string })[] = [];
      for (const t of tracks) {
        try {
          const objectUrl = await fetchAndProcessSubtitle(t.src, t.format || 'srt');

          objectUrlsToRevoke.push(objectUrl);
          loaded.push({ ...t, objectUrl });
        } catch (e) {
          console.error('Subtitle track load error:', e);
        }
      }
      if (mounted) {
        setProcessedTracks(loaded);
      }
    };

    void loadTracks();

    return () => {
      mounted = false;
      objectUrlsToRevoke.forEach(url => URL.revokeObjectURL(url));
    };
  }, [tracks]);

  // Apply active track dynamically
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const textTracks = video.textTracks;
    for (let i = 0; i < textTracks.length; i++) {
      const tt = textTracks[i];
      const match = processedTracks.find(pt => pt.id === activeTrackId);
      if (match && tt.language === match.language) {
        tt.mode = 'showing';
      } else {
        tt.mode = 'hidden';
      }
    }
  }, [activeTrackId, processedTracks]);

  const getSubtitleCSS = () => {
    const sizes = { small: '75%', medium: '100%', large: '150%' };
    const opacities = { low: '0.3', medium: '0.6', high: '0.9' };
    
    return `
      .cineiq-video-player::cue {
        font-size: ${sizes[prefs.fontSize]};
        background-color: rgba(0, 0, 0, ${opacities[prefs.backgroundOpacity]});
        color: white;
        text-shadow: 1px 1px 2px black;
      }
    `;
  };

  const srcToUse = videoUrl || "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4";

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', flexDirection: 'column', background: 'black' }}>
      <style>{getSubtitleCSS()}</style>
      
      <video
        ref={videoRef}
        className="cineiq-video-player"
        src={srcToUse}
        style={{ width: '100%', height: '100%', objectFit: 'contain' }}
        crossOrigin="anonymous"
        onClick={() => onPlayPause && onPlayPause(!isPlaying)}
      >
        {processedTracks.map(t => (
          <track
            key={t.id}
            kind={t.kind}
            label={t.label}
            srcLang={t.language}
            src={t.objectUrl}
            default={t.id === activeTrackId}
          />
        ))}
      </video>

      {/* Controls Bar */}
      <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between rounded-xl bg-black/60 p-4 backdrop-blur-md z-40">
        <button
          onClick={() => onPlayPause?.(!isPlaying)}
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-violet-500"
        >
          {isPlaying ? 'Pause' : 'Play'}
        </button>

        <input
          type="range"
          min={0}
          max={100}
          value={progress}
          onChange={(e) => onSeek?.(Number(e.target.value))}
          className="mx-4 flex-1 accent-violet-500"
        />

        <div className="flex items-center gap-2">
          {tracks.length > 0 && (
            <button
              ref={subtitlesButtonRef}
              onClick={() => { setShowSubtitlesMenu(!showSubtitlesMenu); setShowSettings(false); }}
              style={{ background: 'rgba(0,0,0,0.5)', border: 'none', color: 'white', padding: '8px', borderRadius: '50%', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              aria-label="Subtitles Menu"
              aria-expanded={showSubtitlesMenu}
            >
              <Subtitles size={20} color={activeTrackId ? 'var(--accent-primary)' : 'white'} />
            </button>
          )}

          <button
            ref={settingsButtonRef}
            onClick={() => { setShowSettings(!showSettings); setShowSubtitlesMenu(false); }}
            style={{ background: 'rgba(0,0,0,0.5)', border: 'none', color: 'white', padding: '8px', borderRadius: '50%', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            aria-label="Subtitle Settings"
            aria-expanded={showSettings}
          >
            <Settings size={20} />
          </button>
        </div>
      </div>

      {/* Menus overlay */}
      {showSubtitlesMenu && (
        <div style={{ position: 'absolute', bottom: '80px', right: '80px', background: 'rgba(17, 24, 39, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '8px', zIndex: 60, minWidth: '180px' }}>
          <div style={{ padding: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', fontWeight: 600, fontSize: '14px', color: 'white' }}>Subtitles</div>
          <button
            onClick={() => { onTrackChange?.(null); setShowSubtitlesMenu(false); }}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', padding: '10px 12px', background: 'transparent', border: 'none', color: 'white', cursor: 'pointer', fontSize: '14px', borderRadius: '6px', marginTop: '4px' }}
            className="hover:bg-white/10"
            aria-label="Turn off subtitles"
          >
            <span>Off</span>
            {activeTrackId === null && <Check size={16} color="var(--accent-primary)" />}
          </button>
          {tracks.map(t => (
            <button
              key={t.id}
              onClick={() => { onTrackChange?.(t.id); setShowSubtitlesMenu(false); }}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', padding: '10px 12px', background: 'transparent', border: 'none', color: 'white', cursor: 'pointer', fontSize: '14px', borderRadius: '6px' }}
              className="hover:bg-white/10"
              aria-label={`Select ${t.label} subtitles`}
            >
              <span>{t.label}</span>
              {activeTrackId === t.id && <Check size={16} color="var(--accent-primary)" />}
            </button>
          ))}
        </div>
      )}

      {showSettings && (
        <div style={{ position: 'absolute', bottom: '80px', right: '40px', background: 'rgba(17, 24, 39, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '12px', zIndex: 60, minWidth: '220px', color: 'white' }}>
          <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '12px' }}>Subtitle Settings</div>
          
          <div style={{ marginBottom: '16px' }}>
            <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Font Size</label>
            <div style={{ display: 'flex', gap: '4px' }}>
              {(['small', 'medium', 'large'] as SubtitleFontSize[]).map(s => (
                <button
                  key={s}
                  onClick={() => setPrefs(p => ({ ...p, fontSize: s }))}
                  style={{ flex: 1, padding: '6px 0', background: prefs.fontSize === s ? 'var(--accent-primary)' : 'rgba(255,255,255,0.1)', border: 'none', color: 'white', borderRadius: '4px', fontSize: '12px', cursor: 'pointer', textTransform: 'capitalize' }}
                  aria-label={`Set font size to ${s}`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
          
          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Background Opacity</label>
            <div style={{ display: 'flex', gap: '4px' }}>
              {(['low', 'medium', 'high'] as SubtitleBackgroundOpacity[]).map(o => (
                <button
                  key={o}
                  onClick={() => setPrefs(p => ({ ...p, backgroundOpacity: o }))}
                  style={{ flex: 1, padding: '6px 0', background: prefs.backgroundOpacity === o ? 'var(--accent-primary)' : 'rgba(255,255,255,0.1)', border: 'none', color: 'white', borderRadius: '4px', fontSize: '12px', cursor: 'pointer', textTransform: 'capitalize' }}
                  aria-label={`Set background opacity to ${o}`}
                >
                  {o}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {(showSettings || showSubtitlesMenu) && (
        <div style={{ position: 'absolute', inset: 0, zIndex: 50 }} onClick={() => { setShowSettings(false); setShowSubtitlesMenu(false); }} />
      )}
    </div>
  );
}
