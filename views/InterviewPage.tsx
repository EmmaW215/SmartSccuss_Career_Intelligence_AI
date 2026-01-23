import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, RefreshCw, Send, Play, Square, AlertCircle, Bot, LogIn, Lock, CheckCircle, User, Crown, Star, TrendingUp } from 'lucide-react';
import { InterviewType, Message } from '../types';
import SimpleVisitorCounter from '../components/SimpleVisitorCounter';
import { 
  startInterviewSession, 
  sendInterviewMessage, 
  deleteInterviewSession,
  checkBackendHealth,
  type MessageResponse 
} from '../services/interviewService';
import { useAuth } from '../contexts/AuthContext';

interface InterviewPageProps {
  interviewType: InterviewType;
  onNavigateToDashboard: () => void;
}

export const InterviewPage: React.FC<InterviewPageProps> = ({ interviewType, onNavigateToDashboard }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [backendAvailable, setBackendAvailable] = useState<boolean>(true);
  const [currentQuestionNumber, setCurrentQuestionNumber] = useState<number>(0);
  const [totalQuestions, setTotalQuestions] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const { user, login, isAuthenticated, isLoading, isPro, triggerLogin, triggerUpgrade } = useAuth();

  // Initialize interview session when component mounts or interview type changes
  useEffect(() => {
    if (!isAuthenticated) return;

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
      if (response.type === 'completion' && response.summary) {
        // Interview completed - could navigate to results page
        console.log('Interview completed:', response.summary);
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

  // Mock Speech-to-Text
  const toggleRecording = () => {
    if (!checkAccess()) return;

    // Special check for Customize Interview + Voice Input
    if (interviewType === InterviewType.CUSTOMIZE && !isPro) {
        triggerUpgrade();
        return;
    }

    if (isRecording) {
      setIsRecording(false);
      if (!input) setInput("I have extensive experience building RAG pipelines using Python and Pinecone.");
    } else {
      setIsRecording(true);
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
                disabled={!backendAvailable}
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
        <div className="text-center mt-2 text-xs text-gray-400 flex items-center justify-center gap-1">
            {interviewType === InterviewType.CUSTOMIZE && !isPro && <Lock size={10} />}
            {isRecording ? "Listening..." : interviewType === InterviewType.CUSTOMIZE && !isPro ? "Voice input: Pro Only" : "Press microphone to speak"}
        </div>
      </div>
    </div>
  );
};
