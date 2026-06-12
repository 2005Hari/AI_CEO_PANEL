import React, { useState } from 'react';
import { Project, submitManagerPlan } from '@/lib/api';

interface ManagerInputProps {
  project: Project;
  onPlanCreated: () => void;
}

export function ManagerInput({ project, onPlanCreated }: ManagerInputProps) {
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;

    const requestText = input;
    setInput('');
    setIsProcessing(true);

    try {
      await submitManagerPlan(project.id, requestText);
      onPlanCreated(); // Trigger a refresh of the task board
    } catch (e) {
      console.error(e);
      // Revert input on error
      setInput(requestText);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 w-[80%] max-w-3xl z-50">
      <div className="glass-strong rounded-2xl p-2 border border-blue-500/20 shadow-2xl shadow-blue-900/20 animate-fadeSlideIn backdrop-blur-xl">
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <div className="absolute left-4 w-6 h-6 rounded-md bg-blue-500/20 flex items-center justify-center text-blue-400 text-xs">
            ✨
          </div>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isProcessing}
            placeholder={isProcessing ? "Manager is delegating tasks..." : "Tell the Manager Agent what needs to be done..."}
            className="w-full bg-transparent border-none py-3 pl-14 pr-24 text-sm text-white focus:outline-none placeholder:text-gray-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || isProcessing}
            className="absolute right-2 px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-500 text-white text-xs font-semibold rounded-xl transition-colors"
          >
            Delegate
          </button>
        </form>
      </div>
    </div>
  );
}
