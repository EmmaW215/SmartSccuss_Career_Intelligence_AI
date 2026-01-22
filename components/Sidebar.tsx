import React, { useState } from 'react';
import { LayoutDashboard, Mic, FileText, Home, ChevronDown, ChevronRight, User as UserIcon, Settings, LogOut, Beaker, LogIn } from 'lucide-react';
import { ViewState, InterviewType } from '../types';
import { useAuth } from '../contexts/AuthContext';

interface SidebarProps {
  currentView: ViewState;
  onNavigate: (view: ViewState) => void;
  onInterviewTypeSelect: (type: InterviewType) => void;
  selectedInterviewType: InterviewType;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  currentView, 
  onNavigate, 
  onInterviewTypeSelect,
  selectedInterviewType
}) => {
  const [isInterviewOpen, setIsInterviewOpen] = useState(true);
  const { user, isAuthenticated, logout, login, isLoading } = useAuth();

  const topMenuItems = [
    { id: 'landing', label: 'Home', icon: Home, view: 'landing' as ViewState },
    { id: 'demo', label: 'Matchwise: Resume', icon: FileText, view: 'demo' as ViewState },
  ];

  const interviewTypes = [
    { id: InterviewType.SCREENING, label: 'Screening Interview', sub: 'Self-Intro & Situation' },
    { id: InterviewType.BEHAVIORAL, label: 'Behavioral Interview', sub: 'Soft Skills & Leadership' },
    { id: InterviewType.TECHNICAL, label: 'Technical Interview', sub: 'AI General Skills' },
    { id: InterviewType.CUSTOMIZE, label: 'Customize Interview', sub: 'Personalized Skills' },
  ];

  return (
    <div className="w-72 h-screen bg-white border-r border-gray-200 flex flex-col shadow-[4px_0_24px_rgba(0,0,0,0.02)] z-10 sticky top-0">
      {/* Header */}
      <div className="p-6 border-b border-gray-100">
        <h2 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
          SmartSuccess.AI
        </h2>
        <p className="text-xs text-gray-400 mt-1 uppercase tracking-wider font-semibold">
            {user?.type === 'registered' ? 'Pro Edition' : 'Free Preview'}
        </p>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto py-6 px-4 space-y-1 custom-scrollbar">
        {topMenuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.view)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
              currentView === item.view 
                ? 'bg-blue-50 text-blue-700 shadow-sm border border-blue-100' 
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }`}
          >
            <item.icon className={`w-5 h-5 ${currentView === item.view ? 'text-blue-600' : 'text-gray-400'}`} />
            {item.label}
          </button>
        ))}

        {/* Accordion for Interview */}
        <div className="mt-4">
          <button
            onClick={() => {
                setIsInterviewOpen(!isInterviewOpen);
                if (currentView !== 'interview') onNavigate('interview');
            }}
            className={`w-full flex items-center justify-between px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
              currentView === 'interview'
                ? 'bg-blue-50 text-blue-700 shadow-sm border border-blue-100'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            <div className="flex items-center gap-3">
              <Mic className={`w-5 h-5 ${currentView === 'interview' ? 'text-blue-600' : 'text-gray-400'}`} />
              <span>Mock Interview</span>
            </div>
            {isInterviewOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>

          {isInterviewOpen && (
            <div className="ml-4 mt-2 pl-4 border-l-2 border-gray-100 space-y-1">
              {interviewTypes.map((type) => (
                <button
                  key={type.id}
                  onClick={() => {
                    onNavigate('interview');
                    onInterviewTypeSelect(type.id);
                  }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
                    currentView === 'interview' && selectedInterviewType === type.id
                      ? 'bg-indigo-50 text-indigo-700 font-semibold'
                      : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  <div className="font-medium">{type.label}</div>
                  <div className="text-[10px] opacity-70 mt-0.5">{type.sub}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* My Dashboard */}
        <button
          onClick={() => onNavigate('dashboard')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 mt-1 ${
            currentView === 'dashboard' 
              ? 'bg-blue-50 text-blue-700 shadow-sm border border-blue-100' 
              : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
          }`}
        >
          <LayoutDashboard className={`w-5 h-5 ${currentView === 'dashboard' ? 'text-blue-600' : 'text-gray-400'}`} />
          My Dashboard
        </button>

        {/* AI Skills Lab */}
        <button
          onClick={() => onNavigate('lab')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 mt-1 ${
            currentView === 'lab' 
              ? 'bg-purple-50 text-purple-700 shadow-sm border border-purple-100' 
              : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
          }`}
        >
          <Beaker className={`w-5 h-5 ${currentView === 'lab' ? 'text-purple-600' : 'text-gray-400'}`} />
          AI Skills Lab
        </button>
      </div>

      {/* User Footer - Synchronized with Auth State */}
      <div className="p-4 border-t border-gray-100 bg-gray-50/50">
        <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-white hover:shadow-sm transition-all cursor-pointer group">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-md group-hover:scale-105 transition-transform ${
                user?.type === 'registered' ? 'bg-gradient-to-br from-indigo-500 to-purple-500' : 'bg-gray-400'
            }`}>
                {user?.avatar || 'GU'}
            </div>
            <div className="flex-1">
                <p className="text-sm font-semibold text-gray-800">{user?.name}</p>
                <p className="text-xs text-gray-500">{user?.type === 'registered' ? 'Pro Plan' : 'Guest Account'}</p>
            </div>
            <Settings className="w-4 h-4 text-gray-400 hover:text-gray-600" />
        </div>
        
        {user?.type === 'registered' ? (
          <button 
            onClick={logout}
            className="w-full mt-3 flex items-center justify-center gap-2 text-xs font-medium text-red-500 hover:text-red-600 py-2 hover:bg-red-50 rounded-lg transition-colors"
          >
            <LogOut className="w-3 h-3" /> Sign Out
          </button>
        ) : (
          <button 
            onClick={login}
            disabled={isLoading}
            className="w-full mt-3 flex items-center justify-center gap-2 text-xs font-medium text-blue-600 hover:text-blue-700 py-2 hover:bg-blue-50 rounded-lg transition-colors"
          >
            {isLoading ? (
                <div className="w-3 h-3 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin"></div>
            ) : <LogIn className="w-3 h-3" />} 
            Login to Save Progress
          </button>
        )}
      </div>
    </div>
  );
};