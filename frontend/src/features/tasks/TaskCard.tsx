import React, { useState } from 'react';

interface TaskCardProps {
  task: any;
  onExecute: () => void;
}

export function TaskCard({ task, onExecute }: TaskCardProps) {
  const [expanded, setExpanded] = useState(false);

  const getPriorityColor = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case 'high': return 'text-orange-400 bg-orange-400/10 border-orange-400/20';
      case 'urgent': return 'text-red-400 bg-red-400/10 border-red-400/20';
      case 'low': return 'text-gray-400 bg-gray-400/10 border-gray-400/20';
      default: return 'text-blue-400 bg-blue-400/10 border-blue-400/20';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'working': return <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />;
      case 'completed': return <div className="w-2 h-2 rounded-full bg-emerald-500" />;
      case 'review': return <div className="w-2 h-2 rounded-full bg-purple-500" />;
      case 'error': return <div className="w-2 h-2 rounded-full bg-red-500" />;
      default: return <div className="w-2 h-2 rounded-full bg-gray-500" />;
    }
  };

  return (
    <div className="glass rounded-xl p-4 border border-white/[0.04] hover:bg-white/[0.02] transition-colors group cursor-pointer" onClick={() => setExpanded(!expanded)}>
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          {getStatusIcon(task.status)}
          <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border ${getPriorityColor(task.priority)}`}>
            {task.priority || 'Medium'}
          </span>
        </div>
        {task.assigned_agent && (
          <div className="text-[10px] text-gray-500 font-mono bg-black/20 px-1.5 py-0.5 rounded">
            @{task.assigned_agent}
          </div>
        )}
      </div>

      <h4 className="text-sm font-semibold text-white mb-1 leading-tight">{task.title}</h4>
      
      {task.description && (
        <p className={`text-xs text-gray-400 line-clamp-2 mt-2 ${expanded ? 'line-clamp-none' : ''}`}>
          {task.description}
        </p>
      )}

      {expanded && task.output_result && (
        <div className="mt-3 pt-3 border-t border-white/[0.04]">
          <h5 className="text-[10px] text-gray-500 uppercase font-semibold mb-1">Output Result</h5>
          <pre className="text-[10px] text-gray-300 bg-black/30 p-2 rounded overflow-x-auto max-h-32">
            {JSON.stringify(task.output_result, null, 2)}
          </pre>
        </div>
      )}

      {(task.status === 'pending' || task.status === 'assigned' || task.status === 'error') && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onExecute();
          }}
          disabled={task.status === 'working'}
          className="mt-4 w-full py-1.5 bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 text-xs font-semibold rounded-lg transition-colors border border-blue-500/20 disabled:opacity-50"
        >
          {task.status === 'error' ? 'Retry Execution' : 'Execute Task'}
        </button>
      )}
    </div>
  );
}
