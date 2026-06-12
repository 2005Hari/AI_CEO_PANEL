import React, { useEffect, useState, useRef } from 'react';
import { Project, getActivityFeed } from '@/lib/api';
import { useGlobalWebSocket } from '@/contexts/WebSocketContext';

interface ActivityFeedProps {
  project: Project;
}

export function ActivityFeed({ project }: ActivityFeedProps) {
  const [activities, setActivities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { latestEvent } = useGlobalWebSocket();

  useEffect(() => {
    // Initial fetch
    const load = async () => {
      try {
        const data = await getActivityFeed(project.id, 50);
        setActivities(data);
      } catch (e) {
        console.error("Failed to load activity feed", e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [project.id]);

  useEffect(() => {
    if (latestEvent) {
      if (latestEvent.type === 'activity_logged') {
        // Construct a pseudo activity object
        const newActivity = {
          id: `live-${Date.now()}`,
          project_id: project.id,
          task_id: latestEvent.task_id,
          agent_role: 'System Worker',
          activity_type: latestEvent.status,
          message: `Worker started task ${latestEvent.task_id}`,
          created_at: new Date().toISOString()
        };
        setActivities(prev => [newActivity, ...prev]);
      } else if (latestEvent.type === 'task_completed') {
        const newActivity = {
          id: `live-${Date.now()}`,
          project_id: project.id,
          task_id: latestEvent.task_id,
          agent_role: 'System Worker',
          activity_type: 'completed',
          message: `Worker completed task ${latestEvent.task_id}`,
          created_at: new Date().toISOString()
        };
        setActivities(prev => [newActivity, ...prev]);
      }
    }
  }, [latestEvent, project.id]);

  useEffect(() => {
    // Auto-scroll to top when new activities arrive (since flex-col-reverse or we just render normally)
    // Wait, our array has newest at index 0. So they appear at the top.
  }, [activities]);

  if (loading) {
    return <div className="p-6 text-gray-500">Loading Activity Feed...</div>;
  }

  const getActivityIcon = (type: string) => {
    switch(type) {
      case 'assigned': return '📋';
      case 'generating': return '⚙️';
      case 'completed': return '✅';
      case 'error': return '❌';
      default: return '💬';
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#050510] border-l border-white/[0.04] w-80 shrink-0">
      <div className="px-5 py-4 border-b border-white/[0.04]">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
          Live Agent Activity
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-6" ref={scrollRef}>
        {activities.map((activity, idx) => {
          const date = new Date(activity.created_at);
          const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          
          return (
            <div key={activity.id || idx} className="relative pl-6 animate-fadeSlideIn">
              {/* Timeline line */}
              {idx !== activities.length - 1 && (
                <div className="absolute left-[11px] top-6 bottom-[-24px] w-px bg-white/[0.04]" />
              )}
              
              {/* Icon dot */}
              <div className="absolute left-0 top-1 w-6 h-6 rounded-full glass border border-white/[0.05] flex items-center justify-center text-[10px]">
                {getActivityIcon(activity.activity_type)}
              </div>
              
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-blue-400">@{activity.agent_role}</span>
                  <span className="text-[9px] text-gray-600 font-mono">{timeStr}</span>
                </div>
                <p className="text-xs text-gray-300 leading-relaxed">
                  {activity.message || `Agent ${activity.activity_type} a task`}
                </p>
              </div>
            </div>
          );
        })}
        {activities.length === 0 && (
          <div className="text-center text-gray-600 text-xs mt-10">No recent activity</div>
        )}
      </div>
    </div>
  );
}
