import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, RefreshCw, Send, Play, Square, AlertCircle, Bot, LogIn } from 'lucide-react';
import { InterviewType, Message } from '../types';
import SimpleVisitorCounter from '../components/SimpleVisitorCounter';
import { generateInterviewResponse } from '../services/geminiService';
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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const { user, login, isAuthenticated, isLoading } = useAuth();

  // Initial Greeting
  useEffect(() => {
    setMessages([
      {
        id: 'init',
        role: 'ai',
        content: `Hello ${user?.name.split(' ')[0]}! I am your SmartSuccess AI coach. I'm ready to conduct your ${interviewType}. Shall we begin?`,
        timestamp: new Date()
      }
    ]);
  }, [interviewType, user]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsProcessing(true);

    try {
        // Prepare history for Gemini
        const history = messages.map(m => ({
            role: m.role === 'user' ? 'user' : 'model',
            parts: [{ text: m.content }]
        }));

        const aiResponseText = await generateInterviewResponse(history, userMsg.content, interviewType);

        const aiMsg: Message = {
            id: (Date.now() + 1).toString(),
            role: 'ai',
            content: aiResponseText,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, aiMsg]);
        speak(aiResponseText);

    } catch (error) {
        console.error("Interview error", error);
    } finally {
        setIsProcessing(false);
    }
  };

  // Mock Speech-to-Text
  const toggleRecording = () => {
    if (isRecording) {
      setIsRecording(false);
      if (!input) setInput("I have extensive experience building RAG pipelines using Python and Pinecone.");
    } else {
      setIsRecording(true);
    }
  };

  // Mock Text-to-Speech
  const speak = (text: string) => {
    if ('speechSynthesis' in window) {
      setIsSpeaking(true);
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.onend = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    }
  };

  const handlePracticeAgain = () => {
    setMessages([{
        id: Date.now().toString(),
        role: 'ai',
        content: `Resetting session... Let's start the ${interviewType} again. Please introduce yourself.`,
        timestamp: new Date()
    }]);
  };

  return (
    <div className="flex flex-col h-full bg-gray-50/50">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-8 py-4 bg-white border-b border-gray-200">
        <div>
          <h1 className="text-xl font-bold text-gray-800">{interviewType}</h1>
          <p className="text-sm text-gray-500 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            AI Interviewer Online
          </p>
        </div>
        <div className="flex items-center gap-4">
          <SimpleVisitorCounter />
          <button 
            onClick={onNavigateToDashboard}
            className="text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors"
          >
            View Analytics
          </button>
          
          <button 
            onClick={isAuthenticated ? undefined : login}
            disabled={isLoading || isAuthenticated}
            className={`px-4 py-2 text-sm font-semibold rounded-lg shadow-md transition-all flex items-center gap-2 ${
              isAuthenticated 
                ? 'bg-green-50 text-green-700 border border-green-200 shadow-none cursor-default' 
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {isLoading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            ) : isAuthenticated ? <Bot size={16} /> : <LogIn size={16} />}
            {isAuthenticated ? 'Pro Connected' : 'Pro Login'}
          </button>
        </div>
      </div>

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
                    <div className="mt-2 pt-2 border-t border-gray-100 flex gap-2">
                        <button onClick={() => speak(msg.content)} className="text-gray-400 hover:text-blue-500">
                            {isSpeaking ? <Square size={14} /> : <Play size={14} />}
                        </button>
                    </div>
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
            >
                <RefreshCw size={20} />
            </button>
            
            <div className="flex-1 relative">
                <input 
                    type="text" 
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    placeholder="Type your answer or use voice..."
                    className="w-full pl-4 pr-12 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-sm"
                />
                <button 
                    onClick={handleSend}
                    disabled={!input.trim()}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors"
                >
                    <Send size={16} />
                </button>
            </div>

            <button 
                onClick={toggleRecording}
                className={`p-3 rounded-full transition-all duration-300 shadow-md ${
                    isRecording 
                    ? 'bg-red-500 text-white animate-pulse ring-4 ring-red-100' 
                    : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
                }`}
            >
                {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
            </button>
        </div>
        <div className="text-center mt-2 text-xs text-gray-400">
            {isRecording ? "Listening..." : "Press microphone to speak"}
        </div>
      </div>
    </div>
  );
};