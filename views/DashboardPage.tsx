import React, { useState, useEffect } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, LineChart, Line
} from 'recharts';
import { ChartDataPoint, PerformanceData, DashboardStats, InterviewHistoryItem, SessionFeedback } from '../types';
import { ChevronLeft, Download, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { getDashboardStats, getDashboardHistory, getSessionFeedback } from '../services/interviewService';

interface DashboardPageProps {
    onBack: () => void;
}

// Data transformation functions
const transformStatsToKPI = (stats: DashboardStats | null, feedbacks: Record<string, SessionFeedback>): Array<{ label: string; value: string; color: string; bg: string }> => {
  if (!stats) {
    return [
      { label: 'Total Interviews', value: '0', color: 'text-blue-600', bg: 'bg-blue-50' },
      { label: 'Avg. Score', value: 'N/A', color: 'text-green-600', bg: 'bg-green-50' },
      { label: 'Hours Practiced', value: '0', color: 'text-purple-600', bg: 'bg-purple-50' },
      { label: 'Focus Area', value: 'N/A', color: 'text-orange-600', bg: 'bg-orange-50' },
    ];
  }

  // Calculate average score from all feedbacks
  const scores: number[] = [];
  Object.values(feedbacks).forEach(feedback => {
    if (feedback.estimated_score?.estimated_percentage) {
      scores.push(feedback.estimated_score.estimated_percentage);
    }
  });
  const avgScore = scores.length > 0 
    ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
    : 0;

  // Calculate hours practiced (estimate: 15 min per interview)
  const hoursPracticed = (stats.total_interviews * 0.25).toFixed(1);

  // Find focus area (interview type with lowest completion rate)
  let focusArea = 'N/A';
  if (stats.by_type && Object.keys(stats.by_type).length > 0) {
    const typeEntries = Object.entries(stats.by_type);
    const sortedByCompletion = typeEntries.sort((a, b) => {
      const rateA = a[1].total > 0 ? a[1].completed / a[1].total : 0;
      const rateB = b[1].total > 0 ? b[1].completed / b[1].total : 0;
      return rateA - rateB;
    });
    if (sortedByCompletion.length > 0) {
      focusArea = sortedByCompletion[0][0].charAt(0).toUpperCase() + sortedByCompletion[0][0].slice(1);
    }
  }

  return [
    { label: 'Total Interviews', value: stats.total_interviews.toString(), color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Avg. Score', value: `${avgScore}%`, color: 'text-green-600', bg: 'bg-green-50' },
    { label: 'Hours Practiced', value: hoursPracticed, color: 'text-purple-600', bg: 'bg-purple-50' },
    { label: 'Focus Area', value: focusArea, color: 'text-orange-600', bg: 'bg-orange-50' },
  ];
};

const transformHistoryToRadarData = (
  history: InterviewHistoryItem[],
  feedbacks: Record<string, SessionFeedback>
): ChartDataPoint[] => {
  // Initialize skill categories
  const skills: Record<string, { total: number; sum: number }> = {
    'Technical': { total: 0, sum: 0 },
    'Behavioral': { total: 0, sum: 0 },
    'System Design': { total: 0, sum: 0 },
    'Leadership': { total: 0, sum: 0 },
    'Communication': { total: 0, sum: 0 },
    'Problem Solving': { total: 0, sum: 0 },
  };

  // Process each completed interview
  history.forEach(item => {
    if (item.status === 'completed' && item.completed_at) {
      const feedback = feedbacks[item.session_id];
      if (feedback?.estimated_score?.estimated_percentage) {
        const score = feedback.estimated_score.estimated_percentage;
        
        // Map interview type to skills
        const interviewType = item.interview_type.toLowerCase();
        if (interviewType.includes('technical') || interviewType.includes('customize')) {
          skills['Technical'].total++;
          skills['Technical'].sum += score;
          skills['System Design'].total++;
          skills['System Design'].sum += score;
          skills['Problem Solving'].total++;
          skills['Problem Solving'].sum += score;
        }
        if (interviewType.includes('behavioral')) {
          skills['Behavioral'].total++;
          skills['Behavioral'].sum += score;
          skills['Leadership'].total++;
          skills['Leadership'].sum += score;
          skills['Communication'].total++;
          skills['Communication'].sum += score;
        }
        if (interviewType.includes('screening')) {
          skills['Communication'].total++;
          skills['Communication'].sum += score;
        }
      }
    }
  });

  // Convert to chart format
  const radarData: ChartDataPoint[] = [];
  Object.entries(skills).forEach(([subject, data]) => {
    const avgScore = data.total > 0 ? Math.round(data.sum / data.total) : 0;
    radarData.push({
      subject,
      A: avgScore,
      fullMark: 100,
    });
  });

  // If no data, return default values
  if (radarData.every(d => d.A === 0)) {
    return [
      { subject: 'Technical', A: 0, fullMark: 100 },
      { subject: 'Behavioral', A: 0, fullMark: 100 },
      { subject: 'System Design', A: 0, fullMark: 100 },
      { subject: 'Leadership', A: 0, fullMark: 100 },
      { subject: 'Communication', A: 0, fullMark: 100 },
      { subject: 'Problem Solving', A: 0, fullMark: 100 },
    ];
  }

  return radarData;
};

const transformHistoryToPerformanceData = (
  history: InterviewHistoryItem[],
  feedbacks: Record<string, SessionFeedback>
): PerformanceData[] => {
  // Filter completed interviews and sort by completion date
  const completedInterviews = history
    .filter(item => item.status === 'completed' && item.completed_at)
    .sort((a, b) => {
      const dateA = new Date(a.completed_at!).getTime();
      const dateB = new Date(b.completed_at!).getTime();
      return dateA - dateB;
    });

  // Transform to performance data
  const performanceData: PerformanceData[] = completedInterviews.map(item => {
    const feedback = feedbacks[item.session_id];
    const score = feedback?.estimated_score?.estimated_percentage || 0;
    
    // Format date as "MMM DD"
    const date = new Date(item.completed_at!);
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const formattedDate = `${monthNames[date.getMonth()]} ${date.getDate()}`;

    return {
      date: formattedDate,
      score: Math.round(score),
    };
  });

  return performanceData.length > 0 ? performanceData : [];
};

const transformFeedbackToRecentList = (
  history: InterviewHistoryItem[],
  feedbacks: Record<string, SessionFeedback>
): Array<{
  sessionId: string;
  title: string;
  summary: string;
  tags: Array<{ label: string; color: string }>;
}> => {
  // Get recent completed interviews (last 3)
  const recentCompleted = history
    .filter(item => item.status === 'completed' && item.completed_at)
    .sort((a, b) => {
      const dateA = new Date(a.completed_at!).getTime();
      const dateB = new Date(b.completed_at!).getTime();
      return dateB - dateA; // Most recent first
    })
    .slice(0, 3);

  return recentCompleted.map(item => {
    const feedback = feedbacks[item.session_id];
    const interviewType = item.interview_type.charAt(0).toUpperCase() + item.interview_type.slice(1);
    
    // Generate summary from feedback hints
    let summary = 'No detailed feedback available.';
    if (feedback?.feedback_hints && feedback.feedback_hints.length > 0) {
      const hints = feedback.feedback_hints.slice(0, 2).map(h => h.hint || '').filter(Boolean);
      summary = hints.length > 0 ? hints.join(' ') : summary;
    }

    // Generate tags from feedback quality
    const tags: Array<{ label: string; color: string }> = [];
    if (feedback?.estimated_score) {
      const { good_responses, fair_responses, needs_improvement } = feedback.estimated_score;
      if (good_responses > 0) {
        tags.push({ label: `Good: ${good_responses}`, color: 'bg-green-100 text-green-700' });
      }
      if (fair_responses > 0) {
        tags.push({ label: `Fair: ${fair_responses}`, color: 'bg-yellow-100 text-yellow-700' });
      }
      if (needs_improvement > 0) {
        tags.push({ label: `Needs Imp.: ${needs_improvement}`, color: 'bg-orange-100 text-orange-700' });
      }
    }

    return {
      sessionId: item.session_id,
      title: `${interviewType} Interview`,
      summary,
      tags: tags.length > 0 ? tags : [{ label: 'No feedback tags', color: 'bg-gray-100 text-gray-700' }],
    };
  });
};

export const DashboardPage: React.FC<DashboardPageProps> = ({ onBack }) => {
  const { user, isAuthenticated, triggerLogin } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [history, setHistory] = useState<InterviewHistoryItem[]>([]);
  const [feedbacks, setFeedbacks] = useState<Record<string, SessionFeedback>>({});

  // Fetch dashboard data
  useEffect(() => {
    if (!isAuthenticated || !user?.id) {
      setIsLoading(false);
      return;
    }

    const fetchDashboardData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Fetch stats and history in parallel
        const [statsData, historyData] = await Promise.all([
          getDashboardStats(user.id),
          getDashboardHistory(user.id, 20, 'completed'),
        ]);

        setStats(statsData);
        setHistory(historyData.interviews);

        // Fetch feedbacks for completed interviews
        const completedSessions = historyData.interviews
          .filter(item => item.status === 'completed')
          .slice(0, 10); // Limit to 10 to avoid too many requests

        const feedbackPromises = completedSessions.map(item =>
          getSessionFeedback(item.session_id).catch(err => {
            console.warn(`Failed to fetch feedback for session ${item.session_id}:`, err);
            return null;
          })
        );

        const feedbackResults = await Promise.all(feedbackPromises);
        const feedbacksMap: Record<string, SessionFeedback> = {};
        feedbackResults.forEach((feedback, index) => {
          if (feedback) {
            feedbacksMap[completedSessions[index].session_id] = feedback;
          }
        });

        setFeedbacks(feedbacksMap);
      } catch (err: any) {
        console.error('Error fetching dashboard data:', err);
        setError(err.message || 'Failed to load dashboard data. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, [isAuthenticated, user?.id]);

  const handleRetry = () => {
    if (user?.id) {
      setError(null);
      setIsLoading(true);
      // Trigger re-fetch by updating a dependency
      const fetchDashboardData = async () => {
        try {
          const [statsData, historyData] = await Promise.all([
            getDashboardStats(user.id),
            getDashboardHistory(user.id, 20, 'completed'),
          ]);

          setStats(statsData);
          setHistory(historyData.interviews);

          const completedSessions = historyData.interviews
            .filter(item => item.status === 'completed')
            .slice(0, 10);

          const feedbackPromises = completedSessions.map(item =>
            getSessionFeedback(item.session_id).catch(() => null)
          );

          const feedbackResults = await Promise.all(feedbackPromises);
          const feedbacksMap: Record<string, SessionFeedback> = {};
          feedbackResults.forEach((feedback, index) => {
            if (feedback) {
              feedbacksMap[completedSessions[index].session_id] = feedback;
            }
          });

          setFeedbacks(feedbacksMap);
          setError(null);
        } catch (err: any) {
          setError(err.message || 'Failed to load dashboard data.');
        } finally {
          setIsLoading(false);
        }
      };
      fetchDashboardData();
    }
  };

  const handleDownloadReport = () => {
    if (!isAuthenticated) {
      triggerLogin();
    } else {
      alert("Report downloading...");
    }
  };

  // Transform data for display
  const kpiData = transformStatsToKPI(stats, feedbacks);
  const radarData = transformHistoryToRadarData(history, feedbacks);
  const performanceData = transformHistoryToPerformanceData(history, feedbacks);
  const recentFeedbackList = transformFeedbackToRecentList(history, feedbacks);

  // Show login prompt if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="h-full overflow-y-auto bg-gray-50/50 p-8 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Please Login</h2>
          <p className="text-gray-600 mb-6">You need to be logged in to view your dashboard.</p>
          <button
            onClick={triggerLogin}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Login
          </button>
        </div>
      </div>
    );
  }

  // Show loading state
  if (isLoading) {
    return (
      <div className="h-full overflow-y-auto bg-gray-50/50 p-8 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading your dashboard data...</p>
        </div>
      </div>
    );
  }

  // Show error state
  if (error) {
    const isPhase2Error = error.includes('Phase 2') || error.includes('503');
    return (
      <div className="h-full overflow-y-auto bg-gray-50/50 p-8">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <button onClick={onBack} className="p-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-600">
              <ChevronLeft size={20} />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">Your Analytics Dashboard</h1>
              <p className="text-sm text-gray-500">Track your interview performance and AI success metrics.</p>
            </div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-red-200">
          <div className="flex items-start gap-4">
            <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-1" />
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-red-800 mb-2">Error Loading Dashboard</h3>
              <p className="text-gray-700 mb-4">{error}</p>
              {isPhase2Error && (
                <p className="text-sm text-gray-600 mb-4">
                  The Dashboard feature requires Phase 2 features to be enabled on the backend. 
                  This is an optional feature that provides enhanced analytics.
                </p>
              )}
              <button
                onClick={handleRetry}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <RefreshCw size={16} />
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Show empty state if no data
  const hasNoData = !stats || stats.total_interviews === 0;
  if (hasNoData) {
    return (
      <div className="h-full overflow-y-auto bg-gray-50/50 p-8">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <button onClick={onBack} className="p-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-600">
              <ChevronLeft size={20} />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">Your Analytics Dashboard</h1>
              <p className="text-sm text-gray-500">Track your interview performance and AI success metrics.</p>
            </div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 text-center py-12">
          <h3 className="text-xl font-semibold text-gray-800 mb-2">No Interview Data Yet</h3>
          <p className="text-gray-600 mb-6">Start your first interview to see your analytics here!</p>
          <button
            onClick={onBack}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Start Interview
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-gray-50/50 p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
            <button onClick={onBack} className="p-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-600">
                <ChevronLeft size={20} />
            </button>
            <div>
                <h1 className="text-2xl font-bold text-gray-800">Your Analytics Dashboard</h1>
                <p className="text-sm text-gray-500">Track your interview performance and AI success metrics.</p>
            </div>
        </div>
        <button 
            onClick={handleDownloadReport}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 text-sm font-medium"
        >
            <Download size={16} /> Export Report
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {kpiData.map((stat, i) => (
            <div key={i} className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                <p className="text-sm text-gray-500 font-medium">{stat.label}</p>
                <div className="mt-2 flex items-baseline gap-2">
                    <span className={`text-3xl font-bold ${stat.color}`}>{stat.value}</span>
                </div>
            </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Radar Chart */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
            <h3 className="text-lg font-bold text-gray-800 mb-6">Skill Analysis</h3>
            <div className="h-[300px] w-full">
                {radarData.length > 0 && radarData.some(d => d.A > 0) ? (
                  <ResponsiveContainer width="100%" height="100%">
                      <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                          <PolarGrid stroke="#e5e7eb" />
                          <PolarAngleAxis dataKey="subject" tick={{ fill: '#6b7280', fontSize: 12 }} />
                          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                          <Radar name="My Skills" dataKey="A" stroke="#2563eb" fill="#3b82f6" fillOpacity={0.4} />
                          <RechartsTooltip />
                      </RadarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-gray-400">
                    No skill data available yet
                  </div>
                )}
            </div>
        </div>

        {/* Line Chart */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
            <h3 className="text-lg font-bold text-gray-800 mb-6">Score Progression</h3>
            <div className="h-[300px] w-full">
                {performanceData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={performanceData}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                          <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={false} tickLine={false} />
                          <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={false} tickLine={false} domain={[0, 100]} />
                          <RechartsTooltip 
                              contentStyle={{ backgroundColor: '#fff', borderRadius: '8px', border: '1px solid #e5e7eb', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                          />
                          <Line type="monotone" dataKey="score" stroke="#7c3aed" strokeWidth={3} dot={{ r: 4, fill: '#7c3aed', strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 6 }} />
                      </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-gray-400">
                    No progression data available yet
                  </div>
                )}
            </div>
        </div>
      </div>

      {/* Recent Feedback List */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <h3 className="text-lg font-bold text-gray-800 mb-4">Recent Feedback Summaries</h3>
        <div className="space-y-4">
            {recentFeedbackList.length > 0 ? (
              recentFeedbackList.map((item) => (
                  <div key={item.sessionId} className="flex items-start gap-4 p-4 rounded-xl bg-gray-50 border border-gray-100">
                      <div className="w-2 h-12 bg-blue-500 rounded-full"></div>
                      <div className="flex-1">
                          <h4 className="font-semibold text-gray-800">{item.title}</h4>
                          <p className="text-sm text-gray-500 mt-1">
                              {item.summary}
                          </p>
                          <div className="mt-2 flex gap-2 flex-wrap">
                              {item.tags.map((tag, idx) => (
                                <span key={idx} className={`px-2 py-1 ${tag.color} text-xs rounded-md font-medium`}>
                                    {tag.label}
                                </span>
                              ))}
                          </div>
                      </div>
                  </div>
              ))
            ) : (
              <div className="text-center py-8 text-gray-400">
                No feedback summaries available yet
              </div>
            )}
        </div>
      </div>
    </div>
  );
};
