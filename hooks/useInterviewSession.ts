/**
 * useInterviewSession Hook
 * Manages interview session state and API communication
 * 
 * Adapted from Phase 2 to use main project's interviewService
 */

import { useState, useCallback } from 'react';
import { InterviewType } from '../types';
import {
  startInterviewSession,
  sendInterviewMessage,
  transcribeAudioWithFallback,
  synthesizeSpeech,
  uploadCustomizeInterviewFiles,
} from '../services/interviewService';

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
  resumeSession: (
    greeting: string,
    totalQuestions: number,
    voiceEnabled: boolean
  ) => Promise<StartInterviewResult>;
  sendResponse: (options: SendResponseOptions) => Promise<SendResponseResult>;
  endInterview: () => Promise<EndInterviewResult>;
  isLoading: boolean;
  error: string | null;
}

/**
 * Map voice panel interview type strings to main project's InterviewType enum
 */
function toInterviewType(
  type: 'screening' | 'behavioral' | 'technical' | 'customize'
): InterviewType {
  const map: Record<string, InterviewType> = {
    screening: InterviewType.SCREENING,
    behavioral: InterviewType.BEHAVIORAL,
    technical: InterviewType.TECHNICAL,
    customize: InterviewType.CUSTOMIZE,
  };
  return map[type] || InterviewType.SCREENING;
}

export const useInterviewSession = (
  sessionId: string,
  interviewType: 'screening' | 'behavioral' | 'technical' | 'customize'
): UseInterviewSessionReturn => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string>(sessionId);

  const type = toInterviewType(interviewType);

  /**
   * Start a new interview session
   */
  const startInterview = useCallback(async (
    options: StartInterviewOptions
  ): Promise<StartInterviewResult> => {
    setIsLoading(true);
    setError(null);

    try {
      // Upload files first for customize interview
      if (interviewType === 'customize' && options.customDocuments?.length) {
        await uploadCustomizeInterviewFiles(sessionId, options.customDocuments);
      }

      // Start interview session
      const result = await startInterviewSession(type, sessionId);

      setCurrentSessionId(result.session_id);

      // Synthesize greeting audio if voice enabled
      let audioUrl: string | undefined;
      if (options.voiceEnabled) {
        try {
          const url = await synthesizeSpeech(result.greeting);
          audioUrl = url || undefined;
        } catch (ttsError) {
          console.warn('TTS failed for greeting, continuing without audio:', ttsError);
        }
      }

      return {
        sessionId: result.session_id,
        greeting: result.greeting,
        audioUrl,
        totalQuestions: result.max_questions || 10,
      };

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start interview';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, interviewType, type]);

  /**
   * Resume an EXISTING session in Voice Mode without starting a new one.
   *
   * The parent (InterviewPage) already created the session and has the
   * greeting + question count. Calling startInterview() again here would issue
   * a second /start, producing a divergent backend session record — so the
   * interview completes on one session while the report/dashboard read the
   * other (status "pending" → report 400). This reuses the passed sessionId and
   * only synthesizes the greeting for playback.
   */
  const resumeSession = useCallback(async (
    greeting: string,
    totalQuestions: number,
    voiceEnabled: boolean
  ): Promise<StartInterviewResult> => {
    setIsLoading(true);
    setError(null);

    try {
      // Reuse the existing session id — no /start call.
      setCurrentSessionId(sessionId);

      let audioUrl: string | undefined;
      if (voiceEnabled) {
        try {
          const url = await synthesizeSpeech(greeting);
          audioUrl = url || undefined;
        } catch (ttsError) {
          console.warn('TTS failed for greeting (resume), continuing without audio:', ttsError);
        }
      }

      return {
        sessionId,
        greeting,
        audioUrl,
        totalQuestions,
      };
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

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

      // If audio, transcribe with fallback (GPU → OpenAI → Web Speech API)
      if (options.audio) {
        const transcription = await transcribeAudioWithFallback(options.audio);
        userTranscript = transcription.text;
      } else if (options.text) {
        userTranscript = options.text;
      } else {
        throw new Error('Either audio or text must be provided');
      }

      // Send response to get AI reply
      const result = await sendInterviewMessage(type, currentSessionId, userTranscript);

      // Synthesize AI response audio
      let audioUrl: string | undefined;
      if (result.message) {
        try {
          const url = await synthesizeSpeech(result.message);
          audioUrl = url || undefined;
        } catch (ttsError) {
          console.warn('TTS failed for response:', ttsError);
        }
      }

      return {
        userTranscript,
        aiResponse: result.message,
        audioUrl,
        feedbackHint: undefined, // Standard interviews don't have feedbackHint in same format
        currentQuestion: result.question_number || 0,
        totalQuestions: result.total_questions || 0,
        isComplete: result.is_complete || false,
      };

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to process response';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [currentSessionId, type]);

  /**
   * End interview early
   */
  const endInterview = useCallback(async (): Promise<EndInterviewResult> => {
    setIsLoading(true);
    setError(null);

    try {
      // Send "stop" message to end the interview
      const result = await sendInterviewMessage(type, currentSessionId, 'stop');

      return {
        closingMessage: result.message || 'Interview ended.',
        questionsAnswered: result.question_number || 0,
        totalQuestions: result.total_questions || 0,
      };

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to end interview';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [currentSessionId, type]);

  return {
    startInterview,
    resumeSession,
    sendResponse,
    endInterview,
    isLoading,
    error,
  };
};

export default useInterviewSession;
