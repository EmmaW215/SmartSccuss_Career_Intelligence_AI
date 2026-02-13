import React from 'react';
import { Eye } from 'lucide-react';

interface VisitorCounterProps {
  isVisible: boolean;
}

// Module 6: Visitor Counter — placeholder component for future backend integration
// Currently displays a static count. Future options:
// - Option A: Firebase Firestore counter
// - Option B: Vercel KV (if deploying frontend on Vercel)
// - Option C: Custom Render backend endpoint
const VisitorCounter: React.FC<VisitorCounterProps> = ({ isVisible }) => {
  if (!isVisible) return null;

  return (
    <div className="bg-white/90 backdrop-blur-sm px-3 py-1.5 rounded-full shadow-md border border-gray-200 flex items-center gap-2 text-sm text-gray-600">
      <Eye className="w-4 h-4 text-blue-500" />
      <span className="font-medium">1,245</span>
      <span className="text-xs text-gray-400">visits</span>
    </div>
  );
};

export default VisitorCounter;
