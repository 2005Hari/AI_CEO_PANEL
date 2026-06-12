// frontend/src/lib/api.ts
import { getAuthToken } from './auth-token';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = await getAuthToken();
  const headers = new Headers(options.headers);
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  return fetch(url, { ...options, headers });
}

export type AgentDraft = {
  analysis: string;
  risks: string[];
  recommendations: string[];
  confidence: number;
};

export type Project = {
  id: string;
  name: string;
  core_context: {
    company_name?: string;
    value_proposition?: string;
    target_audience?: string;
    tech_stack?: string;
    business_model?: string;
    [key: string]: any;
  };
  created_at: string;
  operating_mode?: string;
  discovery_completed?: boolean;
  health_score?: number;
};

export type Session = {
  id: string;
  project_id: string;
  created_at: string;
};

export type Message = {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  agent_drafts: Record<string, AgentDraft>;
  created_at: string;
};

export type StreamUpdate = 
  | { type: 'status'; content: string }
  | { type: 'session_created'; session_id: string }
  | { type: 'agent_draft'; agent: string; content: AgentDraft }
  | { type: 'critic'; agent: string; content: any }
  | { type: 'consensus'; content: string }
  | { type: 'error'; content: string }
  | { type: 'done' };

export async function fetchProjects(): Promise<Project[]> {
  const response = await authFetch(`${API_BASE_URL}/projects/`);
  if (!response.ok) {
    throw new Error('Failed to fetch projects');
  }
  return response.json();
}

export async function createProject(name: string, coreContext: Record<string, any> = {}): Promise<Project> {
  const response = await authFetch(`${API_BASE_URL}/projects/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name, core_context: coreContext }),
  });
  if (!response.ok) {
    throw new Error('Failed to create project');
  }
  return response.json();
}

export async function updateProject(
  projectId: string,
  name: string | null,
  coreContext: Record<string, any>
): Promise<Project> {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name, core_context: coreContext }),
  });
  if (!response.ok) {
    throw new Error('Failed to update project');
  }
  return response.json();
}

export async function fetchSessions(projectId: string): Promise<Session[]> {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/sessions`);
  if (!response.ok) {
    throw new Error('Failed to fetch sessions');
  }
  return response.json();
}

export async function fetchMessages(sessionId: string): Promise<Message[]> {
  const response = await authFetch(`${API_BASE_URL}/sessions/${sessionId}/messages`);
  if (!response.ok) {
    throw new Error('Failed to fetch messages');
  }
  return response.json();
}

export async function createSession(projectId: string): Promise<Session> {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    throw new Error('Failed to create session');
  }
  return response.json();
}

export async function sendChatMessage(
  projectId: string, 
  message: string, 
  sessionId: string | null,
  onUpdate: (update: StreamUpdate) => void,
  mode: 'advisor' | 'pitch' = 'advisor'
) {
  try {
    const response = await authFetch(`${API_BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        project_id: projectId,
        message: message,
        session_id: sessionId,
        mode: mode
      }),
    });

    if (!response.body) {
      throw new Error('ReadableStream not yet supported in this browser.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let done = false;

    while (!done) {
      const { value, done: readerDone } = await reader.read();
      done = readerDone;
      if (value) {
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6)) as StreamUpdate;
              onUpdate(data);
              if (data.type === 'done' || data.type === 'error') {
                done = true;
              }
            } catch (e) {
              console.error('Failed to parse SSE line', line);
            }
          }
        }
      }
    }
  } catch (err) {
    onUpdate({ type: 'error', content: String(err) });
  }
}

export type ProjectDocument = {
  id: string;
  project_id: string;
  filename: string;
  created_at: string;
};

export async function fetchDocuments(projectId: string): Promise<ProjectDocument[]> {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/documents`);
  if (!response.ok) {
    throw new Error('Failed to fetch documents');
  }
  return response.json();
}

export async function uploadDocument(projectId: string, file: File): Promise<ProjectDocument> {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/documents/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to upload document');
  }
  return response.json();
}

export async function deleteDocument(projectId: string, docId: string): Promise<void> {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/documents/${docId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete document');
  }
}

export type AgentConfig = {
  agent_role: string;
  system_prompt: string | null;
  model_override: string | null;
  temperature: number | null;
  is_enabled: boolean;
};

export async function fetchAgentConfigs(projectId: string): Promise<AgentConfig[]> {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/agents/config`);
  if (!response.ok) {
    throw new Error('Failed to fetch agent configurations');
  }
  return response.json();
}

export async function saveAgentConfig(
  projectId: string,
  role: string,
  config: Partial<AgentConfig>
): Promise<AgentConfig> {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/agents/config/${role}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(config),
  });
  if (!response.ok) {
    throw new Error('Failed to save agent configuration');
  }
  return response.json();
}

export async function resetAgentConfig(projectId: string, role: string): Promise<void> {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/agents/config/${role}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to reset agent configuration');
  }
}

// ──────────────────────────────────────────────
// NEW ROUTES: Blueprint, Discovery, Tasks, etc.
// ──────────────────────────────────────────────

export async function getBlueprint(projectId: string) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/blueprint`);
  if (!response.ok) throw new Error('Failed to fetch blueprint');
  return response.json();
}

