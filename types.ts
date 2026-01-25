export type ViewState = 'landing' | 'interview' | 'dashboard' | 'demo' | 'lab' | 'sample-analysis';

export enum InterviewType {
  SCREENING = 'Screening Interview',
  BEHAVIORAL = 'Behavioral Interview',
  TECHNICAL = 'Technical Interview',
  CUSTOMIZE = 'Customize Interview',
}

export interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  isPro: boolean;
  type: 'guest' | 'registered';
}

export interface Message {
  id: string;
  role: 'user' | 'ai';
  content: string;
  timestamp: Date;
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
  questionNumber?: number;
  totalQuestions?: number;
}

export interface InterviewSession {
  id: string;
  type: InterviewType;
  date: string;
  score: number;
  duration: string;
}

export interface ChartDataPoint {
  subject: string;
  A: number;
  fullMark: number;
}

export interface PerformanceData {
  date: string;
  score: number;
}

// Dashboard API Response Types
export interface DashboardStats {
  user_id: string;
  total_interviews: number;
  completed_interviews: number;
  in_progress: number;
  by_type: Record<string, { total: number; completed: number }>;
  completion_rate: number;
}

export interface InterviewHistoryItem {
  session_id: string;
  interview_type: string;
  status: string;
  questions_answered: number;
  total_questions: number;
  voice_enabled: boolean;
  created_at: string;
  completed_at: string | null;
}

export interface DashboardHistory {
  user_id: string;
  total_interviews: number;
  interviews: InterviewHistoryItem[];
}

export interface SessionFeedback {
  session_id: string;
  interview_type: string;
  status: string;
  questions_answered: number;
  total_questions: number;
  responses: Array<{
    question_index: number;
    question: string;
    user_response: string;
    ai_response: string;
  }>;
  feedback_hints: Array<{
    quality?: 'good' | 'fair' | 'needs_improvement';
    hint?: string;
  }>;
  estimated_score?: {
    good_responses: number;
    fair_responses: number;
    needs_improvement: number;
    estimated_percentage: number;
  };
}

// ============================================
// Lab-specific types (AI Skills Lab)
// ============================================
import { LucideIcon } from 'lucide-react';

export type LabViewState = 'lab-dashboard' | 'lab-workspace' | 'lab-results';

export interface LabChallenge {
  id: string;
  title: string;
  category: string;
  difficulty: 'Basic' | 'Intermediate' | 'Advanced' | 'Expert';
  icon: LucideIcon;
  description: string;
  reward: string;
  initialFiles: LabFileNode[];
  timeLimit: number; // in minutes
  
  // Detailed Content
  scenario: string;
  requirements: string[];
  expectations: { aspect: string; expectation: string }[];
  minimumPass: string[];
  timeEstimate: string;
  
  // Evaluation / Post-Completion
  keyPoints: string[];
  expectedOutputs: string;
  qualificationCriteria: { level: string; criteria: string; score?: string }[];
}

export interface LabFileNode {
  id: string;
  name: string;
  language: string;
  content: string;
}

export interface LabChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export interface AssessmentResult {
  score: number;
  level: string;
  breakdown: {
    planning: number;
    promptEngineering: number;
    toolOrchestration: number;
    outcomeQuality: number;
  };
  strengths: string[];
  improvements: string[];
  summary: string;
}