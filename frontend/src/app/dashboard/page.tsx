// frontend/src/app/dashboard/page.tsx
"use client";

import React, { useState, useEffect } from 'react';
import { useAuth, UserButton } from '@clerk/nextjs';
import { registerAuthTokenGetter } from '@/lib/auth-token';
import { WebSocketProvider } from '@/contexts/WebSocketContext';
import { ChatArea } from '@/features/chat/ChatArea';
import { ProfileSettings } from '@/features/projects/ProfileSettings';
import { ProjectWizard } from '@/components/ProjectWizard';
import { fetchProjects, fetchSessions, Project, Session } from '@/lib/api';

// New components
import { OverviewPanel } from '@/features/overview/OverviewPanel';
import { ObjectivesPanel } from '@/features/objectives/ObjectivesPanel';
import { TaskBoard } from '@/features/tasks/TaskBoard';
import { ActivityFeed } from '@/features/activity/ActivityFeed';
import { DiscoveryChat } from '@/features/discovery/DiscoveryChat';
import { ManagerInput } from '@/features/manager/ManagerInput';
import { ManagerV2Input } from '@/features/manager/ManagerV2Input';
import { PlanViewer } from '@/features/manager/PlanViewer';
import { ApprovalWorkflow } from '@/features/approval/ApprovalWorkflow';
import { MetricsDashboard } from '@/features/metrics/MetricsDashboard';
import { CeoDashboard } from '@/features/ceo_dashboard/CeoDashboard';
import { DepartmentsPanel } from '@/features/departments/DepartmentsPanel';
import { DeliverablesInbox } from '@/features/deliverables/DeliverablesInbox';

type Tab = 'overview' | 'ceo_dashboard' | 'departments' | 'deliverables' | 'objectives' | 'tasks' | 'boardroom' | 'settings' | 'discovery' | 'plans' | 'approvals' | 'metrics';

