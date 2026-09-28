"use client";

import React, { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import Link from 'next/link';
import { useAuth, UserButton } from '@clerk/nextjs';
import { registerAuthTokenGetter } from '@/lib/auth-token';
import {
  BoardroomEvent, BoardroomSummary, deleteBoardroom, getBoardroom, listBoardrooms, refineBoardroom, runBoardroom,
} from '@/lib/boardroom-api';
import { BoardroomTable } from './BoardroomTable';
import { boardroomReducer, initialState } from './boardroomState';
import { DeliverablePanel, DiscussionPanel, SourcesPanel, TeamPanel, WorkspacePanel } from './Panels';

const EXAMPLES = [
  'I need to plan a wedding for 500 guests with a ₹15 lakh budget.',
  'Review my resume and help me improve it for a software engineering job.',
  'I want to open a restaurant in Mumbai.',
  'Create a presentation about climate change for a school audience.',
  'Help me understand why my manufacturing business is losing money.',
  'I have five priorities and only two weeks. Help me decide what to do.',
];

type Tab = 'deliverable' | 'discussion' | 'team' | 'research' | 'workspace';
const TABS: { id: Tab; label: string }[] = [
  { id: 'deliverable', label: 'Deliverable' }, { id: 'discussion', label: 'Discussion' }, { id: 'team', label: 'Team' },
  { id: 'research', label: 'Research' }, { id: 'workspace', label: 'Workspace' },
];

export function BoardroomApp() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [state, dispatch] = useReducer(boardroomReducer, initialState);
  const [objective, setObjective] = useState('');
  const [context, setContext] = useState('');
  const [showContext, setShowContext] = useState(false);
  const [history, setHistory] = useState<BoardroomSummary[]>([]);
  const [tab, setTab] = useState<Tab>('discussion');
  const [selected, setSelected] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (isLoaded) registerAuthTokenGetter(() => getToken());
  }, [getToken, isLoaded]);

  const refreshHistory = useCallback(async () => {
    try { setHistory(await listBoardrooms()); } catch { /* list is best-effort */ }
  }, []);
  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    let cancelled = false;
    listBoardrooms().then((rows) => { if (!cancelled) setHistory(rows); }).catch(() => { /* list is best-effort */ });
    return () => { cancelled = true; };
  }, [isLoaded, isSignedIn]);
  useEffect(() => () => abortRef.current?.abort(), []);

  const onEvent = useCallback((event: BoardroomEvent) => {
    dispatch({ type: 'event', event, now: Date.now() });
    if (event.type === 'output') setTab('deliverable');
    if (event.type === 'done' || event.type === 'error') void refreshHistory();
  }, [refreshHistory]);

  const start = async (text: string) => {
    if (!text.trim() || state.running) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setTab('discussion');
    setSelected(null);
    dispatch({ type: 'start', objective: text.trim() });
    await runBoardroom(text.trim(), context, onEvent, ctrl.signal);
  };

  const refine = async (feedback: string) => {
    if (!state.id) return;
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    dispatch({ type: 'refine_start' });
    await refineBoardroom(state.id, feedback, onEvent, ctrl.signal);
    const detail = await getBoardroom(state.id).catch(() => null);
    if (detail) dispatch({ type: 'load', detail });
  };

  const open = async (id: string) => {
    abortRef.current?.abort();
    try {
      const detail = await getBoardroom(id);
      dispatch({ type: 'load', detail });
      setObjective('');
      setSelected(null);
      setTab(detail.outputs.length ? 'deliverable' : 'discussion');
    } catch { onEvent({ type: 'error', content: 'Could not open that boardroom.' }); }
  };

  const remove = async (id: string) => {
    if (!window.confirm('Delete this boardroom and everything in it?')) return;
    try {
      await deleteBoardroom(id);
      if (state.id === id) dispatch({ type: 'reset' });
      await refreshHistory();
    } catch { /* keep list as is */ }
  };

  const hasSession = !!state.objective || !!state.agents.length;
  const selectedAgent = state.agents.find((a) => a.id === selected);
  const agentMessages = selectedAgent ? state.messages.filter((m) => m.agent_id === selectedAgent.id || m.target === selectedAgent.id) : state.messages;

  return (
    <div className="min-h-screen bg-[#050510] text-gray-100 flex flex-col lg:flex-row">
      {/* History */}
      <aside className="lg:w-64 shrink-0 border-b lg:border-b-0 lg:border-r border-white/[0.06] p-4 flex flex-col gap-3 lg:h-screen lg:sticky lg:top-0">
        <div className="flex items-center justify-between">
          <Link href="/" className="font-bold text-white">AI Boardroom</Link>
          <UserButton />
        </div>
        <button onClick={() => { abortRef.current?.abort(); dispatch({ type: 'reset' }); setObjective(''); }}
          className="text-sm px-3 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium cursor-pointer">+ New boardroom</button>
        <div className="text-[10px] uppercase tracking-wider text-gray-500">Your workspaces</div>
        <ul className="flex-1 overflow-y-auto space-y-1 max-h-48 lg:max-h-none">
          {history.length === 0 && <li className="text-xs text-gray-600">Nothing yet.</li>}
          {history.map((h) => (
            <li key={h.id} className={`group flex items-center gap-1 rounded-lg ${state.id === h.id ? 'bg-white/[0.06]' : 'hover:bg-white/[0.03]'}`}>
              <button onClick={() => open(h.id)} className="flex-1 text-left px-2.5 py-2 min-w-0 cursor-pointer">
                <div className="text-xs text-gray-200 truncate">{h.title}</div>
                <div className="text-[10px] text-gray-500">{h.artifact_type ?? h.status} · {h.team_size} members</div>
              </button>
              <button onClick={() => remove(h.id)} aria-label={`Delete ${h.title}`} className="px-2 text-gray-600 hover:text-rose-400 opacity-0 group-hover:opacity-100 focus:opacity-100 cursor-pointer">✕</button>
            </li>
          ))}
        </ul>
      </aside>

      <main className="flex-1 min-w-0 p-4 sm:p-8 max-w-5xl w-full mx-auto">
        {!hasSession ? (
          <section className="max-w-2xl mx-auto pt-8 sm:pt-16 animate-slideUp">
            <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">Your AI team for any problem.</h1>
            <p className="mt-3 text-gray-400">Tell me what you’re trying to accomplish. I’ll assemble the right room: the experts, the research and the challenge you need.</p>
            <form onSubmit={(e) => { e.preventDefault(); void start(objective); }} className="mt-8 space-y-3">
              <textarea value={objective} onChange={(e) => setObjective(e.target.value)} rows={4} maxLength={4000} autoFocus
                onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); void start(objective); } }}
                placeholder="Describe the work: a problem, decision, project, question…"
                className="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-white placeholder-gray-500 focus-glow resize-none" />
              <button type="button" onClick={() => setShowContext((v) => !v)} className="text-xs text-gray-400 hover:text-gray-200 cursor-pointer">{showContext ? '− Hide' : '+ Add'} background / pasted material</button>
              {showContext && <textarea value={context} onChange={(e) => setContext(e.target.value)} rows={5} maxLength={20000} placeholder="Paste a resume, plan, notes, numbers, anything the team should know…"
                className="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-sm text-white placeholder-gray-500 focus-glow" />}
              <div className="flex items-center gap-3">
                <button type="submit" disabled={!objective.trim()} className="px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 disabled:opacity-40 font-semibold text-white cursor-pointer">Assemble the board</button>
                <span className="text-[11px] text-gray-500">Ctrl/⌘ + Enter</span>
              </div>
            </form>
            <div className="mt-8 flex flex-wrap gap-2">
              {EXAMPLES.map((ex) => (
                <button key={ex} onClick={() => setObjective(ex)} className="text-left text-xs px-3 py-2 rounded-xl glass glass-hover text-gray-300 cursor-pointer">{ex}</button>
              ))}
            </div>
          </section>
        ) : (
          <div className="space-y-6">
            <header>
              <div className="text-[10px] uppercase tracking-wider text-gray-500">{state.analysis ? `${state.analysis.domain} · ${state.analysis.task_types.join(', ')} · ${state.analysis.complexity.replace('_', ' ')}` : 'Understanding the work…'}</div>
              <h2 className="text-lg sm:text-xl font-semibold text-white mt-1">{state.analysis?.objective ?? state.objective}</h2>
              {!!state.analysis?.constraints.length && <div className="mt-2 flex flex-wrap gap-1.5">{state.analysis.constraints.map((c, i) => <span key={i} className="text-[11px] px-2 py-0.5 rounded-full bg-white/5 text-gray-300">{c}</span>)}</div>}
            </header>

            {state.agents.length > 0
              ? <BoardroomTable agents={state.agents} chairStatus={state.chairStatus} messages={state.messages} stageDetail={state.stageDetail} running={state.running} onSelect={(id) => { setSelected((s) => (s === id ? null : id)); setTab('discussion'); }} selectedId={selected} />
              : state.running && <div className="text-center text-sm text-gray-400 py-16 animate-pulse">{state.stageDetail || 'Working…'}</div>}

            {state.error && <div role="alert" className="rounded-xl border border-rose-500/40 bg-rose-500/10 text-rose-200 text-sm p-3">{state.error}</div>}
            {state.notices.length > 0 && <ul className="space-y-1">{state.notices.map((n, i) => <li key={i} className="text-xs text-amber-300/90">• {n}</li>)}</ul>}

            <div>
              <div role="tablist" className="flex gap-1 border-b border-white/[0.06] overflow-x-auto">
                {TABS.map((t) => (
                  <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}
                    className={`px-3 py-2 text-sm whitespace-nowrap cursor-pointer border-b-2 -mb-px ${tab === t.id ? 'border-blue-500 text-white' : 'border-transparent text-gray-500 hover:text-gray-300'}`}>
                    {t.label}{t.id === 'research' && state.sources.length ? ` (${state.sources.length})` : ''}
                  </button>
                ))}
              </div>
              <div className="pt-4" role="tabpanel">
                {tab === 'discussion' && (
                  <>
                    {selectedAgent && <div className="mb-3 text-xs text-gray-400">Showing {selectedAgent.perspective}. <button className="text-blue-300 cursor-pointer" onClick={() => setSelected(null)}>Show all</button></div>}
                    <DiscussionPanel messages={agentMessages} agents={state.agents} />
                  </>
                )}
                {tab === 'deliverable' && <DeliverablePanel outputs={state.outputs} sources={state.sources} canRefine={!!state.id && !state.running} refining={state.running && state.stage === 'refine'} onRefine={refine} />}
                {tab === 'team' && <TeamPanel agents={state.agents} rationale={state.rationale} tools={state.tools} />}
                {tab === 'research' && <SourcesPanel sources={state.sources} live={state.running} />}
                {tab === 'workspace' && <WorkspacePanel decisions={state.decisions} tasks={state.tasks} history={state.history} />}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
