/**
 * useAudioPlayer Hook
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
  const audioQueueRef = useRef<string[]>([]);

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

      // Play next in queue
      if (audioQueueRef.current.length > 0) {
        const nextUrl = audioQueueRef.current.shift();
        if (nextUrl) {
          playAudioInternal(nextUrl);
        }
      }
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
   * Play audio from URL
   */
  const playAudio = useCallback(async (url: string): Promise<void> => {
    const audio = audioRef.current;
    if (!audio) return;

    try {
      // If autoplay not allowed, queue and show message
      if (!canAutoPlay && autoPlay) {
        audioQueueRef.current.push(url);
        console.log('Autoplay blocked. Audio queued.');
        return;
      }

      await playAudioInternal(url);
    } catch (error) {
      console.error('Audio play error:', error);
      // Queue for later if blocked
      audioQueueRef.current.push(url);
      setCanAutoPlay(false);
      throw error;
    }
  }, [canAutoPlay, autoPlay]);

  /**
   * Stop audio playback
   */
  const stopAudio = useCallback(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
      setIsPlaying(false);
    }
    // Clear queue
    audioQueueRef.current = [];
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
