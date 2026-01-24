/**
 * useMicrophone Hook (Phase 2)
 * Handles microphone detection, permission, and recording
 */

import { useState, useCallback, useRef } from 'react';

interface MicrophoneStatus {
  available: boolean;
  permissionGranted: boolean;
  deviceName?: string;
  error?: string;
}

interface UseMicrophoneReturn {
  isMicAvailable: boolean;
  permissionGranted: boolean;
  deviceName?: string;
  error?: string;
  isRecording: boolean;
  audioBlob: Blob | null;
  checkMicrophone: () => Promise<MicrophoneStatus>;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<Blob>;
  cancelRecording: () => void;
}

export const useMicrophone = (): UseMicrophoneReturn => {
  const [status, setStatus] = useState<MicrophoneStatus>({
    available: false,
    permissionGranted: false
  });
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  /**
   * Check if microphone is available and request permission
   */
  const checkMicrophone = useCallback(async (): Promise<MicrophoneStatus> => {
    try {
      // Check browser support
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        const errorStatus: MicrophoneStatus = {
          available: false,
          permissionGranted: false,
          error: 'Browser does not support microphone access'
        };
        setStatus(errorStatus);
        return errorStatus;
      }

      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      // Get device info
      const devices = await navigator.mediaDevices.enumerateDevices();
      const audioDevice = devices.find(d => d.kind === 'audioinput');

      // Stop test stream
      stream.getTracks().forEach(track => track.stop());

      const successStatus: MicrophoneStatus = {
        available: true,
        permissionGranted: true,
        deviceName: audioDevice?.label || 'Microphone'
      };
      setStatus(successStatus);
      return successStatus;

    } catch (error) {
      let errorMessage = 'Microphone access denied';
      
      if (error instanceof DOMException) {
        switch (error.name) {
          case 'NotAllowedError':
            errorMessage = 'Microphone permission denied. Please allow access in browser settings.';
            break;
          case 'NotFoundError':
            errorMessage = 'No microphone found. Please connect a microphone.';
            break;
          case 'NotReadableError':
            errorMessage = 'Microphone is in use by another application.';
            break;
          default:
            errorMessage = `Microphone error: ${error.message}`;
        }
      }

      const errorStatus: MicrophoneStatus = {
        available: false,
        permissionGranted: false,
        error: errorMessage
      };
      setStatus(errorStatus);
      return errorStatus;
    }
  }, []);

  /**
   * Start recording audio
   */
  const startRecording = useCallback(async (): Promise<void> => {
    if (!status.available) {
      const check = await checkMicrophone();
      if (!check.available) {
        throw new Error(check.error || 'Microphone not available');
      }
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000
        }
      });

      streamRef.current = stream;
      chunksRef.current = [];

      // Determine supported MIME type
      let mimeType = 'audio/webm;codecs=opus';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/webm';
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = 'audio/mp4';
        }
      }

      const mediaRecorder = new MediaRecorder(stream, { mimeType });

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event);
        setIsRecording(false);
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(100); // Collect data every 100ms
      setIsRecording(true);

    } catch (error) {
      throw new Error('Failed to start recording');
    }
  }, [status.available, checkMicrophone]);

  /**
   * Stop recording and return audio blob
   */
  const stopRecording = useCallback(async (): Promise<Blob> => {
    return new Promise((resolve, reject) => {
      if (!mediaRecorderRef.current || !isRecording) {
        reject(new Error('No recording in progress'));
        return;
      }

      const mediaRecorder = mediaRecorderRef.current;

      mediaRecorder.onstop = () => {
        // Create blob from chunks
        const mimeType = mediaRecorder.mimeType || 'audio/webm';
        const blob = new Blob(chunksRef.current, { type: mimeType });
        
        setAudioBlob(blob);
        setIsRecording(false);

        // Stop all tracks
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }

        // Cleanup
        mediaRecorderRef.current = null;
        chunksRef.current = [];

        resolve(blob);
      };

      mediaRecorder.stop();
    });
  }, [isRecording]);

  /**
   * Cancel recording without returning data
   */
  const cancelRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    mediaRecorderRef.current = null;
    chunksRef.current = [];
    setIsRecording(false);
  }, [isRecording]);

  return {
    isMicAvailable: status.available,
    permissionGranted: status.permissionGranted,
    deviceName: status.deviceName,
    error: status.error,
    isRecording,
    audioBlob,
    checkMicrophone,
    startRecording,
    stopRecording,
    cancelRecording
  };
};

export default useMicrophone;
