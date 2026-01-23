import React from 'react';
import { ArrowRight, CheckCircle2, FileText, ChevronLeft, ExternalLink } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface DemoPageProps {
    onBack: () => void;
    onViewSample: () => void;
}

export const DemoPage: React.FC<DemoPageProps> = ({ onBack, onViewSample }) => {
  const { isAuthenticated, isPro, triggerLogin, triggerUpgrade } = useAuth();

  const handleTryLive = (e: React.MouseEvent) => {
    e.preventDefault();
    if (!isAuthenticated) {
      triggerLogin();
    } else if (!isPro) {
      triggerUpgrade();
    } else {
      window.open("https://matchwise-ai.vercel.app/", "_blank");
    }
  };

  const handleViewSample = () => {
    if (!isAuthenticated) {
      triggerLogin();
    } else {
      onViewSample();
    }
  };

  return (
    <div className="h-full overflow-y-auto bg-white">
      <div className="max-w-6xl mx-auto p-8">
        <button onClick={onBack} className="flex items-center gap-2 text-gray-500 hover:text-gray-900 mb-6 transition-colors">
            <ChevronLeft size={16} /> Back to Interview
        </button>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            {/* Left: Content */}
            <div className="space-y-6">
                <div className="inline-block px-3 py-1 bg-indigo-50 text-indigo-700 text-xs font-bold rounded-full uppercase tracking-wider">
                    Powered by Gemini 1.5 Pro
                </div>
                <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight leading-tight">
                    MatchWise: <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
                        Tailor Your Resume with AI
                    </span>
                </h1>
                <p className="text-lg text-gray-600 leading-relaxed">
                    An AI-Powered Resume Comparison Platform (RCP) that provides intelligent job application assistance. We optimize your resume & cover letter for specific job postings to get past ATS and impress recruiters.
                </p>

                <ul className="space-y-3">
                    {['ATS Keyword Optimization', 'Match Score Analysis', 'Tailored Cover Letters', 'Gap Analysis'].map((item, i) => (
                        <li key={i} className="flex items-center gap-3 text-gray-700">
                            <CheckCircle2 className="w-5 h-5 text-green-500" />
                            {item}
                        </li>
                    ))}
                </ul>

                <div className="flex gap-4 pt-4">
                    <button 
                        onClick={handleTryLive}
                        className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gray-900 text-white font-semibold rounded-xl hover:bg-gray-800 transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
                    >
                        Try MatchWise Live <ExternalLink size={16} />
                    </button>
                    <button 
                        onClick={handleViewSample}
                        className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-white border border-gray-200 text-gray-700 font-semibold rounded-xl hover:bg-gray-50 transition-all"
                    >
                        View Sample Analysis
                    </button>
                </div>
            </div>

            {/* Right: Visual Demo */}
            <div className="relative">
                <div className="absolute -inset-4 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-3xl blur-2xl opacity-50"></div>
                <div className="relative bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden">
                    {/* Mock Browser Header */}
                    <div className="bg-gray-50 border-b border-gray-100 px-4 py-3 flex gap-2">
                        <div className="w-3 h-3 rounded-full bg-red-400"></div>
                        <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                        <div className="w-3 h-3 rounded-full bg-green-400"></div>
                    </div>
                    {/* Content Preview */}
                    <div className="p-6 space-y-4">
                        <div className="flex justify-between items-center">
                            <div className="h-4 w-32 bg-gray-200 rounded"></div>
                            <div className="h-8 w-16 bg-green-100 text-green-700 rounded flex items-center justify-center font-bold text-sm">94% Match</div>
                        </div>
                        <div className="space-y-2">
                            <div className="h-3 w-full bg-gray-100 rounded"></div>
                            <div className="h-3 w-5/6 bg-gray-100 rounded"></div>
                            <div className="h-3 w-4/6 bg-gray-100 rounded"></div>
                        </div>
                        <div className="p-4 bg-blue-50 rounded-xl border border-blue-100">
                            <h4 className="text-sm font-bold text-blue-800 mb-2">AI Suggestion</h4>
                            <p className="text-xs text-blue-600">
                                Add "TensorFlow" and "Kubernetes" to your skills section to match the Senior AI Engineer requirements found in the job description.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
};