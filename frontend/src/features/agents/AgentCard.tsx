// frontend/src/features/agents/AgentCard.tsx
"use client";
import React from 'react';
import { AgentDraft } from '@/lib/api';

interface AgentCardProps {
  name: string;
  role: string;
  draft?: AgentDraft;
  isLoading: boolean;
  mode?: 'advisor' | 'pitch';
  isExpanded: boolean;
  onToggle: () => void;
}

const AGENT_COLORS: Record<string, { ring: string; bg: string; text: string; glow: string }> = {
  visionary: { ring: 'ring-blue-500/60', bg: 'bg-blue-500', text: 'text-blue-400', glow: 'shadow-blue-500/20' },
  operations: { ring: 'ring-amber-500/60', bg: 'bg-amber-500', text: 'text-amber-400', glow: 'shadow-amber-500/20' },
  marketing: { ring: 'ring-purple-500/60', bg: 'bg-purple-500', text: 'text-purple-400', glow: 'shadow-purple-500/20' },
  finance: { ring: 'ring-emerald-500/60', bg: 'bg-emerald-500', text: 'text-emerald-400', glow: 'shadow-emerald-500/20' },
};

const AGENT_ICONS: Record<string, string> = {
  visionary: '🔭',
  operations: '⚙️',
  marketing: '📢',
  finance: '📊',
};

export const AgentAvatar: React.FC<{
  name: string;
  role: string;
  hasDraft: boolean;
  isLoading: boolean;
  isExpanded: boolean;
  onClick: () => void;
  mode?: 'advisor' | 'pitch';
  confidence?: number;
}> = ({ name, role, hasDraft, isLoading, isExpanded, onClick, mode = 'advisor', confidence }) => {
  const colors = AGENT_COLORS[name] || AGENT_COLORS.visionary;
  const icon = AGENT_ICONS[name] || '💼';

  return (
    <button
      onClick={onClick}
      className={`group flex flex-col items-center gap-2 px-3 py-2 rounded-xl transition-all duration-300 cursor-pointer select-none
        ${isExpanded
          ? `glass-strong ${colors.glow} shadow-lg scale-[1.02]`
          : 'hover:bg-white/[0.03]'
        }
      `}
    >
      {/* Avatar Circle */}
      <div className="relative">
        <div
          className={`w-12 h-12 rounded-full flex items-center justify-center text-lg transition-all duration-300
            ${hasDraft
              ? `ring-2 ${colors.ring} shadow-md ${colors.glow}`
              : 'ring-1 ring-white/10'
            }
            ${isExpanded ? `ring-2 ${colors.ring}` : ''}
            bg-white/[0.04]
          `}
        >
          {isLoading && !hasDraft ? (
            <div className="w-5 h-5 border-2 border-white/20 border-t-white/70 rounded-full animate-spin" />
          ) : (
            <span>{icon}</span>
          )}
        </div>

        {/* Completion check */}
        {hasDraft && (
          <div className={`absolute -bottom-0.5 -right-0.5 w-4 h-4 ${colors.bg} rounded-full flex items-center justify-center animate-checkPop`}>
            <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" strokeWidth={3} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
        )}

        {/* Loading pulse ring */}
        {isLoading && !hasDraft && (
          <div className={`absolute inset-0 w-12 h-12 rounded-full border-2 ${colors.ring.replace('/60', '/30')} animate-ringPulse`} />
        )}
      </div>

      {/* Label */}
      <div className="text-center">
        <p className={`text-[11px] font-semibold transition-colors ${isExpanded ? colors.text : 'text-gray-400 group-hover:text-gray-200'}`}>
          {name.charAt(0).toUpperCase() + name.slice(1)}
        </p>
        {hasDraft && confidence !== undefined && (
          <p className="text-[10px] text-gray-500 font-mono">
            {mode === 'pitch' ? `${(confidence * 10).toFixed(0)}/10` : `${(confidence * 100).toFixed(0)}%`}
          </p>
        )}
      </div>
    </button>
  );
};

export const AgentDetailPanel: React.FC<AgentCardProps> = ({ name, role, draft, isLoading, mode = 'advisor', isExpanded, onToggle }) => {
  if (!isExpanded) return null;
  const colors = AGENT_COLORS[name] || AGENT_COLORS.visionary;

  return (
    <div className="animate-slideDown glass rounded-2xl p-5 overflow-hidden">
      {/* Panel Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-xl">{AGENT_ICONS[name] || '💼'}</span>
          <div>
            <h3 className={`text-sm font-bold ${colors.text}`}>{role}</h3>
            <p className="text-[11px] text-gray-500 capitalize">{name} Agent</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {draft && (
            <span className={`text-xs font-mono font-bold px-2.5 py-1 rounded-lg glass ${
              (draft.confidence || 0) > 0.8 ? 'text-emerald-400' : (draft.confidence || 0) > 0.6 ? 'text-amber-400' : 'text-red-400'
            }`}>
              {mode === 'pitch' ? `${((draft.confidence || 0.5) * 10).toFixed(1)}/10` : `${((draft.confidence || 0) * 100).toFixed(0)}%`}
            </span>
          )}
          <button
            onClick={onToggle}
            className="p-1.5 rounded-lg hover:bg-white/5 text-gray-500 hover:text-gray-300 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Content */}
      {isLoading && !draft && (
        <div className="flex items-center gap-3 py-6 justify-center">
          <div className="w-5 h-5 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
          <span className="text-sm text-gray-500">Analyzing...</span>
        </div>
      )}

      {draft && (
        <div className="space-y-4 text-sm">
          {/* Analysis */}
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 mb-1.5">
              {mode === 'pitch' ? 'VC Feedback' : 'Analysis'}
            </p>
            <p className="text-gray-300 leading-relaxed">{draft.analysis}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Risks */}
            {draft.risks && draft.risks.length > 0 && (
              <div className="glass rounded-xl p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-red-400 mb-2 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                  {mode === 'pitch' ? 'Investment Objections' : 'Key Risks'}
                </p>
                <ul className="space-y-1.5">
                  {draft.risks.map((risk, idx) => (
                    <li key={idx} className="text-gray-400 text-xs leading-relaxed flex items-start gap-2">
                      <span className="text-red-500/60 mt-0.5 shrink-0">•</span>
                      {risk}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Recommendations */}
            {draft.recommendations && draft.recommendations.length > 0 && (
              <div className="glass rounded-xl p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400 mb-2 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  {mode === 'pitch' ? 'Objection Mitigations' : 'Recommendations'}
                </p>
                <ul className="space-y-1.5">
                  {draft.recommendations.map((rec, idx) => (
                    <li key={idx} className="text-gray-400 text-xs leading-relaxed flex items-start gap-2">
                      <span className="text-emerald-500/60 mt-0.5 shrink-0">•</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Keep backward-compat default export
export const AgentCard = AgentDetailPanel;
