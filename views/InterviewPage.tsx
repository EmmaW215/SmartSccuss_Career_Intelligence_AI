import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, RefreshCw, Send, Play, Square, AlertCircle, Bot, LogIn, Lock, CheckCircle, User, Crown, Star, TrendingUp, Upload, X, FileText, XCircle } from 'lucide-react';
import { InterviewType, Message } from '../types';
import SimpleVisitorCounter from '../components/SimpleVisitorCounter';
import { FileUploader } from '../components/interview/FileUploader';
import { useMicrophone } from '../hooks/useMicrophone';
import { 
  startInterviewSession, 
  sendInterviewMessage, 
  deleteInterviewSession,
  checkBackendHealth,
  uploadCustomizeInterviewFiles,
  transcribeAudio,
  getInterviewReport,
  type MessageResponse,
  type InterviewReport
} from '../services/interviewService';
import { useAuth } from '../contexts/AuthContext';

// Phase 2: Optional hooks (only used if available)
// Note: Hooks are imported dynamically when needed, not at module level
// This prevents build errors if hooks are not available

interface InterviewPageProps {
  interviewType: InterviewType;
  onNavigateToDashboard: () => void;
}

export const InterviewPage: React.FC<InterviewPageProps> = ({ interviewType, onNavigateToDashboard }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [backendAvailable, setBackendAvailable] = useState<boolean>(true);
  const [currentQuestionNumber, setCurrentQuestionNumber] = useState<number>(0);
  const [totalQuestions, setTotalQuestions] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [isInterviewComplete, setIsInterviewComplete] = useState(false);
  const [interviewReport, setInterviewReport] = useState<InterviewReport | null>(null);
  const [showReport, setShowReport] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // File upload state (for Customize Interview)
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ id: string; name: string; size: number; type: string; file: File }>>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [showFileUploader, setShowFileUploader] = useState(false);
  const [filesUploaded, setFilesUploaded] = useState(false);
  
  // Microphone hook for voice recording
  const {
    isMicAvailable,
    permissionGranted,
    deviceName,
    error: micError,
    isRecording,
    checkMicrophone,
    startRecording: startMicRecording,
    stopRecording: stopMicRecording,
    cancelRecording: cancelMicRecording
  } = useMicrophone();
  
  const { user, login, isAuthenticated, isLoading, isPro, triggerLogin, triggerUpgrade } = useAuth();

  // Show login prompt if not authenticated (similar to Dashboard)
  if (!isAuthenticated) {
    return (
      <div className="h-full overflow-y-auto bg-gray-50/50 p-8 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Please Login</h2>
          <p className="text-gray-600 mb-6">You need to be logged in to initiate your Mock Interview.</p>
          <button
            onClick={triggerLogin}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Login
          </button>
        </div>
      </div>
    );
  }

  // Initialize interview session when component mounts or interview type changes
  useEffect(() => {

    const initializeSession = async () => {
      try {
        setError(null);
        setIsProcessing(true);
        
        // Check backend health first
        const isHealthy = await checkBackendHealth();
        if (!isHealthy) {
          setBackendAvailable(false);
          setError('Backend service is not available. Please ensure the backend server is running.');
          setIsProcessing(false);
          return;
        }
        setBackendAvailable(true);

        // Start new interview session
        const userId = user?.id || `user_${Date.now()}`;
        const response = await startInterviewSession(
          interviewType,
          userId,
          undefined, // resume_text - can be added later
          undefined  // job_description - can be added later
        );

        setSessionId(response.session_id);
        setTotalQuestions(response.max_questions);
        setCurrentQuestionNumber(1);

        // Add greeting message
        const greetingMsg: Message = {
          id: 'greeting',
          role: 'ai',
          content: response.greeting,
          timestamp: new Date(),
          questionNumber: 1,
          totalQuestions: response.max_questions
        };

        setMessages([greetingMsg]);
      } catch (error: any) {
        console.error('Failed to initialize interview session:', error);
        setError(error.message || 'Failed to start interview. Please try again.');
        setBackendAvailable(false);
      } finally {
        setIsProcessing(false);
      }
    };

    initializeSession();

    // Cleanup: delete session when component unmounts or interview type changes
    return () => {
      // Note: sessionId will be captured from the closure, but we need to check it
      // The actual cleanup will happen when sessionId changes (see separate useEffect)
    };
  }, [interviewType, isAuthenticated, user?.id]);

  // Check microphone availability on mount (optional, non-blocking)
  useEffect(() => {
    if (isAuthenticated) {
      checkMicrophone().catch(err => {
        // Don't show error to user unless they try to use it
        console.warn('Microphone check failed:', err);
      });
    }
  }, [isAuthenticated, checkMicrophone]);

  // Cleanup session when component unmounts or interview type changes
  useEffect(() => {
    return () => {
      if (sessionId) {
        deleteInterviewSession(interviewType, sessionId).catch(console.error);
      }
    };
  }, [sessionId, interviewType]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const checkAccess = () => {
    if (!isAuthenticated) {
        triggerLogin();
        return false;
    }
    return true;
  };

  const handleSend = async () => {
    if (!checkAccess()) return;
    if (!input.trim()) return;
    if (!sessionId) {
      setError('Session not initialized. Please refresh the page.');
      return;
    }

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsProcessing(true);
    setError(null);

    try {
      const response: MessageResponse = await sendInterviewMessage(
        interviewType,
        sessionId,
        userMsg.content
      );

      // Update question number if provided
      if (response.question_number) {
        setCurrentQuestionNumber(response.question_number);
      }
      if (response.total_questions) {
        setTotalQuestions(response.total_questions);
      }

      // Create AI message with evaluation data
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: response.message,
        timestamp: new Date(),
        evaluation: response.evaluation,
        questionNumber: response.question_number,
        totalQuestions: response.total_questions
      };

      setMessages(prev => [...prev, aiMsg]);
      speak(response.message);

      // Handle interview completion
      if (response.type === 'completion' || response.is_complete) {
        setIsInterviewComplete(true);
        
        // Interview completed
        const completionMsg: Message = {
          id: `completion-${Date.now()}`,
          role: 'ai',
          content: response.message || 'Thank you for completing the interview! Your feedback report is being generated.',
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, completionMsg]);
        
        // Fetch and display report
        if (sessionId) {
          try {
            setIsProcessing(true); // Show loading state
            const report = await getInterviewReport(sessionId);
            setInterviewReport(report);
            setShowReport(true);
          } catch (reportError: any) {
            console.error('Failed to fetch report:', reportError);
            // Show user-friendly error message
            setError(`Failed to generate report: ${reportError.message || 'Please try again later.'}`);
          } finally {
            setIsProcessing(false);
          }
        }
        
        // Show completion notification
        if (response.summary) {
          console.log('Interview completed:', response.summary);
        }
      }

    } catch (error: any) {
      console.error("Interview error", error);
      setError(error.message || 'Failed to send message. Please try again.');
      
      // Add error message to chat
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        role: 'ai',
        content: 'I apologize, but I encountered an error processing your response. Please try again or refresh the page.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsProcessing(false);
    }
  };

  // Real Speech-to-Text with microphone recording
  const toggleRecording = async () => {
    if (!checkAccess()) return;

    // Special check for Customize Interview + Voice Input
    if (interviewType === InterviewType.CUSTOMIZE && !isPro) {
        triggerUpgrade();
        return;
    }

    try {
      if (isRecording) {
        // Stop recording
        setIsProcessing(true);
        setError(null);
        
        try {
          // Stop microphone recording and get audio blob
          const audioBlob = await stopMicRecording();
          
          // Check if audio blob is valid
          if (!audioBlob || audioBlob.size === 0) {
            throw new Error('No audio recorded. Please try again.');
          }
          
          // Transcribe audio to text
          const transcribeResult = await transcribeAudio(audioBlob, 'en');
          const transcribedText = transcribeResult.text.trim();
          
          if (transcribedText && transcribedText.length > 0) {
            // Set transcribed text to input field
            setInput(transcribedText);
            
            // Optional: You can uncomment this to auto-send after transcription
            // await handleSend();
          } else {
            setError('No speech detected. Please try speaking again.');
          }
        } catch (transcribeError: any) {
          console.error('Transcription error:', transcribeError);
          
          // Provide user-friendly error messages
          if (transcribeError.message.includes('Failed to fetch') || transcribeError.message.includes('NetworkError')) {
            setError('Network error. Please check your connection and try again.');
          } else if (transcribeError.message.includes('503') || transcribeError.message.includes('not available')) {
            setError('Voice service is temporarily unavailable. Please try typing your response instead.');
          } else {
            setError(transcribeError.message || 'Failed to transcribe audio. Please try typing your response.');
          }
        } finally {
          setIsProcessing(false);
        }
      } else {
        // Start recording
        setError(null);
        
        try {
          // Check microphone availability first
          const micStatus = await checkMicrophone();
          
          if (!micStatus.available || !micStatus.permissionGranted) {
            let errorMessage = micStatus.error || 'Microphone not available.';
            
            // Provide helpful guidance based on error type
            if (micStatus.error?.includes('permission denied') || micStatus.error?.includes('NotAllowedError')) {
              errorMessage = 'Microphone permission denied. Please allow microphone access in your browser settings and refresh the page.';
            } else if (micStatus.error?.includes('No microphone found') || micStatus.error?.includes('NotFoundError')) {
              errorMessage = 'No microphone found. Please connect a microphone and try again.';
            } else if (micStatus.error?.includes('in use') || micStatus.error?.includes('NotReadableError')) {
              errorMessage = 'Microphone is in use by another application. Please close other applications using the microphone.';
            }
            
            setError(errorMessage);
            return;
          }
          
          // Start recording
          await startMicRecording();
        } catch (recordingError: any) {
          console.error('Recording start error:', recordingError);
          setError(recordingError.message || 'Failed to start recording. Please try again.');
        }
      }
    } catch (error: any) {
      console.error('Recording toggle error:', error);
      setError(error.message || 'An error occurred. Please try again.');
      setIsProcessing(false);
      
      // Cancel recording if it was started
      if (isRecording) {
        cancelMicRecording();
      }
    }
  };

  // Text-to-Speech
  const speak = (text: string) => {
    if (!checkAccess()) return;

    if ('speechSynthesis' in window) {
      setIsSpeaking(true);
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.onend = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    }
  };

  // Handle file upload for Customize Interview
  const handleFilesChange = (files: Array<{ id: string; name: string; size: number; type: string; file: File }>) => {
    setUploadedFiles(files);
  };

  const handleUploadFiles = async () => {
    if (!user?.id || uploadedFiles.length === 0) return;

    try {
      setIsUploading(true);
      setError(null);

      const fileObjects = uploadedFiles.map(f => f.file);
      const result = await uploadCustomizeInterviewFiles(user.id, fileObjects);

      if (result.success) {
        setFilesUploaded(true);
        setShowFileUploader(false);
        
        // Add success message
        const successMsg: Message = {
          id: `upload-success-${Date.now()}`,
          role: 'ai',
          content: `✅ Successfully uploaded ${result.files_processed} file(s)! Your interview has been personalized based on your documents. You can now proceed with the interview.`,
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, successMsg]);
      }
    } catch (error: any) {
      console.error('Error uploading files:', error);
      setError(error.message || 'Failed to upload files. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handlePracticeAgain = async () => {
    if (!checkAccess()) return;
    
    try {
      // Delete old session
      if (sessionId) {
        await deleteInterviewSession(interviewType, sessionId);
      }

      // Reset state
      setMessages([]);
      setSessionId(null);
      setCurrentQuestionNumber(0);
      setTotalQuestions(0);
      setError(null);
      setUploadedFiles([]);
      setFilesUploaded(false);
      setShowFileUploader(false);
      setIsInterviewComplete(false);
      setInterviewReport(null);
      setShowReport(false);

      // Reinitialize session
      const userId = user?.id || `user_${Date.now()}`;
      const response = await startInterviewSession(interviewType, userId);
      
      setSessionId(response.session_id);
      setTotalQuestions(response.max_questions);
      setCurrentQuestionNumber(1);

      const greetingMsg: Message = {
        id: 'greeting',
        role: 'ai',
        content: response.greeting,
        timestamp: new Date(),
        questionNumber: 1,
        totalQuestions: response.max_questions
      };

      setMessages([greetingMsg]);
    } catch (error: any) {
      console.error('Failed to restart interview:', error);
      setError('Failed to restart interview. Please refresh the page.');
    }
  };

  const handleNavigateToAnalytics = () => {
    if (!checkAccess()) return;
    onNavigateToDashboard();
  };

  // Helper for button appearance
  const getStatusButtonConfig = () => {
    if (isLoading) {
        return {
            text: 'Loading...',
            icon: <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>,
            className: 'bg-gray-400 text-white cursor-wait',
            disabled: true,
            onClick: undefined
        };
    }

    if (!isAuthenticated) {
        return {
            text: 'Guest user Login/Sign up',
            icon: <LogIn size={16} />,
            className: 'bg-blue-600 text-white hover:bg-blue-700 shadow-md',
            disabled: false,
            onClick: login
        };
    }

    if (isPro) {
        return {
            text: 'Pro Connected',
            icon: <Crown size={16} />,
            className: 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-md cursor-default',
            disabled: true,
            onClick: undefined
        };
    }

    return {
        text: 'User Connected',
        icon: <CheckCircle size={16} />,
        className: 'bg-green-50 text-green-700 border border-green-200 shadow-none cursor-default',
        disabled: true,
        onClick: undefined
    };
  };

  // Render evaluation feedback
  const renderEvaluation = (evaluation: Message['evaluation']) => {
    if (!evaluation) return null;

    return (
      <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
        {evaluation.score !== undefined && (
          <div className="flex items-center gap-2 text-xs">
            <TrendingUp size={12} className="text-blue-500" />
            <span className="font-medium text-gray-700">Score: {evaluation.score.toFixed(1)}/5.0</span>
          </div>
        )}

        {evaluation.star_scores && (
          <div className="grid grid-cols-4 gap-2 text-xs">
            {Object.entries(evaluation.star_scores).map(([key, value]) => (
              <div key={key} className="flex items-center gap-1">
                <Star size={10} className="text-yellow-500 fill-yellow-500" />
                <span className="text-gray-600 capitalize">{key}:</span>
                <span className="font-medium text-gray-800">{value}/5</span>
              </div>
            ))}
          </div>
        )}

        {evaluation.technical_scores && (
          <div className="space-y-1 text-xs">
            {Object.entries(evaluation.technical_scores).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-gray-600 capitalize">{key.replace(/_/g, ' ')}:</span>
                <span className="font-medium text-gray-800">{value}/5</span>
              </div>
            ))}
          </div>
        )}

        {evaluation.feedback && (
          <div className="text-xs text-gray-600 italic">
            {evaluation.feedback}
          </div>
        )}

        {evaluation.strengths && evaluation.strengths.length > 0 && (
          <div className="text-xs">
            <span className="font-medium text-green-700">Strengths: </span>
            <span className="text-gray-600">{evaluation.strengths.join(', ')}</span>
          </div>
        )}

        {evaluation.improvements && evaluation.improvements.length > 0 && (
          <div className="text-xs">
            <span className="font-medium text-orange-700">Improvements: </span>
            <span className="text-gray-600">{evaluation.improvements.join(', ')}</span>
          </div>
        )}
      </div>
    );
  };

  const btnConfig = getStatusButtonConfig();

  return (
    <div className="flex flex-col h-full bg-gray-50/50">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-8 py-4 bg-white border-b border-gray-200">
        <div>
          <h1 className="text-xl font-bold text-gray-800">{interviewType}</h1>
          <div className="flex items-center gap-3 mt-1">
            <p className="text-sm text-gray-500 flex items-center gap-1">
              <span className={`w-2 h-2 rounded-full ${backendAvailable ? 'bg-green-500' : 'bg-red-500'} animate-pulse`}></span>
              {backendAvailable ? 'AI Interviewer Online' : 'Backend Offline'}
            </p>
            {currentQuestionNumber > 0 && totalQuestions > 0 && (
              <p className="text-xs text-gray-400">
                Question {currentQuestionNumber} of {totalQuestions}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-4">
          <SimpleVisitorCounter />
          <button 
            onClick={handleNavigateToAnalytics}
            className="text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors"
          >
            View Analytics
          </button>
          
          <button 
            onClick={btnConfig.onClick}
            disabled={btnConfig.disabled}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition-all flex items-center gap-2 ${btnConfig.className}`}
          >
            {btnConfig.icon}
            {btnConfig.text}
          </button>
        </div>
      </div>

      {/* Interview Completion Banner */}
      {isInterviewComplete && (
        <div className="mx-8 mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3 flex-1">
              <CheckCircle size={20} className="text-green-600 mt-0.5" />
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-green-800 mb-1">Interview Completed! 🎉</h3>
                <p className="text-sm text-green-700 mb-3">
                  Your interview has been completed. View your detailed feedback report below or check your dashboard for analytics.
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setShowReport(!showReport)}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium flex items-center gap-2"
                  >
                    <FileText size={16} />
                    {showReport ? 'Hide Report' : 'View Report'}
                  </button>
                  <button
                    onClick={onNavigateToDashboard}
                    className="px-4 py-2 bg-white border border-green-300 text-green-700 rounded-lg hover:bg-green-50 transition-colors text-sm font-medium"
                  >
                    Go to Dashboard
                  </button>
                </div>
              </div>
            </div>
            <button
              onClick={() => {
                setIsInterviewComplete(false);
                setShowReport(false);
              }}
              className="text-green-400 hover:text-green-600"
            >
              <XCircle size={20} />
            </button>
          </div>
        </div>
      )}

      {/* Interview Report Modal */}
      {showReport && interviewReport && (
        <div className="mx-8 mt-4 p-6 bg-white border border-gray-200 rounded-lg shadow-lg max-h-[600px] overflow-y-auto">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-gray-800">Interview Report</h3>
            <button
              onClick={() => setShowReport(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              <X size={20} />
            </button>
          </div>
          
          {/* Report Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 p-3 rounded-lg">
              <p className="text-xs text-gray-600">Questions Answered</p>
              <p className="text-2xl font-bold text-blue-600">{interviewReport.questions_answered}</p>
            </div>
            <div className="bg-green-50 p-3 rounded-lg">
              <p className="text-xs text-gray-600">Overall Score</p>
              <p className="text-2xl font-bold text-green-600">{interviewReport.feedback_analysis.overall_score}%</p>
            </div>
            <div className="bg-purple-50 p-3 rounded-lg">
              <p className="text-xs text-gray-600">Duration</p>
              <p className="text-2xl font-bold text-purple-600">{interviewReport.duration_minutes?.toFixed(0) || 'N/A'}m</p>
            </div>
            <div className="bg-orange-50 p-3 rounded-lg">
              <p className="text-xs text-gray-600">Good Responses</p>
              <p className="text-2xl font-bold text-orange-600">{interviewReport.feedback_analysis.good_responses}</p>
            </div>
          </div>

          {/* Strengths */}
          {interviewReport.strengths.length > 0 && (
            <div className="mb-6">
              <h4 className="text-sm font-semibold text-gray-800 mb-2">Strengths</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                {interviewReport.strengths.map((strength, idx) => (
                  <li key={idx}>{strength}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Areas for Improvement */}
          {interviewReport.areas_for_improvement.length > 0 && (
            <div className="mb-6">
              <h4 className="text-sm font-semibold text-gray-800 mb-2">Areas for Improvement</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                {interviewReport.areas_for_improvement.map((area, idx) => (
                  <li key={idx}>{area}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommendations */}
          {interviewReport.recommendations.length > 0 && (
            <div className="mb-6">
              <h4 className="text-sm font-semibold text-gray-800 mb-2">Recommendations</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                {interviewReport.recommendations.map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Conversation History (Collapsible) */}
          <details className="mt-4">
            <summary className="cursor-pointer text-sm font-semibold text-gray-800 hover:text-blue-600">
              View Full Conversation History ({interviewReport.conversation_history.length} exchanges)
            </summary>
            <div className="mt-3 space-y-4 max-h-[300px] overflow-y-auto">
              {interviewReport.conversation_history.map((exchange, idx) => (
                <div key={idx} className="border-l-2 border-blue-200 pl-3 py-2">
                  <p className="text-xs font-semibold text-gray-600 mb-1">Question {exchange.question_index}:</p>
                  <p className="text-sm text-gray-800 mb-2">{exchange.question}</p>
                  <p className="text-xs font-semibold text-gray-600 mb-1">Your Response:</p>
                  <p className="text-sm text-gray-700">{exchange.user_response}</p>
                </div>
              ))}
            </div>
          </details>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="mx-8 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
          <AlertCircle size={16} className="text-red-600" />
          <span className="text-sm text-red-700">{error}</span>
          <button 
            onClick={() => setError(null)}
            className="ml-auto text-red-600 hover:text-red-800"
          >
            ×
          </button>
        </div>
      )}

      {/* File Upload Section (Only for Customize Interview) */}
      {interviewType === InterviewType.CUSTOMIZE && (
        <div className="mx-8 mt-4">
          {!filesUploaded && !showFileUploader ? (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Upload size={20} className="text-blue-600" />
                  <div>
                    <p className="text-sm font-medium text-blue-800">Upload Your Documents</p>
                    <p className="text-xs text-blue-600">Upload your resume, job description, and other relevant files to personalize your interview</p>
                  </div>
                </div>
                <button
                  onClick={() => setShowFileUploader(true)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                >
                  Upload Files
                </button>
              </div>
            </div>
          ) : showFileUploader && !filesUploaded ? (
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-800">Upload Documents</h3>
                <button
                  onClick={() => {
                    setShowFileUploader(false);
                    setUploadedFiles([]);
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X size={20} />
                </button>
              </div>
              <FileUploader
                onFilesChange={handleFilesChange}
                acceptedFormats={['.pdf', '.txt', '.md', '.docx']}
                maxFiles={5}
                maxSizeMB={10}
              />
              {uploadedFiles.length > 0 && (
                <div className="mt-4 flex justify-end gap-3">
                  <button
                    onClick={() => {
                      setShowFileUploader(false);
                      setUploadedFiles([]);
                    }}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                    disabled={isUploading}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleUploadFiles}
                    disabled={isUploading || uploadedFiles.length === 0}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {isUploading ? (
                      <>
                        <RefreshCw size={16} className="animate-spin" />
                        Uploading...
                      </>
                    ) : (
                      <>
                        <Upload size={16} />
                        Upload {uploadedFiles.length} File{uploadedFiles.length > 1 ? 's' : ''}
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          ) : filesUploaded ? (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <CheckCircle size={20} className="text-green-600" />
                <div>
                  <p className="text-sm font-medium text-green-800">Files Uploaded Successfully</p>
                  <p className="text-xs text-green-600">Your interview has been personalized based on your documents</p>
                </div>
                <button
                  onClick={() => {
                    setFilesUploaded(false);
                    setShowFileUploader(true);
                    setUploadedFiles([]);
                  }}
                  className="ml-auto text-sm text-green-700 hover:text-green-900 underline"
                >
                  Upload More
                </button>
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* Main Chat Area */}
      <div className="flex-1 overflow-y-auto p-8 space-y-6">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex max-w-[80%] gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-indigo-100 text-indigo-600' : 'bg-blue-600 text-white'}`}>
                {msg.role === 'user' ? <span className="font-bold text-xs">{user?.avatar || 'ME'}</span> : <Bot size={16} />}
              </div>
              <div className={`p-4 rounded-2xl shadow-sm text-sm leading-relaxed ${
                msg.role === 'user' 
                  ? 'bg-white border border-gray-100 text-gray-800 rounded-tr-none' 
                  : 'bg-white border border-blue-100 text-gray-800 rounded-tl-none'
              }`}>
                {msg.content}
                
                {msg.role === 'ai' && (
                    <>
                        {/* Show evaluation feedback for the previous user response */}
                        {msg.evaluation && renderEvaluation(msg.evaluation)}
                        <div className="mt-2 pt-2 border-t border-gray-100 flex gap-2">
                            <button onClick={() => speak(msg.content)} className="text-gray-400 hover:text-blue-500">
                                {isSpeaking ? <Square size={14} /> : <Play size={14} />}
                            </button>
                        </div>
                    </>
                )}
              </div>
            </div>
          </div>
        ))}
        {isProcessing && (
          <div className="flex justify-start">
             <div className="bg-white border border-gray-100 p-3 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-2">
                <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-100"></div>
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-200"></div>
                </div>
                <span className="text-xs text-gray-400">AI is thinking...</span>
             </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-6 bg-white border-t border-gray-200">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
            <button 
                onClick={handlePracticeAgain}
                className="p-3 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-all"
                title="Practice Again"
                disabled={isProcessing}
            >
                <RefreshCw size={20} />
            </button>
            
            <div className="flex-1 relative">
                <input 
                    type="text" 
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !isProcessing && handleSend()}
                    placeholder={backendAvailable ? "Type your answer or use voice..." : "Backend unavailable..."}
                    disabled={!backendAvailable || isProcessing}
                    className="w-full pl-4 pr-12 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <button 
                    onClick={handleSend}
                    disabled={!input.trim() || !backendAvailable || isProcessing}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors"
                >
                    <Send size={16} />
                </button>
            </div>

            <button 
                onClick={toggleRecording}
                disabled={!backendAvailable || isProcessing || (!permissionGranted && !isRecording && !micError)}
                className={`p-3 rounded-full transition-all duration-300 shadow-md disabled:opacity-50 disabled:cursor-not-allowed ${
                    isRecording 
                    ? 'bg-red-500 text-white animate-pulse ring-4 ring-red-100' 
                    : interviewType === InterviewType.CUSTOMIZE && !isPro
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200'
                      : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
                }`}
            >
                {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
            </button>
        </div>
        <div className="text-center mt-2 text-xs text-gray-400 flex items-center justify-center gap-1 flex-col">
            {isRecording ? (
              <>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                  <span>Recording... Click to stop</span>
                </div>
              </>
            ) : isProcessing ? (
              <span className="flex items-center gap-2">
                <RefreshCw size={12} className="animate-spin" />
                Processing audio...
              </span>
            ) : interviewType === InterviewType.CUSTOMIZE && !isPro ? (
              <>
                <Lock size={10} />
                <span>Voice input: Pro Only</span>
              </>
            ) : micError && !permissionGranted ? (
              <span className="text-orange-500">Microphone not available</span>
            ) : (
              <span>Press microphone to speak</span>
            )}
            {micError && !isRecording && !isProcessing && (
              <span className="text-xs text-red-500 mt-1 max-w-md text-center">
                {micError.includes('permission') ? 'Allow microphone access in browser settings' : micError}
              </span>
            )}
        </div>
      </div>
    </div>
  );
};
