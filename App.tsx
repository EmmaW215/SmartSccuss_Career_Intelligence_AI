import React, { useState } from 'react';
import { ViewState, InterviewType } from './types';
import { Sidebar } from './components/Sidebar';
import { LandingPage } from './views/LandingPage';
import { InterviewPage } from './views/InterviewPage';
import { DashboardPage } from './views/DashboardPage';
import { DemoPage } from './views/DemoPage';
import { SkillsLabPage } from './views/SkillsLabPage';
import { AuthProvider } from './contexts/AuthContext';

function AppContent() {
  const [currentView, setCurrentView] = useState<ViewState>('landing');
  const [selectedInterviewType, setSelectedInterviewType] = useState<InterviewType>(InterviewType.SCREENING);

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
          <DemoPage onBack={() => setCurrentView('interview')} />
        )}

        {currentView === 'lab' && (
          <SkillsLabPage onBackToHome={() => setCurrentView('landing')} />
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