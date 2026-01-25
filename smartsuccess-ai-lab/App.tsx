import React, { useState } from 'react';
import { SkillsLabPage } from './components/SkillsLabPage';
import { Workspace } from './components/Workspace';
import { ResultsView } from './components/ResultsView';
import { Challenge, ViewState } from './types';
import { MOCK_RESULTS } from './constants';
import { Loader2 } from 'lucide-react';

const App: React.FC = () => {
  const [view, setView] = useState<ViewState>('dashboard');
  const [activeChallenge, setActiveChallenge] = useState<Challenge | null>(null);
  const [isScoring, setIsScoring] = useState(false);
  const [completedChallenges, setCompletedChallenges] = useState<string[]>([]);

  const handleSelectChallenge = (challenge: Challenge) => {
    setActiveChallenge(challenge);
    setView('workspace');
  };

  const handleSubmit = () => {
    setIsScoring(true);
    // Simulate backend scoring delay
    setTimeout(() => {
      setIsScoring(false);
      if (activeChallenge) {
        setCompletedChallenges(prev => [...new Set([...prev, activeChallenge.id])]);
      }
      setView('results');
    }, 2000);
  };

  const handleBackToHome = () => {
    setView('dashboard');
    setActiveChallenge(null);
  };

  if (isScoring) {
    return (
      <div className="h-screen w-full flex flex-col items-center justify-center bg-gray-50">
        <Loader2 className="w-12 h-12 text-purple-600 animate-spin mb-4" />
        <h2 className="text-xl font-bold text-gray-800">Analyzing Solution...</h2>
        <p className="text-gray-500 mt-2">Running test cases and AI architectural review</p>
      </div>
    );
  }

  return (
    <>
      {view === 'dashboard' && (
        <SkillsLabPage 
          onBackToHome={() => console.log('Already on home')} 
          onSelectChallenge={handleSelectChallenge}
          completedChallenges={completedChallenges}
        />
      )}
      
      {view === 'workspace' && activeChallenge && (
        <Workspace 
          challenge={activeChallenge}
          onExit={handleBackToHome}
          onSubmit={handleSubmit}
        />
      )}

      {view === 'results' && (
        <ResultsView 
          result={MOCK_RESULTS as any} // Using mock results for demo
          onHome={handleBackToHome}
        />
      )}
    </>
  );
};

export default App;
