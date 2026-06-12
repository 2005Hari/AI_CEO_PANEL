"use client";
// frontend/src/features/departments/DepartmentsPanel.tsx
import React, { useEffect, useState, useCallback } from 'react';
import { Project } from '@/lib/api';
import { useGlobalWebSocket } from '@/contexts/WebSocketContext';

interface DepartmentsPanelProps {
  project: Project;
}

interface DeptData {
  id: string;
  name: string;
  icon: string;
  status: 'Active' | 'Idle' | 'Busy';
  queueLoad: number;      // 0-100
  activeAgents: number;
  completedTasks: number;
  totalTasks: number;
}

const DEPT_ICONS: Record<string, string> = {
  Technology: '💻',
  Marketing: '📈',
  Sales: '🤝',
  Design: '🎨',
  Operations: '⚙️',
  Finance: '💰',
  HR: '👥',
  Legal: '⚖️',
};

export function DepartmentsPanel({ project }: DepartmentsPanelProps) {
  const [departments, setDepartments] = useState<DeptData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { latestEvent } = useGlobalWebSocket();

  const loadDepartments = useCallback(async () => {
    try {
      setError(null);

      // Fetch departments + tasks in parallel
      const [deptsRes, tasksRes] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1'}/projects/${project.id}/departments`, {
          headers: { 'Content-Type': 'application/json' },
        }),
        fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1'}/projects/${project.id}/tasks`, {
          headers: { 'Content-Type': 'application/json' },
        }),
      ]);

      const deptsData = deptsRes.ok ? await deptsRes.json() : [];
      const tasksData = tasksRes.ok ? await tasksRes.json() : [];

      const deptList = Array.isArray(deptsData) ? deptsData : deptsData.departments || [];
      const taskList = Array.isArray(tasksData) ? tasksData : tasksData.tasks || [];

      // Compute live metrics per department
      const enriched: DeptData[] = deptList.map((dept: any) => {
        const deptTasks = taskList.filter(
          (t: any) => t.department_id === dept.id || t.department === dept.name
        );
        const activeTasks = deptTasks.filter(
          (t: any) => t.status === 'working' || t.status === 'pending' || t.status === 'assigned'
        );
        const completedTasks = deptTasks.filter((t: any) => t.status === 'completed');

        const queueLoad =
          deptTasks.length > 0
            ? Math.round((activeTasks.length / deptTasks.length) * 100)
            : 0;

        const status: DeptData['status'] =
          activeTasks.filter((t: any) => t.status === 'working').length > 0
            ? 'Busy'
            : activeTasks.length > 0
            ? 'Active'
            : 'Idle';

        return {
          id: dept.id,
          name: dept.name,
          icon: DEPT_ICONS[dept.name] ?? '🏢',
          status,
          queueLoad,
          activeAgents: activeTasks.filter((t: any) => t.status === 'working').length,
          completedTasks: completedTasks.length,
          totalTasks: deptTasks.length,
        };
      });

      setDepartments(enriched);
    } catch (err: any) {
      console.error('Failed to load departments:', err);
      setError('Could not load departments.');
    } finally {
      setLoading(false);
    }
  }, [project.id]);

  useEffect(() => {
    loadDepartments();
  }, [project.id]);

  // Re-compute on any task lifecycle event
  useEffect(() => {
    if (!latestEvent) return;
    const refresh = [
      'task_completed', 'task_failed', 'activity_logged',
      'tasks_created', 'plan_created',
    ];
    if (refresh.includes(latestEvent.type)) {
      loadDepartments();
    }
  }, [latestEvent]);

  // ── Render ─────────────────────────────────────────────────────
  return (
    <div className="p-8 space-y-6 animate-fadeIn">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Company Departments</h2>
          <p className="text-gray-400 text-sm mt-1">
            Monitor and manage the AI workforce across departments.
          </p>
        </div>
        <button
          onClick={loadDepartments}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors px-3 py-1.5 rounded-lg hover:bg-white/5 border border-white/5"
        >
          ↻ Refresh
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="glass p-6 rounded-2xl animate-pulse">
              <div className="h-6 bg-white/5 rounded w-1/2 mb-4" />
              <div className="h-4 bg-white/5 rounded w-3/4" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="text-red-400 text-sm p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
          {error}
        </div>
      ) : departments.length === 0 ? (
        <div className="text-center py-12 text-gray-500 border-2 border-dashed border-white/5 rounded-2xl">
          <div className="text-3xl mb-3">🏢</div>
          <p className="text-sm">No departments found for this project.</p>
          <p className="text-xs text-gray-600 mt-1">
            Departments are created automatically when you generate a plan.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {departments.map((dept) => (
            <DeptCard key={dept.id} dept={dept} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Department Card ──────────────────────────────────────────────
function DeptCard({ dept }: { dept: DeptData }) {
  const statusConfig = {
    Busy: {
      dot: 'bg-emerald-400 animate-pulse',
      badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
      bar: 'bg-emerald-500',
    },
    Active: {
      dot: 'bg-blue-400',
      badge: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
      bar: 'bg-blue-500',
    },
    Idle: {
      dot: 'bg-gray-500',
      badge: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
      bar: 'bg-gray-600',
    },
  }[dept.status];

  return (
    <div className="glass p-6 rounded-2xl flex flex-col gap-4 hover:border-white/10 transition-all border border-white/[0.04]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-3xl">{dept.icon}</span>
          <h3 className="text-lg font-bold text-white">{dept.name}</h3>
        </div>
        <div className={`w-2 h-2 rounded-full ${statusConfig.dot}`} />
      </div>

      {/* Queue load bar */}
      <div className="space-y-1.5">
        <div className="flex justify-between items-center text-xs">
          <span className="text-gray-500">Queue Load</span>
          <span className="text-white font-semibold">{dept.queueLoad}%</span>
        </div>
        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${statusConfig.bar}`}
            style={{ width: `${dept.queueLoad}%` }}
          />
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-white/[0.03] rounded-lg py-2">
          <div className="text-white font-bold text-sm">{dept.activeAgents}</div>
          <div className="text-gray-600 text-[10px] mt-0.5">Running</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg py-2">
          <div className="text-white font-bold text-sm">{dept.completedTasks}</div>
          <div className="text-gray-600 text-[10px] mt-0.5">Done</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg py-2">
          <div className="text-white font-bold text-sm">{dept.totalTasks}</div>
          <div className="text-gray-600 text-[10px] mt-0.5">Total</div>
        </div>
      </div>

      {/* Status badge */}
      <div className="flex items-center justify-between border-t border-white/5 pt-3">
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${statusConfig.badge}`}>
          {dept.status}
        </span>
        {dept.activeAgents > 0 && (
          <span className="text-xs text-gray-500">
            {dept.activeAgents} agent{dept.activeAgents !== 1 ? 's' : ''} working
          </span>
        )}
      </div>
    </div>
  );
}
