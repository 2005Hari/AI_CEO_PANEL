import React, { useEffect, useState } from 'react';
import { Project, getObjectives, createObjective } from '@/lib/api';

interface ObjectivesPanelProps {
  project: Project;
}

export function ObjectivesPanel({ project }: ObjectivesPanelProps) {
  const [objectives, setObjectives] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [showForm, setShowForm] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');

  const load = async () => {
    try {
      const data = await getObjectives(project.id);
      setObjectives(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [project.id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    try {
      await createObjective(project.id, { title: newTitle, description: newDesc });
      setShowForm(false);
      setNewTitle('');
      setNewDesc('');
      await load();
    } catch (e) {
      console.error("Failed to create objective", e);
    }
  };

  if (loading) {
    return <div className="p-6 text-gray-500">Loading Objectives...</div>;
  }

  return (
    <div className="h-full overflow-y-auto p-6 bg-[#050510] max-w-4xl mx-auto border-x border-white/[0.04]">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-xl font-bold text-white">Company Objectives</h2>
          <p className="text-xs text-gray-500">Strategic goals and milestones</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 text-xs font-bold rounded-lg transition-colors border border-blue-500/20"
        >
          {showForm ? 'Cancel' : '+ New Objective'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="glass p-5 rounded-xl border border-white/[0.04] mb-8 animate-fadeSlideIn space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-400 mb-1">Objective Title</label>
            <input
              type="text"
              value={newTitle}
              onChange={e => setNewTitle(e.target.value)}
              className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 text-sm text-white focus:border-blue-500/50"
              placeholder="e.g. Launch MVP to 100 beta users"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-400 mb-1">Description (optional)</label>
            <textarea
              value={newDesc}
              onChange={e => setNewDesc(e.target.value)}
              className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 text-sm text-white focus:border-blue-500/50"
              placeholder="Success criteria, context, etc."
              rows={3}
            />
          </div>
          <div className="flex justify-end">
            <button type="submit" className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-lg shadow-lg">
              Save Objective
            </button>
          </div>
        </form>
      )}

      <div className="space-y-4">
        {objectives.length === 0 ? (
          <div className="text-center py-10 text-gray-600 text-sm border-2 border-dashed border-white/[0.05] rounded-2xl">
            No active objectives. Set your first goal to align the team.
          </div>
        ) : (
          objectives.map(obj => (
            <div key={obj.id} className="glass p-5 rounded-xl border border-white/[0.04] group">
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-base font-bold text-gray-200">{obj.title}</h3>
                <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                  obj.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-gray-500/10 text-gray-400 border border-gray-500/20'
                }`}>
                  {obj.status}
                </span>
              </div>
              {obj.description && (
                <p className="text-sm text-gray-400 mb-4">{obj.description}</p>
              )}
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full" style={{ width: `${(obj.progress || 0) * 100}%` }} />
                </div>
                <span className="text-xs text-gray-500 font-mono">{Math.round((obj.progress || 0) * 100)}%</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
