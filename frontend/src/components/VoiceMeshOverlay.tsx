import React, { useEffect, useRef, useState } from 'react';
import { Camera, Mic, MicOff, Video, VideoOff, Settings } from 'lucide-react';

interface PeerStreamProps {
  stream: MediaStream;
  peerId: string;
  isMuted: boolean;
}

export function PeerVideoBubble({ stream, peerId, isMuted }: PeerStreamProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isSpeaking, setIsSpeaking] = useState(false);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.srcObject = stream;
    }

    const AudioContextClass = typeof window !== 'undefined' ? (window.AudioContext || (window as any).webkitAudioContext) : null;
    if (!AudioContextClass) return;

    let audioContext: AudioContext | null = null;
    let animationId: number;

    try {
      if (stream.getAudioTracks().length > 0) {
        audioContext = new AudioContextClass();
        const source = audioContext.createMediaStreamSource(stream);
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 512;
        source.connect(analyser);

        const dataArray = new Uint8Array(analyser.frequencyBinCount);

        const monitorAudioVolume = () => {
          analyser.getByteFrequencyData(dataArray);
          const averageVolume = dataArray.reduce((sum, val) => sum + val, 0) / dataArray.length;

          // Toggle speaking ring indicator if volume crosses threshold criteria
          setIsSpeaking(averageVolume > 25 && !isMuted);
          animationId = requestAnimationFrame(monitorAudioVolume);
        };

        monitorAudioVolume();
      }
    } catch (err) {
      console.warn("Audio Context init error:", err);
    }

    return () => {
      if (animationId) cancelAnimationFrame(animationId);
      if (audioContext && audioContext.state !== 'closed') {
        audioContext.close().catch(() => {});
      }
    };
  }, [stream, isMuted]);

  return (
    <div className="relative group flex flex-col items-center">
      <div className={`w-24 h-24 rounded-full overflow-hidden border-2 transition-all duration-300 shadow-xl ${
        isSpeaking ? 'border-emerald-400 ring-4 ring-emerald-500/20 scale-105' : 'border-slate-700'
      }`}>
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted={isMuted}
          className="w-full h-full object-cover transform -scale-x-100"
        />
      </div>
      <span className="absolute bottom-[-18px] text-[10px] font-mono tracking-wide px-1.5 py-0.5 rounded bg-slate-900/80 border border-slate-800 text-slate-300 backdrop-blur-md opacity-80 group-hover:opacity-100 transition-opacity">
        {peerId.slice(0, 8)}
      </span>
    </div>
  );
}

interface VoiceMeshOverlayProps {
  localStream: MediaStream | null;
  peerStreams: Map<string, MediaStream>;
  cameraActive: boolean;
  micActive: boolean;
  onToggleCamera: () => void;
  onToggleMic: () => void;
  onSelectDevice?: (kind: 'videoinput' | 'audioinput', deviceId: string) => void;
}

