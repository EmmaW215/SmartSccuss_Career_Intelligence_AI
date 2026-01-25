import React from 'react';
import { Users } from 'lucide-react';

const SimpleVisitorCounter: React.FC = () => {
  return (
    <div className="flex items-center gap-2 text-sm text-gray-500 bg-gray-50 px-3 py-1.5 rounded-full border border-gray-200">
      <Users size={14} className="text-gray-400" />
      <span className="font-mono font-medium text-gray-700">1,248</span>
      <span className="text-xs">active learners</span>
    </div>
  );
};

export default SimpleVisitorCounter;
