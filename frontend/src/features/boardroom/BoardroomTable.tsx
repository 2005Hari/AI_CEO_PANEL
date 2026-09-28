"use client";

import React, { useEffect, useState } from 'react';
import type { AgentStatus, BoardMessage } from '@/lib/boardroom-api';
import type { SeatedAgent } from './boardroomState';

const BUBBLE_MS = 8000;
const PALETTE = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#a78bfa', '#14b8a6'];
const STATUS_LABEL: Record<string, string> = {
  thinking: 'Thinking', researching: 'Researching', speaking: 'Speaking', challenging: 'Challenging', listening: 'Listening',
};

type Seat = { x: number; y: number };

/** Chair sits at the head (top); members are spread around the rest of the oval. */
export function seatPositions(n: number): Seat[] {
  if (n === 0) return [];
  const start = -50; // degrees (y down): leaves a wide gap at the top for the chair
  const span = 280;
  return Array.from({ length: n }, (_, i) => {
    const deg = n === 1 ? 90 : start + (span * i) / (n - 1) + 0;
    const rad = (deg * Math.PI) / 180;
    return { x: 50 + 41 * Math.cos(rad), y: 50 + 36 * Math.sin(rad) };
  });
}

function Robot({ color, status, chair, error }: { color: string; status: AgentStatus | 'listening'; chair?: boolean; error?: boolean }) {
  const active = status !== 'idle' && status !== 'listening';
  return (
    <svg viewBox="0 0 64 64" className={`w-11 h-11 sm:w-16 sm:h-16 drop-shadow-lg transition-transform ${status === 'speaking' ? 'animate-float' : ''} ${status === 'listening' ? 'rotate-[4deg]' : ''}`} aria-hidden>
      <line x1="32" y1="4" x2="32" y2="12" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="32" cy="4" r="3" fill={active ? '#fff' : color} />
      <rect x="12" y="12" width="40" height="30" rx="9" fill={color} opacity={error ? 0.35 : 1} />
      <rect x="17" y="18" width="30" height="16" rx="6" fill="#0b1020" />
      <circle cx={status === 'listening' ? 27 : 26} cy="26" r="3.2" fill="#e5f0ff" />
      <circle cx={status === 'listening' ? 40 : 38} cy="26" r="3.2" fill="#e5f0ff" />
      {status === 'speaking' ? <rect x="26" y="31" width="12" height="3" rx="1.5" fill="#e5f0ff" /> : <rect x="27" y="32" width="10" height="1.6" rx="0.8" fill="#6b7a99" />}
      <rect x="18" y="44" width="28" height="15" rx="5" fill={color} opacity="0.75" />
      {chair && <path d="M24 44 L32 51 L40 44" fill="none" stroke="#fff" strokeWidth="2" strokeLinejoin="round" />}
    </svg>
  );
}

function Indicator({ status }: { status: AgentStatus | 'listening' }) {
  if (status === 'idle') return null;
  const label = STATUS_LABEL[status];
  if (status === 'thinking') {
    return <span className="flex gap-0.5 items-center" aria-label={label}>{[0, 1, 2].map((i) => <span key={i} className="w-1.5 h-1.5 rounded-full bg-blue-300 animate-pulse" style={{ animationDelay: `${i * 0.2}s` }} />)}</span>;
  }
  const icon = status === 'researching' ? '🔎' : status === 'challenging' ? '⚡' : status === 'listening' ? '👂' : '💬';
  return <span className={`text-xs ${status === 'researching' ? 'animate-pulse' : ''}`} aria-label={label}>{icon}</span>;
}

