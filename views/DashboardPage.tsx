import React from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, LineChart, Line
} from 'recharts';
import { ChartDataPoint, PerformanceData } from '../types';
import { ChevronLeft } from 'lucide-react';

interface DashboardPageProps {
    onBack: () => void;
}

const radarData: ChartDataPoint[] = [
  { subject: 'Technical', A: 120, fullMark: 150 },
  { subject: 'Behavioral', A: 98, fullMark: 150 },
  { subject: 'System Design', A: 86, fullMark: 150 },
  { subject: 'Leadership', A: 99, fullMark: 150 },
  { subject: 'Communication', A: 85, fullMark: 150 },
  { subject: 'Problem Solving', A: 65, fullMark: 150 },
];

const performanceData: PerformanceData[] = [
    { date: 'Jan 10', score: 65 },
    { date: 'Jan 12', score: 72 },
    { date: 'Jan 15', score: 68 },
    { date: 'Jan 18', score: 85 },
    { date: 'Jan 20', score: 90 },
];

export const DashboardPage: React.FC<DashboardPageProps> = ({ onBack }) => {
  return (
    <div className="h-full overflow-y-auto bg-gray-50/50 p-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <button onClick={onBack} className="p-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-600">
            <ChevronLeft size={20} />
        </button>
        <div>
            <h1 className="text-2xl font-bold text-gray-800">Your Analytics Dashboard</h1>
            <p className="text-sm text-gray-500">Track your interview performance and AI success metrics.</p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {[
            { label: 'Total Interviews', value: '12', color: 'text-blue-600', bg: 'bg-blue-50' },
            { label: 'Avg. Score', value: '82%', color: 'text-green-600', bg: 'bg-green-50' },
            { label: 'Hours Practiced', value: '8.5', color: 'text-purple-600', bg: 'bg-purple-50' },
            { label: 'Focus Area', value: 'System Design', color: 'text-orange-600', bg: 'bg-orange-50' },
        ].map((stat, i) => (
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
                <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                        <PolarGrid stroke="#e5e7eb" />
                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#6b7280', fontSize: 12 }} />
                        <PolarRadiusAxis angle={30} domain={[0, 150]} tick={false} axisLine={false} />
                        <Radar name="My Skills" dataKey="A" stroke="#2563eb" fill="#3b82f6" fillOpacity={0.4} />
                        <RechartsTooltip />
                    </RadarChart>
                </ResponsiveContainer>
            </div>
        </div>

        {/* Line Chart */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
            <h3 className="text-lg font-bold text-gray-800 mb-6">Score Progression</h3>
            <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={performanceData}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                        <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={false} tickLine={false} />
                        <RechartsTooltip 
                            contentStyle={{ backgroundColor: '#fff', borderRadius: '8px', border: '1px solid #e5e7eb', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                        />
                        <Line type="monotone" dataKey="score" stroke="#7c3aed" strokeWidth={3} dot={{ r: 4, fill: '#7c3aed', strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 6 }} />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
      </div>

      {/* Recent Feedback List */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <h3 className="text-lg font-bold text-gray-800 mb-4">Recent Feedback Summaries</h3>
        <div className="space-y-4">
            {[1, 2, 3].map((item) => (
                <div key={item} className="flex items-start gap-4 p-4 rounded-xl bg-gray-50 border border-gray-100">
                    <div className="w-2 h-12 bg-blue-500 rounded-full"></div>
                    <div>
                        <h4 className="font-semibold text-gray-800">Technical Interview - Python & ML</h4>
                        <p className="text-sm text-gray-500 mt-1">
                            "Strong understanding of algorithms. However, could improve on explaining the trade-offs in system design choices..."
                        </p>
                        <div className="mt-2 flex gap-2">
                            <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-md font-medium">Wait Time: Good</span>
                            <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs rounded-md font-medium">Clarity: Needs Imp.</span>
                        </div>
                    </div>
                </div>
            ))}
        </div>
      </div>
    </div>
  );
};