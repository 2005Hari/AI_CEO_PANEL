import React, { useEffect, useRef, useState } from 'react';
import { useGlobalWebSocket } from '@/contexts/WebSocketContext';

type LogType = 'thought' | 'tool_call' | 'tool_result' | 'lifecycle_start' | 'lifecycle_end' | 'error' | 'system';

interface LogEntry {
  id: string;
  type: LogType;
  agentRole?: string;
  taskTitle?: string;
  content: string;
  toolName?: string;
  timestamp: Date;
}

const TYPE_CONFIG: Record<LogType, { icon: string; color: string; label: string }> = {
  thought:        { icon: '💭', color: 'text-purple-300',  label: 'Thinking'   },
  tool_call:      { icon: '⚙️', color: 'text-yellow-300',  label: 'Tool'       },
  tool_result:    { icon: '✅', color: 'text-green-300',   label: 'Result'     },
  lifecycle_start:{ icon: '▶',  color: 'text-blue-400',    label: 'Started'    },
  lifecycle_end:  { icon: '✓',  color: 'text-emerald-400', label: 'Completed'  },
  error:          { icon: '✗',  color: 'text-red-400',     label: 'Error'      },
  system:         { icon: '●',  color: 'text-gray-500',    label: 'System'     },
};

export function LiveTerminal() {
  const { latestEvent } = useGlobalWebSocket();
  const [logs, setLogs] = useState<LogEntry[]>([
    {
      id: 'init',
      type: 'system',
      content: 'Terminal ready — waiting for agent activity...',
      timestamp: new Date(),
    },
  ]);
  const [isActive, setIsActive] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const addLog = (entry: Omit<LogEntry, 'id' | 'timestamp'>) => {
    setLogs((prev) => [
      ...prev.slice(-199), // Keep last 200 entries
      { ...entry, id: crypto.randomUUID(), timestamp: new Date() },
    ]);
  };

  useEffect(() => {
    if (!latestEvent) return;

    switch (latestEvent.type) {
      case 'agent_lifecycle':
        if (latestEvent.event === 'started') {
          setIsActive(true);
          setActiveAgent(latestEvent.agent_role);
          addLog({
            type: 'lifecycle_start',
            agentRole: latestEvent.agent_role,
            taskTitle: latestEvent.task_title,
            content: `${latestEvent.agent_role} picked up: "${latestEvent.task_title}"`,
          });
        } else if (latestEvent.event === 'completed') {
          setIsActive(false);
          addLog({
            type: 'lifecycle_end',
            agentRole: latestEvent.agent_role,
            taskTitle: latestEvent.task_title,
            content: `${latestEvent.agent_role} completed: "${latestEvent.task_title}"`,
          });
        }
        break;

      case 'activity_logged':
        if (latestEvent.status === 'working') {
          setIsActive(true);
          setActiveAgent(latestEvent.agent_role);
          addLog({
            type: 'lifecycle_start',
            agentRole: latestEvent.agent_role,
            taskTitle: latestEvent.task_title,
            content: `${latestEvent.agent_role || 'Agent'} started: "${latestEvent.task_title || 'task'}"`,
          });
        }
        break;

      case 'agent_stream':
        if (latestEvent.stream_type === 'thought') {
          addLog({
            type: 'thought',
            agentRole: latestEvent.agent_role,
            content: latestEvent.content,
          });
        } else if (latestEvent.stream_type === 'tool_call') {
          addLog({
            type: 'tool_call',
            agentRole: latestEvent.agent_role,
            toolName: latestEvent.tool_name,
            content: latestEvent.content || `Using tool: ${latestEvent.tool_name}`,
          });
        } else if (latestEvent.stream_type === 'tool_result') {
          addLog({
            type: 'tool_result',
            agentRole: latestEvent.agent_role,
            toolName: latestEvent.tool_name,
            content: latestEvent.content || `Tool ${latestEvent.tool_name} returned`,
          });
        }
        break;

      case 'task_completed':
        setIsActive(false);
        addLog({
          type: 'lifecycle_end',
          agentRole: latestEvent.agent_role,
          taskTitle: latestEvent.task_title,
          content: `Task completed${latestEvent.task_title ? `: "${latestEvent.task_title}"` : ''}`,
        });
        if (latestEvent.deliverable_preview) {
          addLog({
            type: 'system',
            content: `Preview: ${latestEvent.deliverable_preview}`,
          });
        }
        break;

      case 'task_failed':
        setIsActive(false);
        addLog({
          type: 'error',
          agentRole: latestEvent.agent_role,
          content: `Task failed: ${latestEvent.error || 'Unknown error'}`,
        });
        break;

      case 'plan_created':
        addLog({
          type: 'system',
          content: `New plan created: "${latestEvent.plan_title || 'Plan'}" — tasks queuing...`,
        });
        break;

      case 'tasks_created':
        addLog({
          type: 'system',
          content: `${latestEvent.count || 'Multiple'} tasks queued for execution.`,
        });
        break;
    }
  }, [latestEvent]);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const clearLogs = () => {
    setLogs([{
      id: 'cleared',
      type: 'system',
      content: 'Terminal cleared.',
      timestamp: new Date(),
    }]);
  };

  return (
    <div className="flex flex-col h-64 bg-black/60 rounded-xl border border-white/[0.06] overflow-hidden font-mono text-xs">
      {/* Terminal header */}
      <div className="flex items-center justify-between px-4 py-2 bg-white/[0.03] border-b border-white/[0.04] shrink-0">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full transition-colors ${isActive ? 'bg-emerald-400 animate-pulse' : 'bg-gray-600'}`} />
          <span className="text-gray-400 text-[11px]">
            {isActive && activeAgent ? `${activeAgent} — working...` : 'Agent Activity Terminal'}
          </span>
        </div>
        <button
          onClick={clearLogs}
          className="text-gray-600 hover:text-gray-400 transition-colors text-[10px]"
        >
          clear
        </button>
      </div>

      {/* Log entries */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
        {logs.map((log) => {
          const config = TYPE_CONFIG[log.type];
          return (
            <div key={log.id} className="flex gap-2 items-start leading-relaxed">
              <span className={`shrink-0 ${config.color} w-4 text-center`}>{config.icon}</span>
              <div className="flex-1 min-w-0">
                {log.agentRole && log.type !== 'system' && (
                  <span className="text-gray-600 mr-1.5">[{log.agentRole}]</span>
                )}
                <span className={config.color}>{log.content}</span>
              </div>
              <span className="text-gray-700 shrink-0 text-[10px]">
                {log.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
