import React, { useEffect, useState } from 'react';
import { getMetrics } from '@/lib/api';

interface MetricsDashboardProps {
  projectId: string;
}

export function MetricsDashboard({ projectId }: MetricsDashboardProps) {
  const [metrics, setMetrics] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [projectId]);

  const fetchMetrics = async () => {
    try {
      setIsLoading(true);
      const data = await getMetrics(projectId);
      setMetrics(data);
    } catch (err) {
      console.error('Failed to fetch metrics:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const renderMetricCard = (label: string, value: number, color: string) => (
    <div className={`rounded-lg border ${color} p-4 text-center`}>
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  );

  return (
    <div className="rounded-lg border border-cyan-500/30 bg-gradient-to-br from-cyan-900/10 to-blue-900/10 p-6 backdrop-blur">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-white">📈 Metrics Dashboard</h2>
        <button
          onClick={fetchMetrics}
          disabled={isLoading}
          className="px-3 py-1 text-xs rounded bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-600 text-white transition-colors"
        >
          {isLoading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {!metrics ? (
        <div className="text-gray-400">Loading metrics...</div>
      ) : (
        <div className="space-y-6">
          {/* Tasks Metrics */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3">📋 Tasks</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {renderMetricCard(
                'Pending',
                metrics.tasks?.pending || 0,
                'border-yellow-500/30 bg-yellow-900/10'
              )}
              {renderMetricCard(
                'Assigned',
                metrics.tasks?.assigned || 0,
                'border-blue-500/30 bg-blue-900/10'
              )}
              {renderMetricCard(
                'In Progress',
                (metrics.tasks?.working || 0) + (metrics.tasks?.review || 0),
                'border-cyan-500/30 bg-cyan-900/10'
              )}
              {renderMetricCard(
                'Completed',
                metrics.tasks?.completed || 0,
                'border-green-500/30 bg-green-900/10'
              )}
            </div>
          </div>

          {/* Deliverables Metrics */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3">📦 Deliverables</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {renderMetricCard(
                'Pending',
                metrics.deliverables?.pending || 0,
                'border-yellow-500/30 bg-yellow-900/10'
              )}
              {renderMetricCard(
                'In Progress',
                metrics.deliverables?.in_progress || 0,
                'border-blue-500/30 bg-blue-900/10'
              )}
              {renderMetricCard(
                'For Review',
                metrics.deliverables?.ready_for_review || 0,
                'border-orange-500/30 bg-orange-900/10'
              )}
              {renderMetricCard(
                'Approved',
                metrics.deliverables?.approved || 0,
                'border-green-500/30 bg-green-900/10'
              )}
            </div>
          </div>

          {/* Approvals Metrics */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3">✅ Approvals</h3>
            <div className="grid grid-cols-3 gap-3">
              {renderMetricCard(
                'Pending',
                metrics.approvals?.pending || 0,
                'border-amber-500/30 bg-amber-900/10'
              )}
              {renderMetricCard(
                'Approved',
                metrics.approvals?.approved || 0,
                'border-green-500/30 bg-green-900/10'
              )}
              {renderMetricCard(
                'Rejected',
                metrics.approvals?.rejected || 0,
                'border-red-500/30 bg-red-900/10'
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
