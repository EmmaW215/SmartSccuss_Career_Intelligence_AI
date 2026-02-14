import React, { useEffect, useState, useRef } from "react";
import { UploadCloud, FileText, Loader2, ChevronRight, ArrowLeft, CheckCircle, Crown, LogIn } from 'lucide-react';

import VisitorCounter from './components/VisitorCounter';
import ResultsDisplay from './components/ResultsDisplay';
import { useParentMessage } from './hooks/useParentMessage';
import { ComparisonResponse } from './types';
import { useAuth } from '../../contexts/AuthContext';

// Backend URL — points to SmartSuccess.AI backend's /api/matchwise prefix
const BACKEND_URL = import.meta.env.VITE_MATCHWISE_BACKEND_URL 
  || (import.meta.env.VITE_BACKEND_URL ? `${import.meta.env.VITE_BACKEND_URL}` : '')
  || (typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_BACKEND_URL ? `${process.env.NEXT_PUBLIC_BACKEND_URL}` : '')
  || 'https://smartsccuss-career-intelligence-ai.onrender.com';

// Matchwise API base — all endpoints under /api/matchwise/
const MATCHWISE_API = `${BACKEND_URL}/api/matchwise`;

interface MatchwiseAppProps {
  onBack?: () => void;
}

const MatchwiseApp: React.FC<MatchwiseAppProps> = ({ onBack }) => {
  // SmartSuccess.AI auth — synced user status
  const { isAuthenticated, isPro, user, triggerLogin, triggerUpgrade } = useAuth();

  const [jobText, setJobText] = useState('');
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ComparisonResponse | null>(null);
  
  // Free trial tracking (local, per browser)
  const [trialUsed, setTrialUsed] = useState(false);
  
  // UI State
  const [showVisitorCounter, setShowVisitorCounter] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);

  // Initialize — check if free trial was already used
  useEffect(() => {
    const used = localStorage.getItem('matchwise_trial_used') === 'true';
    setTrialUsed(used);
  }, []);

  // Parent Window Communication
  useParentMessage({
    showLoginModal: () => {
      triggerLogin();
    },
    hideVisitorCounter: () => setShowVisitorCounter(false),
  });

  // Logic Helpers
  const canGenerate = () => {
    // First free try: always allowed (regardless of login status)
    if (!trialUsed) return true;
    // After first try: must be Pro user
    if (isPro) return true;
    return false;
  };

  const getErrorMessage = () => {
    if (!trialUsed) return '';
    if (isPro) return '';
    if (!isAuthenticated) {
      return 'Your free trial is finished. Please sign in and upgrade to Pro to continue!';
    }
    return 'Your free trial is finished. Please upgrade to Pro to continue using MatchWise!';
  };

  // Handlers
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setResumeFile(e.target.files[0]);
      setError('');
    }
  };

  const handleDrag = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setResumeFile(e.dataTransfer.files[0]);
      setError('');
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!jobText || !resumeFile) {
      alert('Please provide both job description and resume.');
      return;
    }

    if (!canGenerate()) {
      const errorMsg = getErrorMessage();
      setResponse(null);
      setError(errorMsg);
      return;
    }

    const formData = new FormData();
    formData.append('job_text', jobText);
    formData.append('resume', resumeFile);

    setLoading(true);
    setError('');
    setResponse(null);

    try {
      const apiResponse = await fetch(`${MATCHWISE_API}/compare`, {
        method: 'POST',
        body: formData,
      });
      
      if (!apiResponse.ok) {
        const errorData = await apiResponse.json();
        throw new Error(errorData.error || 'Failed to fetch comparison');
      }
      
      const data = await apiResponse.json();
      setResponse(data);

      // Mark free trial as used after successful generation
      if (!trialUsed) {
        localStorage.setItem('matchwise_trial_used', 'true');
        setTrialUsed(true);
      }

    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
      setError(errorMessage.includes('403') ? 'Insufficient credits. Please contact support.' : errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // User status badge — matches InterviewPage style
  const getUserStatusBadge = () => {
    if (!isAuthenticated) {
      return (
        <button
          onClick={triggerLogin}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 font-semibold rounded-full shadow-md transition-all text-sm"
        >
          <LogIn className="w-4 h-4" />
          Guest user Login/Sign up
        </button>
      );
    }

    if (isPro) {
      return (
        <div className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-full shadow-md text-sm font-semibold">
          <Crown className="w-4 h-4" />
          Pro Connected
        </div>
      );
    }

    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-green-50 text-green-700 border border-green-200 rounded-full text-sm font-semibold">
        <CheckCircle className="w-4 h-4" />
        User Connected
      </div>
    );
  };

  return (
    <div className="h-full overflow-y-auto flex flex-col bg-gray-50 text-gray-900 font-sans relative">
      {/* Background */}
      <div 
        className="absolute inset-0 z-0 bg-cover bg-center opacity-10 pointer-events-none"
        style={{ backgroundImage: `url('/Job_Search_Pic.png'), linear-gradient(to bottom right, #eff6ff, #f5f3ff)` }}
      />
      
      {/* Header */}
      <header className="relative z-20 w-full px-6 py-4 flex justify-between items-center bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0">
        <div className="flex items-center gap-3">
          {onBack && (
            <button 
              onClick={onBack}
              className="p-2 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-full transition-colors"
              title="Back to Matchwise: Resume"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
          )}
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-lg">M</div>
          <span className="font-bold text-xl text-gray-800 tracking-tight">MatchWise</span>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="hidden sm:block">
            <VisitorCounter isVisible={showVisitorCounter} />
          </div>

          {/* User status badge — synced with SmartSuccess.AI */}
          {getUserStatusBadge()}
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 flex-1 flex flex-col items-center p-4 sm:p-8 max-w-7xl mx-auto w-full">
        
        <div className="text-center mb-10 mt-6 max-w-2xl">
          <h1 className="text-4xl sm:text-5xl font-extrabold text-gray-900 mb-4 tracking-tight leading-tight">
            Optimize Your <span className="text-blue-600">Career Path</span>
          </h1>
          <p className="text-lg text-gray-600 leading-relaxed">
            AI-powered analysis to tailor your resume and cover letter for specific job postings. Increase your interview chances instantly.
          </p>
        </div>

        <div className="w-full max-w-4xl bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-white/50 p-6 sm:p-8">
          <form onSubmit={handleSubmit} className="flex flex-col gap-6">
            
            {/* Job Description Input */}
            <div className="flex flex-col gap-2">
              <label htmlFor="matchwise-jobText" className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-500" />
                Job Description
              </label>
              <textarea
                id="matchwise-jobText"
                required
                value={jobText}
                onChange={(e) => setJobText(e.target.value)}
                placeholder="Paste the full job description here..."
                rows={6}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all resize-none text-sm leading-relaxed"
              />
            </div>

            {/* Resume Upload */}
            <div
              className={`relative w-full border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer group ${
                dragActive 
                  ? 'border-blue-500 bg-blue-50/50 scale-[1.01]' 
                  : 'border-gray-200 bg-gray-50 hover:border-blue-400 hover:bg-white'
              }`}
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
            >
              <input
                id="matchwise-resume"
                type="file"
                accept=".pdf,.doc,.docx"
                ref={inputRef}
                onChange={handleFileChange}
                className="hidden"
              />
              <div className="flex flex-col items-center justify-center gap-3">
                <div className={`p-4 rounded-full bg-blue-100 text-blue-600 transition-transform duration-300 ${dragActive ? 'scale-110' : 'group-hover:scale-110'}`}>
                  <UploadCloud className="w-8 h-8" />
                </div>
                <div>
                  <h3 className="text-gray-900 font-semibold text-lg">
                    {resumeFile ? resumeFile.name : "Upload Resume"}
                  </h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {resumeFile ? "Click to change file" : "Drag & drop or click to select (PDF/DOCX)"}
                  </p>
                </div>
              </div>
            </div>

            {/* Status & Errors */}
            {error && (
              <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm font-medium border border-red-100 flex items-center justify-between animate-fade-in">
                <span>{error}</span>
                {(error.includes('upgrade') || error.includes('Upgrade')) && (
                  <button
                    type="button"
                    onClick={() => isAuthenticated ? triggerUpgrade() : triggerLogin()}
                    className="text-xs bg-red-100 hover:bg-red-200 text-red-700 px-3 py-1 rounded-full transition-colors font-bold"
                  >
                    {isAuthenticated ? 'Upgrade Now' : 'Sign In'}
                  </button>
                )}
              </div>
            )}
            
            {/* Generate Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 px-6 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold text-lg rounded-xl shadow-lg hover:shadow-xl transition-all disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2 group"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  Generate Analysis
                  <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Results Section */}
        {response && <ResultsDisplay data={response} />}
        
      </main>

      {/* Footer */}
      <footer className="w-full py-6 text-center text-gray-400 text-sm mt-12 bg-gray-50 border-t border-gray-200">
        <p>&copy; {new Date().getFullYear()} MatchWise. All rights reserved.</p>
        <span className="text-blue-400 mt-2 inline-block">
          Powered by SmartSuccess.AI
        </span>
      </footer>
    </div>
  );
};

export default MatchwiseApp;