export default function DashboardPage() {
  const { getToken, isLoaded } = useAuth();

  useEffect(() => {
    if (isLoaded) {
      registerAuthTokenGetter(() => getToken());
    }
  }, [getToken, isLoaded]);

  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);

  // Session states for Boardroom
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [isLoading, setIsLoading] = useState(true);
  const [showWizard, setShowWizard] = useState(false);
  const [error, setError] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Layout states
  const [showActivityFeed, setShowActivityFeed] = useState(false);

  // Initial load of projects
  useEffect(() => {
    async function loadProjects() {
      try {
        const data = await fetchProjects();
        setProjects(data);
        if (data.length > 0) {
          setActiveProject(data[0]);
          // If no blueprint or low confidence, maybe go to discovery
          if (!data[0].discovery_completed) {
            setActiveTab('discovery');
          } else {
            setActiveTab('ceo_dashboard');
          }
        } else {
          setShowWizard(true);
        }
      } catch (err: any) {
        console.error(err);
        setError('Failed to connect to backend server. Make sure FastAPI server is running at http://localhost:8000.');
      } finally {
        setIsLoading(false);
      }
    }
    loadProjects();
  }, []);

  // Fetch sessions when active project changes
  useEffect(() => {
    if (activeProject) {
      const loadSessions = async () => {
        try {
          const data = await fetchSessions(activeProject.id);
          setSessions(data);
          setActiveSessionId(null);
        } catch (err) {
          console.error("Failed to load sessions", err);
        }
      };
      loadSessions();
    } else {
      setSessions([]);
      setActiveSessionId(null);
    }
  }, [activeProject]);

  const handleWizardSuccess = (newProject: Project) => {
    setProjects(prev => [...prev, newProject]);
    setActiveProject(newProject);
    setShowWizard(false);
    setActiveTab('discovery'); // Go to discovery for new projects
  };

  const handleProjectUpdate = (updatedProject: Project) => {
    setProjects(prev => prev.map(p => p.id === updatedProject.id ? updatedProject : p));
    setActiveProject(updatedProject);
  };

  const handleCreateNewClick = () => {
    setShowWizard(true);
  };

  const handleSessionCreated = async (newSessionId: string) => {
    if (activeProject) {
      try {
        const data = await fetchSessions(activeProject.id);
        setSessions(data);
      } catch (err) {
        console.error("Failed to reload sessions", err);
      }
    }
    setActiveSessionId(newSessionId);
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#050510]">
        <div className="flex flex-col items-center gap-4 animate-fadeIn">
          <div className="w-12 h-12 rounded-2xl glass flex items-center justify-center">
            <div className="w-6 h-6 border-2 border-blue-500/40 border-t-blue-400 rounded-full animate-spin" />
          </div>
          <p className="text-gray-500 text-sm font-medium">Loading Operating System...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#050510] p-4">
        <div className="max-w-md glass-strong rounded-2xl p-8 shadow-2xl text-center space-y-5 animate-fadeSlideIn">
          <div className="w-14 h-14 glass rounded-2xl flex items-center justify-center mx-auto text-red-400 text-2xl">⚠️</div>
          <h2 className="text-lg font-bold text-white">Connection Error</h2>
          <p className="text-gray-400 text-sm leading-relaxed">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-xl transition-all duration-200 shadow-lg shadow-blue-600/20 cursor-pointer"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <WebSocketProvider projectId={activeProject?.id}>
      <main className="flex min-h-screen bg-[#050510] text-gray-100 overflow-hidden">
        {/* Setup Wizard Overlay */}
      {showWizard && (
        <ProjectWizard onSuccess={handleWizardSuccess} />
      )}

      {/* ─── Sidebar ─── */}
      <div
        className={`hidden md:flex flex-col shrink-0 border-r border-white/[0.04] bg-[#08081a] select-none transition-all duration-300 ease-in-out z-20 ${
          sidebarCollapsed ? 'w-16' : 'w-60'
        }`}
      >
        {/* Sidebar Header */}
        <div className={`flex items-center justify-between p-4 ${sidebarCollapsed ? 'px-3' : 'px-5'}`}>
          {!sidebarCollapsed && (
            <div className="flex items-center gap-2 animate-fadeIn">
              <span className="font-bold text-sm bg-gradient-to-r from-blue-400 to-emerald-400 text-transparent bg-clip-text tracking-tight">
                AI Startup OS
              </span>
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded glass text-blue-400 uppercase">Beta</span>
            </div>
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-1.5 rounded-lg hover:bg-white/5 text-gray-500 hover:text-gray-300 transition-colors cursor-pointer"
            title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <svg className={`w-4 h-4 transition-transform duration-300 ${sidebarCollapsed ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            </svg>
          </button>
        </div>

        {/* Sidebar Content */}
        {!sidebarCollapsed ? (
          <div className="flex-1 flex flex-col px-3 pb-4 overflow-hidden animate-fadeIn">
            {/* Project Selector */}
            <div className="mb-6 px-2">
              <select 
                className="w-full bg-black/40 border border-white/10 rounded-lg py-2 px-3 text-xs text-white focus:outline-none focus:border-blue-500/50"
                value={activeProject?.id || ''}
                onChange={(e) => {
                  if (e.target.value === 'new') {
                    handleCreateNewClick();
                  } else {
                    const p = projects.find(p => p.id === e.target.value);
                    if (p) setActiveProject(p);
                  }
                }}
              >
                {projects.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
                <option value="new">+ Create New Startup</option>
              </select>
            </div>

            {/* Navigation */}
            <div className="flex-1 flex flex-col gap-1 overflow-y-auto pr-1">
              <div className="text-[10px] text-gray-600 font-semibold uppercase tracking-widest px-2 mb-2">Control Center</div>
              
              <button
                onClick={() => setActiveTab('ceo_dashboard')}
                className={`text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 cursor-pointer ${
                  activeTab === 'ceo_dashboard' ? 'glass-strong text-white' : 'text-gray-500 hover:bg-white/[0.03] hover:text-gray-300'
                }`}
              >
                🏢 CEO Dashboard
              </button>

              <button
                onClick={() => setActiveTab('departments')}
                className={`text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 cursor-pointer ${
                  activeTab === 'departments' ? 'glass-strong text-white' : 'text-gray-500 hover:bg-white/[0.03] hover:text-gray-300'
                }`}
              >
                👥 Departments
              </button>

              <button
                onClick={() => setActiveTab('deliverables')}
                className={`text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 cursor-pointer ${
                  activeTab === 'deliverables' ? 'glass-strong text-white' : 'text-gray-500 hover:bg-white/[0.03] hover:text-gray-300'
                }`}
              >
                📥 Deliverables Inbox
              </button>
              
              <button
                onClick={() => setActiveTab('discovery')}
                className={`text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 cursor-pointer ${
                  activeTab === 'discovery' ? 'glass-strong text-white' : 'text-gray-500 hover:bg-white/[0.03] hover:text-gray-300'
                }`}
              >
                🧭 Discovery
              </button>

              <button
                onClick={() => setActiveTab('objectives')}
                className={`text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 cursor-pointer ${
                  activeTab === 'objectives' ? 'glass-strong text-white' : 'text-gray-500 hover:bg-white/[0.03] hover:text-gray-300'
                }`}
              >
                🎯 Objectives
              </button>

              <button
                onClick={() => setActiveTab('tasks')}
                className={`text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 cursor-pointer ${
                  activeTab === 'tasks' ? 'glass-strong text-white' : 'text-gray-500 hover:bg-white/[0.03] hover:text-gray-300'
                }`}
              >
                📋 Task Board
              </button>

              <button
                onClick={() => setActiveTab('plans')}
                className={`text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 cursor-pointer ${
                  activeTab === 'plans' ? 'glass-strong text-white' : 'text-gray-500 hover:bg-white/[0.03] hover:text-gray-300'
                }`}
              >
                📊 Plans
              </button>

              <button
                onClick={() => setActiveTab('approvals')}
                className={`text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 cursor-pointer ${
                  activeTab === 'approvals' ? 'glass-strong text-white' : 'text-gray-500 hover:bg-white/[0.03] hover:text-gray-300'
                }`}
              >
                ✅ Approvals
              </button>

              <button
                onClick={() => setActiveTab('metrics')}
                className={`text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 cursor-pointer ${
                  activeTab === 'metrics' ? 'glass-strong text-white' : 'text-gray-500 hover:bg-white/[0.03] hover:text-gray-300'
                }`}
              >
                📈 Metrics
              </button>

              <div className="text-[10px] text-gray-600 font-semibold uppercase tracking-widest px-2 mt-6 mb-2">Legacy</div>
              
              <button
                onClick={() => {
                  setActiveSessionId(null);
                  setActiveTab('boardroom');
                }}
                className={`text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 cursor-pointer ${
                  activeTab === 'boardroom' ? 'glass-strong text-white' : 'text-gray-500 hover:bg-white/[0.03] hover:text-gray-300'
                }`}
              >
                💬 Boardroom Chat
              </button>

              <button
                onClick={() => setActiveTab('settings')}
                className={`text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 cursor-pointer ${
                  activeTab === 'settings' ? 'glass-strong text-white' : 'text-gray-500 hover:bg-white/[0.03] hover:text-gray-300'
                }`}
              >
                ⚙️ Settings
              </button>

            </div>
          </div>
        ) : (
          /* Collapsed state */
          <div className="flex-1 flex flex-col items-center gap-4 pt-4 animate-fadeIn">
            <button onClick={() => { setActiveTab('overview'); setSidebarCollapsed(false); }} className="w-9 h-9 rounded-xl flex items-center justify-center text-sm hover:bg-white/[0.03] transition-all cursor-pointer" title="Overview">📊</button>
            <button onClick={() => { setActiveTab('discovery'); setSidebarCollapsed(false); }} className="w-9 h-9 rounded-xl flex items-center justify-center text-sm hover:bg-white/[0.03] transition-all cursor-pointer" title="Discovery">🧭</button>
            <button onClick={() => { setActiveTab('objectives'); setSidebarCollapsed(false); }} className="w-9 h-9 rounded-xl flex items-center justify-center text-sm hover:bg-white/[0.03] transition-all cursor-pointer" title="Objectives">🎯</button>
            <button onClick={() => { setActiveTab('tasks'); setSidebarCollapsed(false); }} className="w-9 h-9 rounded-xl flex items-center justify-center text-sm hover:bg-white/[0.03] transition-all cursor-pointer" title="Task Board">📋</button>
            <button onClick={() => { setActiveTab('boardroom'); setSidebarCollapsed(false); }} className="w-9 h-9 rounded-xl flex items-center justify-center text-sm hover:bg-white/[0.03] transition-all cursor-pointer mt-4 border-t border-white/[0.04] pt-4" title="Boardroom">💬</button>
            <button onClick={() => { setActiveTab('settings'); setSidebarCollapsed(false); }} className="w-9 h-9 rounded-xl flex items-center justify-center text-sm hover:bg-white/[0.03] transition-all cursor-pointer" title="Settings">⚙️</button>
          </div>
        )}

        <div className="p-4 border-t border-white/[0.04] flex justify-center shrink-0">
          <UserButton />
        </div>
      </div>

      {/* ─── Main Workspace ─── */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {activeProject ? (
          <>
            {/* Top Workspace Header */}
            <div className="bg-[#08081a]/80 backdrop-blur-md border-b border-white/[0.04] px-6 py-3 flex items-center justify-between shrink-0 z-10">
              <div className="flex items-center gap-4">
                <h1 className="text-sm font-bold text-white capitalize">{activeTab.replace('_', ' ')}</h1>
              </div>

              {/* Header Toggles & Badges */}
              <div className="flex items-center gap-3">
                <button 
                  onClick={() => setShowActivityFeed(!showActivityFeed)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-2 border cursor-pointer ${
                    showActivityFeed 
                      ? 'bg-blue-600/20 text-blue-400 border-blue-500/30' 
                      : 'bg-white/[0.02] text-gray-400 border-white/[0.05] hover:bg-white/[0.05]'
                  }`}
                >
                  <div className={`w-1.5 h-1.5 rounded-full ${showActivityFeed ? 'bg-blue-400 animate-pulse' : 'bg-gray-500'}`} />
                  Live Activity
                </button>
              </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 flex overflow-hidden">
              
              <div className="flex-1 relative">
                {activeTab === 'ceo_dashboard' && (
                  <CeoDashboard project={activeProject} />
                )}
                {activeTab === 'departments' && (
                  <DepartmentsPanel project={activeProject} />
                )}
                {activeTab === 'deliverables' && (
                  <DeliverablesInbox project={activeProject} />
                )}
                {activeTab === 'overview' && (
                  <OverviewPanel 
                    project={activeProject} 
                    onNavigateToDiscovery={() => setActiveTab('discovery')} 
                  />
                )}
                {activeTab === 'discovery' && (
                  <DiscoveryChat 
                    project={activeProject} 
                    onComplete={() => setActiveTab('overview')}
                  />
                )}
                {activeTab === 'objectives' && (
                  <ObjectivesPanel project={activeProject} />
                )}
                {activeTab === 'tasks' && (
                  <TaskBoard project={activeProject} />
                )}
                {activeTab === 'plans' && (
                  <div className="h-full overflow-y-auto p-6 bg-[#050510] space-y-6">
                    <ManagerV2Input projectId={activeProject.id} onPlanCreated={() => {}} />
                    <PlanViewer projectId={activeProject.id} />
                  </div>
                )}
                {activeTab === 'approvals' && (
                  <div className="h-full overflow-y-auto p-6 bg-[#050510]">
                    <ApprovalWorkflow projectId={activeProject.id} />
                  </div>
                )}
                {activeTab === 'metrics' && (
                  <div className="h-full overflow-y-auto p-6 bg-[#050510]">
                    <MetricsDashboard projectId={activeProject.id} />
                  </div>
                )}
                {activeTab === 'boardroom' && (
                  <ChatArea
                    projectId={activeProject.id}
                    sessionId={activeSessionId}
                    onSessionCreated={handleSessionCreated}
                  />
                )}
                {activeTab === 'settings' && (
                  <div className="h-full overflow-y-auto p-6 bg-[#050510]">
                    <ProfileSettings project={activeProject} onUpdate={handleProjectUpdate} />
                  </div>
                )}

                {/* Manager Command Palette - Only visible on Overview and Tasks */}
                {(activeTab === 'overview' || activeTab === 'tasks') && (
                  <ManagerInput 
                    project={activeProject} 
                    onPlanCreated={() => {
                      if (activeTab !== 'tasks') setActiveTab('tasks');
                    }} 
                  />
                )}
              </div>

              {/* Slide-out Activity Feed */}
              {showActivityFeed && (
                <ActivityFeed project={activeProject} />
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-4 animate-fadeSlideIn">
              <div className="w-16 h-16 rounded-2xl glass flex items-center justify-center mx-auto text-3xl">🏢</div>
              <p className="text-gray-500 text-sm">Create your first startup to begin.</p>
              <button
                onClick={handleCreateNewClick}
                className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 rounded-xl text-sm font-semibold text-white transition-all shadow-lg shadow-blue-600/20 cursor-pointer"
              >
                Create Startup
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
    </WebSocketProvider>
  );
}
