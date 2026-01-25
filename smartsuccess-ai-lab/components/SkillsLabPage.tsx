import React, { useState } from 'react';
import { Beaker, ArrowRight, CheckCircle2, Home, Search, Filter, ChevronDown, Clock, AlertCircle, FileText, Target, CheckSquare, Award } from 'lucide-react';
import SimpleVisitorCounter from '../components/SimpleVisitorCounter';
import { CHALLENGES } from '../constants';
import { Challenge } from '../types';

interface SkillsLabPageProps {
  onBackToHome: () => void;
  onSelectChallenge: (challenge: Challenge) => void;
  completedChallenges: string[];
}

interface AccordionProps {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
}

const Accordion: React.FC<AccordionProps> = ({ title, icon, children, defaultOpen = false, className = "" }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  return (
    <div className={`border rounded-xl mb-3 overflow-hidden border-gray-200 bg-white transition-all ${className}`}>
      <button 
        onClick={() => setIsOpen(!isOpen)} 
        className="w-full flex justify-between items-center p-3.5 bg-gray-50/50 hover:bg-gray-50 text-sm font-semibold text-gray-700 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          {icon}
          {title}
        </div>
        <ChevronDown className={`text-gray-400 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} size={16}/>
      </button>
      {isOpen && (
        <div className="p-4 text-sm text-gray-600 border-t border-gray-100 animate-in slide-in-from-top-1">
          {children}
        </div>
      )}
    </div>
  );
};

export const SkillsLabPage: React.FC<SkillsLabPageProps> = ({ onBackToHome, onSelectChallenge, completedChallenges }) => {
  const [selectedTask, setSelectedTask] = useState<string | null>(null);

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
          {CHALLENGES.map((challenge) => {
            const isCompleted = completedChallenges.includes(challenge.id);
            return (
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
                    <div className="flex flex-col items-end gap-2">
                      <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                        challenge.difficulty === 'Expert' ? 'bg-red-50 text-red-600' :
                        challenge.difficulty === 'Advanced' ? 'bg-orange-50 text-orange-600' :
                        'bg-green-50 text-green-600'
                      }`}>
                        {challenge.difficulty}
                      </span>
                      {isCompleted && (
                        <span className="flex items-center gap-1 text-[10px] font-bold text-green-600 bg-green-50 px-2 py-0.5 rounded-full border border-green-100">
                          <CheckCircle2 size={10} /> Completed
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <h3 className="text-lg font-bold text-gray-900 mb-2">{challenge.title}</h3>
                  <p className="text-sm text-gray-500 mb-6 line-clamp-2">{challenge.description}</p>
                  
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-xs text-purple-700 font-semibold bg-purple-50 px-2 py-1 rounded-md">
                      <CheckCircle2 size={12} />
                      {challenge.reward}
                    </div>
                    <button 
                      onClick={() => setSelectedTask(challenge.id === selectedTask ? null : challenge.id)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                        selectedTask === challenge.id 
                        ? 'bg-purple-600 text-white' 
                        : 'bg-gray-900 text-white hover:bg-purple-600'
                      }`}
                    >
                      {selectedTask === challenge.id ? 'View Details' : 'Select Challenge'} 
                      <ArrowRight size={14} />
                    </button>
                  </div>
                </div>

                {/* Expanded Task Details */}
                {selectedTask === challenge.id && (
                  <div className="px-6 pb-6 pt-2 border-t border-gray-50 bg-purple-50/30 animate-in slide-in-from-top-4 duration-300">
                    
                    {/* Scenario */}
                    <div className="mt-4 mb-6">
                      <h4 className="text-xs font-bold text-purple-700 uppercase tracking-wider mb-2 flex items-center gap-2">
                        <Target size={14} /> Task Requirement Details
                      </h4>
                      <p className="text-sm text-gray-700 bg-white p-4 rounded-xl border border-purple-100 shadow-sm leading-relaxed">
                        <span className="font-semibold text-gray-900 block mb-1">Scenario:</span>
                        {challenge.scenario}
                      </p>
                    </div>

                    {/* Requirements Foldable */}
                    <Accordion title="Requirements" icon={<FileText size={16} className="text-purple-600" />}>
                      <ul className="list-disc pl-4 space-y-1.5 marker:text-purple-500">
                        {challenge.requirements.map((req, idx) => (
                          <li key={idx} className="leading-relaxed">{req}</li>
                        ))}
                      </ul>
                    </Accordion>

                    {/* Expectations Foldable */}
                    <Accordion title="Expectations" icon={<Target size={16} className="text-blue-600" />}>
                      <div className="overflow-hidden rounded-lg border border-gray-200">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-gray-50 text-gray-500 font-semibold border-b border-gray-200">
                            <tr>
                              <th className="px-3 py-2">Aspect</th>
                              <th className="px-3 py-2">Expectation</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">
                            {challenge.expectations.map((exp, idx) => (
                              <tr key={idx} className="bg-white">
                                <td className="px-3 py-2 font-medium text-gray-900">{exp.aspect}</td>
                                <td className="px-3 py-2 text-gray-600">{exp.expectation}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </Accordion>

                    {/* Minimum Pass Foldable */}
                    <Accordion title="Minimum Pass" icon={<CheckSquare size={16} className="text-green-600" />}>
                      <ul className="space-y-2">
                        {challenge.minimumPass.map((pass, idx) => (
                          <li key={idx} className="flex gap-2 items-start">
                             <div className="mt-0.5 w-1.5 h-1.5 rounded-full bg-green-500 shrink-0"></div>
                             <span>{pass}</span>
                          </li>
                        ))}
                      </ul>
                    </Accordion>

                    {/* Time Estimate */}
                    <div className="flex items-center gap-2 mt-4 mb-6 bg-blue-50 text-blue-800 px-4 py-3 rounded-xl text-sm border border-blue-100">
                      <Clock size={16} />
                      <span className="font-semibold">Time Estimate:</span>
                      {challenge.timeEstimate}
                    </div>

                    {/* Ready to Start Block */}
                    <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm mt-4">
                      <h4 className="text-sm font-bold text-gray-900 mb-2">Ready to start?</h4>
                      <p className="text-sm text-gray-500 mb-4">You will be taken to the Workspace where you can design, code, and test your solution with AI assistance.</p>
                      
                      {/* Evaluation Section - Only shown if completed */}
                      {isCompleted && (
                        <div className="mt-4 mb-4 border-t border-gray-100 pt-4">
                          <Accordion 
                            title="Evaluation Results & Criteria" 
                            defaultOpen={true}
                            icon={<Award size={16} className="text-amber-500" />}
                            className="border-amber-200 bg-amber-50/30"
                          >
                            <div className="space-y-4">
                              <div>
                                <h5 className="font-bold text-gray-900 mb-2 text-xs uppercase">Key Points Tested</h5>
                                <ul className="list-disc pl-4 space-y-1 marker:text-amber-500">
                                  {challenge.keyPoints.map((pt, i) => <li key={i}>{pt}</li>)}
                                </ul>
                              </div>
                              
                              <div>
                                <h5 className="font-bold text-gray-900 mb-2 text-xs uppercase">Expected Outputs</h5>
                                <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg text-xs font-mono overflow-x-auto">
                                  {challenge.expectedOutputs}
                                </pre>
                              </div>

                              <div>
                                <h5 className="font-bold text-gray-900 mb-2 text-xs uppercase">Qualification Criteria</h5>
                                <div className="overflow-hidden rounded-lg border border-gray-200">
                                  <table className="w-full text-left text-xs">
                                    <thead className="bg-gray-50 text-gray-500 font-semibold border-b border-gray-200">
                                      <tr>
                                        <th className="px-3 py-2">Level</th>
                                        <th className="px-3 py-2">Criteria</th>
                                        <th className="px-3 py-2">Score/Metric</th>
                                      </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-100">
                                      {challenge.qualificationCriteria.map((c, idx) => (
                                        <tr key={idx} className="bg-white">
                                          <td className="px-3 py-2 font-bold text-gray-900">{c.level}</td>
                                          <td className="px-3 py-2 text-gray-600">{c.criteria}</td>
                                          <td className="px-3 py-2 text-gray-600 font-mono">{c.score}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            </div>
                          </Accordion>
                        </div>
                      )}

                      <div className="mt-4 flex justify-end gap-3">
                        <button 
                          onClick={() => setSelectedTask(null)}
                          className="px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-700"
                        >
                          Cancel
                        </button>
                        <button 
                          onClick={() => onSelectChallenge(challenge)}
                          className="px-6 py-2 rounded-lg text-sm font-bold text-white transition-all flex items-center gap-2 bg-purple-600 hover:bg-purple-700"
                        >
                          {isCompleted ? 'Re-enter Lab' : 'Enter Lab'} <ArrowRight size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