export async function updateBlueprint(projectId: string, data: Record<string, any>) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/blueprint`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to update blueprint');
  return response.json();
}

export async function startDiscovery(projectId: string) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/discovery/start`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to start discovery');
  return response.json();
}

export async function respondDiscovery(projectId: string, responseText: string, history: any[] = []) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/discovery/respond`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ response: responseText, conversation_history: history }),
  });
  if (!response.ok) throw new Error('Failed to submit discovery response');
  return response.json();
}

export async function getDiscoveryStatus(projectId: string) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/discovery/status`);
  if (!response.ok) throw new Error('Failed to fetch discovery status');
  return response.json();
}

export async function finalizeDiscovery(projectId: string) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/discovery/finalize`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to finalize discovery');
  return response.json();
}

export async function getTasks(projectId: string, status?: string, agent?: string) {
  let url = `${API_BASE_URL}/projects/${projectId}/tasks?`;
  if (status) url += `status_filter=${status}&`;
  if (agent) url += `agent_filter=${agent}&`;
  const response = await authFetch(url);
  if (!response.ok) throw new Error('Failed to fetch tasks');
  return response.json();
}

export async function createTask(projectId: string, data: Record<string, any>) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create task');
  return response.json();
}

export async function executeTask(taskId: string) {
  const response = await authFetch(`${API_BASE_URL}/tasks/${taskId}/execute`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to execute task');
  return response.json();
}

export async function getObjectives(projectId: string) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/objectives`);
  if (!response.ok) throw new Error('Failed to fetch objectives');
  return response.json();
}

export async function createObjective(projectId: string, data: Record<string, any>) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/objectives`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create objective');
  return response.json();
}

export async function submitManagerPlan(projectId: string, request: string) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/manager/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request }),
  });
  if (!response.ok) throw new Error('Failed to generate manager plan');
  return response.json();
}

export async function getActivityFeed(projectId: string, limit = 50) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/activity?limit=${limit}`);
  if (!response.ok) throw new Error('Failed to fetch activity feed');
  return response.json();
}

export async function getAgents(mode?: string) {
  let url = `${API_BASE_URL}/agents`;
  if (mode) url += `?mode=${mode}`;
  const response = await authFetch(url);
  if (!response.ok) throw new Error('Failed to fetch agents');
  return response.json();
}

export type IntegrationStatus = {
  id?: string;
  project_id: string;
  provider: string;
  status: 'connected' | 'disconnected' | 'error';
  config: Record<string, any>;
  connected_at?: string;
  created_at?: string;
};

export async function fetchIntegrations(projectId: string): Promise<IntegrationStatus[]> {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/integrations`);
  if (!response.ok) {
    throw new Error('Failed to fetch integrations');
  }
  return response.json();
}

export async function connectIntegration(
  projectId: string,
  provider: string,
  config: Record<string, any>
): Promise<IntegrationStatus> {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/integrations/${provider}/connect`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ config }),
  });
  if (!response.ok) {
    throw new Error(`Failed to connect ${provider} integration`);
  }
  return response.json();
}

export async function disconnectIntegration(
  projectId: string,
  provider: string
): Promise<IntegrationStatus> {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/integrations/${provider}/disconnect`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to disconnect ${provider} integration`);
  }
  return response.json();
}

export async function syncIntegration(
  projectId: string,
  provider: string
): Promise<{ status: string; message: string; synced_files: string[]; synced_at: string }> {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/integrations/${provider}/sync`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`Failed to sync ${provider} integration`);
  }
  return response.json();
}

// ──────────────────────────────────────────────
// MVP PHASE: Manager v2, Plans, Approvals, Metrics
// ──────────────────────────────────────────────

export type Plan = {
  id: string;
  project_id: string;
  title: string;
  description?: string;
  status: 'draft' | 'active' | 'paused' | 'completed';
  owner_agent?: string;
  milestones: any[];
  confidence_score?: number;
  created_at: string;
  updated_at: string;
};

export async function submitManagerPlanV2(projectId: string, request: string) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/manager/plan_v2`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request }),
  });
  if (!response.ok) throw new Error('Failed to generate Manager v2 plan');
  return response.json();
}

export async function getPlans(projectId: string) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/plans`);
  if (!response.ok) throw new Error('Failed to fetch plans');
  return response.json();
}

export async function getPlan(projectId: string, planId: string) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/plans/${planId}`);
  if (!response.ok) throw new Error('Failed to fetch plan');
  return response.json();
}

export async function requestApproval(projectId: string, resourceType: string, resourceId: string, reason?: string) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/approvals/request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resource_type: resourceType, resource_id: resourceId, reason }),
  });
  if (!response.ok) throw new Error('Failed to request approval');
  return response.json();
}

export async function decideApproval(projectId: string, approvalId: string, approve: boolean, reason?: string) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/approvals/${approvalId}/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approve, reason }),
  });
  if (!response.ok) throw new Error('Failed to decide approval');
  return response.json();
}

export async function getPendingApprovals(projectId: string) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/approvals/pending`);
  if (!response.ok) throw new Error('Failed to fetch approvals');
  return response.json();
}

export async function getMetrics(projectId: string) {
  const response = await authFetch(`${API_BASE_URL}/projects/${projectId}/metrics`);
  if (!response.ok) throw new Error('Failed to fetch metrics');
  return response.json();
}

