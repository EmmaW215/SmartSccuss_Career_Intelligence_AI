/**
 * GPUStatusIndicator - Shows GPU/voice service status
 * 
 * Displays current voice provider quality level and GPU availability.
 * Polls the backend voice status endpoint periodically.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Cpu, Wifi, WifiOff, Volume2, ChevronDown, ChevronUp } from 'lucide-react';
import { getVoiceStatus } from '../services/interviewService';

interface VoiceStatusData {
  available: boolean;
  provider: string;
  gpu?: {
    available: boolean;
    services: Record<string, boolean>;
    latency_ms?: number | null;
  };
}

// Provider display configuration
const PROVIDER_CONFIG: Record<string, {
  label: string;
  quality: string;
  color: string;
  bgColor: string;
  dotColor: string;
  description: string;
}> = {
  gpu: {
    label: 'GPU',
    quality: 'High Quality',
    color: 'text-green-700',
    bgColor: 'bg-green-50 border-green-200',
    dotColor: 'bg-green-500',
    description: 'GPU-accelerated Whisper STT + VITS TTS',
  },
  openai: {
    label: 'OpenAI',
    quality: 'Standard',
    color: 'text-blue-700',
    bgColor: 'bg-blue-50 border-blue-200',
    dotColor: 'bg-blue-500',
    description: 'OpenAI Whisper STT + TTS',
  },
  edge_tts: {
    label: 'Edge TTS',
    quality: 'Basic (Free)',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-50 border-yellow-200',
    dotColor: 'bg-yellow-500',
    description: 'Microsoft Edge TTS (free fallback)',
  },
  'web-speech-api': {
    label: 'Browser',
    quality: 'Fallback',
    color: 'text-orange-700',
    bgColor: 'bg-orange-50 border-orange-200',
    dotColor: 'bg-orange-500',
    description: 'Browser built-in speech recognition',
  },
  none: {
    label: 'Offline',
    quality: 'Unavailable',
    color: 'text-gray-500',
    bgColor: 'bg-gray-50 border-gray-200',
    dotColor: 'bg-gray-400',
    description: 'Voice services unavailable',
  },
};

interface GPUStatusIndicatorProps {
  compact?: boolean;
}

export const GPUStatusIndicator: React.FC<GPUStatusIndicatorProps> = ({ compact = true }) => {
  const [status, setStatus] = useState<VoiceStatusData | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await getVoiceStatus();
      setStatus(data);
    } catch {
      setStatus({ available: false, provider: 'none' });
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll status every 60 seconds
  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 60000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  if (loading) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-gray-400">
        <div className="w-2 h-2 rounded-full bg-gray-300 animate-pulse" />
        <span>Checking...</span>
      </div>
    );
  }

  const provider = status?.provider || 'none';
  const config = PROVIDER_CONFIG[provider] || PROVIDER_CONFIG.none;
  const gpuServices = status?.gpu?.services || {};
  const latency = status?.gpu?.latency_ms;

  // Compact mode: just a dot + label
  if (compact && !expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs transition-all hover:shadow-sm ${config.bgColor}`}
        title={`Voice: ${config.quality} (${config.description})`}
      >
        <span className={`w-2 h-2 rounded-full ${config.dotColor} ${provider === 'gpu' ? 'animate-pulse' : ''}`} />
        <span className={`font-medium ${config.color}`}>
          <Volume2 size={12} className="inline mr-0.5" />
          {config.label}
        </span>
        <ChevronDown size={10} className="text-gray-400" />
      </button>
    );
  }

  // Expanded mode: full details
  return (
    <div className={`rounded-lg border p-3 text-xs ${config.bgColor} relative`}>
      <button
        onClick={() => setExpanded(false)}
        className="absolute top-2 right-2 text-gray-400 hover:text-gray-600"
      >
        <ChevronUp size={14} />
      </button>

      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <span className={`w-2.5 h-2.5 rounded-full ${config.dotColor} ${provider === 'gpu' ? 'animate-pulse' : ''}`} />
        <span className={`font-semibold ${config.color}`}>
          Voice: {config.quality}
        </span>
      </div>

      {/* Provider info */}
      <p className="text-gray-600 mb-2">{config.description}</p>

      {/* GPU details (when GPU is the provider) */}
      {status?.gpu && (
        <div className="space-y-1.5 mb-2">
          <div className="flex items-center gap-2">
            <Cpu size={12} className={status.gpu.available ? 'text-green-600' : 'text-gray-400'} />
            <span className={status.gpu.available ? 'text-green-700' : 'text-gray-500'}>
              GPU: {status.gpu.available ? 'Connected' : 'Offline'}
            </span>
          </div>

          {status.gpu.available && (
            <>
              {/* Services */}
              <div className="flex flex-wrap gap-1.5 ml-5">
                {Object.entries(gpuServices).map(([name, available]) => (
                  <span
                    key={name}
                    className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      available
                        ? 'bg-green-100 text-green-700'
                        : 'bg-red-100 text-red-700'
                    }`}
                  >
                    {name.toUpperCase()}: {available ? 'ON' : 'OFF'}
                  </span>
                ))}
              </div>

              {/* Latency */}
              {latency != null && (
                <div className="flex items-center gap-2 ml-5">
                  <Wifi size={10} className="text-gray-500" />
                  <span className="text-gray-600">
                    Latency: {Math.round(latency)}ms
                  </span>
                </div>
              )}
            </>
          )}

          {!status.gpu.available && (
            <div className="flex items-center gap-2 ml-5">
              <WifiOff size={10} className="text-gray-400" />
              <span className="text-gray-500">
                Using fallback: {config.label}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Refresh button */}
      <button
        onClick={(e) => { e.stopPropagation(); setLoading(true); fetchStatus(); }}
        className="text-gray-500 hover:text-gray-700 underline text-[10px]"
      >
        Refresh
      </button>
    </div>
  );
};

export default GPUStatusIndicator;