export default function VoiceMeshOverlay({
  localStream,
  peerStreams,
  cameraActive,
  micActive,
  onToggleCamera,
  onToggleMic,
  onSelectDevice
}: VoiceMeshOverlayProps) {
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [videoDevices, setVideoDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedAudio, setSelectedAudio] = useState<string>('');
  const [selectedVideo, setSelectedVideo] = useState<string>('');
  const [showSettings, setShowSettings] = useState<boolean>(false);

  useEffect(() => {
    if (typeof navigator !== 'undefined' && navigator.mediaDevices?.enumerateDevices) {
      navigator.mediaDevices.enumerateDevices().then((devices) => {
        const audio = devices.filter(d => d.kind === 'audioinput');
        const video = devices.filter(d => d.kind === 'videoinput');
        setAudioDevices(audio);
        setVideoDevices(video);
        if (audio.length > 0 && !selectedAudio) setSelectedAudio(audio[0].deviceId);
        if (video.length > 0 && !selectedVideo) setSelectedVideo(video[0].deviceId);
      }).catch(err => console.error("Enumerate devices error:", err));
    }
  }, [selectedAudio, selectedVideo]);

  const handleDeviceChange = (kind: 'videoinput' | 'audioinput', deviceId: string) => {
    if (kind === 'audioinput') setSelectedAudio(deviceId);
    if (kind === 'videoinput') setSelectedVideo(deviceId);
    if (onSelectDevice) onSelectDevice(kind, deviceId);
  };

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Floating PIP Peer Bubbles */}
      <aside className="w-full bg-slate-950/60 p-4 rounded-2xl flex flex-wrap items-center justify-center gap-6 border border-slate-800 backdrop-blur-md shadow-2xl">
        <h4 className="w-full text-center text-[11px] font-bold font-mono tracking-widest text-slate-400 uppercase">
          Voice Mesh Group ({peerStreams.size + (localStream ? 1 : 0)}/4)
        </h4>

        {/* Local Stream Bubble */}
        {localStream && (
          <PeerVideoBubble stream={localStream} peerId="You" isMuted={true} />
        )}

        {/* Remote Mesh Streams Loop mapping */}
        {Array.from(peerStreams.entries()).map(([peerId, stream]) => (
          <PeerVideoBubble key={peerId} stream={stream} peerId={peerId} isMuted={false} />
        ))}
      </aside>

      {/* Floating Action Controls Bar */}
      <div className="px-4 py-2 bg-slate-950/80 backdrop-blur-md border border-slate-800 rounded-xl flex items-center gap-3 shadow-2xl">
        <button
          onClick={onToggleCamera}
          className={`p-2.5 rounded-lg text-xs font-bold border transition flex items-center gap-1.5 ${
            cameraActive ? 'bg-slate-800 text-slate-200 border-slate-700 hover:bg-slate-700' : 'bg-rose-500/20 border-rose-500/30 text-rose-400'
          }`}
        >
          {cameraActive ? <Video size={14} /> : <VideoOff size={14} />}
          {cameraActive ? 'Cam On' : 'Cam Off'}
        </button>

        <button
          onClick={onToggleMic}
          className={`p-2.5 rounded-lg text-xs font-bold border transition flex items-center gap-1.5 ${
            micActive ? 'bg-slate-800 text-slate-200 border-slate-700 hover:bg-slate-700' : 'bg-rose-500/20 border-rose-500/30 text-rose-400'
          }`}
        >
          {micActive ? <Mic size={14} /> : <MicOff size={14} />}
          {micActive ? 'Mic On' : 'Mic Off'}
        </button>

        {(audioDevices.length > 0 || videoDevices.length > 0) && (
          <button
            onClick={() => setShowSettings(!showSettings)}
            aria-label="Device Settings"
            className="p-2.5 rounded-lg text-xs font-bold border border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700 transition"
          >
            <Settings size={14} />
          </button>
        )}
      </div>

      {/* Device Selector Modal / Dropdown */}
      {showSettings && (
        <div className="w-full max-w-xs bg-slate-900 border border-slate-800 p-3 rounded-xl shadow-xl flex flex-col gap-2 text-xs">
          {audioDevices.length > 0 && (
            <div>
              <label className="block text-slate-400 font-mono mb-1">Microphone</label>
              <select
                value={selectedAudio}
                onChange={(e) => handleDeviceChange('audioinput', e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 text-slate-200 rounded p-1.5"
              >
                {audioDevices.map(dev => (
                  <option key={dev.deviceId} value={dev.deviceId}>
                    {dev.label || `Microphone (${dev.deviceId.slice(0, 4)})`}
                  </option>
                ))}
              </select>
            </div>
          )}

          {videoDevices.length > 0 && (
            <div>
              <label className="block text-slate-400 font-mono mb-1">Camera</label>
              <select
                value={selectedVideo}
                onChange={(e) => handleDeviceChange('videoinput', e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 text-slate-200 rounded p-1.5"
              >
                {videoDevices.map(dev => (
                  <option key={dev.deviceId} value={dev.deviceId}>
                    {dev.label || `Camera (${dev.deviceId.slice(0, 4)})`}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
