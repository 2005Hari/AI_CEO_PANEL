// AI Boardroom API client: types, buffered SSE streaming, workspace CRUD.
import { API_BASE_URL } from './api';
import { getAuthToken } from './auth-token';

export type WorkAnalysis = {
  objective: string;
  domain: string;
  task_types: string[];
  complexity: 'simple' | 'moderate' | 'complex' | 'very_complex';
  constraints: string[];
  desired_output: string;
  needs_live_research: boolean;
  sensitivity: string[];
  summary: string;
};

export type AgentSpec = {
  id: string;
  role: string;
  perspective: string;
  archetype: string;
  domain: string;
  expertise: string;
  objectives: string[];
  priorities: string[];
  behavior: string;
  research_lens: string;
  research_queries: string[];
  tools: string[];
  temporary: boolean;
};

export type Source = { id: string; title: string; url: string; snippet: string; agent_id?: string | null; query?: string | null };

export type BoardMessage = {
  id: string;
  agent_id: string;
  agent_name: string;
  kind: 'analysis' | 'challenge' | 'response' | 'feedback';
  round: number;
  content: string;
  target?: string;
  severity?: 'low' | 'medium' | 'high';
  key_points?: string[];
  confidence?: number;
  citations?: string[];
  position_changed?: boolean;
};

export type Quality = { passed: boolean; score: number | null; issues: string[]; revised?: boolean; note?: string };

export type BoardOutput = {
  version: number;
  artifact_type: string;
  title: string;
  content: string;
  disclaimer: string;
  sources_used: string[];
  quality: Quality;
  created_at: string;
};

export type Decision = { decision: string; rationale?: string };
export type ActionItem = { task: string; owner_role?: string; priority?: string };
export type ToolInfo = { label: string; implemented: boolean };

export type AgentStatus = 'idle' | 'thinking' | 'researching' | 'speaking' | 'challenging';

export type BoardroomEvent =
  | { type: 'boardroom_created' | 'boardroom_resumed'; boardroom_id: string; objective: string }
  | { type: 'stage'; stage: string; detail: string }
  | { type: 'analysis'; analysis: WorkAnalysis }
  | { type: 'board'; agents: AgentSpec[]; rationale: string; tools: Record<string, ToolInfo> }
  | { type: 'research_result'; agent_id: string; query: string; sources: Source[] }
  | { type: 'agent_status'; agent_id: string; status: AgentStatus }
  | { type: 'agent_message'; message: BoardMessage }
  | { type: 'agent_error'; agent_id: string; content: string }
  | { type: 'agent_join'; agent: AgentSpec; reason: string; chair_note?: string }
  | { type: 'agent_leave'; agent_id: string; reason: string }
  | { type: 'notice'; level: string; content: string }
  | { type: 'quality'; quality: Quality }
  | { type: 'output'; output: BoardOutput; decisions: Decision[]; tasks: ActionItem[]; sources: Source[] }
  | { type: 'error'; content: string }
  | { type: 'done' };

export type BoardroomSummary = {
  id: string;
  title: string;
  objective: string;
  status: string;
  artifact_type: string | null;
  team_size: number;
  created_at: string | null;
};

export type BoardroomDetail = {
  id: string;
  title: string;
  objective: string;
  status: string;
  error: string | null;
  analysis: WorkAnalysis | null;
  board: { agents?: AgentSpec[]; rationale?: string };
  sources: Source[];
  messages: BoardMessage[];
  decisions: Decision[];
  tasks: ActionItem[];
  outputs: BoardOutput[];
  history: { stage: string; detail: string; at: string }[];
};

async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = await getAuthToken();
  const headers = new Headers(options.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(url, { ...options, headers });
}

/** Split an SSE byte stream into JSON events, tolerating events split across chunks. */
export function createSseParser(onEvent: (e: BoardroomEvent) => void) {
  let buffer = '';
  return (chunk: string) => {
    buffer += chunk;
    const parts = buffer.split(/\r?\n\r?\n/);
    buffer = parts.pop() ?? '';
    for (const part of parts) {
      const data = part
        .split(/\r?\n/)
        .filter((l) => l.startsWith('data:'))
        .map((l) => l.slice(5).trimStart())
        .join('\n');
      if (!data) continue;
      try {
        onEvent(JSON.parse(data) as BoardroomEvent);
      } catch {
        console.error('Failed to parse SSE event', data);
      }
    }
  };
}

async function stream(url: string, body: unknown, onEvent: (e: BoardroomEvent) => void, signal?: AbortSignal) {
  try {
    const res = await authFetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    });
    if (!res.ok || !res.body) {
      const detail = await res.json().then((j) => j.detail).catch(() => null);
      throw new Error(detail || `Request failed (${res.status})`);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    const feed = createSseParser(onEvent);
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      feed(decoder.decode(value, { stream: true }));
    }
  } catch (err) {
    if ((err as Error).name === 'AbortError') return;
    onEvent({ type: 'error', content: err instanceof Error ? err.message : String(err) });
  }
}

export const runBoardroom = (objective: string, context: string, onEvent: (e: BoardroomEvent) => void, signal?: AbortSignal) =>
  stream(`${API_BASE_URL}/boardrooms/stream`, { objective, context: context || null }, onEvent, signal);

export const refineBoardroom = (id: string, feedback: string, onEvent: (e: BoardroomEvent) => void, signal?: AbortSignal) =>
  stream(`${API_BASE_URL}/boardrooms/${id}/refine`, { feedback }, onEvent, signal);

export async function listBoardrooms(): Promise<BoardroomSummary[]> {
  const res = await authFetch(`${API_BASE_URL}/boardrooms`);
  if (!res.ok) throw new Error('Failed to load boardrooms');
  return res.json();
}

export async function getBoardroom(id: string): Promise<BoardroomDetail> {
  const res = await authFetch(`${API_BASE_URL}/boardrooms/${id}`);
  if (!res.ok) throw new Error('Failed to load boardroom');
  return res.json();
}

export async function deleteBoardroom(id: string): Promise<void> {
  const res = await authFetch(`${API_BASE_URL}/boardrooms/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete boardroom');
}