function firstSentence(text: string, max = 150): string {
  const clean = text.replace(/[#*_`>]/g, '').replace(/\s+/g, ' ').trim();
  const cut = clean.search(/[.!?]\s/);
  const s = cut > 30 ? clean.slice(0, cut + 1) : clean;
  return s.length > max ? s.slice(0, max - 1) + '…' : s;
}

type Props = {
  agents: SeatedAgent[];
  chairStatus: AgentStatus;
  messages: BoardMessage[];
  stageDetail: string;
  running: boolean;
  onSelect: (id: string) => void;
  selectedId: string | null;
};

export function BoardroomTable({ agents, chairStatus, messages, stageDetail, running, onSelect, selectedId }: Props) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  const seated = agents.filter((a) => !a.left);
  const seats = seatPositions(seated.length);
  const anySpeaking = seated.some((a) => a.status === 'speaking');
  const lastBy = (id: string) => [...messages].reverse().find((m) => m.agent_id === id);

  return (
    <div className="relative w-full mx-auto max-w-3xl aspect-[4/5] sm:aspect-[16/10]" role="group" aria-label="Boardroom table">
      {/* table */}
      <div className="absolute inset-[16%_14%_14%_14%] rounded-[50%] border border-white/10 bg-gradient-to-br from-[#14182f] to-[#0a0d1f] shadow-[inset_0_0_60px_rgba(59,130,246,0.08)] flex items-center justify-center">
        <div className="text-center px-6">
          <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500">{running ? 'In session' : 'Boardroom'}</div>
          <div className="text-xs text-gray-300 mt-1 max-w-[16rem] mx-auto min-h-[1rem]">{stageDetail}</div>
        </div>
      </div>

      {/* chairperson */}
      <div className="absolute left-1/2 top-[1%] -translate-x-1/2 flex flex-col items-center">
        <Robot color="#e2e8f0" status={chairStatus} chair />
        <div className="flex items-center gap-1 text-[10px] text-gray-300 font-medium"><span>Chairperson</span><Indicator status={chairStatus} /></div>
      </div>

      {/* members */}
      {seated.map((a, i) => {
        const pos = seats[i];
        const color = PALETTE[agents.findIndex((x) => x.id === a.id) % PALETTE.length];
        const status: AgentStatus | 'listening' = a.status === 'idle' && anySpeaking && running ? 'listening' : a.status;
        const msg = lastBy(a.id);
        const showBubble = a.lastSpokeAt !== null && now - a.lastSpokeAt < BUBBLE_MS && msg;
        const above = pos.y > 55;
        return (
          <button
            key={a.id}
            onClick={() => onSelect(a.id)}
            className={`absolute -translate-x-1/2 -translate-y-1/2 flex flex-col items-center group cursor-pointer animate-fadeSlideIn ${selectedId === a.id ? 'scale-105' : ''}`}
            style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
            aria-label={`${a.perspective}${a.temporary ? ' (specialist)' : ''}: ${STATUS_LABEL[status] ?? 'idle'}`}
          >
            {showBubble && (
              <div className={`hidden sm:block absolute z-20 w-44 sm:w-52 rounded-xl px-3 py-2 text-[11px] leading-snug text-left text-gray-100 shadow-xl border ${msg.kind === 'challenge' ? 'bg-rose-950/90 border-rose-500/40' : 'bg-[#141a33]/95 border-white/15'} ${above ? 'bottom-full mb-1' : 'top-full mt-1'} ${pos.x > 50 ? 'right-1/2 translate-x-[30%]' : 'left-1/2 -translate-x-[30%]'}`}>
                {msg.kind === 'challenge' && <span className="text-rose-300 font-semibold">Challenge · </span>}
                {firstSentence(msg.content)}
              </div>
            )}
            <div className={`relative rounded-full ${a.status !== 'idle' ? 'ring-2 ring-offset-2 ring-offset-[#050510]' : ''}`} style={{ ['--tw-ring-color' as string]: color }}>
              <Robot color={color} status={status} error={a.error} />
            </div>
            <div className="mt-0.5 flex items-center gap-1 max-w-[5.5rem] sm:max-w-[7.5rem]">
              <span className="text-[9px] sm:text-[11px] text-gray-200 font-medium truncate group-hover:text-white">{a.role}</span>
              <Indicator status={status} />
            </div>
            {a.temporary && <span className="text-[9px] text-amber-300/90 -mt-0.5">specialist</span>}
          </button>
        );
      })}
    </div>
  );
}
