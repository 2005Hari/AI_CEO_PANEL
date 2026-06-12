import React, { useState } from 'react';
import { submitManagerPlanV2 } from '@/lib/api';

interface ManagerV2InputProps {
  projectId: string;
  onPlanCreated: () => void;
}

export function ManagerV2Input({ projectId, onPlanCreated }: ManagerV2InputProps) {
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;

    const requestText = input;
    setInput('');
    setIsProcessing(true);
    setError(null);

    try {
      await submitManagerPlanV2(projectId, requestText);
      onPlanCreated();
    } catch (err: any) {
      setError(err.message || 'Failed to generate plan');
      setInput(requestText);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="w-full">
      <div className="rounded-lg border border-purple-500/30 bg-gradient-to-br from-purple-900/10 to-blue-900/10 p-6 backdrop-blur">
        <h2 className="text-lg font-semibold text-white mb-4">📋 Manager v2: Generate Plan & Tasks</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isProcessing}
            placeholder="Describe what you need: e.g., 'I need a landing page and marketing strategy for my SaaS product'"
            className="w-full rounded-lg bg-gray-900/50 border border-gray-700 text-white p-4 focus:border-purple-500 focus:outline-none placeholder:text-gray-500 disabled:opacity-50"
            rows={4}
          />
          {error && <div className="text-red-400 text-sm">{error}</div>}
          <button
            type="submit"
            disabled={!input.trim() || isProcessing}
            className="px-6 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 disabled:from-gray-700 disabled:to-gray-700 text-white font-semibold rounded-lg transition-all disabled:cursor-not-allowed"
          >
            {isProcessing ? 'Generating Plan...' : 'Generate Plan & Tasks'}
          </button>
        </form>
      </div>
    </div>
  );
}
