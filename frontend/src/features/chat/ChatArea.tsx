// frontend/src/features/chat/ChatArea.tsx
"use client";

import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { AgentAvatar, AgentDetailPanel } from '@/features/agents/AgentCard';
import { sendChatMessage, fetchMessages, StreamUpdate, AgentDraft } from '@/lib/api';

interface ChatAreaProps {
  projectId: string;
  sessionId: string | null;
  onSessionCreated: (id: string) => void;
}

const SUGGESTED_PROMPTS = {
  advisor: [
    "What's the best go-to-market strategy for a B2B SaaS startup?",
    "Evaluate our pricing model and suggest improvements.",
    "What are the biggest risks to our growth trajectory?",
  ],
  pitch: [
    "We're building an AI-powered recruiting platform for mid-market companies...",
    "Our startup automates compliance reporting for fintech companies...",
    "We have a dev-tools SaaS with 500 beta users and 12% week-over-week growth...",
  ],
};

export const ChatArea: React.FC<ChatAreaProps> = ({ projectId, sessionId, onSessionCreated }) => {
  const [input, setInput] = useState('');
  const [status, setStatus] = useState('');
  const [drafts, setDrafts] = useState<Record<string, AgentDraft>>({});
  const [criticCritique, setCriticCritique] = useState<AgentDraft | null>(null);
  const [consensus, setConsensus] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [mode, setMode] = useState<'advisor' | 'pitch'>('advisor');
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [showRiskDetails, setShowRiskDetails] = useState(false);

  // Restore session message logs on session selection
  useEffect(() => {
    if (sessionId) {
      const loadHistory = async () => {
        setIsRestoring(true);
        setStatus('Reconvening boardroom...');
        setDrafts({});
        setCriticCritique(null);
        setConsensus('');
        setInput('');
        setExpandedAgent(null);
        setShowRiskDetails(false);
        try {
          const messages = await fetchMessages(sessionId);
          const userMsgs = messages.filter(m => m.role === 'user');
          if (userMsgs.length > 0) {
            setStatus(`Last consulted: "${userMsgs[userMsgs.length - 1].content}"`);
          } else {
            setStatus('');
          }

          const assistantMsgs = messages.filter(m => m.role === 'assistant');
          if (assistantMsgs.length > 0) {
            const latest = assistantMsgs[assistantMsgs.length - 1];
            setConsensus(latest.content);

            if (latest.content && (
              latest.content.toLowerCase().includes("vc pitch") ||
              latest.content.toLowerCase().includes("investment thesis")
            )) {
              setMode('pitch');
            } else {
              setMode('advisor');
            }

            const allDrafts = latest.agent_drafts || {};
            const executives: Record<string, AgentDraft> = {};
            let riskCritique: AgentDraft | null = null;

            Object.entries(allDrafts).forEach(([key, val]) => {
              if (key === 'risk') {
                riskCritique = val as AgentDraft;
              } else {
                executives[key] = val as AgentDraft;
              }
            });

            setDrafts(executives);
            setCriticCritique(riskCritique);
          }
        } catch (e: any) {
          setStatus(`Failed to restore session: ${e.message}`);
        } finally {
          setIsRestoring(false);
        }
      };
      loadHistory();
    } else {
      setStatus('');
      setDrafts({});
      setCriticCritique(null);
      setConsensus('');
      setInput('');
      setIsProcessing(false);
      setIsRestoring(false);
      setExpandedAgent(null);
      setShowRiskDetails(false);
    }
  }, [sessionId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing || isRestoring) return;

    setIsProcessing(true);
    setStatus('Initializing AI Panel...');
    setDrafts({});
    setCriticCritique(null);
    setConsensus('');
    setExpandedAgent(null);
    setShowRiskDetails(false);

    await sendChatMessage(projectId, input, sessionId, (update: StreamUpdate) => {
      switch (update.type) {
        case 'session_created':
          onSessionCreated(update.session_id);
          break;
        case 'status':
          setStatus(update.content);
          break;
        case 'agent_draft':
          setDrafts(prev => ({
            ...prev,
            [update.agent]: update.content
          }));
          break;
        case 'critic':
          if (update.agent === 'risk') {
            setCriticCritique(update.content);
          }
          break;
        case 'consensus':
          setConsensus(update.content);
          break;
        case 'done':
          setStatus('');
          setIsProcessing(false);
          break;
        case 'error':
          setStatus(`Error: ${update.content}`);
          setIsProcessing(false);
          break;
      }
    }, mode);
  };

  const expectedAgents = ['visionary', 'operations', 'marketing', 'finance'];

  const getAgentRole = (agent: string) => {
    if (mode === 'pitch') {
      switch (agent) {
        case 'visionary': return 'Angel Investor';
        case 'operations': return 'SaaS/B2B VC';
        case 'marketing': return 'Deep Tech VC';
        case 'finance': return 'Growth VC';
        default: return agent;
      }
    } else {
      switch (agent) {
        case 'visionary': return 'Visionary CEO';
        case 'operations': return 'Operations CEO';
        case 'marketing': return 'Marketing CEO';
        case 'finance': return 'Finance CEO';
        default: return agent;
      }
    }
  };

  const hasAnyContent = Object.keys(drafts).length > 0 || consensus || criticCritique;

  return (
    <div className="flex flex-col h-full w-full p-4 sm:p-6 gap-4 overflow-hidden select-none">

      {isRestoring ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-4">
          <div className="w-10 h-10 border-2 border-blue-500/50 border-t-blue-400 rounded-full animate-spin" />
          <p className="text-gray-500 text-sm">Restoring boardroom state...</p>
        </div>
      ) : (
        <>
          {/* ─── Agent Avatar Row ─── */}
          {(hasAnyContent || isProcessing) && (
            <div className="animate-fadeIn flex items-center justify-center gap-1 sm:gap-2 py-2 shrink-0 select-none">
              {expectedAgents.map(agent => (
                <AgentAvatar
                  key={agent}
                  name={agent}
                  role={getAgentRole(agent)}
                  hasDraft={!!drafts[agent]}
                  isLoading={isProcessing && !drafts[agent]}
                  isExpanded={expandedAgent === agent}
                  onClick={() => setExpandedAgent(expandedAgent === agent ? null : agent)}
                  mode={mode}
                  confidence={drafts[agent]?.confidence}
                />
              ))}

              {/* Risk / Devil's Advocate avatar */}
              <div className="w-px h-8 bg-white/5 mx-1 hidden sm:block" />
              <button
                onClick={() => {
                  setExpandedAgent(null);
                  setShowRiskDetails(!showRiskDetails);
                }}
                className={`group flex flex-col items-center gap-2 px-3 py-2 rounded-xl transition-all duration-300 cursor-pointer select-none
                  ${showRiskDetails ? 'glass-strong shadow-lg shadow-red-500/10 scale-[1.02]' : 'hover:bg-white/[0.03]'}
                `}
              >
                <div className={`relative w-12 h-12 rounded-full flex items-center justify-center text-lg transition-all duration-300
                  ${criticCritique ? 'ring-2 ring-red-500/60 shadow-md shadow-red-500/20' : 'ring-1 ring-white/10'}
                  ${showRiskDetails ? 'ring-2 ring-red-500/60' : ''}
                  bg-white/[0.04]
                `}>
                  {isProcessing && !criticCritique ? (
                    <div className="w-5 h-5 border-2 border-white/20 border-t-white/70 rounded-full animate-spin" />
                  ) : (
                    <span>{mode === 'pitch' ? '🔥' : '🛡️'}</span>
                  )}
                  {criticCritique && (
                    <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center animate-checkPop">
                      <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" strokeWidth={3} viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                </div>
                <div className="text-center">
                  <p className={`text-[11px] font-semibold transition-colors ${showRiskDetails ? 'text-red-400' : 'text-gray-400 group-hover:text-gray-200'}`}>
                    {mode === 'pitch' ? "Devil's Adv." : 'Risk'}
                  </p>
                  {criticCritique && (
                    <p className="text-[10px] text-gray-500 font-mono">
                      {mode === 'pitch' ? `${((criticCritique.confidence || 0.5) * 10).toFixed(0)}/10` : `${((criticCritique.confidence || 0.5) * 100).toFixed(0)}%`}
                    </p>
                  )}
                </div>
              </button>
            </div>
          )}

          {/* ─── Status Line ─── */}
          {status && (
            <div className="flex items-center justify-center gap-2 text-xs text-gray-500 animate-fadeIn">
              {isProcessing && <div className="w-3 h-3 border-2 border-white/10 border-t-blue-400 rounded-full animate-spin" />}
              <span className="truncate max-w-md">{status}</span>
            </div>
          )}

          {/* ─── Scrollable Content Area ─── */}
          <div className="flex-1 overflow-y-auto flex flex-col gap-4 px-1 pb-2 select-text">

            {/* Expanded Agent Detail Panel */}
            {expandedAgent && (
              <AgentDetailPanel
                name={expandedAgent}
                role={getAgentRole(expandedAgent)}
                draft={drafts[expandedAgent]}
                isLoading={isProcessing && !drafts[expandedAgent]}
                mode={mode}
                isExpanded={true}
                onToggle={() => setExpandedAgent(null)}
              />
            )}

            {/* Risk / Devil's Advocate Expanded Panel */}
            {showRiskDetails && criticCritique && (
              <div className="animate-slideDown glass rounded-2xl p-5 overflow-hidden border border-red-900/20">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{mode === 'pitch' ? '🔥' : '🛡️'}</span>
                    <div>
                      <h3 className="text-sm font-bold text-red-400">
                        {mode === 'pitch' ? "Devil's Advocate VC" : 'Skeptical Risk Audit'}
                      </h3>
                      <p className="text-[11px] text-gray-500">Critical Review Agent</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-xs font-mono font-bold px-2.5 py-1 rounded-lg glass text-red-400`}>
                      {mode === 'pitch' ? `${((criticCritique.confidence || 0.5) * 10).toFixed(1)}/10` : `${((criticCritique.confidence || 0.5) * 100).toFixed(0)}%`}
                    </span>
                    <button
                      onClick={() => setShowRiskDetails(false)}
                      className="p-1.5 rounded-lg hover:bg-white/5 text-gray-500 hover:text-gray-300 transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>

                <div className="space-y-4 text-sm">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 mb-1.5">
                      {mode === 'pitch' ? 'VC Feedback' : 'Critical Critique'}
                    </p>
                    <p className="text-gray-300 leading-relaxed">{criticCritique.analysis}</p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {criticCritique.risks && criticCritique.risks.length > 0 && (
                      <div className="glass rounded-xl p-4">
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-red-400 mb-2 flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                          {mode === 'pitch' ? 'Investment Objections' : 'Flagged Fatal Flaws'}
                        </p>
                        <ul className="space-y-1.5">
                          {criticCritique.risks.map((risk, idx) => (
                            <li key={idx} className="text-gray-400 text-xs leading-relaxed flex items-start gap-2">
                              <span className="text-red-500/60 mt-0.5 shrink-0">•</span>
                              {risk}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {criticCritique.recommendations && criticCritique.recommendations.length > 0 && (
                      <div className="glass rounded-xl p-4">
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-amber-400 mb-2 flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                          {mode === 'pitch' ? 'Objection Mitigations' : 'Mitigation Strategies'}
                        </p>
                        <ul className="space-y-1.5">
                          {criticCritique.recommendations.map((rec, idx) => (
                            <li key={idx} className="text-gray-400 text-xs leading-relaxed flex items-start gap-2">
                              <span className="text-amber-500/60 mt-0.5 shrink-0">•</span>
                              {rec}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* ─── Consensus ─── */}
            {consensus && (
              <div className={`animate-fadeSlideIn glass rounded-2xl p-6 sm:p-8 transition-all duration-300 ${
                mode === 'pitch' ? 'border border-purple-900/30' : 'border border-emerald-900/30'
              }`}>
                <h2 className={`text-base font-bold mb-5 flex items-center gap-2.5 border-b pb-3 ${
                  mode === 'pitch' ? 'text-purple-400 border-purple-900/30' : 'text-emerald-400 border-emerald-900/30'
                }`}>
                  <span className={`w-2 h-2 rounded-full animate-pulse ${
                    mode === 'pitch' ? 'bg-purple-400' : 'bg-emerald-400'
                  }`} />
                  {mode === 'pitch' ? 'Investment Thesis Consensus' : 'Executive Consensus Briefing'}
                </h2>
                <div className="prose prose-invert max-w-none text-gray-300 text-sm leading-relaxed">
                  <ReactMarkdown
                    components={{
                      h1: ({node, ...props}) => <h1 className="text-xl font-bold text-white mt-5 mb-3 border-b border-white/5 pb-2" {...props} />,
                      h2: ({node, ...props}) => <h2 className="text-lg font-semibold text-white mt-4 mb-2" {...props} />,
                      h3: ({node, ...props}) => <h3 className="text-base font-medium text-white mt-3 mb-1.5" {...props} />,
                      p: ({node, ...props}) => <p className="mb-3 text-gray-300 leading-relaxed" {...props} />,
                      ul: ({node, ...props}) => <ul className="list-disc list-inside pl-3 mb-3 space-y-1 text-gray-300" {...props} />,
                      ol: ({node, ...props}) => <ol className="list-decimal list-inside pl-3 mb-3 space-y-1 text-gray-300" {...props} />,
                      li: ({node, ...props}) => <li className="mb-0.5" {...props} />,
                      strong: ({node, ...props}) => <strong className="font-bold text-white" {...props} />,
                      em: ({node, ...props}) => <em className="italic text-gray-400" {...props} />,
                      blockquote: ({node, ...props}) => (
                        <blockquote className={`border-l-3 pl-4 py-1 italic text-gray-300 my-3 rounded-r ${
                          mode === 'pitch' ? 'border-purple-500/50 bg-purple-950/10' : 'border-emerald-500/50 bg-emerald-950/10'
                        }`} {...props} />
                      ),
                      code: ({node, ...props}) => (
                        <code className={`px-1.5 py-0.5 rounded text-xs font-mono glass ${
                          mode === 'pitch' ? 'text-purple-400' : 'text-emerald-400'
                        }`} {...props} />
                      )
                    }}
                  >
                    {consensus}
                  </ReactMarkdown>
                </div>
              </div>
            )}

            {/* ─── Empty State — Welcome ─── */}
            {!hasAnyContent && !isProcessing && (
              <div className="flex-1 flex flex-col items-center justify-center gap-6 py-12 animate-fadeIn">
                <div className="text-center space-y-3">
                  <div className="w-16 h-16 rounded-2xl glass flex items-center justify-center mx-auto text-3xl mb-4">
                    {mode === 'pitch' ? '🚀' : '👔'}
                  </div>
                  <h2 className="text-xl font-bold text-white">
                    {mode === 'pitch' ? 'Pitch to the VC Panel' : 'Consult Your Executive Panel'}
                  </h2>
                  <p className="text-sm text-gray-500 max-w-md">
                    {mode === 'pitch'
                      ? 'Describe your startup to get evaluated by Angel, SaaS, Deep Tech, and Growth investors.'
                      : 'Ask a strategic question and get insights from your AI CTO, CMO, CFO, and Risk Analyst.'}
                  </p>
                </div>

                {/* Suggested Prompts */}
                <div className="flex flex-col gap-2 w-full max-w-lg">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-600 text-center">Try asking</p>
                  {SUGGESTED_PROMPTS[mode].map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => setInput(prompt)}
                      className="text-left text-sm text-gray-400 hover:text-gray-200 px-4 py-3 rounded-xl glass glass-hover transition-all duration-200 hover:translate-x-1 cursor-pointer"
                    >
                      <span className="text-gray-600 mr-2">→</span>
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* ─── Input Area ─── */}
          <div className="shrink-0 select-none animate-fadeIn">
            <form onSubmit={handleSubmit} className="relative">
              {/* Mode Selector - Compact Pills Inside Input Area */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex gap-1 p-0.5 rounded-lg glass">
                  <button
                    type="button"
                    onClick={() => setMode('advisor')}
                    disabled={isProcessing}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-semibold uppercase tracking-wider transition-all duration-300 cursor-pointer
                      ${mode === 'advisor'
                        ? 'bg-blue-600/20 text-blue-400 shadow-sm'
                        : 'text-gray-500 hover:text-gray-300'
                      } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    <span className="text-xs">👔</span> Advisor
                  </button>
                  <button
                    type="button"
                    onClick={() => setMode('pitch')}
                    disabled={isProcessing}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-semibold uppercase tracking-wider transition-all duration-300 cursor-pointer
                      ${mode === 'pitch'
                        ? 'bg-purple-600/20 text-purple-400 shadow-sm'
                        : 'text-gray-500 hover:text-gray-300'
                      } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    <span className="text-xs">🚀</span> VC Pitch
                  </button>
                </div>
              </div>

              {/* Input Field */}
              <div className="relative">
                <input
                  type="text"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  placeholder={mode === 'pitch'
                    ? "Pitch your startup to the VC panel..."
                    : "Ask your executive panel a strategy question..."}
                  className={`w-full glass-strong rounded-xl px-5 py-4 pr-28 text-sm text-gray-100 placeholder-gray-600 transition-all duration-300 ${
                    mode === 'pitch' ? 'focus-glow-purple' : 'focus-glow'
                  }`}
                  disabled={isProcessing || isRestoring}
                />
                <button
                  type="submit"
                  disabled={isProcessing || isRestoring || !input.trim()}
                  className={`absolute right-2 top-1/2 -translate-y-1/2 text-white px-5 py-2 rounded-lg font-semibold text-xs uppercase tracking-wider transition-all duration-300 disabled:opacity-40 cursor-pointer ${
                    mode === 'pitch'
                      ? 'bg-purple-600 hover:bg-purple-500 shadow-lg shadow-purple-600/20'
                      : 'bg-blue-600 hover:bg-blue-500 shadow-lg shadow-blue-600/20'
                  }`}
                >
                  {isProcessing ? (
                    <span className="flex items-center gap-1.5">
                      <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Wait
                    </span>
                  ) : mode === 'pitch' ? 'Pitch' : 'Consult'}
                </button>
              </div>
            </form>
          </div>
        </>
      )}
    </div>
  );
};
