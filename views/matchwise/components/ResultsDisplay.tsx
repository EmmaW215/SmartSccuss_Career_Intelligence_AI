import React from 'react';
import DOMPurify from 'dompurify';
import { ComparisonResponse } from '../types';

// Allowed HTML tags for LLM output — blocks scripts, iframes, etc. (XSS prevention)
const SANITIZE_CONFIG = {
  ALLOWED_TAGS: [
    'p', 'br', 'ul', 'ol', 'li', 'strong', 'em', 'b', 'i',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'h1', 'h2', 'h3', 'h4', 'span', 'div', 'a',
  ],
  ALLOWED_ATTR: ['class', 'style', 'href', 'target', 'rel'],
};

/** Sanitize LLM-generated HTML to prevent XSS attacks */
const SafeHTML: React.FC<{ html: string; className?: string }> = ({ html, className }) => {
  const clean = DOMPurify.sanitize(html, SANITIZE_CONFIG);
  return <div className={className} dangerouslySetInnerHTML={{ __html: clean }} />;
};

interface ResultsDisplayProps {
  data: ComparisonResponse;
}

const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ data }) => {
  return (
    <div className="w-full max-w-4xl bg-white rounded-2xl shadow-xl p-6 sm:p-10 mt-8 border border-blue-50 flex flex-col gap-10 animate-fade-in relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500" />
      
      <h2 className="text-3xl font-bold text-gray-800 mb-2 border-b border-gray-100 pb-4">
        Analysis Results
      </h2>

      {/* Job Requirement Summary */}
      <div className="group">
        <div className="flex items-center mb-4">
          <div className="w-1.5 h-8 bg-blue-500 rounded-full mr-4 group-hover:h-10 transition-all duration-300"></div>
          <span className="text-xl font-bold text-gray-800">Job Requirement Summary</span>
        </div>
        <SafeHTML
          className="ml-6 text-gray-700 leading-relaxed prose prose-blue max-w-none"
          html={data.job_summary || 'No job summary available.'}
        />
      </div>

      {/* Resume - Job Posting Comparison */}
      <div className="group">
        <div className="flex items-center mb-4">
          <div className="w-1.5 h-8 bg-purple-500 rounded-full mr-4 group-hover:h-10 transition-all duration-300"></div>
          <span className="text-xl font-bold text-gray-800">Comparison Table</span>
        </div>
        <div className="ml-6 overflow-x-auto">
          <SafeHTML
            className="resume-table-html text-gray-700 text-sm"
            html={data.resume_summary}
          />
        </div>
      </div>

      {/* Match Score */}
      <div className="group">
        <div className="flex items-center mb-4">
          <div className="w-1.5 h-8 bg-green-500 rounded-full mr-4 group-hover:h-10 transition-all duration-300"></div>
          <span className="text-xl font-bold text-gray-800">Match Score</span>
        </div>
        <div className="flex items-center ml-6 mb-2">
          <span className="text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-green-600 to-emerald-500 mr-6">
            {data.match_score || 0}%
          </span>
          <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden shadow-inner">
            <div
              className="h-full bg-gradient-to-r from-green-500 to-emerald-400 rounded-full transition-all duration-1000 ease-out"
              style={{ width: `${data.match_score || 0}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Tailored Resume Summary */}
      <div className="group">
        <div className="flex items-center mb-4">
          <div className="w-1.5 h-8 bg-pink-500 rounded-full mr-4 group-hover:h-10 transition-all duration-300"></div>
          <span className="text-xl font-bold text-gray-800">Tailored Resume Summary</span>
        </div>
        <SafeHTML
          className="ml-6 text-gray-700 leading-relaxed prose prose-pink max-w-none bg-pink-50/50 p-4 rounded-lg border border-pink-100"
          html={data.tailored_resume_summary || 'No tailored resume summary available.'}
        />
      </div>

      {/* Tailored Resume Work Experience */}
      <div className="group">
        <div className="flex items-center mb-4">
          <div className="w-1.5 h-8 bg-orange-500 rounded-full mr-4 group-hover:h-10 transition-all duration-300"></div>
          <span className="text-xl font-bold text-gray-800">Suggested Work Experience</span>
        </div>
        <SafeHTML
          className="ml-6 text-gray-700 leading-relaxed prose prose-orange max-w-none"
          html={
            Array.isArray(data.tailored_work_experience) 
              ? data.tailored_work_experience.join('') 
              : (data.tailored_work_experience || '<ul><li>No tailored work experience provided.</li></ul>')
          }
        />
      </div>

      {/* Cover Letter */}
      <div className="group">
        <div className="flex items-center mb-4">
          <div className="w-1.5 h-8 bg-teal-500 rounded-full mr-4 group-hover:h-10 transition-all duration-300"></div>
          <span className="text-xl font-bold text-gray-800">Draft Cover Letter</span>
        </div>
        <SafeHTML
          className="bg-teal-50/50 border border-teal-100 rounded-xl p-6 ml-6 text-gray-700 leading-relaxed font-serif"
          html={data.cover_letter || 'No cover letter available.'}
        />
      </div>
    </div>
  );
};

export default ResultsDisplay;
