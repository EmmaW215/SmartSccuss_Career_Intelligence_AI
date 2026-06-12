/**
 * AI Skills Lab Backend API Service
 * Server-side proxy for Lab generation/evaluation (/api/lab/*).
 * Replaces the browser-side Gemini client so no API key ships in the bundle.
 */

import { AssessmentResult } from '../types';

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

const MAX_MESSAGES = 30;
const MAX_MESSAGE_CHARS = 8000;
const MAX_FILES = 10;
const MAX_FILE_CHARS = 12000;

export interface LabChallengeContext {
  id: string;
  title: string;
  description: string;
}

/**
 * Generate an AI assistant reply for the Lab chat via the backend proxy.
 * Always resolves to a displayable string (errors become friendly messages),
 * matching the contract LabWorkspace previously had with the Gemini client.
 */
export async function generateLabResponse(
  userId: string,
  challenge: LabChallengeContext,
  messages: { role: string; content: string }[]
): Promise<string> {
  try {
    const payload = {
      user_id: userId,
      task_type: 'lab_chat',
      challenge_title: challenge.title,
      challenge_description: challenge.description?.slice(0, 4000),
      messages: messages.slice(-MAX_MESSAGES).map(m => ({
        role: m.role === 'assistant' || m.role === 'system' ? m.role : 'user',
        content: m.content.slice(0, MAX_MESSAGE_CHARS),
      })),
    };

    const response = await fetch(`${BACKEND_URL}/api/lab/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (response.status === 429) {
      return 'You are sending requests a bit too quickly — please wait a moment and try again.';
    }
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Lab generate failed:', response.status, errorText);
      return 'The Lab assistant is temporarily unavailable. Please try again in a moment.';
    }

    const data = await response.json();
    return data.response || 'No response generated. Please try again.';
  } catch (error) {
    console.error('Lab generate error:', error);
    return 'Error connecting to the Lab assistant. Please check your connection and try again.';
  }
}

/**
 * Evaluate a lab submission via the backend proxy.
 * The backend returns an AssessmentResult-compatible payload (with its own
 * server-side fallback), so this only needs a network-failure fallback.
 */
export async function evaluateLabSubmission(
  userId: string,
  challenge: LabChallengeContext,
  files: { name: string; content: string }[]
): Promise<AssessmentResult> {
  const fileMap: Record<string, string> = {};
  for (const file of files.slice(0, MAX_FILES)) {
    fileMap[file.name.slice(0, 128)] = (file.content || '').slice(0, MAX_FILE_CHARS);
  }

  try {
    const response = await fetch(`${BACKEND_URL}/api/lab/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        challenge_id: challenge.id,
        challenge_title: challenge.title,
        challenge_description: challenge.description?.slice(0, 4000),
        submission: '',
        files: fileMap,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to evaluate submission: ${response.status} ${errorText}`);
    }

    return (await response.json()) as AssessmentResult;
  } catch (error) {
    console.error('Lab evaluate error:', error);
    // Network-failure fallback: keep the results page functional.
    return {
      score: 0,
      level: 'Unscored',
      breakdown: { planning: 0, promptEngineering: 0, toolOrchestration: 0, outcomeQuality: 0 },
      strengths: [],
      improvements: ['Evaluation service was unreachable — please resubmit to get your score.'],
      summary:
        'Your submission was received, but the evaluation service could not be reached. Resubmit to get a real score.',
    };
  }
}
