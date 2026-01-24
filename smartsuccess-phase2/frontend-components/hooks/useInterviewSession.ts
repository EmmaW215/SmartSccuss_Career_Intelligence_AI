/**
 * useInterviewSession Hook
 * Manages interview session state and API communication
 */

import { useState, useCallback } from 'react';
import { interviewApi } from '../services/interviewApi';

interface StartInterviewOptions {
  userName?: string;
  voiceEnabled?: boolean;
  customDocuments?: File[];
}

interface StartInterviewResult {
  sessionId: string;
  greeting: string;
  audioUrl?: string;
  totalQuestions: number;
}

interface SendResponseOptions {
  audio?: Blob;
  text?: string;
}

interface SendResponseResult {
  userTranscript: string;
  aiResponse: string;
  audioUrl?: string;
  feedbackHint?: {
    hint: string;
    quality: 'good' | 'fair' | 'needs_improvement';
  };
  currentQuestion: number;
  totalQuestions: number;
  isComplete: boolean;
}

interface EndInterviewResult {
  closingMessage: string;
  questionsAnswered: number;
  totalQuestions: number;
}

interface UseInterviewSessionReturn {
  startInterview: (options: StartInterviewOptions) => Promise<StartInterviewResult>;
  sendResponse: (options: SendResponseOptions) => Promise<SendResponseResult>;
  endInterview: () => Promise<EndInterviewResult>;
  isLoading: boolean;
  error: string | null;
}

export const useInterviewSession = (
  sessionId: string,
  interviewType: 'screening' | 'behavioral' | 'technical' | 'customize'
): UseInterviewSessionReturn => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string>(sessionId);

  /**
   * Start a new interview session
   */
  const startInterview = useCallback(async (
    options: StartInterviewOptions
  ): Promise<StartInterviewResult> => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await interviewApi.startInterview(interviewType, {
        userId: sessionId, // Use sessionId as userId for now
        userName: options.userName,
        voiceEnabled: options.voiceEnabled ?? true,
        customDocuments: options.customDocuments
      });

      setCurrentSessionId(result.sessionId);

      // If voice enabled, get audio for greeting
      let audioUrl: string | undefined;
      if (options.voiceEnabled) {
        try {
          audioUrl = await interviewApi.synthesizeSpeech(result.greeting);
        } catch (ttsError) {
          console.warn('TTS failed, continuing without audio:', ttsError);
        }
      }

      return {
        sessionId: result.sessionId,
        greeting: result.greeting,
        audioUrl,
        totalQuestions: result.totalQuestions
      };

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start interview';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, interviewType]);

  /**
   * Send user response (voice or text)
   */
  const sendResponse = useCallback(async (
    options: SendResponseOptions
  ): Promise<SendResponseResult> => {
    setIsLoading(true);
    setError(null);

    try {
      let userTranscript: string;

      // If audio, transcribe first
      if (options.audio) {
        const transcription = await interviewApi.transcribeAudio(options.audio);
        userTranscript = transcription.text;
      } else if (options.text) {
        userTranscript = options.text;
      } else {
        throw new Error('Either audio or text must be provided');
      }

      // Send response to get AI reply
      const result = await interviewApi.submitResponse(
        currentSessionId,
        interviewType,
        userTranscript
      );

      // Get audio for AI response
      let audioUrl: string | undefined;
      try {
        audioUrl = await interviewApi.synthesizeSpeech(result.aiResponse);
      } catch (ttsError) {
        console.warn('TTS failed:', ttsError);
      }

      return {
        userTranscript,
        aiResponse: result.aiResponse,
        audioUrl,
        feedbackHint: result.feedbackHint,
        currentQuestion: result.currentQuestion,
        totalQuestions: result.totalQuestions,
        isComplete: result.isComplete
      };

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to process response';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [currentSessionId, interviewType]);

  /**
   * End interview early
   */
  const endInterview = useCallback(async (): Promise<EndInterviewResult> => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await interviewApi.endInterview(currentSessionId, interviewType);
      
      return {
        closingMessage: result.closingMessage,
        questionsAnswered: result.questionsAnswered,
        totalQuestions: result.totalQuestions
      };

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to end interview';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [currentSessionId, interviewType]);

  return {
    startInterview,
    sendResponse,
    endInterview,
    isLoading,
    error
  };
};

export default useInterviewSession;
