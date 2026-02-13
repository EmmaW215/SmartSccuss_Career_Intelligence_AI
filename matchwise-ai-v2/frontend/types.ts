export interface ComparisonResponse {
  job_summary: string;
  resume_summary: string;
  match_score: number;
  tailored_resume_summary: string;
  tailored_work_experience: string[]; // API might return string HTML or array, we handle string in UI usually
  cover_letter: string;
}

export interface UserStatus {
  trialUsed: boolean;
  isUpgraded: boolean;
  planType: string | null;
  scanLimit: number | null;
  scansUsed: number;
  lastScanMonth: string;
}

export interface MessageHandler {
  showLoginModal?: (message?: string) => void;
  hideVisitorCounter?: () => void;
}
