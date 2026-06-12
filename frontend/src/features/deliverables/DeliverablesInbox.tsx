import React, { useEffect, useState } from 'react';
import { Project, getTasks } from '@/lib/api';
import { useGlobalWebSocket } from '@/contexts/WebSocketContext';

interface DeliverablesInboxProps {
  project: Project;
}

export function DeliverablesInbox({ project }: DeliverablesInboxProps) {
  const [deliverables, setDeliverables] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { latestEvent } = useGlobalWebSocket();

  useEffect(() => {
    const load = async () => {
      try {
        const tasks = await getTasks(project.id, 'completed');
        // Filter out tasks that don't have output or just map them
        const completed = tasks.filter((t: any) => t.status === 'completed');
        setDeliverables(completed);
      } catch (e) {
        console.error("Failed to load deliverables", e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [project.id]);

  useEffect(() => {
    if (latestEvent && latestEvent.type === 'task_completed') {
      const newDeliverable = {
        id: latestEvent.task_id,
        title: `Task ${latestEvent.task_id}`,
        output_result: { content: latestEvent.deliverable },
        updated_at: new Date().toISOString(),
        assigned_worker: 'System Worker',
      };
      setDeliverables(prev => [newDeliverable, ...prev]);
    }
  }, [latestEvent]);

  if (loading) {
    return <div className="p-8 text-gray-500">Loading Deliverables...</div>;
  }

  return (
    <div className="p-8 space-y-6 animate-fadeIn">
      <h2 className="text-2xl font-bold text-white">Deliverables Inbox</h2>
      <p className="text-gray-400 text-sm">Review completed work from your AI workforce.</p>
      
      <div className="space-y-4">
        {deliverables.length === 0 && (
          <div className="text-gray-500 text-sm mt-4">No deliverables available yet.</div>
        )}
        {deliverables.map((item, idx) => (
          <div key={item.id || idx} className="glass p-5 rounded-2xl flex items-center justify-between hover:bg-white/[0.04] hover:shadow-xl hover:-translate-y-0.5 transition-all cursor-pointer border border-white/5">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 text-blue-400 flex items-center justify-center text-xl shadow-lg shadow-blue-500/10">
                📄
              </div>
              <div>
                <h3 className="text-white font-semibold">{item.title}</h3>
                <p className="text-xs text-gray-500">From {item.assigned_worker || 'System Worker'} • {new Date(item.updated_at || item.created_at || Date.now()).toLocaleDateString()}</p>
              </div>
            </div>
            <div>
              <span className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-semibold px-3 py-1.5 rounded-full">
                Completed
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
