import React from 'react';
import { X, CheckCircle2, Zap, Crown } from 'lucide-react';

interface UpgradeModalProps {
  onClose: () => void;
  onUpgradeOneTime: () => void;
  onUpgradeSub6: () => void;
  onUpgradeSub15: () => void;
}

const UpgradeModal: React.FC<UpgradeModalProps> = ({ 
  onClose, 
  onUpgradeOneTime, 
  onUpgradeSub6, 
  onUpgradeSub15 
}) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div 
        className="relative bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]"
      >
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50 to-purple-50 opacity-50 pointer-events-none" />
        
        <div className="relative p-6 border-b border-gray-100 flex justify-between items-center bg-white/50">
          <h2 className="text-2xl font-bold text-gray-800">Unlock Potential</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-500"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="relative p-6 overflow-y-auto space-y-4">
          
          {/* Option 1 */}
          <div className="bg-white rounded-xl p-5 border border-gray-200 shadow-sm hover:border-blue-300 hover:shadow-md transition-all group">
            <div className="flex justify-between items-start mb-3">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                  <Zap className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-800">One-time Scan</h3>
                  <p className="text-xs text-gray-500">Perfect for a quick check</p>
                </div>
              </div>
              <div className="text-right">
                <span className="text-2xl font-bold text-gray-900">$2</span>
              </div>
            </div>
            <button
              onClick={onUpgradeOneTime}
              className="w-full py-2.5 bg-gray-900 text-white font-medium rounded-lg hover:bg-gray-800 transition shadow-sm flex justify-center items-center gap-2"
            >
              Pay $2
            </button>
          </div>

          {/* Option 2 */}
          <div className="bg-gradient-to-br from-purple-50 to-white rounded-xl p-5 border border-purple-100 shadow-sm hover:border-purple-300 hover:shadow-md transition-all relative overflow-hidden group">
            <div className="absolute top-0 right-0 bg-purple-600 text-white text-[10px] px-2 py-1 rounded-bl-lg font-bold">
              POPULAR
            </div>
            <div className="flex justify-between items-start mb-3">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg text-purple-600 group-hover:bg-purple-600 group-hover:text-white transition-colors">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-800">Basic Subscription</h3>
                  <p className="text-xs text-gray-500">30 scans / month</p>
                </div>
              </div>
              <div className="text-right">
                <span className="text-2xl font-bold text-gray-900">$6</span>
                <span className="text-xs text-gray-500">/mo</span>
              </div>
            </div>
            <button
              onClick={onUpgradeSub6}
              className="w-full py-2.5 bg-purple-600 text-white font-medium rounded-lg hover:bg-purple-700 transition shadow-lg shadow-purple-200"
            >
              Subscribe
            </button>
          </div>

          {/* Option 3 */}
          <div className="bg-white rounded-xl p-5 border border-orange-200 shadow-sm hover:border-orange-300 hover:shadow-md transition-all group">
            <div className="flex justify-between items-start mb-3">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-orange-100 rounded-lg text-orange-600 group-hover:bg-orange-600 group-hover:text-white transition-colors">
                  <Crown className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-800">Pro Subscription</h3>
                  <p className="text-xs text-gray-500">180 scans / month</p>
                </div>
              </div>
              <div className="text-right">
                <span className="text-2xl font-bold text-gray-900">$15</span>
                <span className="text-xs text-gray-500">/mo</span>
              </div>
            </div>
            <button
              onClick={onUpgradeSub15}
              className="w-full py-2.5 bg-orange-600 text-white font-medium rounded-lg hover:bg-orange-700 transition shadow-lg shadow-orange-200"
            >
              Subscribe
            </button>
          </div>
          
        </div>
      </div>
    </div>
  );
};

export default UpgradeModal;
