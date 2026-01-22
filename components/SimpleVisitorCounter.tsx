import React, { useState, useEffect } from 'react';
import { Eye } from 'lucide-react';

export default function SimpleVisitorCounter() {
  const [count, setCount] = useState<number>(1234);

  useEffect(() => {
    // Mocking the API call behavior
    const updateCount = () => {
        // Simulating a fetch to /api/visitor-count
        setTimeout(() => {
            setCount(prev => prev + 1);
        }, 1000);
    };

    updateCount();
  }, []);

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-white/50 backdrop-blur-sm border border-gray-200 rounded-full text-xs font-mono text-gray-600 shadow-sm">
      <Eye className="w-3 h-3" />
      <span>Visitors: {count.toLocaleString()}</span>
    </div>
  );
}