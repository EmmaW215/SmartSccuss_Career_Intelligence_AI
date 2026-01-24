/**
 * Interview API Service
 * Handles all API communication with the backend
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface StartInterviewRequest {
  userId: string;
  userName?: string;
  voiceEnabled?: boolean;
  customDocuments?: File[];
}

interface StartInterviewResponse {
  sessionId: string;
  greeting: string;
  totalQuestions: number;
  voiceEnabled: boolean;
}

interface SubmitResponseResponse {
  aiResponse: string;
  tone: string;
  feedbackHint?: {
    hint: string;
    quality: 'good' | 'fair' | 'needs_improvement';
  };
  currentQuestion: number;
  totalQuestions: number;
  isComplete: boolean;
  sessionId: string;
}

interface EndInterviewResponse {
  closingMessage: string;
  questionsAnswered: number;
  totalQuestions: number;
}

interface TranscribeResponse {
  text: string;
  language: string;
  provider: string;
}

class InterviewApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Start a new interview
   */
  async startInterview(
    interviewType: string,
    request: StartInterviewRequest
  ): Promise<StartInterviewResponse> {
    // Handle customize interview with files
    if (interviewType === 'customize' && request.customDocuments?.length) {
      return this.startCustomizeInterview(request);
    }

    const response = await fetch(`${this.baseUrl}/api/interview/${interviewType}/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: request.userId,
        user_name: request.userName,
        voice_enabled: request.voiceEnabled
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to start interview');
    }

    const data = await response.json();
    return {
      sessionId: data.session_id,
      greeting: data.greeting,
      totalQuestions: data.total_questions,
      voiceEnabled: data.voice_enabled
    };
  }

  /**
   * Start customize interview with file upload
   */
  private async startCustomizeInterview(
    request: StartInterviewRequest
  ): Promise<StartInterviewResponse> {
    const formData = new FormData();
    formData.append('user_id', request.userId);
    
    if (request.userName) {
      formData.append('user_name', request.userName);
    }
    formData.append('voice_enabled', String(request.voiceEnabled ?? true));

    // Add files
    if (request.customDocuments) {
      request.customDocuments.forEach(file => {
        formData.append('files', file);
      });
    }

    const response = await fetch(`${this.baseUrl}/api/interview/customize/start-with-rag`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to start customize interview');
    }

    const data = await response.json();
    return {
      sessionId: data.session_id,
      greeting: data.greeting,
      totalQuestions: data.total_questions,
      voiceEnabled: data.voice_enabled
    };
  }

  /**
   * Submit a response
   */
  async submitResponse(
    sessionId: string,
    interviewType: string,
    userResponse: string
  ): Promise<SubmitResponseResponse> {
    let endpoint = `${this.baseUrl}/api/interview/${interviewType}/respond`;
    let body: string | FormData;
    let headers: HeadersInit = {};

    if (interviewType === 'customize') {
      const formData = new FormData();
      formData.append('session_id', sessionId);
      formData.append('user_response', userResponse);
      body = formData;
    } else {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify({
        session_id: sessionId,
        user_response: userResponse
      });
    }

    const response = await fetch(endpoint, {
      method: 'POST',
      headers,
      body
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to submit response');
    }

    const data = await response.json();
    return {
      aiResponse: data.ai_response,
      tone: data.tone || 'neutral',
      feedbackHint: data.feedback_hint,
      currentQuestion: data.current_question || 0,
      totalQuestions: data.total_questions || 0,
      isComplete: data.is_complete,
      sessionId: data.session_id
    };
  }

  /**
   * End interview early
   */
  async endInterview(
    sessionId: string,
    interviewType: string
  ): Promise<EndInterviewResponse> {
    const response = await fetch(
      `${this.baseUrl}/api/interview/${interviewType}/end?session_id=${sessionId}`,
      {
        method: 'POST'
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to end interview');
    }

    const data = await response.json();
    return {
      closingMessage: data.closing_message,
      questionsAnswered: data.questions_answered,
      totalQuestions: data.total_questions
    };
  }

  /**
   * Transcribe audio to text
   */
  async transcribeAudio(audioBlob: Blob): Promise<TranscribeResponse> {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');
    formData.append('language', 'en');

    const response = await fetch(`${this.baseUrl}/api/voice/transcribe`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to transcribe audio');
    }

    return response.json();
  }

  /**
   * Synthesize text to speech
   * Returns data URL for audio playback
   */
  async synthesizeSpeech(text: string, voice: string = 'professional'): Promise<string> {
    const response = await fetch(`${this.baseUrl}/api/voice/synthesize-url`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        text,
        voice,
        emotion: null
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to synthesize speech');
    }

    const data = await response.json();
    return data.audio_url;
  }

  /**
   * Check voice service status
   */
  async getVoiceStatus(): Promise<{
    voiceEnabled: boolean;
    tts: { available: boolean; provider: string };
    stt: { available: boolean; provider: string };
  }> {
    const response = await fetch(`${this.baseUrl}/api/voice/status`);
    
    if (!response.ok) {
      return {
        voiceEnabled: false,
        tts: { available: false, provider: 'none' },
        stt: { available: false, provider: 'none' }
      };
    }

    return response.json();
  }

  /**
   * Get dashboard data
   */
  async getDashboard(userId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/dashboard/history?user_id=${userId}`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch dashboard data');
    }

    return response.json();
  }
}

// Export singleton instance
export const interviewApi = new InterviewApiService();

export default interviewApi;
