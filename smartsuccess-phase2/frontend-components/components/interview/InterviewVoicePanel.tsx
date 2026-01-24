/**
 * InterviewVoicePanel - Main voice interaction component
 * 
 * Features:
 * - Auto-play AI greeting on mount
 * - Microphone detection and recording
 * - Real-time conversation display
 * - Voice/text mode toggle
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useMicrophone } from '../../hooks/useMicrophone';
import { useAudioPlayer } from '../../hooks/useAudioPlayer';
import { useInterviewSession } from '../../hooks/useInterviewSession';

// Types
interface Message {
  role: 'user' | 'assistant';
  content: string;
  audioUrl?: string;
  feedbackHint?: {
    hint: string;
    quality: 'good' | 'fair' | 'needs_improvement';
  };
  timestamp: Date;
}

interface InterviewVoicePanelProps {
  interviewType: 'screening' | 'behavioral' | 'technical' | 'customize';
  sessionId: string;
  userName?: string;
  voiceEnabled?: boolean;
  onInterviewComplete: (transcript: Message[]) => void;
  customDocuments?: File[];
}

export const InterviewVoicePanel: React.FC<InterviewVoicePanelProps> = ({
  interviewType,
  sessionId,
  userName,
  voiceEnabled = true,
  onInterviewComplete,
  customDocuments
}) => {
  // State
  const [conversation, setConversation] = useState<Message[]>([]);
  const [isAISpeaking, setIsAISpeaking] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [textInput, setTextInput] = useState('');
  const [useTextMode, setUseTextMode] = useState(!voiceEnabled);

  // Hooks
  const {
    isMicAvailable,
    isRecording,
    startRecording,
    stopRecording,
    checkMicrophone,
    error: micError
  } = useMicrophone();

  const {
    playAudio,
    isPlaying,
    stopAudio
  } = useAudioPlayer();

  const {
    startInterview,
    sendResponse,
    endInterview,
    isLoading
  } = useInterviewSession(sessionId, interviewType);

  // Initialize interview on mount
  useEffect(() => {
    initializeInterview();
  }, []);

  const initializeInterview = async () => {
    try {
      setIsProcessing(true);
      
      // Check microphone if voice enabled
      if (voiceEnabled) {
        const micStatus = await checkMicrophone();
        if (!micStatus.available) {
          setUseTextMode(true);
        }
      }

      // Start interview
      const result = await startInterview({
        userName,
        voiceEnabled: voiceEnabled && isMicAvailable,
        customDocuments
      });

      setTotalQuestions(result.totalQuestions);

      // Add greeting to conversation
      const greetingMessage: Message = {
        role: 'assistant',
        content: result.greeting,
        audioUrl: result.audioUrl,
        timestamp: new Date()
      };
      setConversation([greetingMessage]);

      // Auto-play greeting if voice enabled
      if (voiceEnabled && result.audioUrl) {
        setIsAISpeaking(true);
        await playAudio(result.audioUrl);
        setIsAISpeaking(false);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start interview');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle voice input
  const handleVoiceInput = useCallback(async () => {
    if (isRecording) {
      // Stop recording and send
      try {
        setIsProcessing(true);
        const audioBlob = await stopRecording();
        
        // Add placeholder message
        setConversation(prev => [...prev, {
          role: 'user',
          content: '(Transcribing...)',
          timestamp: new Date()
        }]);

        // Send to backend
        const result = await sendResponse({ audio: audioBlob });

        // Update user message with transcript
        setConversation(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: 'user',
            content: result.userTranscript,
            timestamp: new Date()
          };
          return updated;
        });

        // Add AI response
        const aiMessage: Message = {
          role: 'assistant',
          content: result.aiResponse,
          audioUrl: result.audioUrl,
          feedbackHint: result.feedbackHint,
          timestamp: new Date()
        };
        setConversation(prev => [...prev, aiMessage]);
        setCurrentQuestion(result.currentQuestion);

        // Play AI response
        if (result.audioUrl) {
          setIsAISpeaking(true);
          await playAudio(result.audioUrl);
          setIsAISpeaking(false);
        }

        // Check completion
        if (result.isComplete) {
          onInterviewComplete(conversation);
        }

      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to process response');
      } finally {
        setIsProcessing(false);
      }
    } else {
      // Start recording
      try {
        await startRecording();
      } catch (err) {
        setError('Failed to start recording. Please check microphone permissions.');
        setUseTextMode(true);
      }
    }
  }, [isRecording, stopRecording, startRecording, sendResponse, playAudio]);

  // Handle text input
  const handleTextSubmit = async () => {
    if (!textInput.trim()) return;

    try {
      setIsProcessing(true);

      // Add user message
      setConversation(prev => [...prev, {
        role: 'user',
        content: textInput,
        timestamp: new Date()
      }]);

      const userText = textInput;
      setTextInput('');

      // Send to backend
      const result = await sendResponse({ text: userText });

      // Add AI response
      const aiMessage: Message = {
        role: 'assistant',
        content: result.aiResponse,
        audioUrl: result.audioUrl,
        feedbackHint: result.feedbackHint,
        timestamp: new Date()
      };
      setConversation(prev => [...prev, aiMessage]);
      setCurrentQuestion(result.currentQuestion);

      // Play audio if available and voice enabled
      if (voiceEnabled && result.audioUrl && !useTextMode) {
        setIsAISpeaking(true);
        await playAudio(result.audioUrl);
        setIsAISpeaking(false);
      }

      if (result.isComplete) {
        onInterviewComplete(conversation);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send response');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle end interview
  const handleEndInterview = async () => {
    try {
      await endInterview();
      onInterviewComplete(conversation);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to end interview');
    }
  };

  return (
    <div className="interview-voice-panel flex flex-col h-full bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="panel-header p-4 border-b flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold capitalize">{interviewType} Interview</h2>
          <p className="text-sm text-gray-500">
            Question {currentQuestion} of {totalQuestions}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setUseTextMode(!useTextMode)}
            className="text-sm px-3 py-1 rounded border hover:bg-gray-100"
          >
            {useTextMode ? '🎤 Voice Mode' : '⌨️ Text Mode'}
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 text-red-500">✕</button>
        </div>
      )}

      {/* Conversation Display */}
      <div className="conversation-display flex-1 overflow-y-auto p-4 space-y-4">
        {conversation.map((msg, idx) => (
          <div
            key={idx}
            className={`message flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] p-3 rounded-lg ${
                msg.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.feedbackHint && (
                <div className={`mt-2 text-xs px-2 py-1 rounded ${
                  msg.feedbackHint.quality === 'good' ? 'bg-green-100 text-green-700' :
                  msg.feedbackHint.quality === 'fair' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-red-100 text-red-700'
                }`}>
                  💡 {msg.feedbackHint.hint}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* AI Speaking Indicator */}
        {isAISpeaking && (
          <div className="flex justify-start">
            <div className="bg-gray-100 p-3 rounded-lg flex items-center gap-2">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </div>
              <span className="text-sm text-gray-500">Speaking...</span>
            </div>
          </div>
        )}
      </div>

      {/* Progress Bar */}
      <div className="px-4 py-2">
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div 
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${(currentQuestion / totalQuestions) * 100}%` }}
          ></div>
        </div>
      </div>

      {/* Input Controls */}
      <div className="input-controls p-4 border-t">
        {useTextMode ? (
          /* Text Input Mode */
          <div className="flex gap-2">
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleTextSubmit()}
              placeholder="Type your response..."
              disabled={isProcessing || isAISpeaking}
              className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleTextSubmit}
              disabled={isProcessing || isAISpeaking || !textInput.trim()}
              className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>
        ) : (
          /* Voice Input Mode */
          <div className="flex justify-center gap-4">
            <button
              onClick={handleVoiceInput}
              disabled={isProcessing || isAISpeaking}
              className={`w-16 h-16 rounded-full flex items-center justify-center text-2xl transition-all ${
                isRecording
                  ? 'bg-red-500 text-white animate-pulse'
                  : 'bg-blue-500 text-white hover:bg-blue-600'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {isRecording ? '⏹️' : '🎤'}
            </button>
          </div>
        )}

        {/* Mic Status */}
        {!useTextMode && !isMicAvailable && (
          <p className="text-center text-sm text-red-500 mt-2">
            ⚠️ Microphone not available. <button onClick={() => setUseTextMode(true)} className="underline">Use text mode</button>
          </p>
        )}

        {/* Recording Status */}
        {isRecording && (
          <p className="text-center text-sm text-red-500 mt-2 animate-pulse">
            🔴 Recording... Click to stop and send
          </p>
        )}
      </div>

      {/* End Interview Button */}
      <div className="p-4 border-t">
        <button
          onClick={handleEndInterview}
          className="w-full py-2 text-gray-600 hover:text-red-500 transition-colors"
        >
          End Interview Early
        </button>
      </div>
    </div>
  );
};

export default InterviewVoicePanel;
