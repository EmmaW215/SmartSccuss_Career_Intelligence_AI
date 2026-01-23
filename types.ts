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