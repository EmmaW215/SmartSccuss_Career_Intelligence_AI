/**
 * useMicrophone Hook (Phase 2 + Web Speech API fallback)
 * Handles microphone detection, permission, recording, and browser STT fallback
 * 
 * During recording, Web Speech API runs in parallel as a fallback transcription
 * source in case GPU Whisper and OpenAI Whisper are both unavailable.
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
  webSpeechTranscript: string | null;
  webSpeechAvailable: boolean;
  checkMicrophone: () => Promise<MicrophoneStatus>;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<Blob>;
  cancelRecording: () => void;
}

// Check if Web Speech API is available
function checkWebSpeechSupport(): boolean {
  return !!(
    typeof window !== 'undefined' &&
    (window.SpeechRecognition || (window as any).webkitSpeechRecognition)
  );
}

// Get SpeechRecognition constructor
function getSpeechRecognition(): (new () => SpeechRecognition) | null {
  if (typeof window === 'undefined') return null;
  return window.SpeechRecognition || (window as any).webkitSpeechRecognition || null;
}

export const useMicrophone = (): UseMicrophoneReturn => {
  const [status, setStatus] = useState<MicrophoneStatus>({
    available: false,
    permissionGranted: false
  });
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [webSpeechTranscript, setWebSpeechTranscript] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const speechRecognitionRef = useRef<SpeechRecognition | null>(null);
  const webSpeechTextRef = useRef<string>('');

  const webSpeechAvailable = checkWebSpeechSupport();

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
            errorMessage = `Microphone error: ${(error as DOMException).message}`;
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
   * Start Web Speech API recognition in background (fallback STT)
   */
  const startWebSpeechRecognition = useCallback(() => {
    const SpeechRecognitionClass = getSpeechRecognition();
    if (!SpeechRecognitionClass) return;

    try {
      const recognition = new SpeechRecognitionClass();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      webSpeechTextRef.current = '';

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        let finalText = '';
        let interimText = '';

        for (let i = 0; i < event.results.length; i++) {
          const result = event.results[i];
          if (result.isFinal) {
            finalText += result[0].transcript;
          } else {
            interimText += result[0].transcript;
          }
        }

        webSpeechTextRef.current = (finalText + interimText).trim();
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        // Don't log 'no-speech' or 'aborted' as they're expected
        if (event.error !== 'no-speech' && event.error !== 'aborted') {
          console.warn('Web Speech API fallback error:', event.error);
        }
      };

      recognition.onend = () => {
        // Auto-restart if still recording (Web Speech API stops after silence)
        if (mediaRecorderRef.current && isRecording) {
          try {
            recognition.start();
          } catch {
            // Ignore restart errors
          }
        }
      };

      recognition.start();
      speechRecognitionRef.current = recognition;
      console.log('Web Speech API fallback started');

    } catch (error) {
      console.warn('Failed to start Web Speech API fallback:', error);
    }
  }, [isRecording]);

  /**
   * Stop Web Speech API recognition
   */
  const stopWebSpeechRecognition = useCallback(() => {
    if (speechRecognitionRef.current) {
      try {
        speechRecognitionRef.current.stop();
      } catch {
        // Ignore stop errors
      }
      speechRecognitionRef.current = null;
    }
    // Save the final transcript
    const transcript = webSpeechTextRef.current.trim();
    if (transcript) {
      setWebSpeechTranscript(transcript);
    }
    return transcript;
  }, []);

  /**
   * Start recording audio (with parallel Web Speech API fallback)
   */
  const startRecording = useCallback(async (): Promise<void> => {
    if (!status.available) {
      const check = await checkMicrophone();
      if (!check.available) {
        throw new Error(check.error || 'Microphone not available');
      }
    }

    // Reset fallback transcript
    setWebSpeechTranscript(null);
    webSpeechTextRef.current = '';

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

      // Start Web Speech API in parallel as fallback STT
      startWebSpeechRecognition();

    } catch (error) {
      throw new Error('Failed to start recording');
    }
  }, [status.available, checkMicrophone, startWebSpeechRecognition]);

  /**
   * Stop recording and return audio blob
   */
  const stopRecording = useCallback(async (): Promise<Blob> => {
    // Stop Web Speech API first to capture final transcript
    stopWebSpeechRecognition();

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
  }, [isRecording, stopWebSpeechRecognition]);

  /**
   * Cancel recording without returning data
   */
  const cancelRecording = useCallback(() => {
    // Stop Web Speech API
    stopWebSpeechRecognition();

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
    setWebSpeechTranscript(null);
  }, [isRecording, stopWebSpeechRecognition]);

  return {
    isMicAvailable: status.available,
    permissionGranted: status.permissionGranted,
    deviceName: status.deviceName,
    error: status.error,
    isRecording,
    audioBlob,
    webSpeechTranscript,
    webSpeechAvailable,
    checkMicrophone,
    startRecording,
    stopRecording,
    cancelRecording
  };
};

export default useMicrophone;
