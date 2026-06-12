import React, { useEffect, useState, useCallback } from 'react';
import { getPlans, getTasks, executeTask, Plan } from '@/lib/api';
import { useGlobalWebSocket } from '@/contexts/WebSocketContext';

interface PlanViewerProps {
  projectId: string;
}

export function PlanViewer({ projectId }: PlanViewerProps) {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const [tasks, setTasks] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [executingTask, setExecutingTask] = useState<string | null>(null);
  const { latestEvent } = useGlobalWebSocket();

  // ── Fetch all plans ──────────────────────────────────────────
  const fetchPlans = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await getPlans(projectId);
      const planList: Plan[] = data.plans || data || [];
      setPlans(planList);
      if (planList.length > 0) {
        // Keep current selection if it still exists
        const stillExists = selectedPlan
          ? planList.find((p) => p.id === selectedPlan.id)
          : null;
        const toSelect = stillExists || planList[0];
        await loadTasksForPlan(toSelect);
        setSelectedPlan(toSelect);
      }
    } catch (err) {
      console.error('Failed to fetch plans:', err);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, selectedPlan?.id]);

  useEffect(() => {
    fetchPlans();
  }, [projectId]);

  // ── WebSocket: reload when new plan/tasks arrive ─────────────
  useEffect(() => {
    if (!latestEvent) return;
    if (
      latestEvent.type === 'plan_created' ||
      latestEvent.type === 'tasks_created' ||
      latestEvent.type === 'task_completed' ||
      latestEvent.type === 'task_failed'
    ) {
      fetchPlans();
    }
    // Live status update for tasks already visible
    if (
      latestEvent.type === 'activity_logged' &&
      latestEvent.status === 'working'
    ) {
      setTasks((curr) =>
        curr.map((t) =>
          t.id === latestEvent.task_id ? { ...t, status: 'working' } : t
        )
      );
    }
  }, [latestEvent]);

  // ── Load tasks for a given plan ──────────────────────────────
  const loadTasksForPlan = async (plan: Plan) => {
    try {
      const data = await getTasks(projectId);
      const allTasks = Array.isArray(data) ? data : data.tasks || [];
      setTasks(allTasks.filter((t: any) => t.plan_id === plan.id));
    } catch (err) {
      console.error('Failed to fetch tasks:', err);
    }
  };

  const selectPlan = async (plan: Plan) => {
    setSelectedPlan(plan);
    await loadTasksForPlan(plan);
  };

  // ── Execute a task directly from plan view ───────────────────
  const handleExecuteTask = async (taskId: string) => {
    try {
      setExecutingTask(taskId);
      setTasks((curr) =>
        curr.map((t) => (t.id === taskId ? { ...t, status: 'working' } : t))
      );
      await executeTask(taskId);
    } catch (err) {
      console.error('Failed to execute task:', err);
    } finally {
      setExecutingTask(null);
    }
  };

  // ── Helpers ──────────────────────────────────────────────────
  const getStatusBadge = (status: string) => {
    const map: Record<string, string> = {
      active: 'bg-green-500/20 text-green-300 border-green-500/30',
      completed: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
      paused: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
      draft: 'bg-gray-500/20 text-gray-300 border-gray-500/30',
    };
    return map[status] ?? 'bg-gray-500/20 text-gray-300 border-gray-500/30';
  };

  const getTaskStatusStyle = (status: string) => {
    const map: Record<string, string> = {
      completed: 'bg-green-900/20 border-green-500/30',
      working: 'bg-blue-900/20 border-blue-500/30',
      pending: 'bg-gray-900/30 border-gray-700/50',
      assigned: 'bg-gray-900/30 border-gray-700/50',
      failed: 'bg-red-900/20 border-red-500/30',
      review: 'bg-purple-900/20 border-purple-500/30',
    };
    return map[status] ?? 'bg-gray-900/30 border-gray-700/50';
  };

  const getPriorityDot = (priority: string) => {
    const map: Record<string, string> = {
      high: 'bg-red-400',
      medium: 'bg-yellow-400',
      low: 'bg-green-400',
    };
    return map[priority?.toLowerCase()] ?? 'bg-gray-400';
  };

  // ── Render ───────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-blue-500/20 bg-gradient-to-br from-blue-900/10 to-cyan-900/10 p-6 backdrop-blur">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            📊 Plans & Tasks
          </h2>
          <button
            onClick={fetchPlans}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors px-2 py-1 rounded-lg hover:bg-white/5"
          >
            ↻ Refresh
          </button>
        </div>

        {isLoading ? (
          <div className="flex items-center gap-3 text-gray-500 text-sm py-4">
            <div className="w-4 h-4 border-2 border-gray-600 border-t-gray-300 rounded-full animate-spin" />
            Loading plans...
          </div>
        ) : plans.length === 0 ? (
          <div className="text-center py-8 text-gray-500 text-sm border-2 border-dashed border-white/5 rounded-xl">
            <div className="text-2xl mb-2">📋</div>
            No plans yet. Use the input above to generate your first plan.
          </div>
        ) : (
          <div className="space-y-6">
            {/* ── Plan list ──────────────────────────────────── */}
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                Available Plans
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {plans.map((plan) => (
                  <div
                    key={plan.id}
                    onClick={() => selectPlan(plan)}
                    className={`p-4 rounded-xl cursor-pointer transition-all border ${
                      selectedPlan?.id === plan.id
                        ? 'bg-blue-900/30 border-blue-500/60 ring-1 ring-blue-500/30'
                        : 'bg-gray-900/30 border-gray-700/50 hover:border-gray-600'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <h4 className="font-semibold text-white text-sm truncate">
                          {plan.title}
                        </h4>
                        {plan.description && (
                          <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                            {plan.description}
                          </p>
                        )}
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap border ${getStatusBadge(
                          plan.status
                        )}`}
                      >
                        {plan.status}
                      </span>
                    </div>
                    {plan.milestones && plan.milestones.length > 0 && (
                      <div className="mt-2 text-xs text-gray-600">
                        {plan.milestones.length} milestone
                        {plan.milestones.length !== 1 ? 's' : ''}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* ── Tasks for selected plan ─────────────────────── */}
            {selectedPlan && (
              <div>
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                  Tasks for "{selectedPlan.title}"
                </h3>
                {tasks.length === 0 ? (
                  <div className="text-gray-600 text-sm text-center py-4 border-2 border-dashed border-white/5 rounded-xl">
                    No tasks yet — the agent may still be generating them.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {tasks.map((task) => (
                      <div
                        key={task.id}
                        className={`p-3 rounded-xl border transition-all ${getTaskStatusStyle(
                          task.status
                        )}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <div
                                className={`w-1.5 h-1.5 rounded-full shrink-0 ${getPriorityDot(
                                  task.priority
                                )}`}
                              />
                              <h5 className="font-medium text-white text-sm">
                                {task.title}
                              </h5>
                            </div>
                            {task.description && (
                              <p className="text-xs text-gray-400 mt-1 ml-3.5">
                                {task.description}
                              </p>
                            )}
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            {/* Agent badge */}
                            <span className="text-xs px-2 py-0.5 rounded-full bg-white/5 text-gray-400 border border-white/10">
                              {task.assigned_agent || 'unassigned'}
                            </span>

                            {/* Execute button — only for pending/assigned tasks */}
                            {(task.status === 'pending' ||
                              task.status === 'assigned') && (
                              <button
                                onClick={() => handleExecuteTask(task.id)}
                                disabled={executingTask === task.id}
                                className="text-xs px-3 py-1 bg-blue-600/80 hover:bg-blue-500 text-white rounded-lg transition-all disabled:opacity-50 flex items-center gap-1.5"
                              >
                                {executingTask === task.id ? (
                                  <>
                                    <div className="w-2.5 h-2.5 border border-white/40 border-t-white rounded-full animate-spin" />
                                    Running
                                  </>
                                ) : (
                                  '▶ Run'
                                )}
                              </button>
                            )}

                            {/* Working indicator */}
                            {task.status === 'working' && (
                              <div className="flex items-center gap-1.5 text-xs text-blue-400">
                                <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
                                Working
                              </div>
                            )}

                            {/* Completed check */}
                            {task.status === 'completed' && (
                              <span className="text-xs text-green-400">✓</span>
                            )}
                          </div>
                        </div>

                        <div className="mt-2 flex items-center gap-3 text-xs text-gray-600 ml-3.5">
                          <span>{task.priority || 'medium'} priority</span>
                          <span className="text-gray-700">·</span>
                          <span
                            className={
                              task.status === 'completed'
                                ? 'text-green-500'
                                : task.status === 'working'
                                ? 'text-blue-400'
                                : 'text-gray-500'
                            }
                          >
                            {task.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
