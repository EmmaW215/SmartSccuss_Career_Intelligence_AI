/**
 * useAudioPlayer Hook (Phase 2)
 * Handles audio playback with auto-play support
 */

import { useState, useRef, useCallback, useEffect } from 'react';

interface UseAudioPlayerOptions {
  autoPlay?: boolean;
  onPlayStart?: () => void;
  onPlayEnd?: () => void;
  onError?: (error: Error) => void;
}

interface UseAudioPlayerReturn {
  isPlaying: boolean;
  duration: number;
  currentTime: number;
  volume: number;
  playAudio: (url: string) => Promise<void>;
  stopAudio: () => void;
  pauseAudio: () => void;
  resumeAudio: () => Promise<void>;
  setVolume: (volume: number) => void;
  canAutoPlay: boolean;
}

export const useAudioPlayer = (options: UseAudioPlayerOptions = {}): UseAudioPlayerReturn => {
  const { autoPlay = true, onPlayStart, onPlayEnd, onError } = options;

  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolumeState] = useState(1);
  const [canAutoPlay, setCanAutoPlay] = useState(true);

  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Initialize audio element
  useEffect(() => {
    const audio = new Audio();
    audioRef.current = audio;

    // Event handlers
    audio.onplay = () => {
      setIsPlaying(true);
      onPlayStart?.();
    };

    audio.onpause = () => {
      setIsPlaying(false);
    };

    audio.onended = () => {
      setIsPlaying(false);
      onPlayEnd?.();
      // NOTE: no auto-replay queue. Each clip is played once, latest-wins —
      // a queue here previously cascaded older clips back into playback
      // (the Voice-Mode "questions repeat on mic click" regression).
    };

    audio.ontimeupdate = () => {
      setCurrentTime(audio.currentTime);
    };

    audio.onloadedmetadata = () => {
      setDuration(audio.duration);
    };

    audio.onerror = (e) => {
      console.error('Audio playback error:', e);
      setIsPlaying(false);
      onError?.(new Error('Audio playback failed'));
    };

    // Check autoplay permission
    checkAutoPlayPermission().then(setCanAutoPlay);

    return () => {
      audio.pause();
      audio.src = '';
      audioRef.current = null;
    };
  }, []);

  /**
   * Check if browser allows autoplay
   */
  const checkAutoPlayPermission = async (): Promise<boolean> => {
    try {
      const audio = new Audio();
      audio.volume = 0;
      // Short silent audio
      audio.src = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA';
      
      await audio.play();
      audio.pause();
      return true;
    } catch {
      return false;
    }
  };

  /**
   * Internal play function
   */
  const playAudioInternal = async (url: string): Promise<void> => {
    const audio = audioRef.current;
    if (!audio) return;

    return new Promise((resolve, reject) => {
      audio.oncanplaythrough = async () => {
        try {
          await audio.play();
          resolve();
        } catch (err) {
          reject(err);
        }
      };

      audio.onerror = () => {
        reject(new Error('Failed to load audio'));
      };

      audio.src = url;
      audio.load();
    });
  };

  /**
   * Play audio from URL.
   *
   * Single-shot, latest-wins: always plays exactly this clip. If the browser
   * blocks autoplay, play() rejects and we rethrow so the caller can surface a
   * tap-to-play affordance. We do NOT queue the clip (a queue previously
   * cascaded older clips back into playback).
   */
  const playAudio = useCallback(async (url: string): Promise<void> => {
    const audio = audioRef.current;
    if (!audio) return;

    try {
      await playAudioInternal(url);
    } catch (error) {
      // Autoplay blocked / load interrupted — mark and rethrow; the caller
      // decides what to do (e.g. show a "play greeting" button).
      setCanAutoPlay(false);
      throw error;
    }
  }, []);

  /**
   * Stop audio playback. Also detaches the "ready" handler so the just-stopped
   * clip cannot be replayed: a leftover oncanplaythrough (from the last
   * playAudioInternal) would otherwise re-fire on a seek and call play() again.
   * The next playAudioInternal re-installs its own handler, so this is safe.
   */
  const stopAudio = useCallback(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.oncanplaythrough = null;
      setIsPlaying(false);
    }
  }, []);

  /**
   * Pause audio playback
   */
  const pauseAudio = useCallback(() => {
    audioRef.current?.pause();
    setIsPlaying(false);
  }, []);

  /**
   * Resume audio playback
   */
  const resumeAudio = useCallback(async (): Promise<void> => {
    const audio = audioRef.current;
    if (audio && audio.paused && audio.src) {
      try {
        await audio.play();
      } catch (error) {
        console.error('Resume error:', error);
        throw error;
      }
    }
  }, []);

  /**
   * Set volume (0-1)
   */
  const setVolume = useCallback((newVolume: number) => {
    const clampedVolume = Math.max(0, Math.min(1, newVolume));
    setVolumeState(clampedVolume);
    if (audioRef.current) {
      audioRef.current.volume = clampedVolume;
    }
  }, []);

  return {
    isPlaying,
    duration,
    currentTime,
    volume,
    playAudio,
    stopAudio,
    pauseAudio,
    resumeAudio,
    setVolume,
    canAutoPlay
  };
};

export default useAudioPlayer;
