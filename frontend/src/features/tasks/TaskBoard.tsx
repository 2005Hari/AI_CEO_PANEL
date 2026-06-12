import React, { useEffect, useState, useRef } from 'react';
import { Project, getTasks, executeTask, submitManagerPlanV2 } from '@/lib/api';
import { TaskCard } from './TaskCard';
import { useGlobalWebSocket } from '@/contexts/WebSocketContext';

interface TaskBoardProps {
  project: Project;
}

export function TaskBoard({ project }: TaskBoardProps) {
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [delegateInput, setDelegateInput] = useState('');
  const [isDelegating, setIsDelegating] = useState(false);
  const [delegateStatus, setDelegateStatus] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);
  const { latestEvent } = useGlobalWebSocket();
  const statusTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Load tasks — handle both array and {tasks:[]} shapes ─────
  const loadTasks = async () => {
    try {
      const data = await getTasks(project.id);
      const taskList = Array.isArray(data) ? data : data.tasks || [];
      setTasks(taskList);
    } catch (e) {
      console.error('Failed to load tasks:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, [project.id]);

  // ── WebSocket: live status updates ───────────────────────────
  useEffect(() => {
    if (!latestEvent) return;

    switch (latestEvent.type) {
      case 'activity_logged':
        if (latestEvent.status === 'working') {
          setTasks((curr) =>
            curr.map((t) =>
              t.id === latestEvent.task_id ? { ...t, status: 'working' } : t
            )
          );
        }
        break;
      case 'task_completed':
        setTasks((curr) =>
          curr.map((t) =>
            t.id === latestEvent.task_id ? { ...t, status: 'completed' } : t
          )
        );
        break;
      case 'task_failed':
        setTasks((curr) =>
          curr.map((t) =>
            t.id === latestEvent.task_id ? { ...t, status: 'failed' } : t
          )
        );
        break;
      case 'plan_created':
      case 'tasks_created':
        // New plan/tasks created — reload the board
        setTimeout(loadTasks, 800);
        break;
    }
  }, [latestEvent]);

  // ── Execute a single task ─────────────────────────────────────
  const handleExecute = async (taskId: string) => {
    try {
      setTasks((curr) =>
        curr.map((t) => (t.id === taskId ? { ...t, status: 'working' } : t))
      );
      await executeTask(taskId);
      await loadTasks();
    } catch (e) {
      console.error('Failed to execute task:', e);
      await loadTasks();
    }
  };

  // ── Delegate bar — wire to Manager v2 ────────────────────────
  const handleDelegate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!delegateInput.trim() || isDelegating) return;
    const text = delegateInput;
    setDelegateInput('');
    setIsDelegating(true);
    setDelegateStatus(null);
    try {
      await submitManagerPlanV2(project.id, text);
      setDelegateStatus({
        type: 'success',
        message: '✓ Delegated — Manager Agent is building the plan now.',
      });
      // Reload tasks after a short delay to pick up new ones
      setTimeout(loadTasks, 2500);
    } catch (err: any) {
      setDelegateStatus({
        type: 'error',
        message: err.message || 'Failed to delegate',
      });
      setDelegateInput(text);
    } finally {
      setIsDelegating(false);
      // Auto-clear status after 4s
      if (statusTimerRef.current) clearTimeout(statusTimerRef.current);
      statusTimerRef.current = setTimeout(() => setDelegateStatus(null), 4000);
    }
  };

  // ── Column config ─────────────────────────────────────────────
  const columns = [
    {
      id: 'pending',
      title: 'Pending',
      tasks: tasks.filter(
        (t) => t.status === 'pending' || t.status === 'assigned'
      ),
    },
    {
      id: 'working',
      title: 'In Progress',
      tasks: tasks.filter((t) => t.status === 'working'),
    },
    {
      id: 'review',
      title: 'Review',
      tasks: tasks.filter((t) => t.status === 'review'),
    },
    {
      id: 'completed',
      title: 'Completed',
      tasks: tasks.filter((t) => t.status === 'completed'),
    },
  ];

  const activeCount = tasks.filter(
    (t) => t.status === 'working' || t.status === 'pending' || t.status === 'assigned'
  ).length;

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-[#050510]">
        <div className="flex items-center gap-3 text-gray-500">
          <div className="w-4 h-4 border-2 border-gray-600 border-t-gray-300 rounded-full animate-spin" />
          Loading tasks...
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-[#050510] overflow-hidden">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="px-6 py-4 border-b border-white/[0.04] shrink-0 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">Task Board</h2>
          <p className="text-xs text-gray-500">Manage and execute agent tasks</p>
        </div>
        <div className="flex items-center gap-2">
          {activeCount > 0 && (
            <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-full">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              {activeCount} task{activeCount !== 1 ? 's' : ''} running
            </div>
          )}
          <button
            onClick={loadTasks}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors px-2 py-1 rounded-lg hover:bg-white/5"
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* ── Kanban columns ──────────────────────────────────────── */}
      <div className="flex-1 overflow-x-auto p-6">
        <div className="flex gap-6 h-full min-w-max">
          {columns.map((col) => (
            <div key={col.id} className="w-80 flex flex-col h-full">
              <div className="flex items-center justify-between mb-4 px-2">
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">
                  {col.title}
                </h3>
                <span className="bg-white/5 text-gray-400 text-[10px] px-2 py-0.5 rounded-full font-medium">
                  {col.tasks.length}
                </span>
              </div>

              <div className="flex-1 overflow-y-auto space-y-3 pb-6">
                {col.tasks.length === 0 ? (
                  <div className="border-2 border-dashed border-white/[0.04] rounded-xl p-4 text-center text-gray-600 text-xs font-medium">
                    No tasks
                  </div>
                ) : (
                  col.tasks.map((task) => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      onExecute={() => handleExecute(task.id)}
                    />
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Delegate bar — WIRED ────────────────────────────────── */}
      <div className="shrink-0 border-t border-white/[0.04] p-4 bg-[#050510]">
        {delegateStatus && (
          <div
            className={`mb-3 px-4 py-2 rounded-lg text-xs ${
              delegateStatus.type === 'success'
                ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/20'
                : 'bg-red-500/15 text-red-400 border border-red-500/20'
            }`}
          >
            {delegateStatus.message}
          </div>
        )}
        <form onSubmit={handleDelegate} className="flex gap-3">
          <div className="flex-1 flex items-center gap-3 bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 focus-within:border-blue-500/40 transition-colors">
            <span className="text-lg shrink-0">⚡</span>
            <input
              type="text"
              value={delegateInput}
              onChange={(e) => setDelegateInput(e.target.value)}
              placeholder="Tell the Manager Agent what needs to be done..."
              className="flex-1 bg-transparent text-white text-sm placeholder-gray-600 focus:outline-none"
              disabled={isDelegating}
            />
          </div>
          <button
            type="submit"
            disabled={!delegateInput.trim() || isDelegating}
            className="px-5 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-white/5 disabled:text-gray-600 text-white text-sm font-semibold rounded-xl transition-all disabled:cursor-not-allowed flex items-center gap-2 min-w-[110px] justify-center"
          >
            {isDelegating ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Working...
              </>
            ) : (
              'Delegate'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
