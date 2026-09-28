// Pure reducer: folds the boardroom event stream (or a saved workspace) into UI state.
import type {
  ActionItem, AgentSpec, AgentStatus, BoardMessage, BoardOutput, BoardroomDetail, BoardroomEvent,
  Decision, Source, ToolInfo, WorkAnalysis,
} from '@/lib/boardroom-api';

export type SeatedAgent = AgentSpec & { status: AgentStatus; left: boolean; lastSpokeAt: number | null; error?: boolean };

export type BoardroomState = {
  id: string | null;
  objective: string;
  running: boolean;
  stage: string;
  stageDetail: string;
  analysis: WorkAnalysis | null;
  rationale: string;
  tools: Record<string, ToolInfo>;
  agents: SeatedAgent[];
  messages: BoardMessage[];
  sources: Source[];
  outputs: BoardOutput[];
  decisions: Decision[];
  tasks: ActionItem[];
  notices: string[];
  history: { stage: string; detail: string }[];
  chairStatus: AgentStatus;
  error: string | null;
};

export const initialState: BoardroomState = {
  id: null, objective: '', running: false, stage: '', stageDetail: '', analysis: null, rationale: '',
  tools: {}, agents: [], messages: [], sources: [], outputs: [], decisions: [], tasks: [], notices: [], history: [],
  chairStatus: 'idle', error: null,
};

export type Action =
  | { type: 'start'; objective: string }
  | { type: 'refine_start' }
  | { type: 'load'; detail: BoardroomDetail }
  | { type: 'reset' }
  | { type: 'event'; event: BoardroomEvent; now: number };

const seat = (a: AgentSpec): SeatedAgent => ({ ...a, status: 'idle', left: false, lastSpokeAt: null });

function setStatus(agents: SeatedAgent[], id: string, status: AgentStatus): SeatedAgent[] {
  return agents.map((a) => (a.id === id ? { ...a, status } : a));
}

export function boardroomReducer(state: BoardroomState, action: Action): BoardroomState {
  switch (action.type) {
    case 'reset':
      return initialState;
    case 'start':
      return { ...initialState, objective: action.objective, running: true, stage: 'understand', stageDetail: 'Understanding the work' };
    case 'refine_start':
      return { ...state, running: true, error: null, stage: 'refine', stageDetail: 'Refining with your feedback' };
    case 'load': {
      const d = action.detail;
      return {
        ...initialState,
        id: d.id, objective: d.objective, analysis: d.analysis, rationale: d.board?.rationale ?? '',
        agents: (d.board?.agents ?? []).map((a) => ({ ...seat(a), left: a.temporary })),
        messages: d.messages, history: d.history, sources: d.sources, outputs: d.outputs, decisions: d.decisions, tasks: d.tasks,
        error: d.status === 'failed' || d.status === 'interrupted' ? d.error ?? 'This run did not finish.' : null,
        stage: d.status === 'complete' ? 'complete' : '',
      };
    }
    case 'event':
      return applyEvent(state, action.event, action.now);
  }
}

function applyEvent(s: BoardroomState, e: BoardroomEvent, now: number): BoardroomState {
  switch (e.type) {
    case 'boardroom_created':
    case 'boardroom_resumed':
      return { ...s, id: e.boardroom_id };
    case 'stage':
      return { ...s, stage: e.stage, stageDetail: e.detail, history: [...s.history, { stage: e.stage, detail: e.detail }] };
    case 'analysis':
      return { ...s, analysis: e.analysis };
    case 'board':
      return { ...s, agents: e.agents.map(seat), rationale: e.rationale, tools: e.tools };
    case 'agent_status':
      return e.agent_id === 'chair'
        ? { ...s, chairStatus: e.status }
        : { ...s, agents: setStatus(s.agents, e.agent_id, e.status) };
    case 'research_result':
      return { ...s, sources: [...s.sources, ...e.sources] };
    case 'agent_message':
      return {
        ...s,
        messages: [...s.messages, e.message],
        agents: s.agents.map((a) => (a.id === e.message.agent_id ? { ...a, lastSpokeAt: now } : a)),
      };
    case 'agent_error':
      return { ...s, agents: s.agents.map((a) => (a.id === e.agent_id ? { ...a, error: true } : a)), notices: [...s.notices, e.content] };
    case 'agent_join':
      return { ...s, agents: [...s.agents.filter((a) => a.id !== e.agent.id), seat(e.agent)], notices: [...s.notices, `${e.agent.perspective} joined: ${e.reason}`] };
    case 'agent_leave':
      return { ...s, agents: s.agents.map((a) => (a.id === e.agent_id ? { ...a, left: true, status: 'idle' } : a)) };
    case 'notice':
      return { ...s, notices: [...s.notices, e.content] };
    case 'output':
      return { ...s, outputs: [...s.outputs, e.output], decisions: e.decisions, tasks: e.tasks, sources: e.sources };
    case 'error':
      return { ...s, running: false, error: e.content, chairStatus: 'idle' };
    case 'done':
      return { ...s, running: false, stage: 'complete', stageDetail: '', chairStatus: 'idle' };
    default:
      return s;
  }
}
