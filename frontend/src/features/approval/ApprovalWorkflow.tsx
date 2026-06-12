import React, { useEffect, useState } from 'react';
import { getPendingApprovals, decideApproval } from '@/lib/api';

interface ApprovalWorkflowProps {
  projectId: string;
  onApprovalDecided?: () => void;
}

export function ApprovalWorkflow({ projectId, onApprovalDecided }: ApprovalWorkflowProps) {
  const [approvals, setApprovals] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [decidingId, setDecidingId] = useState<string | null>(null);

  useEffect(() => {
    fetchApprovals();
  }, [projectId]);

  const fetchApprovals = async () => {
    try {
      setIsLoading(true);
      const data = await getPendingApprovals(projectId);
      setApprovals(data.approvals || []);
    } catch (err) {
      console.error('Failed to fetch approvals:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApproval = async (approvalId: string, approve: boolean) => {
    setDecidingId(approvalId);
    try {
      await decideApproval(projectId, approvalId, approve);
      setApprovals(approvals.filter((a) => a.id !== approvalId));
      onApprovalDecided?.();
    } catch (err: any) {
      console.error('Failed to decide approval:', err);
      alert('Error: ' + (err.message || 'Failed to decide approval'));
    } finally {
      setDecidingId(null);
    }
  };

  return (
    <div className="rounded-lg border border-amber-500/30 bg-gradient-to-br from-amber-900/10 to-orange-900/10 p-6 backdrop-blur">
      <h2 className="text-lg font-bold text-white mb-4">✅ Approval Workflow</h2>

      {isLoading ? (
        <div className="text-gray-400">Loading approvals...</div>
      ) : approvals.length === 0 ? (
        <div className="text-gray-400">No pending approvals.</div>
      ) : (
        <div className="space-y-3">
          {approvals.map((approval) => (
            <div
              key={approval.id}
              className="p-4 rounded-lg bg-gray-900/30 border border-amber-500/30 hover:border-amber-500/50 transition-colors"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <h4 className="font-semibold text-white text-sm">
                    {approval.resource_type.toUpperCase()} Review Requested
                  </h4>
                  <p className="text-xs text-gray-400 mt-1">
                    Resource ID: <span className="text-gray-300 font-mono">{approval.resource_id.slice(0, 8)}</span>
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    Requested {new Date(approval.requested_at).toLocaleDateString()}
                  </p>
                </div>
                <span className="px-2 py-1 rounded text-xs bg-amber-500/20 text-amber-300 whitespace-nowrap ml-2">
                  Pending
                </span>
              </div>

              <div className="flex items-center gap-2 pt-3 border-t border-gray-700">
                <button
                  onClick={() => handleApproval(approval.id, true)}
                  disabled={decidingId === approval.id}
                  className="flex-1 px-3 py-2 rounded-lg bg-green-600 hover:bg-green-500 disabled:bg-gray-600 text-white text-sm font-semibold transition-colors disabled:cursor-not-allowed"
                >
                  {decidingId === approval.id ? '...' : 'Approve'}
                </button>
                <button
                  onClick={() => handleApproval(approval.id, false)}
                  disabled={decidingId === approval.id}
                  className="flex-1 px-3 py-2 rounded-lg bg-red-600 hover:bg-red-500 disabled:bg-gray-600 text-white text-sm font-semibold transition-colors disabled:cursor-not-allowed"
                >
                  {decidingId === approval.id ? '...' : 'Reject'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
