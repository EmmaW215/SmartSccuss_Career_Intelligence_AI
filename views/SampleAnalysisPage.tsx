import React from 'react';
import { ChevronLeft, CheckCircle2, AlertCircle, FileText, Briefcase, Award, ArrowRight, Zap } from 'lucide-react';

interface SampleAnalysisPageProps {
  onBack: () => void;
}

export const SampleAnalysisPage: React.FC<SampleAnalysisPageProps> = ({ onBack }) => {
  // Sample demo data
  const demoData = {
    job_summary: {
      position: 'Senior Software Engineer',
      company: 'TechCorp Inc.',
      location: 'San Francisco, CA (Hybrid)',
      keyRequirements: [
        '5+ years of experience in full-stack development',
        'Proficiency in React, Node.js, and Python',
        'Experience with cloud platforms (AWS/GCP)',
        'Strong problem-solving and communication skills',
        'Bachelor\'s degree in Computer Science or related field',
      ],
      preferredQualifications: [
        'Experience with microservices architecture',
        'Knowledge of CI/CD pipelines',
        'Leadership experience in Agile teams',
      ],
    },
    resume_comparison: [
      { category: 'Years of Experience', status: '✅ Strong', comments: '7+ years of full-stack development experience' },
      { category: 'React & Frontend', status: '✅ Strong', comments: 'Extensive React experience with multiple production apps' },
      { category: 'Node.js Backend', status: '✅ Strong', comments: 'Built RESTful APIs and microservices' },
      { category: 'Python', status: '✅ Moderate-Strong', comments: 'Used for data processing and automation scripts' },
      { category: 'Cloud Platforms (AWS)', status: '✅ Strong', comments: 'Deployed and managed applications on AWS' },
      { category: 'Problem-Solving', status: '✅ Strong', comments: 'Led technical troubleshooting for critical systems' },
      { category: 'Communication', status: '✅ Strong', comments: 'Cross-functional collaboration experience' },
      { category: 'Education', status: '✅ Strong', comments: 'B.S. in Computer Science' },
      { category: 'Microservices', status: '✅ Moderate-Strong', comments: 'Implemented service-oriented architecture' },
      { category: 'CI/CD Pipelines', status: '⚠️ Partial', comments: 'Basic experience with Jenkins and GitHub Actions' },
      { category: 'Leadership', status: '✅ Moderate-Strong', comments: 'Mentored junior developers' },
    ],
    match_score: 87,
    tailored_resume_summary: `Results-driven Senior Software Engineer with 7+ years of experience building scalable web applications using React, Node.js, and Python. Proven track record of delivering high-impact solutions in cloud environments (AWS), with expertise in microservices architecture and cross-functional team collaboration. Passionate about clean code, performance optimization, and mentoring emerging talent. Seeking to leverage technical leadership skills and full-stack expertise to drive innovation at TechCorp Inc.`,
    tailored_work_experience: [
      `<strong>Led development of customer-facing React application</strong> serving 500K+ monthly active users, implementing responsive design patterns and state management with Redux that improved user engagement by 35%`,
      `<strong>Architected and deployed microservices</strong> on AWS (ECS, Lambda, API Gateway), reducing system latency by 40% and enabling horizontal scaling during peak traffic periods`,
      `<strong>Built RESTful APIs using Node.js and Express</strong>, integrating with PostgreSQL and MongoDB databases, supporting 10M+ daily API calls with 99.9% uptime`,
      `<strong>Implemented CI/CD pipelines</strong> using GitHub Actions, automating testing and deployment processes that reduced release cycles from 2 weeks to 2 days`,
      `<strong>Mentored team of 4 junior developers</strong>, conducting code reviews and pair programming sessions that improved team velocity by 25% over 6 months`,
      `<strong>Collaborated with product and design teams</strong> in Agile sprints, translating business requirements into technical specifications and delivering features on schedule`,
    ],
    cover_letter: `Dear Hiring Manager,

I am writing to express my strong interest in the Senior Software Engineer position at TechCorp Inc. With over 7 years of experience in full-stack development and a passion for building scalable, user-centric applications, I am excited about the opportunity to contribute to your innovative team.

Throughout my career, I have developed expertise in React, Node.js, and Python—technologies central to this role. At my current position, I led the development of a customer-facing application serving over 500,000 monthly users, where I implemented performance optimizations that improved user engagement by 35%. My experience architecting microservices on AWS has given me deep insights into building resilient, scalable systems.

What particularly draws me to TechCorp Inc. is your commitment to innovation and your collaborative engineering culture. I thrive in Agile environments where cross-functional teamwork drives results, and I have a proven track record of mentoring junior developers while delivering high-quality code.

I am confident that my technical skills, leadership experience, and passion for continuous learning make me a strong fit for this position. I would welcome the opportunity to discuss how my background aligns with TechCorp's goals and how I can contribute to your team's success.

Thank you for considering my application. I look forward to the possibility of speaking with you.

Best regards,
[Your Name]`
  };

  return (
    <div className="h-full overflow-y-auto bg-gray-50/50">
      <div className="max-w-5xl mx-auto p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <button 
              onClick={onBack} 
              className="p-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-600 transition-colors"
            >
              <ChevronLeft size={20} />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">Analysis Report Preview</h1>
              <p className="text-sm text-gray-500">Sample output based on a Senior Software Engineer role</p>
            </div>
          </div>
          <button 
            onClick={onBack}
            className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition shadow-sm font-medium flex items-center gap-2"
          >
            Try Your Resume <ArrowRight size={16} />
          </button>
        </div>

        {/* Demo Banner */}
        <div className="bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-100 rounded-xl p-4 mb-8 flex items-start gap-4">
          <div className="p-2 bg-white rounded-lg shadow-sm text-indigo-600">
            <Zap size={20} fill="currentColor" />
          </div>
          <div>
            <h3 className="font-semibold text-indigo-900">AI Analysis Demo</h3>
            <p className="text-sm text-indigo-700 mt-1">
              This is a static demonstration of the deep analysis engine. Upload your own resume to get personalized insights, ATS optimization, and tailored content.
            </p>
          </div>
        </div>

        <div className="space-y-8">
          {/* 1. Job Requirement Summary */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1.5 h-full bg-blue-500"></div>
            <h2 className="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
              <span className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-bold">1</span>
              Job Requirement Summary
            </h2>
            
            <div className="bg-blue-50/50 rounded-xl p-6 border border-blue-100">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div>
                  <span className="text-xs font-semibold text-blue-600 uppercase tracking-wider">Position</span>
                  <p className="font-medium text-gray-900 mt-1">{demoData.job_summary.position}</p>
                </div>
                <div>
                  <span className="text-xs font-semibold text-blue-600 uppercase tracking-wider">Company</span>
                  <p className="font-medium text-gray-900 mt-1">{demoData.job_summary.company}</p>
                </div>
                <div>
                  <span className="text-xs font-semibold text-blue-600 uppercase tracking-wider">Location</span>
                  <p className="font-medium text-gray-900 mt-1">{demoData.job_summary.location}</p>
                </div>
              </div>
              
              <div className="grid md:grid-cols-2 gap-8">
                <div>
                  <h4 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <Briefcase size={16} className="text-blue-500" /> Key Requirements
                  </h4>
                  <ul className="space-y-2">
                    {demoData.job_summary.keyRequirements.map((req, index) => (
                      <li key={index} className="text-sm text-gray-600 flex items-start gap-2">
                        <span className="w-1.5 h-1.5 bg-blue-400 rounded-full mt-1.5 shrink-0"></span>
                        {req}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <Award size={16} className="text-blue-500" /> Preferred Qualifications
                  </h4>
                  <ul className="space-y-2">
                    {demoData.job_summary.preferredQualifications.map((qual, index) => (
                      <li key={index} className="text-sm text-gray-600 flex items-start gap-2">
                        <span className="w-1.5 h-1.5 bg-blue-300 rounded-full mt-1.5 shrink-0"></span>
                        {qual}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* 2. Comparison Table */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1.5 h-full bg-purple-500"></div>
            <h2 className="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
              <span className="w-8 h-8 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center text-sm font-bold">2</span>
              Resume vs. Job Match
            </h2>

            <div className="overflow-x-auto rounded-xl border border-gray-100">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-gray-500 uppercase bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th className="px-6 py-4 font-semibold">Category</th>
                    <th className="px-6 py-4 font-semibold">Match Status</th>
                    <th className="px-6 py-4 font-semibold">Analysis Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {demoData.resume_comparison.map((row, index) => (
                    <tr key={index} className="bg-white hover:bg-gray-50/50 transition-colors">
                      <td className="px-6 py-4 font-medium text-gray-900">{row.category}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                          row.status.includes('Strong') ? 'bg-green-50 text-green-700 border border-green-100' :
                          row.status.includes('Moderate') ? 'bg-yellow-50 text-yellow-700 border border-yellow-100' :
                          'bg-orange-50 text-orange-700 border border-orange-100'
                        }`}>
                          {row.status.includes('Strong') ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
                          {row.status.replace(/✅|⚠️/g, '').trim()}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-500">{row.comments}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 3. Match Score */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1.5 h-full bg-green-500"></div>
            <h2 className="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
              <span className="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-sm font-bold">3</span>
              Overall Match Score
            </h2>

            <div className="bg-green-50/50 border border-green-100 rounded-xl p-8 flex items-center gap-8">
              <div className="relative w-32 h-32 flex items-center justify-center">
                 <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                    <path className="text-green-200" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" />
                    <path className="text-green-500" strokeDasharray={`${demoData.match_score}, 100`} d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" />
                 </svg>
                 <span className="absolute text-3xl font-bold text-green-700">{demoData.match_score}%</span>
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold text-gray-900 mb-2">Excellent Match!</h3>
                <p className="text-gray-600 leading-relaxed">
                  Your profile aligns significantly with the job requirements. Focus on the few partial matches in your interview prep to secure this role.
                </p>
              </div>
            </div>
          </div>

          {/* 4. Tailored Summary */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1.5 h-full bg-indigo-500"></div>
            <h2 className="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
              <span className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-sm font-bold">4</span>
              Optimized Professional Summary
            </h2>
            
            <div className="bg-indigo-50/50 rounded-xl p-6 border-l-4 border-indigo-500 italic text-gray-700 leading-relaxed relative">
              <p>"{demoData.tailored_resume_summary}"</p>
            </div>
            <p className="flex items-center gap-2 text-xs text-gray-400 mt-3 pl-2">
              <Zap size={12} className="text-yellow-500 fill-current" />
              Copy this to your resume header to improve ATS ranking.
            </p>
          </div>

          {/* 5. Tailored Bullets */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 relative overflow-hidden">
             <div className="absolute top-0 left-0 w-1.5 h-full bg-orange-500"></div>
             <h2 className="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
              <span className="w-8 h-8 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center text-sm font-bold">5</span>
              Enhancement Suggestions
            </h2>

            <div className="space-y-3">
              {demoData.tailored_work_experience.map((item, index) => (
                <div key={index} className="flex gap-4 p-4 rounded-xl bg-orange-50/30 border border-orange-100/50">
                  <div className="mt-1">
                    <CheckCircle2 size={18} className="text-orange-500" />
                  </div>
                  <p className="text-sm text-gray-700 leading-relaxed" dangerouslySetInnerHTML={{ __html: item }}></p>
                </div>
              ))}
            </div>
          </div>

           {/* 6. Cover Letter */}
           <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 relative overflow-hidden">
             <div className="absolute top-0 left-0 w-1.5 h-full bg-teal-500"></div>
             <h2 className="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
              <span className="w-8 h-8 rounded-full bg-teal-100 text-teal-600 flex items-center justify-center text-sm font-bold">6</span>
              Generated Cover Letter
            </h2>

            <div className="bg-gray-50 rounded-xl p-8 border border-gray-200">
               <div className="font-mono text-sm text-gray-600 whitespace-pre-wrap leading-relaxed">
                 {demoData.cover_letter}
               </div>
            </div>
          </div>

          <div className="flex justify-center pt-8 pb-12">
            <button 
                onClick={onBack}
                className="px-8 py-4 bg-gray-900 text-white text-lg font-bold rounded-xl shadow-xl hover:bg-gray-800 hover:-translate-y-1 transition-all flex items-center gap-3"
            >
                Start Your Own Analysis <ArrowRight size={20} />
            </button>
          </div>

        </div>
      </div>
    </div>
  );
};