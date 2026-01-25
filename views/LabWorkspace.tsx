import React, { useState, useEffect, useRef } from 'react';
import { 
  FileCode, 
  Terminal as TerminalIcon, 
  Play, 
  Save, 
  ChevronRight, 
  ChevronDown,
  ArrowLeft,
  Send,
  Loader2,
  Clock,
  Sparkles
} from 'lucide-react';
import { LabChallenge, LabFileNode, LabChatMessage } from '../types';
import { generateLabAIResponse } from '../services/geminiService';
import { useAuth } from '../contexts/AuthContext';

interface LabWorkspaceProps {
  challenge: LabChallenge;
  onExit: () => void;
  onSubmit: () => void;
}

export const LabWorkspace: React.FC<LabWorkspaceProps> = ({ challenge, onExit, onSubmit }) => {
  const [activeFile, setActiveFile] = useState<LabFileNode>(challenge.initialFiles[0]);
  const [files, setFiles] = useState<LabFileNode[]>(challenge.initialFiles);
  const [isTerminalOpen, setIsTerminalOpen] = useState(true);
  const [terminalOutput, setTerminalOutput] = useState<string[]>(['> Environment initialized.', '> Ready for tasks.']);
  const [messages, setMessages] = useState<LabChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `Welcome to the ${challenge.title} lab! I'm your AI assistant. I can help you architect the solution, debug code, or explain concepts. How should we start?`,
      timestamp: new Date()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isAiThinking, setIsAiThinking] = useState(false);
  const [timeLeft, setTimeLeft] = useState(challenge.timeLimit * 60);
  const { isPro } = useAuth();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Timer effect
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Auto scroll chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Pro check on mount
  useEffect(() => {
    if (!isPro) {
      // Redirect if not Pro (shouldn't happen, but safety check)
      onExit();
    }
  }, [isPro, onExit]);

  const handleFileChange = (content: string) => {
    setFiles(prev => prev.map(f => f.id === activeFile.id ? { ...f, content } : f));
    setActiveFile(prev => ({ ...prev, content }));
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !isPro) return;

    const userMsg: LabChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMsg]);
    setInputMessage('');
    setIsAiThinking(true);

    // Call Lab Gemini Service
    const aiResponseText = await generateLabAIResponse(
      [...messages, userMsg].map(m => ({ role: m.role, content: m.content })),
      `You are an expert AI Architect and Engineering assistant helping a user with the task: "${challenge.title}". The context is: ${challenge.description}. Be concise, helpful, and technical.`
    );

    const aiMsg: LabChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: aiResponseText,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, aiMsg]);
    setIsAiThinking(false);
  };

  const handleRunCode = () => {
    setTerminalOutput(prev => [...prev, `> python ${activeFile.name}`, `> Running simulation...`, `> OK.`]);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!isPro) {
    return null; // Should not render if not Pro
  }

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-gray-100 overflow-hidden font-sans">
      {/* Top Bar */}
      <div className="h-14 bg-gray-800 border-b border-gray-700 flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-4">
          <button onClick={onExit} className="p-2 hover:bg-gray-700 rounded-lg text-gray-400 hover:text-white transition-colors">
            <ArrowLeft size={18} />
          </button>
          <div>
            <h2 className="font-semibold text-sm text-gray-100">{challenge.title}</h2>
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <span className={`w-2 h-2 rounded-full ${timeLeft < 600 ? 'bg-red-500' : 'bg-green-500'}`}></span>
              <Clock size={12} />
              <span className="font-mono">{formatTime(timeLeft)}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleRunCode} className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-md text-sm font-medium transition-colors text-green-400">
            <Play size={14} /> Run
          </button>
          <button onClick={onSubmit} className="flex items-center gap-2 px-3 py-1.5 bg-purple-600 hover:bg-purple-700 rounded-md text-sm font-medium transition-colors text-white ml-2">
            <Save size={14} /> Submit
          </button>
        </div>
      </div>

      {/* Main Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - Files */}
        <div className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col shrink-0">
          <div className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Explorer</div>
          <div className="flex-1 overflow-y-auto">
            {files.map(file => (
              <button
                key={file.id}
                onClick={() => setActiveFile(file)}
                className={`w-full flex items-center gap-2 px-4 py-2 text-sm hover:bg-gray-800 transition-colors ${activeFile.id === file.id ? 'bg-gray-800 text-purple-400 border-l-2 border-purple-500' : 'text-gray-400 border-l-2 border-transparent'}`}
              >
                <FileCode size={16} />
                {file.name}
              </button>
            ))}
          </div>
        </div>

        {/* Center - Editor */}
        <div className="flex-1 flex flex-col min-w-0 bg-[#0d1117]">
          {/* Tab Bar */}
          <div className="flex bg-gray-900 border-b border-gray-800 overflow-x-auto">
            {files.map(file => (
               <div
                 key={file.id}
                 onClick={() => setActiveFile(file)}
                 className={`px-4 py-2.5 text-xs font-medium border-r border-gray-800 cursor-pointer flex items-center gap-2 ${activeFile.id === file.id ? 'bg-[#0d1117] text-gray-200 border-t-2 border-t-purple-500' : 'text-gray-500 hover:bg-gray-800 border-t-2 border-t-transparent'}`}
               >
                 {file.name}
               </div>
            ))}
          </div>
          
          {/* Editor Area */}
          <div className="flex-1 relative">
            <textarea
              value={activeFile.content}
              onChange={(e) => handleFileChange(e.target.value)}
              className="absolute inset-0 w-full h-full bg-[#0d1117] text-gray-300 font-mono text-sm p-4 resize-none focus:outline-none"
              spellCheck={false}
            />
          </div>

          {/* Terminal */}
          <div className={`border-t border-gray-800 bg-gray-900 flex flex-col transition-all duration-300 ${isTerminalOpen ? 'h-48' : 'h-8'}`}>
            <div 
              className="flex items-center justify-between px-4 py-1.5 cursor-pointer bg-gray-800 hover:bg-gray-750"
              onClick={() => setIsTerminalOpen(!isTerminalOpen)}
            >
              <div className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase">
                <TerminalIcon size={12} /> Terminal
              </div>
              {isTerminalOpen ? <ChevronDown size={14} className="text-gray-500" /> : <ChevronRight size={14} className="text-gray-500" />}
            </div>
            {isTerminalOpen && (
              <div className="flex-1 p-3 font-mono text-xs text-gray-400 overflow-y-auto">
                {terminalOutput.map((line, i) => (
                  <div key={i} className="mb-1">{line}</div>
                ))}
                <div className="animate-pulse">_</div>
              </div>
            )}
          </div>
        </div>

        {/* Right Sidebar - AI Chat */}
        <div className="w-80 bg-gray-900 border-l border-gray-800 flex flex-col shrink-0">
          <div className="p-3 border-b border-gray-800 flex items-center gap-2">
            <Sparkles size={16} className="text-purple-400" />
            <span className="text-sm font-bold text-gray-200">AI Assistant</span>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map(msg => (
              <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`max-w-[90%] rounded-lg px-3 py-2 text-sm ${msg.role === 'user' ? 'bg-purple-600 text-white' : 'bg-gray-800 text-gray-300 border border-gray-700'}`}>
                  {msg.content}
                </div>
                <span className="text-[10px] text-gray-600 mt-1">{msg.role === 'user' ? 'You' : 'Gemini'}</span>
              </div>
            ))}
            {isAiThinking && (
              <div className="flex items-center gap-2 text-gray-500 text-xs">
                <Loader2 size={12} className="animate-spin" /> Thinking...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="p-3 border-t border-gray-800">
            <div className="relative">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="Ask about your code..."
                className="w-full bg-gray-800 text-gray-200 text-sm rounded-lg pl-3 pr-10 py-2.5 focus:outline-none focus:ring-1 focus:ring-purple-500 border border-gray-700 placeholder-gray-600"
              />
              <button 
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || isAiThinking || !isPro}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-purple-400 disabled:opacity-50"
              >
                <Send size={14} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
