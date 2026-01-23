import React from 'react';
import { X, CheckCircle, Lock, Crown, LogIn } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export const AccessModals: React.FC = () => {
  const { 
    showLoginModal, setShowLoginModal, login, isLoading,
    showUpgradeModal, setShowUpgradeModal, upgradeToPro, user
  } = useAuth();

  if (!showLoginModal && !showUpgradeModal) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm">
      
      {/* Login / Signup Modal */}
      {showLoginModal && (
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
          <div className="p-6 bg-gradient-to-r from-blue-600 to-indigo-600 text-white flex justify-between items-start">
            <div>
              <h2 className="text-xl font-bold">Join SmartSuccess.AI</h2>
              <p className="text-blue-100 text-sm mt-1">Save your progress and unlock career tools.</p>
            </div>
            <button onClick={() => setShowLoginModal(false)} className="text-white/80 hover:text-white">
              <X size={20} />
            </button>
          </div>
          
          <div className="p-8">
            <div className="space-y-4 mb-6">
              <div className="flex items-center gap-3 text-gray-600 text-sm">
                <CheckCircle size={18} className="text-green-500" />
                <span>Save interview history and resume analysis</span>
              </div>
              <div className="flex items-center gap-3 text-gray-600 text-sm">
                <CheckCircle size={18} className="text-green-500" />
                <span>Access Dashboard Analytics</span>
              </div>
              <div className="flex items-center gap-3 text-gray-600 text-sm">
                <CheckCircle size={18} className="text-green-500" />
                <span>Personalized AI Coaching</span>
              </div>
            </div>

            <p className="text-center text-gray-500 text-sm mb-6">Guest user, please sign up or log in to continue.</p>

            <button
              onClick={login}
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-3 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-semibold py-3 px-4 rounded-xl transition-all shadow-sm hover:shadow-md"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin"></div>
              ) : (
                <>
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                  </svg>
                  Sign in with Google
                </>
              )}
            </button>
            <p className="text-center text-xs text-gray-400 mt-4">
              By signing in, you agree to our Terms and Privacy Policy.
            </p>
          </div>
        </div>
      )}

      {/* Upgrade to Pro Modal */}
      {showUpgradeModal && (
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in duration-200">
          <div className="relative h-32 bg-gradient-to-br from-indigo-900 via-purple-800 to-indigo-900 flex items-center justify-center overflow-hidden">
             <div className="absolute top-0 left-0 w-full h-full opacity-30 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]"></div>
             <div className="relative z-10 text-center">
                 <div className="inline-flex p-3 bg-white/10 rounded-full backdrop-blur-md mb-2 shadow-xl">
                    <Crown size={32} className="text-yellow-400" fill="currentColor" />
                 </div>
                 <h2 className="text-2xl font-bold text-white tracking-tight">Upgrade to Pro</h2>
             </div>
             <button onClick={() => setShowUpgradeModal(false)} className="absolute top-4 right-4 text-white/60 hover:text-white">
                <X size={20} />
             </button>
          </div>

          <div className="p-8">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Unlock the Full Power of AI</h3>
            <p className="text-gray-500 mb-6">You've discovered a Pro feature! Subscribe now to access advanced tools and limitless preparation.</p>

            <div className="grid grid-cols-2 gap-4 mb-8">
                <div className="p-3 bg-purple-50 rounded-xl border border-purple-100">
                    <h4 className="font-bold text-purple-700 text-sm mb-1">Live Resume Match</h4>
                    <p className="text-xs text-purple-600">Real-time matching with external sites.</p>
                </div>
                <div className="p-3 bg-blue-50 rounded-xl border border-blue-100">
                    <h4 className="font-bold text-blue-700 text-sm mb-1">Voice Customization</h4>
                    <p className="text-xs text-blue-600">Speak naturally in custom scenarios.</p>
                </div>
                <div className="p-3 bg-indigo-50 rounded-xl border border-indigo-100">
                    <h4 className="font-bold text-indigo-700 text-sm mb-1">AI Skills Lab</h4>
                    <p className="text-xs text-indigo-600">Full access to architectural challenges.</p>
                </div>
                <div className="p-3 bg-green-50 rounded-xl border border-green-100">
                    <h4 className="font-bold text-green-700 text-sm mb-1">Unlimited Usage</h4>
                    <p className="text-xs text-green-600">No caps on tokens or interviews.</p>
                </div>
            </div>

            <button
                onClick={upgradeToPro}
                disabled={isLoading}
                className="w-full py-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-bold rounded-xl shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2"
            >
                {isLoading ? (
                    <>
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                        Processing Payment...
                    </>
                ) : (
                    <>
                        Subscribe via Stripe
                        <span className="bg-white/20 px-2 py-0.5 rounded text-xs ml-2">$19/mo</span>
                    </>
                )}
            </button>
            <p className="text-center text-xs text-gray-400 mt-4">
                Secure payment powered by Stripe. Cancel anytime.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};