import React, { useState } from 'react';
import { Beaker, ChevronLeft, ArrowRight, Code2, Cpu, BrainCircuit, CheckCircle2, Home, Search, Filter } from 'lucide-react';
import SimpleVisitorCounter from '../components/SimpleVisitorCounter';

interface SkillsLabPageProps {
  onBackToHome: () => void;
}

const CHALLENGES = [
  {
    id: '1',
    title: 'RAG Implementation Logic',
    category: 'Architecture',
    difficulty: 'Advanced',
    icon: Cpu,
    description: 'Design a scalable Retrieval-Augmented Generation pipeline for a private dataset of 10M documents.',
    reward: 'Level 4 Badge'
  },
  {
    id: '2',
    title: 'Prompt Engineering Optimization',
    category: 'NLP',
    difficulty: 'Intermediate',
    icon: BrainCircuit,
    description: 'Optimize a system prompt to reduce hallucination rates in a customer support chatbot by at least 25%.',
    reward: 'NLP Specialist'
  },
  {
    id: '3',
    title: 'Fine-Tuning Llama 3',
    category: 'Model Training',
    difficulty: 'Expert',
    icon: Code2,
    description: 'Select the optimal hyper-parameters for LoRA fine-tuning on a specific medical terminology dataset.',
    reward: 'Model Mastery'
  },
  {
    id: '4',
    title: 'AI Agent Orchestration',
    category: 'Agents',
    difficulty: 'Intermediate',
    icon: BrainCircuit,
    description: 'Build a multi-agent system where a "Planner" delegates tasks to "Executors" with clear feedback loops.',
    reward: 'Architect Junior'
  }
];

export const SkillsLabPage: React.FC<SkillsLabPageProps> = ({ onBackToHome }) => {
  const [selectedTask, setSelectedTask] = useState<string | null>(null);
  const [submissionStatus, setSubmissionStatus] = useState<'idle' | 'submitting' | 'done'>('idle');

  const handleSubmit = () => {
    setSubmissionStatus('submitting');
    setTimeout(() => {
      setSubmissionStatus('done');
      setTimeout(() => {
        setSubmissionStatus('idle');
        setSelectedTask(null);
      }, 2000);
    }, 1500);
  };

  return (
    <div className="h-full overflow-y-auto bg-gray-50/30">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-8 py-6 sticky top-0 z-20 backdrop-blur-sm bg-white/90">
        <div className="flex justify-between items-center max-w-7xl mx-auto">
          <div className="flex items-center gap-4">
            <button 
              onClick={onBackToHome}
              className="p-2 hover:bg-gray-100 rounded-lg text-gray-500 transition-colors"
              title="Back to Home"
            >
              <Home size={20} />
            </button>
            <div>
              <div className="flex items-center gap-2">
                <Beaker className="text-purple-600 w-5 h-5" />
                <h1 className="text-2xl font-bold text-gray-900 tracking-tight">AI Skills Lab</h1>
              </div>
              <p className="text-sm text-gray-500">Validate your expertise through real-world AI architecture and engineering tasks.</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <SimpleVisitorCounter />
            <div className="flex items-center gap-2 bg-purple-50 px-3 py-1.5 rounded-full border border-purple-100">
              <span className="w-2 h-2 bg-purple-600 rounded-full animate-pulse"></span>
              <span className="text-xs font-bold text-purple-700">Lab Status: Active</span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-8">
        {/* Search and Filters */}
        <div className="flex flex-col md:flex-row gap-4 mb-8">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input 
              type="text" 
              placeholder="Search challenges (e.g. RAG, Fine-tuning...)" 
              className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 outline-none transition-all text-sm"
            />
          </div>
          <div className="flex gap-2">
            <button className="flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50">
              <Filter size={14} /> Difficulty
            </button>
            <button className="flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50">
              Category
            </button>
          </div>
        </div>

        {/* Challenge Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6">
          {CHALLENGES.map((challenge) => (
            <div 
              key={challenge.id}
              className={`group bg-white rounded-2xl border transition-all duration-300 overflow-hidden hover:shadow-xl hover:shadow-purple-500/5 ${
                selectedTask === challenge.id ? 'border-purple-500 ring-2 ring-purple-500/10' : 'border-gray-100'
              }`}
            >
              <div className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <div className={`p-3 rounded-xl transition-colors ${
                    selectedTask === challenge.id ? 'bg-purple-600 text-white' : 'bg-purple-50 text-purple-600'
                  }`}>
                    <challenge.icon size={24} />
                  </div>
                  <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                    challenge.difficulty === 'Expert' ? 'bg-red-50 text-red-600' :
                    challenge.difficulty === 'Advanced' ? 'bg-orange-50 text-orange-600' :
                    'bg-green-50 text-green-600'
                  }`}>
                    {challenge.difficulty}
                  </span>
                </div>
                
                <h3 className="text-lg font-bold text-gray-900 mb-2">{challenge.title}</h3>
                <p className="text-sm text-gray-500 mb-6 line-clamp-2">{challenge.description}</p>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs text-purple-700 font-semibold bg-purple-50 px-2 py-1 rounded-md">
                    <CheckCircle2 size={12} />
                    {challenge.reward}
                  </div>
                  <button 
                    onClick={() => setSelectedTask(challenge.id)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                      selectedTask === challenge.id 
                      ? 'bg-purple-600 text-white' 
                      : 'bg-gray-900 text-white hover:bg-purple-600'
                    }`}
                  >
                    {selectedTask === challenge.id ? 'Task Active' : 'Select Challenge'} 
                    <ArrowRight size={14} />
                  </button>
                </div>
              </div>

              {/* Task Details / Submission View */}
              {selectedTask === challenge.id && (
                <div className="px-6 pb-6 pt-2 border-t border-gray-50 bg-purple-50/30 animate-in slide-in-from-top-4 duration-300">
                  <div className="bg-white p-4 rounded-xl border border-purple-100 shadow-inner mt-4">
                    <label className="block text-xs font-bold text-gray-400 uppercase mb-2">Solution Draft / Architecture Diagram URL</label>
                    <textarea 
                      placeholder="Paste your architecture summary or Git link here..."
                      className="w-full h-32 p-3 text-sm border border-gray-100 rounded-lg focus:ring-2 focus:ring-purple-500/20 outline-none resize-none bg-gray-50/50 font-mono"
                    />
                    <div className="mt-4 flex justify-end gap-3">
                      <button 
                        onClick={() => setSelectedTask(null)}
                        className="px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-700"
                      >
                        Cancel
                      </button>
                      <button 
                        onClick={handleSubmit}
                        disabled={submissionStatus !== 'idle'}
                        className={`px-6 py-2 rounded-lg text-sm font-bold text-white transition-all flex items-center gap-2 ${
                          submissionStatus === 'done' ? 'bg-green-500' : 'bg-purple-600 hover:bg-purple-700'
                        }`}
                      >
                        {submissionStatus === 'submitting' ? (
                          <>
                            <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                            Verifying...
                          </>
                        ) : submissionStatus === 'done' ? (
                          <>
                            <CheckCircle2 size={14} />
                            Verified
                          </>
                        ) : (
                          'Submit Task'
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};