import React from 'react';
import { ArrowRight, Upload, CheckCircle, LogIn } from 'lucide-react';
import SimpleVisitorCounter from '../components/SimpleVisitorCounter';
import { ViewState } from '../types';
import { useAuth } from '../contexts/AuthContext';

interface LandingPageProps {
  onEnterApp: () => void;
  onNavigateToView: (view: ViewState) => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onEnterApp, onNavigateToView }) => {
  const { user, login, isLoading, isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen flex flex-col font-sans text-gray-800 bg-white relative">
      {/* Background Image */}
      <div 
        className="fixed inset-0 z-0"
        style={{
          backgroundImage: 'url(/Job_Search_Pic.png)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
          opacity: 0.1
        }}
      />
      
      {/* Content Container with z-index to appear above background */}
      <div className="relative z-10 flex flex-col min-h-screen">
      {/* Navigation */}
      <nav className="w-full px-8 py-5 flex justify-between items-center bg-white/80 backdrop-blur-md sticky top-0 z-50 border-b border-gray-100">
        <div className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent cursor-pointer" onClick={() => onNavigateToView('landing')}>
          SmartSuccess.AI
        </div>
        <div className="flex items-center gap-6">
          <SimpleVisitorCounter />
          <a href="#" className="text-gray-600 hover:text-blue-600 text-sm font-medium">About</a>
          <a href="#" className="text-gray-600 hover:text-blue-600 text-sm font-medium">Pricing</a>
          
          <button 
            onClick={isAuthenticated ? () => onNavigateToView('dashboard') : login}
            disabled={isLoading}
            className="flex items-center gap-2 px-5 py-2.5 bg-gray-900 text-white text-sm font-semibold rounded-full hover:bg-gray-800 transition-all shadow-lg hover:shadow-xl disabled:opacity-70"
          >
            {isLoading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            ) : <LogIn size={16} />}
            {isAuthenticated ? `Welcome, ${user?.name.split(' ')[0]}` : "Guest user Login/Sign up"}
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 text-center mt-12 mb-20">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 text-blue-600 text-xs font-bold uppercase tracking-wider mb-6">
           <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse"></span>
           New: AI Voice Mock Interviews
        </div>
        
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-gray-900 mb-6 max-w-4xl">
          Master Your <span className="text-blue-600">AI Career</span> <br/>
          With Intelligent Coaching
        </h1>
        
        <p className="text-xl text-gray-500 max-w-2xl mb-10 leading-relaxed">
          Precision-Engineered Career Intelligence Platform for the AI Era. Optimize your application, master the interview, and architect your future: mastery for the next generation of AI leaders.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 w-full max-w-md mx-auto">
            <button 
                onClick={onEnterApp}
                className="group relative flex-1 flex items-center justify-center gap-2 px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-lg font-bold rounded-xl shadow-blue-200 shadow-xl hover:shadow-2xl hover:scale-[1.02] transition-all overflow-hidden"
            >
                {/* Flowing light effect */}
                <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-r from-transparent via-white/25 to-transparent -translate-x-full animate-shimmer z-0"></div>
                
                <span className="relative z-10 flex items-center gap-2">
                    Start your Intelligent Journey <ArrowRight size={20} />
                </span>
            </button>
        </div>

        {/* Feature Cards / Mock UI */}
        <div className="mt-24 w-full max-w-5xl grid grid-cols-1 md:grid-cols-2 gap-8 px-4">
            {/* Card 1: Resume - Clickable */}
            <div 
                onClick={() => onNavigateToView('demo')}
                className="bg-white p-8 rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-100 text-left hover:border-blue-300 hover:shadow-2xl hover:shadow-blue-500/10 transition-all group cursor-pointer active:scale-[0.98]"
            >
                <div className="w-12 h-12 bg-orange-100 rounded-2xl flex items-center justify-center text-orange-600 mb-6 group-hover:scale-110 group-hover:bg-orange-600 group-hover:text-white transition-all">
                    <Upload size={24} />
                </div>
                <h3 className="text-2xl font-bold mb-3 text-gray-900 flex items-center gap-2">
                    Resume Tailoring
                    <ArrowRight size={20} className="opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all text-blue-600" />
                </h3>
                <p className="text-gray-500 mb-6">Upload your resume and a job URL. Our AI compares them and rewrites your bullet points to match the job description perfectly.</p>
                <div className="h-32 bg-gray-50 rounded-xl border border-gray-100 relative overflow-hidden group-hover:bg-blue-50/30 transition-colors">
                    <div className="absolute top-4 left-4 right-4 h-2 bg-gray-200 rounded group-hover:bg-blue-200 transition-colors"></div>
                    <div className="absolute top-8 left-4 w-2/3 h-2 bg-gray-200 rounded group-hover:bg-blue-200 transition-colors"></div>
                    <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-white to-transparent group-hover:from-blue-50/50"></div>
                </div>
            </div>

            {/* Card 2: Interview - Clickable */}
            <div 
                onClick={() => onNavigateToView('interview')}
                className="bg-white p-8 rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-100 text-left hover:border-purple-300 hover:shadow-2xl hover:shadow-purple-500/10 transition-all group cursor-pointer active:scale-[0.98]"
            >
                <div className="w-12 h-12 bg-purple-100 rounded-2xl flex items-center justify-center text-purple-600 mb-6 group-hover:scale-110 group-hover:bg-purple-600 group-hover:text-white transition-all">
                    <CheckCircle size={24} />
                </div>
                <h3 className="text-2xl font-bold mb-3 text-gray-900 flex items-center gap-2">
                    Mock Interviews
                    <ArrowRight size={20} className="opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all text-purple-600" />
                </h3>
                <p className="text-gray-500 mb-6">Practice with our Voice AI. Choose from Behavioral, Technical, or Screening modes and get real-time feedback on your answers.</p>
                <div className="h-32 bg-gray-50 rounded-xl border border-gray-100 flex items-center justify-center relative overflow-hidden group-hover:bg-purple-50/30 transition-colors">
                    <div className="flex gap-1 items-end h-8">
                        <div className="w-1 bg-purple-400 h-4 rounded-full animate-[bounce_1s_infinite] group-hover:bg-purple-600"></div>
                        <div className="w-1 bg-purple-400 h-8 rounded-full animate-[bounce_1.2s_infinite] group-hover:bg-purple-600"></div>
                        <div className="w-1 bg-purple-400 h-6 rounded-full animate-[bounce_0.8s_infinite] group-hover:bg-purple-600"></div>
                        <div className="w-1 bg-purple-400 h-3 rounded-full animate-[bounce_1.1s_infinite] group-hover:bg-purple-600"></div>
                    </div>
                </div>
            </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-12 border-t border-gray-100 text-center text-gray-400 text-sm">
        <p>© 2024 SmartSuccess.AI. Empowering AI Careers.</p>
      </footer>
      </div>
    </div>
  );
};