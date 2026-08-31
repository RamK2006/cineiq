import { useState, useEffect, useRef } from 'react';

export type VoiceStatus = 'muted' | 'active' | 'speaking';

export function useAudioAnalyzer(stream: MediaStream | null, isMuted: boolean): VoiceStatus {
  const [status, setStatus] = useState<VoiceStatus>(isMuted ? 'muted' : 'active');
  const statusRef = useRef<VoiceStatus>(isMuted ? 'muted' : 'active');

  useEffect(() => {
    if (isMuted) {
      if (statusRef.current !== 'muted') {
        statusRef.current = 'muted';
        setStatus('muted');
      }
      return;
    }

    if (!stream || stream.getAudioTracks().length === 0) {
      if (statusRef.current !== 'muted') {
        statusRef.current = 'muted';
        setStatus('muted');
      }
      return;
    }

    const AudioContextClass = typeof window !== 'undefined' ? (window.AudioContext || (window as any).webkitAudioContext) : null;
    if (!AudioContextClass) {
      if (statusRef.current !== 'active') {
        statusRef.current = 'active';
        setStatus('active');
      }
      return;
    }

    let audioContext: AudioContext | null = null;
    let animationId: number;
    let source: MediaStreamAudioSourceNode | null = null;
    let analyser: AnalyserNode | null = null;

    try {
      audioContext = new AudioContextClass();
      
      // Some browsers suspend audio context until user interaction.
      if (audioContext.state === 'suspended') {
        audioContext.resume().catch(() => {});
      }

      source = audioContext.createMediaStreamSource(stream);
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);

      const dataArray = new Float32Array(analyser.fftSize);
      
      // Noise gate settings
      const NOISE_GATE_THRESHOLD = 0.02; // RMS threshold
      let smoothVolume = 0;
      const SMOOTHING_FACTOR = 0.8; // 0 = no smoothing, 0.99 = heavily smoothed
      
      let speakingFrames = 0;
      let silentFrames = 0;
      const FRAMES_TO_START_SPEAKING = 3;
      const FRAMES_TO_STOP_SPEAKING = 15; // Release time to avoid flickering

      const monitor = () => {
        analyser!.getFloatTimeDomainData(dataArray);
        
        // Calculate RMS (Root Mean Square) for time-domain data
        let sumSquares = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sumSquares += dataArray[i] * dataArray[i];
        }
        const rms = Math.sqrt(sumSquares / dataArray.length);
        
        // Exponential smoothing
        smoothVolume = (smoothVolume * SMOOTHING_FACTOR) + (rms * (1 - SMOOTHING_FACTOR));
        
        const isSpeakingRaw = smoothVolume > NOISE_GATE_THRESHOLD;
        
        if (isSpeakingRaw) {
          speakingFrames++;
          silentFrames = 0;
        } else {
          silentFrames++;
          speakingFrames = 0;
        }

        let newStatus = statusRef.current;
        
        if (statusRef.current === 'active' && speakingFrames >= FRAMES_TO_START_SPEAKING) {
          newStatus = 'speaking';
        } else if (statusRef.current === 'speaking' && silentFrames >= FRAMES_TO_STOP_SPEAKING) {
          newStatus = 'active';
        }

        if (newStatus !== statusRef.current) {
          statusRef.current = newStatus;
          setStatus(newStatus);
        }

        animationId = requestAnimationFrame(monitor);
      };

      monitor();

    } catch (err) {
      console.warn("Audio Context init error:", err);
      if (statusRef.current !== 'active') {
        statusRef.current = 'active';
        setStatus('active');
      }
    }

    return () => {
      if (animationId) cancelAnimationFrame(animationId);
      if (source) source.disconnect();
      if (analyser) analyser.disconnect();
      if (audioContext && audioContext.state !== 'closed') {
        audioContext.close().catch(() => {});
      }
    };
  }, [stream, isMuted]);

  return status;
}
