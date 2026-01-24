import React, { useEffect, useState, useRef } from "react";
import { onAuthStateChanged, User, GoogleAuthProvider, signInWithPopup, signOut } from "firebase/auth";
import { auth } from "./firebase";
import { loadStripe } from '@stripe/stripe-js';
import { UploadCloud, FileText, Loader2, LogOut, ChevronRight } from 'lucide-react';

import VisitorCounter from './components/VisitorCounter';
import LoginModal from './components/LoginModal';
import UpgradeModal from './components/UpgradeModal';
import ResultsDisplay from './components/ResultsDisplay';
import { useParentMessage } from './hooks/useParentMessage';
import { ComparisonResponse, UserStatus } from './types';

// Constants
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'https://resume-matcher-backend-rrrw.onrender.com';
const STRIPE_KEY = process.env.REACT_APP_STRIPE_KEY || 'pk_test_51RnB7HE6OOEHr6ZoCxyyExample'; // Replace with actual key from env or dashboard

const App: React.FC = () => {
  const [jobText, setJobText] = useState('');
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ComparisonResponse | null>(null);
  
  // Modals
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [loginMessage, setLoginMessage] = useState('');
  
  // User State
  const [user, setUser] = useState<User | null>(null);
  const [userStatus, setUserStatus] = useState<UserStatus | null>(null);
  const [userStatusLoading, setUserStatusLoading] = useState(false);
  const [anonymousTrialUsed, setAnonymousTrialUsed] = useState(false);
  
  // UI State
  const [showVisitorCounter, setShowVisitorCounter] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);

  // Initialize
  useEffect(() => {
    const trialUsed = localStorage.getItem('anonymousTrialUsed') === 'true';
    setAnonymousTrialUsed(trialUsed);

    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      setUser(firebaseUser);
    });
    return () => unsubscribe();
  }, []);

  // Clear errors when user changes
  useEffect(() => {
    setError('');
    setShowUpgradeModal(false);
  }, [user]);

  // Fetch User Status
  useEffect(() => {
    if (user) {
      console.log('🔄 Loading user status for:', user.uid);
      setUserStatusLoading(true);
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);
      
      fetch(`${BACKEND_URL}/api/user/status?uid=${user.uid}`, { signal: controller.signal })
        .then(res => res.json())
        .then(data => {
          if (data.error) {
            console.error('❌ Error fetching user status:', data.error);
            setUserStatus({
              trialUsed: false,
              isUpgraded: false,
              planType: null,
              scanLimit: null,
              scansUsed: 0,
              lastScanMonth: new Date().toISOString().slice(0, 7)
            });
          } else {
            setUserStatus(data);
          }
        })
        .catch((error) => {
          console.error('❌ Failed to fetch user status:', error);
          setUserStatus({
            trialUsed: false,
            isUpgraded: false,
            planType: null,
            scanLimit: null,
            scansUsed: 0,
            lastScanMonth: new Date().toISOString().slice(0, 7)
          });
        })
        .finally(() => {
          clearTimeout(timeoutId);
          setUserStatusLoading(false);
        });
    } else {
      setUserStatus(null);
      setUserStatusLoading(false);
    }
  }, [user]);

  // Parent Window Communication
  useParentMessage({
    showLoginModal: (message) => {
      setShowLoginModal(true);
      if (message) setLoginMessage(message);
    },
    hideVisitorCounter: () => setShowVisitorCounter(false),
  });

  // Logic Helpers
  const canGenerate = () => {
    if (!user) return !anonymousTrialUsed;
    if (!userStatus) return true; // Fail open while loading
    if (!userStatus.trialUsed) return true;
    if (userStatus.isUpgraded) {
      if (userStatus.scanLimit === null) return true;
      return userStatus.scansUsed < userStatus.scanLimit;
    }
    return false;
  };

  const getErrorMessage = () => {
    if (!user) {
      if (anonymousTrialUsed) return 'Your free trial is finished. Please sign in and upgrade to continue!';
      return '';
    }
    if (!userStatus) return 'Loading user status...';
    if (userStatus.trialUsed && !userStatus.isUpgraded) {
      return 'Your free trial is finished. Please upgrade to continue using MatchWise!';
    }
    if (userStatus.isUpgraded && userStatus.scanLimit !== null && userStatus.scansUsed >= userStatus.scanLimit) {
      return 'You have reached your monthly scan limit.';
    }
    return '';
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
    if (user) formData.append('uid', user.uid);

    setLoading(true);
    setError('');
    setResponse(null);

    try {
      const apiResponse = await fetch(`${BACKEND_URL}/api/compare`, {
        method: 'POST',
        body: formData,
      });
      
      if (!apiResponse.ok) {
        const errorData = await apiResponse.json();
        throw new Error(errorData.error || 'Failed to fetch comparison');
      }
      
      const data = await apiResponse.json();
      setResponse(data);

      // Update Local State
      if (!user) {
        localStorage.setItem('anonymousTrialUsed', 'true');
        setAnonymousTrialUsed(true);
      } else {
        // Optimistic update - in real app backend handles usage counting, we just refresh status
        await fetch(`${BACKEND_URL}/api/user/use-trial?uid=${user.uid}`, { method: "POST" });
        const statusResponse = await fetch(`${BACKEND_URL}/api/user/status?uid=${user.uid}`);
        const statusData = await statusResponse.json();
        if (!statusData.error) setUserStatus(statusData);
      }

    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
      setError(errorMessage.includes('403') ? 'Insufficient credits. Please contact support.' : errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleAuth = async (action: 'login' | 'logout') => {
    if (action === 'logout') {
      await signOut(auth);
      setResponse(null);
      setJobText('');
      setResumeFile(null);
    } else {
      try {
        await signInWithPopup(auth, new GoogleAuthProvider());
      } catch (e: any) {
        alert("Login failed: " + e.message);
      }
    }
  };

  // Stripe Logic
  const handleUpgrade = async (priceId: string, mode: 'payment' | 'subscription') => {
    if (!user) {
      setShowLoginModal(true);
      setLoginMessage("Please sign in to upgrade your plan.");
      return;
    }
    try {
      const res = await fetch(`${BACKEND_URL}/api/create-checkout-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ uid: user.uid, price_id: priceId, mode })
      });
      const data = await res.json();
      if (data.checkout_url) window.open(data.checkout_url, '_blank');
      else alert('Failed to create checkout session');
    } catch (e) {
      alert('Error connecting to payment server');
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 text-gray-900 font-sans relative">
      {/* Background with placeholder if image missing */}
      <div 
        className="absolute inset-0 z-0 bg-cover bg-center opacity-10 pointer-events-none"
        style={{ backgroundImage: `url('/Job_Search_Pic.png'), linear-gradient(to bottom right, #eff6ff, #f5f3ff)` }}
      />
      
      {/* Header */}
      <header className="relative z-20 w-full px-6 py-4 flex justify-between items-center bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0">
        <div className="flex items-center gap-2">
           <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-lg">M</div>
           <span className="font-bold text-xl text-gray-800 tracking-tight">MatchWise</span>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="hidden sm:block">
            <VisitorCounter isVisible={showVisitorCounter} />
          </div>

          {!user ? (
            <button
              onClick={() => handleAuth('login')}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-full shadow-md transition-all transform hover:scale-105"
            >
              Sign In
            </button>
          ) : (
            <div className="flex items-center gap-4">
              <div className="hidden md:flex flex-col items-end mr-2">
                 <span className="text-sm font-semibold text-gray-800">{user.displayName}</span>
                 {userStatus?.isUpgraded && (
                    <span className="text-xs text-green-600 font-medium bg-green-50 px-2 py-0.5 rounded-full border border-green-100">
                       {userStatus.planType === 'pro' ? 'Pro Plan' : 'Basic Plan'}
                    </span>
                 )}
              </div>
              {user.photoURL ? (
                <img src={user.photoURL} alt="User" className="w-9 h-9 rounded-full border-2 border-white shadow-sm" />
              ) : (
                <div className="w-9 h-9 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold">
                  {user.email?.[0].toUpperCase()}
                </div>
              )}
              <button
                onClick={() => handleAuth('logout')}
                className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-full transition-colors"
                title="Sign Out"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          )}
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
              <label htmlFor="jobText" className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-500" />
                Job Description
              </label>
              <textarea
                id="jobText"
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
                id="resume"
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
                {(error.includes('upgrade') || error.includes('limit')) && (
                  <button
                    type="button"
                    onClick={() => user ? setShowUpgradeModal(true) : handleAuth('login')}
                    className="text-xs bg-red-100 hover:bg-red-200 text-red-700 px-3 py-1 rounded-full transition-colors font-bold"
                  >
                    Upgrade Now
                  </button>
                )}
              </div>
            )}
            
            {/* Generate Button */}
            <button
              type="submit"
              disabled={loading || Boolean(user && userStatusLoading)}
              className="w-full py-4 px-6 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold text-lg rounded-xl shadow-lg hover:shadow-xl transition-all disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2 group"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Analyzing...
                </>
              ) : userStatusLoading ? (
                'Checking Status...'
              ) : (
                <>
                  Generate Analysis
                  <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
            
            {/* Usage Stats */}
            {user && userStatus && userStatus.isUpgraded && userStatus.scanLimit !== null && (
              <div className="text-center text-xs text-gray-400">
                Monthly Usage: <span className="font-medium text-gray-600">{userStatus.scansUsed}</span> / {userStatus.scanLimit} scans
              </div>
            )}
          </form>
        </div>

        {/* Results Section */}
        {response && <ResultsDisplay data={response} />}
        
      </main>

      {/* Footer */}
      <footer className="w-full py-6 text-center text-gray-400 text-sm mt-12 bg-gray-50 border-t border-gray-200">
        <p>© {new Date().getFullYear()} MatchWise. All rights reserved.</p>
        <a href="https://smart-success-ai.vercel.app" className="text-blue-400 hover:text-blue-600 transition-colors mt-2 inline-block">
          Powered by SmartSuccess.AI
        </a>
      </footer>

      {/* Modals */}
      {showUpgradeModal && (
        <UpgradeModal 
          onClose={() => setShowUpgradeModal(false)}
          onUpgradeOneTime={() => handleUpgrade('price_1RnBbcE6OOEHr6Zo6igE1U8B', 'payment')}
          onUpgradeSub6={() => handleUpgrade('price_1RnBehE6OOEHr6Zo4QLLJZTg', 'payment')} // Note: Original code used payment mode for sub 6, likely specific stripe config
          onUpgradeSub15={() => handleUpgrade('price_1RnBgPE6OOEHr6Zo9EFmgyA5', 'subscription')}
        />
      )}
      
      {showLoginModal && (
        <LoginModal 
          onClose={() => setShowLoginModal(false)}
          message={loginMessage}
        />
      )}
    </div>
  );
};

export default App;
