/**
 * Interview Backend API Service
 * Handles all communication with the SmartSuccess Interview Backend
 */

import { InterviewType, DashboardStats, DashboardHistory, SessionFeedback } from '../types';

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
  is_complete?: boolean;
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
    [InterviewType.CUSTOMIZE]: 'customize', // Use customize API endpoint
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
    // Customize Interview uses different request format
    let requestBody: any;
    if (type === InterviewType.CUSTOMIZE) {
      requestBody = {
        user_id: userId,
        user_name: undefined, // Can be added later if needed
        voice_enabled: false, // Can be enabled later if needed
      };
    } else {
      requestBody = {
        user_id: userId,
        resume_text: resumeText || undefined,
        job_description: jobDescription || undefined,
      };
    }

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to start interview: ${response.status} ${errorText}`);
    }

    const data: StartSessionResponse = await response.json();
    
    // Normalize response format for Customize Interview
    if (type === InterviewType.CUSTOMIZE) {
      return {
        session_id: data.session_id,
        interview_type: data.interview_type || 'customize',
        greeting: data.greeting,
        duration_limit_minutes: 45, // Customize interview duration
        max_questions: data.total_questions || 10, // Use total_questions from customize response
      };
    }
    
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
  
  // Customize Interview uses different endpoint and format
  let url: string;
  let requestBody: any;
  
  if (type === InterviewType.CUSTOMIZE) {
    url = `${BACKEND_URL}/api/interview/customize/respond`;
    requestBody = {
      session_id: sessionId,
      user_response: message,
    };
  } else {
    url = `${BACKEND_URL}/api/interview/${interviewType}/message`;
    requestBody = {
      session_id: sessionId,
      message: message,
    };
  }

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to send message: ${response.status} ${errorText}`);
    }

    const data: any = await response.json();
    
    // Normalize Customize Interview response format
    if (type === InterviewType.CUSTOMIZE) {
      return {
        type: data.is_complete ? 'completion' : 'question',
        message: data.ai_response || data.message || '',
        question_number: data.current_question || data.question_number,
        total_questions: data.total_questions,
        is_complete: data.is_complete || false,
        evaluation: undefined, // Customize interview may not have evaluation yet
        summary: data.is_complete ? data : undefined,
      };
    }
    
    return data as MessageResponse;
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
  
  // Customize Interview may use different endpoint or may not have delete endpoint
  // For now, try the standard endpoint, but don't fail if it doesn't exist
  let url: string;
  if (type === InterviewType.CUSTOMIZE) {
    // Customize interview uses dashboard API for deletion
    url = `${BACKEND_URL}/api/dashboard/session/${sessionId}`;
  } else {
    url = `${BACKEND_URL}/api/interview/${interviewType}/session/${sessionId}`;
  }

  try {
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // For Customize Interview, 404 is acceptable (session may not exist in Phase 2 store)
    if (!response.ok && type === InterviewType.CUSTOMIZE && response.status === 404) {
      console.log('Customize session not found (may have been cleaned up)');
      return;
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to delete session: ${response.status} ${errorText}`);
    }
  } catch (error) {
    // For Customize Interview, log but don't throw (session may not exist)
    if (type === InterviewType.CUSTOMIZE) {
      console.log('Error deleting customize session (non-critical):', error);
      return;
    }
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

/**
 * Voice API Functions
 */

/**
 * Transcribe audio to text using backend API
 */
export interface TranscribeResponse {
  text: string;
  language: string;
  provider: string;
}

export async function transcribeAudio(
  audioBlob: Blob,
  language: string = 'en'
): Promise<TranscribeResponse> {
  const url = `${BACKEND_URL}/api/voice/transcribe`;
  
  // Convert Blob to File for FormData
  // Determine file extension based on blob type
  let filename = 'recording.webm';
  let mimeType = audioBlob.type || 'audio/webm';
  
  if (mimeType.includes('webm')) {
    filename = 'recording.webm';
  } else if (mimeType.includes('mp4') || mimeType.includes('m4a')) {
    filename = 'recording.m4a';
  } else if (mimeType.includes('wav')) {
    filename = 'recording.wav';
  } else if (mimeType.includes('ogg')) {
    filename = 'recording.ogg';
  }
  
  const audioFile = new File([audioBlob], filename, { type: mimeType });
  
  const formData = new FormData();
  formData.append('audio', audioFile);
  formData.append('language', language);
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to transcribe audio: ${response.status} ${errorText}`);
    }

    const data: TranscribeResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error transcribing audio:', error);
    throw error;
  }
}

/**
 * Dashboard API Functions
 */

/**
 * Get user's interview statistics
 */
export async function getDashboardStats(userId: string): Promise<DashboardStats> {
  const url = `${BACKEND_URL}/api/dashboard/stats/${userId}`;
  
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get dashboard stats: ${response.status} ${errorText}`);
    }

    const data: DashboardStats = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting dashboard stats:', error);
    throw error;
  }
}

/**
 * Get user's interview history
 */
export async function getDashboardHistory(
  userId: string,
  limit: number = 10,
  status?: string
): Promise<DashboardHistory> {
  const params = new URLSearchParams();
  if (limit) params.append('limit', limit.toString());
  if (status) params.append('status', status);
  
  const url = `${BACKEND_URL}/api/dashboard/history/${userId}?${params.toString()}`;
  
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get dashboard history: ${response.status} ${errorText}`);
    }

    const data: DashboardHistory = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting dashboard history:', error);
    throw error;
  }
}

/**
 * Get detailed feedback for a specific session
 */
export async function getSessionFeedback(sessionId: string): Promise<SessionFeedback> {
  const url = `${BACKEND_URL}/api/dashboard/session/${sessionId}/feedback`;
  
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get session feedback: ${response.status} ${errorText}`);
    }

    const data: SessionFeedback = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting session feedback:', error);
    throw error;
  }
}

/**
 * Upload files for Customize Interview
 */
export interface UploadFilesResponse {
  success: boolean;
  user_id: string;
  files_processed: number;
  profile?: Record<string, any>;
  selected_questions?: Array<any>;
  rag_id?: string;
}

/**
 * Interview Report
 */
export interface InterviewReport {
  session_id: string;
  user_id: string;
  interview_type: string;
  completed_at: string | null;
  duration_minutes: number | null;
  questions_answered: number;
  total_questions: number;
  conversation_history: Array<{
    question_index: number;
    question: string;
    user_response: string;
    ai_response: string;
    timestamp?: string;
  }>;
  responses_summary: Array<{
    question: string;
    user_response_length: number;
    has_feedback: boolean;
  }>;
  feedback_analysis: {
    good_responses: number;
    fair_responses: number;
    needs_improvement: number;
    overall_score: number;
  };
  strengths: string[];
  areas_for_improvement: string[];
  recommendations: string[];
}

export async function uploadCustomizeInterviewFiles(
  userId: string,
  files: File[]
): Promise<UploadFilesResponse> {
  const url = `${BACKEND_URL}/api/interview/customize/upload`;
  
  try {
    const formData = new FormData();
    formData.append('user_id', userId);
    
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to upload files: ${response.status} ${errorText}`);
    }

    const data: UploadFilesResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error uploading files:', error);
    throw error;
  }
}

/**
 * Get interview report for a completed session
 */
export async function getInterviewReport(sessionId: string): Promise<InterviewReport> {
  const url = `${BACKEND_URL}/api/dashboard/session/${sessionId}/report`;
  
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get interview report: ${response.status} ${errorText}`);
    }

    const data: InterviewReport = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting interview report:', error);
    throw error;
  }
}
