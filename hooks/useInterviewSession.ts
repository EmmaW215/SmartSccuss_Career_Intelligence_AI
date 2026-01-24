/**
 * useInterviewSession Hook (Phase 2 - Optional Enhancement)
 * Manages interview session state and API communication
 * 
 * Note: This is an optional enhancement. Existing InterviewPage uses interviewService directly.
 * This hook provides additional Phase 2 features like voice mode, feedback hints, etc.
 */

import { useState, useCallback } from 'react';
import { 
  startInterviewSession, 
  sendInterviewMessage,
  deleteInterviewSession,
  type MessageResponse 
} from '../services/interviewService';
import { InterviewType } from '../types';

interface StartInterviewOptions {
  userName?: string;
  voiceEnabled?: boolean;
  customDocuments?: File[];
  resumeText?: string;
  jobDescription?: string;
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
  sessionId: string | null,
  interviewType: InterviewType
): UseInterviewSessionReturn => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(sessionId);

  /**
   * Start a new interview session
   */
  const startInterview = useCallback(async (
    options: StartInterviewOptions
  ): Promise<StartInterviewResult> => {
    setIsLoading(true);
    setError(null);

    try {
      // Use existing interviewService
      const userId = `user_${Date.now()}`;
      const result = await startInterviewSession(
        interviewType,
        userId,
        options.resumeText,
        options.jobDescription
      );

      setCurrentSessionId(result.session_id);

      // If voice enabled, try to get audio for greeting (Phase 2 feature)
      let audioUrl: string | undefined;
      if (options.voiceEnabled) {
        try {
          // Try to synthesize greeting (Phase 2 - optional)
          const BACKEND_URL = typeof window !== 'undefined' && window.location.hostname === 'localhost'
            ? 'http://localhost:8000'
            : (process.env.NEXT_PUBLIC_BACKEND_URL || 'https://smartsccuss-career-intelligence-ai.onrender.com');
          
          const ttsResponse = await fetch(`${BACKEND_URL}/api/voice/synthesize-url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: result.greeting, voice: 'professional' })
          });
          
          if (ttsResponse.ok) {
            const ttsData = await ttsResponse.json();
            audioUrl = ttsData.audio_url;
          }
        } catch (ttsError) {
          console.warn('TTS failed, continuing without audio:', ttsError);
        }
      }

      return {
        sessionId: result.session_id,
        greeting: result.greeting,
        audioUrl,
        totalQuestions: result.max_questions
      };

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start interview';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [interviewType]);

  /**
   * Send user response (voice or text)
   */
  const sendResponse = useCallback(async (
    options: SendResponseOptions
  ): Promise<SendResponseResult> => {
    setIsLoading(true);
    setError(null);

    if (!currentSessionId) {
      throw new Error('No active session. Please start an interview first.');
    }

    try {
      let userTranscript: string;

      // If audio, transcribe first (Phase 2 feature)
      if (options.audio) {
        const BACKEND_URL = typeof window !== 'undefined' && window.location.hostname === 'localhost'
          ? 'http://localhost:8000'
          : (process.env.NEXT_PUBLIC_BACKEND_URL || 'https://smartsccuss-career-intelligence-ai.onrender.com');
        
        const formData = new FormData();
        formData.append('audio', options.audio, 'recording.webm');
        formData.append('language', 'en');
        
        const transcribeResponse = await fetch(`${BACKEND_URL}/api/voice/transcribe`, {
          method: 'POST',
          body: formData
        });
        
        if (!transcribeResponse.ok) {
          throw new Error('Failed to transcribe audio');
        }
        
        const transcribeData = await transcribeResponse.json();
        userTranscript = transcribeData.text;
      } else if (options.text) {
        userTranscript = options.text;
      } else {
        throw new Error('Either audio or text must be provided');
      }

      // Send response using existing interviewService
      const result: MessageResponse = await sendInterviewMessage(
        interviewType,
        currentSessionId,
        userTranscript
      );

      // Get audio for AI response (Phase 2 feature)
      let audioUrl: string | undefined;
      try {
        const BACKEND_URL = typeof window !== 'undefined' && window.location.hostname === 'localhost'
          ? 'http://localhost:8000'
          : (process.env.NEXT_PUBLIC_BACKEND_URL || 'https://smartsccuss-career-intelligence-ai.onrender.com');
        
        const ttsResponse = await fetch(`${BACKEND_URL}/api/voice/synthesize-url`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: result.message, voice: 'professional' })
        });
        
        if (ttsResponse.ok) {
          const ttsData = await ttsResponse.json();
          audioUrl = ttsData.audio_url;
        }
      } catch (ttsError) {
        console.warn('TTS failed:', ttsError);
      }

      return {
        userTranscript,
        aiResponse: result.message,
        audioUrl,
        feedbackHint: result.evaluation ? {
          hint: result.evaluation.feedback || '',
          quality: result.evaluation.score && result.evaluation.score >= 4 ? 'good' :
                   result.evaluation.score && result.evaluation.score >= 3 ? 'fair' : 'needs_improvement'
        } : undefined,
        currentQuestion: result.question_number || 0,
        totalQuestions: result.total_questions || 0,
        isComplete: result.type === 'completion'
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

    if (!currentSessionId) {
      throw new Error('No active session');
    }

    try {
      // Delete session using existing service
      await deleteInterviewSession(interviewType, currentSessionId);
      
      return {
        closingMessage: 'Interview ended. Thank you for your time!',
        questionsAnswered: 0,
        totalQuestions: 0
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
