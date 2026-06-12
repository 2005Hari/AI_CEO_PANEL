import React, { useState, useEffect } from 'react';
import {
  Project,
  submitManagerPlanV2,
  getTasks,
  getObjectives,
  getPendingApprovals,
  getMetrics,
} from '@/lib/api';
import { LiveTerminal } from './LiveTerminal';
import { useGlobalWebSocket } from '@/contexts/WebSocketContext';

interface CeoDashboardProps {
  project: Project;
}

interface DashboardStats {
  companyHealth: number;
  activeObjectives: number;
  pendingApprovals: number;
}

export function CeoDashboard({ project }: CeoDashboardProps) {
  const [goal, setGoal] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);
  const [stats, setStats] = useState<DashboardStats>({
    companyHealth: 0,
    activeObjectives: 0,
    pendingApprovals: 0,
  });
  const [statsLoading, setStatsLoading] = useState(true);
  const [lastGoalDispatched, setLastGoalDispatched] = useState<string | null>(null);
  const { latestEvent } = useGlobalWebSocket();

  // ── Load real stats from backend ──────────────────────────────
  const loadStats = async () => {
    try {
      const [tasksData, objectivesData, approvalsData, metricsData] = await Promise.allSettled([
        getTasks(project.id),
        getObjectives(project.id),
        getPendingApprovals(project.id),
        getMetrics(project.id),
      ]);

      const tasks =
        tasksData.status === 'fulfilled'
          ? Array.isArray(tasksData.value)
            ? tasksData.value
            : tasksData.value.tasks || []
          : [];

      const objectives =
        objectivesData.status === 'fulfilled'
          ? Array.isArray(objectivesData.value)
            ? objectivesData.value
            : objectivesData.value.objectives || []
          : [];

      const approvals =
        approvalsData.status === 'fulfilled'
          ? Array.isArray(approvalsData.value)
            ? approvalsData.value
            : approvalsData.value.approvals || []
          : [];

      // Derive health from completed vs total tasks
      const completedTasks = tasks.filter(
        (t: any) => t.status === 'completed'
      ).length;
      const health =
        tasks.length > 0 ? Math.round((completedTasks / tasks.length) * 100) : 0;

      // Prefer backend health score if available
      const backendHealth =
        metricsData.status === 'fulfilled'
          ? metricsData.value?.company_health_score ?? health
          : health;

      const activeObjs = objectives.filter(
        (o: any) => o.status === 'active' || o.status === 'in_progress'
      ).length;

      setStats({
        companyHealth: backendHealth,
        activeObjectives: activeObjs,
        pendingApprovals: approvals.length,
      });
    } catch (err) {
      console.error('Failed to load dashboard stats:', err);
    } finally {
      setStatsLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, [project.id]);

  // ── Re-fetch stats when WebSocket fires relevant events ────────
  useEffect(() => {
    if (!latestEvent) return;
    const refreshTypes = [
      'task_completed',
      'task_failed',
      'plan_created',
      'approval_requested',
      'approval_decided',
    ];
    if (refreshTypes.includes(latestEvent.type)) {
      loadStats();
    }
  }, [latestEvent]);

  // ── Submit goal ────────────────────────────────────────────────
  const handleSubmitGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim()) return;
    setIsSubmitting(true);
    setSubmitStatus(null);
    const goalText = goal;
    try {
      await submitManagerPlanV2(project.id, goalText);
      setLastGoalDispatched(goalText);
      setSubmitStatus({
        type: 'success',
        message: '✓ Goal dispatched — Manager Agent is now planning. Watch the terminal below.',
      });
      setGoal('');
      // Refresh stats after plan creation
      setTimeout(loadStats, 2000);
    } catch (err: any) {
      setSubmitStatus({
        type: 'error',
        message: err.message || 'Failed to submit goal',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-8 space-y-8 animate-fadeIn">
      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-3xl font-extrabold bg-gradient-to-r from-white via-gray-200 to-gray-500 text-transparent bg-clip-text">
            CEO Dashboard
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            Real-time command center for {project.core_context?.company_name || 'your company'}
          </p>
        </div>
        <div className="px-4 py-2 bg-emerald-500/10 text-emerald-400 rounded-full text-sm font-semibold border border-emerald-500/30 flex items-center gap-2 shadow-[0_0_15px_rgba(16,185,129,0.2)]">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          System Online
        </div>
      </div>

      {/* ── Direct Command ─────────────────────────────────────── */}
      <div className="glass-premium p-6 rounded-2xl relative overflow-hidden">
        <h3 className="text-xl font-bold text-white mb-1">Direct Command</h3>
        <p className="text-gray-400 text-sm mb-4">
          Input your strategic goals. The Manager Agent will generate a plan and
          delegate tasks to the workforce automatically.
        </p>

        <form onSubmit={handleSubmitGoal} className="flex gap-4">
          <input
            type="text"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="E.g., We need to launch a new marketing campaign for Q3..."
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
            disabled={isSubmitting}
          />
          <button
            type="submit"
            disabled={isSubmitting || !goal.trim()}
            className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-xl font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 min-w-[140px] justify-center"
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Dispatching...
              </>
            ) : (
              'Execute Goal'
            )}
          </button>
        </form>

        {submitStatus && (
          <div
            className={`mt-4 p-3 rounded-lg text-sm flex items-start gap-2 ${
              submitStatus.type === 'success'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'bg-red-500/20 text-red-400 border border-red-500/30'
            }`}
          >
            {submitStatus.message}
          </div>
        )}

        {lastGoalDispatched && (
          <div className="mt-3 text-xs text-gray-500">
            Last goal: <span className="text-gray-400 italic">"{lastGoalDispatched}"</span>
          </div>
        )}
      </div>

      {/* ── Live Terminal — always visible, activates after goal ── */}
      <div className="glass-premium rounded-2xl overflow-hidden">
        <div className="px-5 py-3 border-b border-white/5 flex items-center gap-3">
          <div
            className={`w-2 h-2 rounded-full ${
              isSubmitting ? 'bg-green-400 animate-pulse' : 'bg-gray-600'
            }`}
          />
          <span className="text-sm font-semibold text-gray-300">Agent Activity Terminal</span>
          <span className="text-xs text-gray-600 ml-auto">Live WebSocket stream</span>
        </div>
        <div className="p-4">
          <LiveTerminal />
        </div>
      </div>

      {/* ── Stats ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          label="Company Health"
          value={statsLoading ? '—' : `${stats.companyHealth}%`}
          color="blue"
          loading={statsLoading}
        />
        <StatCard
          label="Active Objectives"
          value={statsLoading ? '—' : String(stats.activeObjectives)}
          color="emerald"
          loading={statsLoading}
        />
        <StatCard
          label="Pending Approvals"
          value={statsLoading ? '—' : String(stats.pendingApprovals)}
          color={stats.pendingApprovals > 0 ? 'amber' : 'gray'}
          loading={statsLoading}
          alert={stats.pendingApprovals > 0}
        />
      </div>

      {/* ── Brain Sync ─────────────────────────────────────────── */}
      <div className="glass-premium p-8 rounded-2xl relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5" />
        <div className="relative z-10">
          <h3 className="text-xl font-bold text-white mb-3 flex items-center gap-2">
            <span className="text-2xl">🧠</span> Digital Company Brain Sync
          </h3>
          <p className="text-gray-300 text-sm leading-relaxed max-w-2xl">
            The CEO Agent has synced the latest discovery data into core operating memory.
            All departments are aligned and awaiting strategic objectives.
          </p>
          {project.core_context?.company_name && (
            <div className="mt-4 flex flex-wrap gap-2">
              {[
                project.core_context.company_name,
                project.core_context.business_model,
                project.core_context.target_audience,
              ]
                .filter(Boolean)
                .map((tag, i) => (
                  <span
                    key={i}
                    className="px-3 py-1 rounded-full text-xs bg-white/5 text-gray-400 border border-white/10"
                  >
                    {tag}
                  </span>
                ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Sub-component: StatCard ────────────────────────────────────────
function StatCard({
  label,
  value,
  color,
  loading,
  alert,
}: {
  label: string;
  value: string;
  color: 'blue' | 'emerald' | 'amber' | 'gray';
  loading?: boolean;
  alert?: boolean;
}) {
  const colorMap = {
    blue: 'bg-blue-500/10 group-hover:bg-blue-500/20',
    emerald: 'bg-emerald-500/10 group-hover:bg-emerald-500/20',
    amber: 'bg-amber-500/10 group-hover:bg-amber-500/20',
    gray: 'bg-gray-500/10 group-hover:bg-gray-500/20',
  };
  const textMap = {
    blue: 'text-white',
    emerald: 'text-white',
    amber: 'text-amber-400',
    gray: 'text-gray-400',
  };

  return (
    <div className="glass-premium p-6 rounded-2xl relative overflow-hidden group">
      <div
        className={`absolute top-0 right-0 w-32 h-32 rounded-full blur-3xl transition-all ${colorMap[color]}`}
      />
      <h3 className="text-sm text-gray-400 font-semibold mb-2">{label}</h3>
      <div className={`text-4xl font-bold ${textMap[color]} ${loading ? 'animate-pulse' : ''}`}>
        {value}
      </div>
      {alert && (
        <div className="mt-2 text-xs text-amber-400/80 flex items-center gap-1">
          <span>●</span> Requires your review
        </div>
      )}
    </div>
  );
}
