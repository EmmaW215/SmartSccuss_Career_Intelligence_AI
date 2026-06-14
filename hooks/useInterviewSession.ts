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
  synthesizeForPlayback: (text: string) => Promise<string | undefined>;
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

      // NOTE: greeting TTS is NOT synthesized here — that would block startup on
      // a slow (up to 25s) synthesize call. The caller plays the greeting in the
      // background via synthesizeForPlayback(). audioUrl is intentionally omitted.
      return {
        sessionId: result.session_id,
        greeting: result.greeting,
        audioUrl: undefined,
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
   * other (status "pending" → report 400). This reuses the passed sessionId.
   * Greeting TTS is played in the background by the caller (not synthesized
   * here) so resume never blocks on a slow synthesize.
   */
  const resumeSession = useCallback(async (
    greeting: string,
    totalQuestions: number,
    _voiceEnabled: boolean
  ): Promise<StartInterviewResult> => {
    setIsLoading(true);
    setError(null);

    try {
      // Reuse the existing session id — no /start call, no blocking TTS.
      setCurrentSessionId(sessionId);
      return {
        sessionId,
        greeting,
        audioUrl: undefined,
        totalQuestions,
      };
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  /**
   * Synthesize speech for background playback (best-effort).
   * Returns a playable object URL, or undefined if TTS failed/timed out.
   * Used by the panel to play audio WITHOUT blocking the conversation turn.
   */
  const synthesizeForPlayback = useCallback(async (
    text: string
  ): Promise<string | undefined> => {
    try {
      const url = await synthesizeSpeech(text);
      return url || undefined;
    } catch (ttsError) {
      console.warn('TTS synthesis failed (background), continuing without audio:', ttsError);
      return undefined;
    }
  }, []);

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

      // NOTE: AI-response TTS is NOT synthesized here. Doing so awaited a
      // slow (up to 25s) synthesize INSIDE the turn, so the user waited on TTS
      // before the turn finished — and often got no audio anyway. The turn now
      // returns immediately with text; the caller plays audio in the background
      // via synthesizeForPlayback(). audioUrl is intentionally omitted.
      return {
        userTranscript,
        aiResponse: result.message,
        audioUrl: undefined,
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
    synthesizeForPlayback,
    sendResponse,
    endInterview,
    isLoading,
    error,
  };
};

export default useInterviewSession;
