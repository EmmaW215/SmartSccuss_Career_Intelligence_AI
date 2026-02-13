import React, { useState } from 'react';
import { ViewState, InterviewType, LabViewState, LabChallenge } from './types';
import { Sidebar } from './components/Sidebar';
import { LandingPage } from './views/LandingPage';
import { InterviewPage } from './views/InterviewPage';
import { DashboardPage } from './views/DashboardPage';
import { DemoPage } from './views/DemoPage';
import { LabSkillsLabPage } from './views/LabSkillsLabPage';
import { LabWorkspace } from './views/LabWorkspace';
import { LabResultsView } from './views/LabResultsView';
import { SampleAnalysisPage } from './views/SampleAnalysisPage';
import MatchwiseApp from './views/matchwise/MatchwiseApp';
import { AuthProvider } from './contexts/AuthContext';
import { AccessModals } from './components/AccessModals';
import { LAB_MOCK_RESULTS } from './constants/labChallenges';

function AppContent() {
  const [currentView, setCurrentView] = useState<ViewState>('landing');
  const [selectedInterviewType, setSelectedInterviewType] = useState<InterviewType>(InterviewType.SCREENING);
  // Lab-specific state management
  const [labView, setLabView] = useState<LabViewState>('lab-dashboard');
  const [activeChallenge, setActiveChallenge] = useState<LabChallenge | null>(null);
  const [completedChallenges, setCompletedChallenges] = useState<string[]>([]);

  const handleNavigate = (view: ViewState) => {
    setCurrentView(view);
  };

  const handleInterviewTypeSelect = (type: InterviewType) => {
    setSelectedInterviewType(type);
    setCurrentView('interview');
  };

  // If on Landing Page, render it fully without sidebar
  if (currentView === 'landing') {
    return (
      <LandingPage 
        onEnterApp={() => setCurrentView('lab')} 
        onNavigateToView={(view) => setCurrentView(view)}
      />
    );
  }

  // Inner App Layout
  return (
    <div className="flex h-screen w-full bg-gray-50 overflow-hidden font-sans">
      <AccessModals />
      <Sidebar 
        currentView={currentView}
        onNavigate={handleNavigate}
        onInterviewTypeSelect={handleInterviewTypeSelect}
        selectedInterviewType={selectedInterviewType}
      />
      
      <main className="flex-1 h-full overflow-hidden relative">
        {/* Decorative background element for "High Tech" feel */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-gradient-to-b from-blue-50 to-transparent rounded-full blur-3xl opacity-50 pointer-events-none -z-10 translate-x-1/3 -translate-y-1/3"></div>

        {currentView === 'interview' && (
          <InterviewPage 
            interviewType={selectedInterviewType} 
            onNavigateToDashboard={() => setCurrentView('dashboard')}
          />
        )}
        
        {currentView === 'dashboard' && (
          <DashboardPage onBack={() => setCurrentView('interview')} />
        )}
        
        {currentView === 'demo' && (
          <DemoPage 
            onBack={() => setCurrentView('interview')} 
            onViewSample={() => setCurrentView('sample-analysis')}
            onTryLive={() => setCurrentView('matchwise-live')}
          />
        )}

        {currentView === 'matchwise-live' && (
          <MatchwiseApp onBack={() => setCurrentView('demo')} />
        )}

        {currentView === 'lab' && (
          <>
            {labView === 'lab-dashboard' && (
              <LabSkillsLabPage 
                onBackToHome={() => setCurrentView('landing')}
                onSelectChallenge={(challenge) => {
                  setActiveChallenge(challenge);
                  setLabView('lab-workspace');
                }}
                completedChallenges={completedChallenges}
              />
            )}
            {labView === 'lab-workspace' && activeChallenge && (
              <LabWorkspace 
                challenge={activeChallenge}
                onExit={() => {
                  setLabView('lab-dashboard');
                  setActiveChallenge(null);
                }}
                onSubmit={() => {
                  if (activeChallenge) {
                    setCompletedChallenges(prev => [...new Set([...prev, activeChallenge.id])]);
                  }
                  setLabView('lab-results');
                }}
              />
            )}
            {labView === 'lab-results' && (
              <LabResultsView 
                result={LAB_MOCK_RESULTS as any}
                onHome={() => {
                  setLabView('lab-dashboard');
                  setActiveChallenge(null);
                }}
              />
            )}
          </>
        )}

        {currentView === 'sample-analysis' && (
          <SampleAnalysisPage onBack={() => setCurrentView('demo')} />
        )}
      </main>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;