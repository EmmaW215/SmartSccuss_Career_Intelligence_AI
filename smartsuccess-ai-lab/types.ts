import { LucideIcon } from 'lucide-react';

export interface Challenge {
  id: string;
  title: string;
  category: string;
  difficulty: 'Basic' | 'Intermediate' | 'Advanced' | 'Expert';
  icon: LucideIcon;
  description: string;
  reward: string;
  initialFiles: FileNode[];
  timeLimit: number; // in minutes
  
  // Detailed Content
  scenario: string;
  requirements: string[]; // List of requirement points
  expectations: { aspect: string; expectation: string }[];
  minimumPass: string[];
  timeEstimate: string;
  
  // Evaluation / Post-Completion
  keyPoints: string[];
  expectedOutputs: string; // File tree or description
  qualificationCriteria: { level: string; criteria: string; score?: string }[];
}

export interface FileNode {
  id: string;
  name: string;
  language: string;
  content: string;
}

export interface Message {
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

export type ViewState = 'dashboard' | 'workspace' | 'results';
