import React, { useEffect, useState } from 'react';
import { Project, getBlueprint } from '@/lib/api';
import { BlueprintViewer } from './BlueprintViewer';

interface OverviewPanelProps {
  project: Project;
  onNavigateToDiscovery: () => void;
}

export function OverviewPanel({ project, onNavigateToDiscovery }: OverviewPanelProps) {
  const [blueprint, setBlueprint] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = await getBlueprint(project.id);
        setBlueprint(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [project.id]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center animate-pulse">
        <div className="text-gray-500 text-sm">Loading Company Overview...</div>
      </div>
    );
  }

  const confidenceScore = blueprint ? Math.round(blueprint.discovery_confidence * 100) : 0;
  const needsDiscovery = confidenceScore < 90;

  return (
    <div className="h-full overflow-y-auto p-6 bg-[#050510] space-y-6">
      
      {/* Top Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass rounded-xl p-5 border border-white/[0.04]">
          <h3 className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Company Health</h3>
          <div className="flex items-end gap-2">
            <span className="text-3xl font-bold text-white">
              {project.health_score ? `${Math.round(project.health_score * 100)}%` : 'TBD'}
            </span>
          </div>
        </div>
        
        <div className="glass rounded-xl p-5 border border-white/[0.04]">
          <h3 className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Discovery Status</h3>
          <div className="flex flex-col gap-2">
            <div className="flex items-end justify-between">
              <span className="text-3xl font-bold text-white">{confidenceScore}%</span>
              {needsDiscovery && (
                <button 
                  onClick={onNavigateToDiscovery}
                  className="text-xs bg-blue-600/20 text-blue-400 px-3 py-1 rounded-md hover:bg-blue-600/30 transition-colors"
                >
                  Continue
                </button>
              )}
            </div>
            <div className="h-1.5 w-full bg-gray-800 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full ${confidenceScore >= 90 ? 'bg-emerald-500' : 'bg-blue-500'}`} 
                style={{ width: `${confidenceScore}%` }}
              />
            </div>
          </div>
        </div>

        <div className="glass rounded-xl p-5 border border-white/[0.04]">
          <h3 className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Operating Mode</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className="px-3 py-1 text-xs font-semibold rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/20">
              {project.operating_mode === 'business' ? 'Business Mode' : 'Startup Mode'}
            </span>
          </div>
          <p className="text-[10px] text-gray-500 mt-2">
            {project.operating_mode === 'business' 
              ? 'Focus: Revenue, Growth, Automation' 
              : 'Focus: Validation, MVP, Fundraising'}
          </p>
        </div>
      </div>

      {/* Blueprint Viewer */}
      {blueprint && <BlueprintViewer blueprint={blueprint} />}

    </div>
  );
}
