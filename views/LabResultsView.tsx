import React from 'react';
import { CheckCircle2, Award, ArrowRight, BarChart3, Share2, Download } from 'lucide-react';
import { AssessmentResult } from '../types';

interface LabResultsViewProps {
  result: AssessmentResult;
  onHome: () => void;
}

export const LabResultsView: React.FC<LabResultsViewProps> = ({ result, onHome }) => {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="bg-gradient-to-r from-purple-600 to-indigo-600 p-8 text-white">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-3xl font-bold mb-2">Assessment Complete</h2>
                <p className="text-purple-100 opacity-90">Great job! Here is your detailed performance analysis.</p>
              </div>
              <div className="bg-white/20 backdrop-blur-sm rounded-lg px-4 py-2 flex items-center gap-2">
                <Award size={20} className="text-yellow-300" />
                <span className="font-bold">{result.level}</span>
              </div>
            </div>
          </div>
          
          <div className="p-8">
            <div className="flex items-end gap-4 mb-8">
              <div className="text-6xl font-bold text-gray-900">{result.score}</div>
              <div className="text-lg text-gray-500 font-medium mb-2">/ 100 Overall Score</div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Radar / Metrics */}
              <div className="space-y-4">
                <h3 className="font-bold text-gray-700 flex items-center gap-2">
                  <BarChart3 size={18} /> Category Breakdown
                </h3>
                <div className="space-y-3">
                  {Object.entries(result.breakdown).map(([key, value]) => (
                    <div key={key}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-600 capitalize">{key.replace(/([A-Z])/g, ' $1').trim()}</span>
                        <span className="font-medium text-gray-900">{value}%</span>
                      </div>
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-purple-500 rounded-full transition-all duration-1000" 
                          style={{ width: `${value}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Summary */}
              <div className="bg-gray-50 rounded-xl p-6">
                <h3 className="font-bold text-gray-700 mb-3">AI Analysis Summary</h3>
                <p className="text-gray-600 text-sm leading-relaxed">
                  {result.summary}
                </p>
                <div className="mt-4 pt-4 border-t border-gray-200 flex gap-2">
                   <button className="flex-1 flex items-center justify-center gap-2 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">
                     <Download size={16} /> Report
                   </button>
                   <button className="flex-1 flex items-center justify-center gap-2 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">
                     <Share2 size={16} /> Share
                   </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Feedback Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
              <CheckCircle2 size={20} className="text-green-500" /> Key Strengths
            </h3>
            <ul className="space-y-3">
              {result.strengths.map((item, idx) => (
                <li key={idx} className="flex gap-3 text-sm text-gray-600">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 mt-1.5 shrink-0"></span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
              <ArrowRight size={20} className="text-orange-500" /> Areas for Improvement
            </h3>
            <ul className="space-y-3">
              {result.improvements.map((item, idx) => (
                <li key={idx} className="flex gap-3 text-sm text-gray-600">
                  <span className="w-1.5 h-1.5 rounded-full bg-orange-400 mt-1.5 shrink-0"></span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="flex justify-center pt-8">
          <button 
            onClick={onHome}
            className="px-8 py-3 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl shadow-lg hover:shadow-xl transition-all flex items-center gap-2"
          >
            Return to Lab Dashboard <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};
