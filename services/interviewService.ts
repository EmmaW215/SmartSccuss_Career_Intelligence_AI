/**
 * Interview Backend API Service
 * Handles all communication with the SmartSuccess Interview Backend
 */

import { InterviewType } from '../types';

// Get backend URL from environment or use default
// Vite injects process.env variables at build time via vite.config.ts
// In browser, detect localhost for development
const getBackendUrl = (): string => {
  // Check if we're in browser and on localhost (development)
  if (typeof window !== 'undefined') {
    const isLocalhost = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1';
    if (isLocalhost) {
      // Development: always use localhost backend when running locally
      return 'http://localhost:8000';
    }
  }
  
  // Production: use environment variable (injected by Vite at build time)
  // @ts-ignore - Vite replaces process.env.NEXT_PUBLIC_BACKEND_URL at build time
  const envUrl = typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_BACKEND_URL;
  if (envUrl && envUrl !== 'undefined' && envUrl !== 'null') {
    return envUrl;
  }
  
  // Fallback to Render production URL
  return 'https://smartsccuss-career-intelligence-ai.onrender.com';
};

const BACKEND_URL = getBackendUrl();

// Log backend URL for debugging (only in development)
if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
  console.log('🔗 Using backend URL:', BACKEND_URL);
}

// API Response Types
export interface StartSessionRequest {
  user_id: string;
  resume_text?: string;
  job_description?: string;
  matchwise_analysis?: Record<string, any>;
}

export interface StartSessionResponse {
  session_id: string;
  interview_type: string;
  greeting: string;
  duration_limit_minutes: number;
  max_questions: number;
}

export interface MessageRequest {
  session_id: string;
  message: string;
}

export interface MessageResponse {
  type: 'question' | 'completion' | 'error';
  message: string;
  question_number?: number;
  total_questions?: number;
  evaluation?: {
    score?: number;
    feedback?: string;
    strengths?: string[];
    improvements?: string[];
    star_scores?: {
      situation?: number;
      task?: number;
      action?: number;
      result?: number;
    };
    technical_scores?: {
      technical_accuracy?: number;
      depth_of_knowledge?: number;
      practical_experience?: number;
      system_thinking?: number;
      communication_clarity?: number;
    };
  };
  summary?: any;
}

export interface SessionInfo {
  session_id: string;
  user_id: string;
  interview_type: string;
  phase: string;
  current_question_index: number;
  total_questions: number;
  total_responses: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  star_scores?: Record<string, number>;
  scores?: Record<string, number>;
}

/**
 * Map frontend InterviewType to backend API path
 */
function getInterviewTypePath(type: InterviewType): string {
  const typeMap: Record<InterviewType, string> = {
    [InterviewType.SCREENING]: 'screening',
    [InterviewType.BEHAVIORAL]: 'behavioral',
    [InterviewType.TECHNICAL]: 'technical',
    [InterviewType.CUSTOMIZE]: 'screening', // Fallback to screening for customize
  };
  return typeMap[type] || 'screening';
}

/**
 * Start a new interview session
 */
export async function startInterviewSession(
  type: InterviewType,
  userId: string,
  resumeText?: string,
  jobDescription?: string
): Promise<StartSessionResponse> {
  const interviewType = getInterviewTypePath(type);
  const url = `${BACKEND_URL}/api/interview/${interviewType}/start`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId,
        resume_text: resumeText || undefined,
        job_description: jobDescription || undefined,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to start interview: ${response.status} ${errorText}`);
    }

    const data: StartSessionResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error starting interview session:', error);
    throw error;
  }
}

/**
 * Send a message in an interview session
 */
export async function sendInterviewMessage(
  type: InterviewType,
  sessionId: string,
  message: string
): Promise<MessageResponse> {
  const interviewType = getInterviewTypePath(type);
  const url = `${BACKEND_URL}/api/interview/${interviewType}/message`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        message: message,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to send message: ${response.status} ${errorText}`);
    }

    const data: MessageResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error sending interview message:', error);
    throw error;
  }
}

/**
 * Get session information
 */
export async function getInterviewSession(
  type: InterviewType,
  sessionId: string
): Promise<SessionInfo> {
  const interviewType = getInterviewTypePath(type);
  const url = `${BACKEND_URL}/api/interview/${interviewType}/session/${sessionId}`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get session: ${response.status} ${errorText}`);
    }

    const data: SessionInfo = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting interview session:', error);
    throw error;
  }
}

/**
 * Delete an interview session
 */
export async function deleteInterviewSession(
  type: InterviewType,
  sessionId: string
): Promise<void> {
  const interviewType = getInterviewTypePath(type);
  const url = `${BACKEND_URL}/api/interview/${interviewType}/session/${sessionId}`;

  try {
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to delete session: ${response.status} ${errorText}`);
    }
  } catch (error) {
    console.error('Error deleting interview session:', error);
    throw error;
  }
}

/**
 * Check if backend is available
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${BACKEND_URL}/health`, {
      method: 'GET',
    });
    return response.ok;
  } catch (error) {
    console.error('Backend health check failed:', error);
    return false;
  }
}
