// frontend/src/features/projects/ProfileSettings.tsx
"use client";

import React, { useState, useEffect } from 'react';
import {
  updateProject,
  Project,
  ProjectDocument,
  AgentConfig,
  fetchDocuments,
  uploadDocument,
  deleteDocument,
  fetchAgentConfigs,
  saveAgentConfig,
  resetAgentConfig,
  fetchIntegrations,
  connectIntegration,
  disconnectIntegration,
  syncIntegration,
  IntegrationStatus
} from '@/lib/api';

interface ProfileSettingsProps {
  project: Project;
  onUpdate: (updatedProject: Project) => void;
}

export const ProfileSettings: React.FC<ProfileSettingsProps> = ({ project, onUpdate }) => {
  // Profile settings state
  const [name, setName] = useState(project.name);
  const [valueProp, setValueProp] = useState(project.core_context?.value_proposition || '');
  const [targetAudience, setTargetAudience] = useState(project.core_context?.target_audience || '');
  const [techStack, setTechStack] = useState(project.core_context?.tech_stack || '');
  const [businessModel, setBusinessModel] = useState(project.core_context?.business_model || '');
  
  const [isSaving, setIsSaving] = useState(false);
  const [profileMessage, setProfileMessage] = useState<{ type: 'success' | 'error'; content: string } | null>(null);

  // Documents state
  const [documents, setDocuments] = useState<ProjectDocument[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [docMessage, setDocMessage] = useState<{ type: 'success' | 'error'; content: string } | null>(null);

  // Agent configs state
  const [agentConfigs, setAgentConfigs] = useState<AgentConfig[]>([]);
  const [isLoadingAgents, setIsLoadingAgents] = useState(false);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [savingAgents, setSavingAgents] = useState<Record<string, boolean>>({});
  const [agentMessage, setAgentMessage] = useState<{ type: 'success' | 'error'; content: string } | null>(null);

  // Integrations state
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [isLoadingInts, setIsLoadingInts] = useState(false);
  const [expandedInt, setExpandedInt] = useState<string | null>(null);
  const [savingInts, setSavingInts] = useState<Record<string, boolean>>({});
  const [syncingInts, setSyncingInts] = useState<Record<string, boolean>>({});
  const [intMessage, setIntMessage] = useState<{ type: 'success' | 'error'; content: string } | null>(null);
  const [intConfigs, setIntConfigs] = useState<Record<string, Record<string, string>>>({
    slack: { webhook_url: '' },
    github: { token: '', org: '' },
    vercel: { token: '', project_id: '' },
    google: { credentials_json: '' },
    hubspot: { api_key: '' },
    stripe: { secret_key: '' }
  });

  // Keep state sync when switching active project
  useEffect(() => {
    setName(project.name);
    setValueProp(project.core_context?.value_proposition || '');
    setTargetAudience(project.core_context?.target_audience || '');
    setTechStack(project.core_context?.tech_stack || '');
    setBusinessModel(project.core_context?.business_model || '');
    setProfileMessage(null);
    setDocMessage(null);
    setAgentMessage(null);
    setExpandedAgent(null);
    
    // Fetch documents for the active project
    const loadDocs = async () => {
      setIsLoadingDocs(true);
      try {
        const docs = await fetchDocuments(project.id);
        setDocuments(docs);
      } catch (err: any) {
        console.error('Failed to load documents', err);
      } finally {
        setIsLoadingDocs(false);
      }
    };

    // Fetch agent configurations
    const loadAgents = async () => {
      setIsLoadingAgents(true);
      try {
        const configs = await fetchAgentConfigs(project.id);
        setAgentConfigs(configs);
      } catch (err: any) {
        console.error('Failed to load agent configs', err);
      } finally {
        setIsLoadingAgents(false);
      }
    };

    // Fetch integrations
    const loadInts = async () => {
      setIsLoadingInts(true);
      try {
        const data = await fetchIntegrations(project.id);
        setIntegrations(data);
      } catch (err: any) {
        console.error('Failed to load integrations', err);
      } finally {
        setIsLoadingInts(false);
      }
    };

    loadDocs();
    loadAgents();
    loadInts();
    
    // Clear alerts
    setIntMessage(null);
    setExpandedInt(null);
  }, [project]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setProfileMessage({ type: 'error', content: 'Company name is required.' });
      return;
    }

    setIsSaving(true);
    setProfileMessage(null);

    try {
      const coreContext = {
        company_name: name,
        value_proposition: valueProp,
        target_audience: targetAudience,
        tech_stack: techStack,
        business_model: businessModel
      };

      const updated = await updateProject(project.id, name, coreContext);
      onUpdate(updated);
      setProfileMessage({ type: 'success', content: 'Startup profile updated successfully!' });
    } catch (err: any) {
      setProfileMessage({ type: 'error', content: err.message || 'Failed to update profile.' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    // Validate file type
    const validExtensions = ['.txt', '.md', '.pdf'];
    const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!validExtensions.includes(fileExt)) {
      setDocMessage({ type: 'error', content: 'Only .txt, .md, and .pdf files are supported.' });
      return;
    }

    setIsUploading(true);
    setDocMessage(null);
    try {
      const newDoc = await uploadDocument(project.id, file);
      setDocuments(prev => [newDoc, ...prev]);
      setDocMessage({ type: 'success', content: `"${file.name}" uploaded and parsed successfully!` });
    } catch (err: any) {
      setDocMessage({ type: 'error', content: err.message || 'Failed to upload document.' });
    } finally {
      setIsUploading(false);
    }
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleDeleteDoc = async (docId: string, filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) return;
    
    setDocMessage(null);
    try {
      await deleteDocument(project.id, docId);
      setDocuments(prev => prev.filter(d => d.id !== docId));
      setDocMessage({ type: 'success', content: `"${filename}" deleted successfully.` });
    } catch (err: any) {
      setDocMessage({ type: 'error', content: err.message || 'Failed to delete document.' });
    }
  };

  const handleAgentFieldChange = (role: string, field: keyof AgentConfig, value: any) => {
    setAgentConfigs(prev => prev.map(cfg => {
      if (cfg.agent_role === role) {
        return { ...cfg, [field]: value };
      }
      return cfg;
    }));
  };

  const handleSaveAgentConfig = async (role: string) => {
    const configToSave = agentConfigs.find(c => c.agent_role === role);
    if (!configToSave) return;

    setSavingAgents(prev => ({ ...prev, [role]: true }));
    setAgentMessage(null);
    try {
      const updated = await saveAgentConfig(project.id, role, {
        system_prompt: configToSave.system_prompt,
        model_override: configToSave.model_override,
        temperature: configToSave.temperature,
        is_enabled: configToSave.is_enabled
      });
      setAgentConfigs(prev => prev.map(cfg => cfg.agent_role === role ? updated : cfg));
      setAgentMessage({ type: 'success', content: `Configuration for ${getAgentLabel(role)} saved successfully!` });
    } catch (err: any) {
      setAgentMessage({ type: 'error', content: err.message || 'Failed to save agent configuration.' });
    } finally {
      setSavingAgents(prev => ({ ...prev, [role]: false }));
    }
  };

  const handleResetAgentConfig = async (role: string) => {
    if (!confirm(`Are you sure you want to reset ${getAgentLabel(role)} to code-level defaults?`)) return;

    setSavingAgents(prev => ({ ...prev, [role]: true }));
    setAgentMessage(null);
    try {
      await resetAgentConfig(project.id, role);
      const configs = await fetchAgentConfigs(project.id);
      setAgentConfigs(configs);
      setAgentMessage({ type: 'success', content: `Configuration for ${getAgentLabel(role)} reset to defaults.` });
    } catch (err: any) {
      setAgentMessage({ type: 'error', content: err.message || 'Failed to reset agent configuration.' });
    } finally {
      setSavingAgents(prev => ({ ...prev, [role]: false }));
    }
  };

  const getAgentLabel = (role: string) => {
    const labels: Record<string, string> = {
      visionary: 'Visionary CEO',
      operations: 'Operations CEO',
      marketing: 'Marketing CEO',
      finance: 'Finance CEO',
      risk: 'Risk Analyst'
    };
    return labels[role] || role;
  };

  const handleConnectIntegration = async (provider: string) => {
    setSavingInts(prev => ({ ...prev, [provider]: true }));
    setIntMessage(null);
    try {
      const config = intConfigs[provider] || {};
      const updated = await connectIntegration(project.id, provider, config);
      setIntegrations(prev => prev.map(i => i.provider === provider ? updated : i));
      setIntMessage({ type: 'success', content: `Successfully connected ${getProviderLabel(provider)}!` });
      setExpandedInt(null);
    } catch (err: any) {
      setIntMessage({ type: 'error', content: err.message || `Failed to connect ${provider}.` });
    } finally {
      setSavingInts(prev => ({ ...prev, [provider]: false }));
    }
  };

  const handleDisconnectIntegration = async (provider: string) => {
    if (!confirm(`Are you sure you want to disconnect ${getProviderLabel(provider)}?`)) return;

    setSavingInts(prev => ({ ...prev, [provider]: true }));
    setIntMessage(null);
    try {
      const updated = await disconnectIntegration(project.id, provider);
      setIntegrations(prev => prev.map(i => i.provider === provider ? updated : i));
      setIntMessage({ type: 'success', content: `Disconnected ${getProviderLabel(provider)}.` });
    } catch (err: any) {
      setIntMessage({ type: 'error', content: err.message || `Failed to disconnect ${provider}.` });
    } finally {
      setSavingInts(prev => ({ ...prev, [provider]: false }));
    }
  };

  const handleSyncIntegration = async (provider: string) => {
    setSyncingInts(prev => ({ ...prev, [provider]: true }));
    setIntMessage(null);
    try {
      const res = await syncIntegration(project.id, provider);
      setIntMessage({ type: 'success', content: res.message || `Sync completed for ${getProviderLabel(provider)}.` });
      // Refresh documents list to show newly synced documents!
      setIsLoadingDocs(true);
      const docs = await fetchDocuments(project.id);
      setDocuments(docs);
    } catch (err: any) {
      setIntMessage({ type: 'error', content: err.message || `Failed to sync ${provider}.` });
    } finally {
      setSyncingInts(prev => ({ ...prev, [provider]: false }));
      setIsLoadingDocs(false);
    }
  };

  const getProviderLabel = (provider: string) => {
    const labels: Record<string, string> = {
      slack: 'Slack Workspace',
      github: 'GitHub Org',
      vercel: 'Vercel Deployment',
      google: 'Google Workspace',
      hubspot: 'HubSpot CRM',
      stripe: 'Stripe Account'
    };
    return labels[provider] || provider;
  };

  const getProviderEmoji = (provider: string) => {
    const emojis: Record<string, string> = {
      slack: '💬',
      github: '🐙',
      vercel: '▲',
      google: '📂',
      hubspot: '🎯',
      stripe: '💳'
    };
    return emojis[provider] || '🔌';
  };

  return (
    <div className="space-y-8 my-6">
      {/* Profile Settings Section */}
      <div className="max-w-3xl mx-auto bg-gray-900 border border-gray-800 rounded-2xl p-8 shadow-xl text-gray-100">
        <div className="border-b border-gray-800 pb-6 mb-6">
          <h2 className="text-2xl font-bold text-white">Startup Profile</h2>
          <p className="text-sm text-gray-400 mt-1">
            Adjust the baseline facts about your company. The AI panel reviews this context on every query.
          </p>
        </div>

        {profileMessage && (
          <div
            className={`mb-6 p-4 rounded-lg text-sm border ${
              profileMessage.type === 'success'
                ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-400'
                : 'bg-red-950/30 border-red-500/30 text-red-400'
            }`}
          >
            {profileMessage.content}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-gray-300 mb-2">Company Name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-300 mb-2">
              Value Proposition (Product Description)
            </label>
            <textarea
              value={valueProp}
              onChange={e => setValueProp(e.target.value)}
              rows={4}
              className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
              placeholder="Describe your product value proposition in details..."
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-semibold text-gray-300 mb-2">Target Audience</label>
              <input
                type="text"
                value={targetAudience}
                onChange={e => setTargetAudience(e.target.value)}
                className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                placeholder="e.g. SMBs, enterprise tech executives"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-300 mb-2">Technology Stack</label>
              <input
                type="text"
                value={techStack}
                onChange={e => setTechStack(e.target.value)}
                className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                placeholder="e.g. Next.js, FastAPI, PostgreSQL"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-300 mb-2">Business & Monetization Model</label>
            <textarea
              value={businessModel}
              onChange={e => setBusinessModel(e.target.value)}
              rows={3}
              className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
              placeholder="Describe your pricing tiers, monetization strategy, and sales models..."
            />
          </div>

          <div className="pt-4 border-t border-gray-800 flex justify-end">
            <button
              type="submit"
              disabled={isSaving}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium rounded-lg transition-colors shadow-lg shadow-blue-600/20"
            >
              {isSaving ? 'Saving Changes...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>

      {/* Knowledge Base Section */}
      <div className="max-w-3xl mx-auto bg-gray-900 border border-gray-800 rounded-2xl p-8 shadow-xl text-gray-100">
        <div className="border-b border-gray-800 pb-6 mb-6">
          <h2 className="text-2xl font-bold text-white">Knowledge Base (RAG)</h2>
          <p className="text-sm text-gray-400 mt-1">
            Upload text, markdown, or PDF files. Documents are automatically chunked, embedded, and searched to inject real-time context into boardroom agent sessions.
          </p>
        </div>

        {docMessage && (
          <div
            className={`mb-6 p-4 rounded-lg text-sm border ${
              docMessage.type === 'success'
                ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-400'
                : 'bg-red-950/30 border-red-500/30 text-red-400'
            }`}
          >
            {docMessage.content}
          </div>
        )}

        {/* Drag & Drop Area */}
        <div
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          className="border-2 border-dashed border-gray-800 hover:border-blue-500/50 rounded-xl p-8 text-center bg-gray-950 transition-colors cursor-pointer relative group"
        >
          <input
            type="file"
            onChange={onFileChange}
            accept=".txt,.md,.pdf"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            disabled={isUploading}
          />
          <div className="flex flex-col items-center justify-center space-y-3">
            <div className="p-3 bg-gray-900 rounded-full border border-gray-800 group-hover:border-blue-500/30 group-hover:bg-blue-950/20 transition-colors">
              {isUploading ? (
                <svg className="animate-spin h-6 w-6 text-blue-500" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              ) : (
                <svg className="h-6 w-6 text-gray-400 group-hover:text-blue-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              )}
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-300">
                {isUploading ? 'Ingesting and embedding document...' : 'Click to upload or drag & drop'}
              </p>
              <p className="text-xs text-gray-500 mt-1">PDF, TXT, or MD up to 10MB</p>
            </div>
          </div>
        </div>

        {/* Documents Table */}
        <div className="mt-8">
          <h3 className="text-lg font-semibold text-white mb-4">Ingested Documents</h3>
          
          {isLoadingDocs ? (
            <div className="text-center py-6 text-gray-500 text-sm">Loading documents...</div>
          ) : documents.length === 0 ? (
            <div className="text-center py-8 border border-gray-800 rounded-xl bg-gray-950/50 text-gray-500 text-sm">
              No documents uploaded yet. Upload pitch decks, financials, or strategy notes to enhance the panel's knowledge base.
            </div>
          ) : (
            <div className="border border-gray-800 rounded-xl overflow-hidden bg-gray-950">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-gray-800 bg-gray-900/50 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    <th className="px-6 py-4">Filename</th>
                    <th className="px-6 py-4">Uploaded At</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800 text-sm text-gray-300">
                  {documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-gray-900/30 transition-colors">
                      <td className="px-6 py-4 font-medium text-white flex items-center space-x-2">
                        <svg className="h-4 w-4 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <span className="truncate max-w-[240px] md:max-w-md" title={doc.filename}>{doc.filename}</span>
                      </td>
                      <td className="px-6 py-4 text-gray-400">
                        {new Date(doc.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => handleDeleteDoc(doc.id, doc.filename)}
                          className="p-1.5 bg-gray-900 hover:bg-red-950/50 border border-gray-800 hover:border-red-500/30 text-gray-400 hover:text-red-400 rounded-lg transition-colors"
                          title="Delete document"
                        >
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Boardroom Agents Section */}
      <div className="max-w-3xl mx-auto bg-gray-900 border border-gray-800 rounded-2xl p-8 shadow-xl text-gray-100">
        <div className="border-b border-gray-800 pb-6 mb-6">
          <h2 className="text-2xl font-bold text-white">Boardroom Agent Config</h2>
          <p className="text-sm text-gray-400 mt-1">
            Customize system prompts, adjust creativity temperatures, swap models, or toggle agent participation.
          </p>
        </div>

        {agentMessage && (
          <div
            className={`mb-6 p-4 rounded-lg text-sm border ${
              agentMessage.type === 'success'
                ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-400'
                : 'bg-red-950/30 border-red-500/30 text-red-400'
            }`}
          >
            {agentMessage.content}
          </div>
        )}

        {isLoadingAgents ? (
          <div className="text-center py-6 text-gray-500 text-sm">Loading agent configurations...</div>
        ) : (
          <div className="space-y-4">
            {agentConfigs.map((cfg) => {
              const isExpanded = expandedAgent === cfg.agent_role;
              const isSaving = !!savingAgents[cfg.agent_role];
              return (
                <div
                  key={cfg.agent_role}
                  className={`border rounded-xl transition-colors ${
                    cfg.is_enabled
                      ? 'border-gray-800 bg-gray-950/30 hover:border-gray-700'
                      : 'border-gray-800 bg-gray-950/10 opacity-70'
                  }`}
                >
                  {/* Collapsible Header */}
                  <div className="flex items-center justify-between px-6 py-4 cursor-pointer select-none" onClick={() => setExpandedAgent(isExpanded ? null : cfg.agent_role)}>
                    <div className="flex items-center space-x-4">
                      {/* Status indicator */}
                      <span className={`h-2.5 w-2.5 rounded-full ${cfg.is_enabled ? 'bg-blue-500 shadow-md shadow-blue-500/50' : 'bg-gray-700'}`} />
                      <div>
                        <h4 className="font-semibold text-white">{getAgentLabel(cfg.agent_role)}</h4>
                        <p className="text-xs text-gray-500 mt-0.5 uppercase tracking-wider font-medium">
                          {cfg.model_override || 'Default Model'} • Temp: {cfg.temperature ?? 0.2}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4" onClick={(e) => e.stopPropagation()}>
                      {/* Activation Toggle */}
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={cfg.is_enabled}
                          onChange={(e) => {
                            handleAgentFieldChange(cfg.agent_role, 'is_enabled', e.target.checked);
                            // Auto save state toggle for immediate UI feedback
                            saveAgentConfig(project.id, cfg.agent_role, {
                              ...cfg,
                              is_enabled: e.target.checked
                            }).catch(err => console.error(err));
                          }}
                          className="sr-only peer"
                        />
                        <div className="w-9 h-5 bg-gray-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-gray-400 after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600 peer-checked:after:bg-white peer-checked:after:border-blue-600"></div>
                      </label>
                      <button
                        type="button"
                        className="p-1 bg-gray-900 border border-gray-800 hover:border-gray-700 rounded-lg text-gray-400 transition-colors"
                        onClick={() => setExpandedAgent(isExpanded ? null : cfg.agent_role)}
                      >
                        <svg className={`h-5 w-5 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>
                    </div>
                  </div>

                  {/* Settings Panel Content */}
                  {isExpanded && (
                    <div className="px-6 pb-6 pt-2 border-t border-gray-900 space-y-5">
                      <div>
                        <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                          System Instructions Prompt
                        </label>
                        <textarea
                          rows={6}
                          value={cfg.system_prompt || ''}
                          onChange={(e) => handleAgentFieldChange(cfg.agent_role, 'system_prompt', e.target.value)}
                          className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none font-mono"
                          placeholder="Enter system prompt instructions overrides..."
                        />
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                            LLM Model Override
                          </label>
                          <select
                            value={cfg.model_override || ''}
                            onChange={(e) => handleAgentFieldChange(cfg.agent_role, 'model_override', e.target.value || null)}
                            className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                          >
                            <option value="">Use Global Default Model</option>
                            <option value="meta/llama-3.1-70b-instruct">Llama 3.1 70B (Tested / Recommended)</option>
                            <option value="meta/llama-3.1-8b-instruct">Llama 3.1 8B (Fast / Budget)</option>
                            <option value="nvidia/llama-3.1-nemotron-70b-instruct">Nemotron 70B (High Quality)</option>
                            <option value="mistralai/mixtral-8x22b-instruct-v0.1">Mixtral 8x22B (Mixture of Experts)</option>
                          </select>
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex justify-between">
                            <span>Creativity Temperature</span>
                            <span className="text-blue-400 font-mono font-medium">{cfg.temperature ?? 0.2}</span>
                          </label>
                          <div className="flex items-center space-x-4 h-[42px]">
                            <input
                              type="range"
                              min="0.0"
                              max="1.0"
                              step="0.05"
                              value={cfg.temperature ?? 0.2}
                              onChange={(e) => handleAgentFieldChange(cfg.agent_role, 'temperature', parseFloat(e.target.value))}
                              className="w-full h-1 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
                            />
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between pt-4 border-t border-gray-900">
                        <button
                          type="button"
                          onClick={() => handleResetAgentConfig(cfg.agent_role)}
                          className="px-4 py-2 bg-gray-900 border border-gray-800 hover:border-gray-700 text-gray-400 hover:text-white rounded-lg text-sm transition-colors"
                        >
                          Reset to Defaults
                        </button>
                        <button
                          type="button"
                          disabled={isSaving}
                          onClick={() => handleSaveAgentConfig(cfg.agent_role)}
                          className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium rounded-lg text-sm transition-colors shadow-lg shadow-blue-600/20"
                        >
                          {isSaving ? 'Saving...' : 'Save Configuration'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* External Integrations Section */}
      <div className="max-w-3xl mx-auto bg-gray-900 border border-gray-800 rounded-2xl p-8 shadow-xl text-gray-100">
        <div className="border-b border-gray-800 pb-6 mb-6">
          <h2 className="text-2xl font-bold text-white">External Integrations</h2>
          <p className="text-sm text-gray-400 mt-1">
            Connect external startup tools to let specialized boardroom agents perform actions and synchronize files dynamically into the RAG base.
          </p>
        </div>

        {intMessage && (
          <div
            className={`mb-6 p-4 rounded-lg text-sm border ${
              intMessage.type === 'success'
                ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-400'
                : 'bg-red-950/30 border-red-500/30 text-red-400'
            }`}
          >
            {intMessage.content}
          </div>
        )}

        {isLoadingInts ? (
          <div className="text-center py-6 text-gray-500 text-sm">Loading integrations...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {integrations.map((int) => {
              const isConnected = int.status === 'connected';
              const isExpanded = expandedInt === int.provider;
              const isSaving = !!savingInts[int.provider];
              const isSyncing = !!syncingInts[int.provider];
              
              return (
                <div
                  key={int.provider}
                  className={`border rounded-xl p-5 flex flex-col justify-between transition-all duration-300 ${
                    isConnected
                      ? 'border-blue-500/30 bg-blue-950/5 shadow-[0_0_15px_rgba(59,130,246,0.05)]'
                      : 'border-gray-800 bg-gray-950/30 hover:border-gray-700'
                  }`}
                >
                  <div>
                    {/* Header */}
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl" role="img" aria-label={int.provider}>
                          {getProviderEmoji(int.provider)}
                        </span>
                        <div>
                          <h4 className="font-semibold text-white capitalize">{int.provider}</h4>
                          <span
                            className={`inline-block text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded mt-1 ${
                              isConnected
                                ? 'bg-blue-500/25 text-blue-400 border border-blue-500/20'
                                : 'bg-gray-800/40 text-gray-500 border border-gray-800/30'
                            }`}
                          >
                            {int.status}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <p className="text-xs text-gray-500 mt-3 leading-relaxed">
                      {int.provider === 'slack' && 'Post messages to channels and alert team members.'}
                      {int.provider === 'github' && 'Provision repositories and pull PR plans.'}
                      {int.provider === 'vercel' && 'Trigger automated deployments and build runs.'}
                      {int.provider === 'google' && 'Generate reports in Google Docs and workspace.'}
                      {int.provider === 'hubspot' && 'Sync pipeline deals and customer analytics.'}
                      {int.provider === 'stripe' && 'Track MRR and revenue performance logs.'}
                    </p>
                  </div>

                  {/* Inline credential config panel */}
                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-gray-800 space-y-3 animate-fadeIn">
                      {int.provider === 'slack' && (
                        <div>
                          <label className="block text-[10px] font-semibold text-gray-400 uppercase mb-1">Slack Webhook URL</label>
                          <input
                            type="text"
                            placeholder="https://hooks.slack.com/services/..."
                            value={intConfigs.slack.webhook_url}
                            onChange={(e) => setIntConfigs(prev => ({
                              ...prev,
                              slack: { ...prev.slack, webhook_url: e.target.value }
                            }))}
                            className="w-full bg-black/40 border border-gray-800 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500/50"
                          />
                        </div>
                      )}
                      {int.provider === 'github' && (
                        <div className="space-y-2">
                          <div>
                            <label className="block text-[10px] font-semibold text-gray-400 uppercase mb-1">GitHub Personal Token</label>
                            <input
                              type="password"
                              placeholder="ghp_..."
                              value={intConfigs.github.token}
                              onChange={(e) => setIntConfigs(prev => ({
                                ...prev,
                                github: { ...prev.github, token: e.target.value }
                              }))}
                              className="w-full bg-black/40 border border-gray-800 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500/50"
                            />
                          </div>
                          <div>
                            <label className="block text-[10px] font-semibold text-gray-400 uppercase mb-1">Target Organization/User</label>
                            <input
                              type="text"
                              placeholder="e.g. acme-corp"
                              value={intConfigs.github.org}
                              onChange={(e) => setIntConfigs(prev => ({
                                ...prev,
                                github: { ...prev.github, org: e.target.value }
                              }))}
                              className="w-full bg-black/40 border border-gray-800 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500/50"
                            />
                          </div>
                        </div>
                      )}
                      {(int.provider !== 'slack' && int.provider !== 'github') && (
                        <div>
                          <label className="block text-[10px] font-semibold text-gray-400 uppercase mb-1">Mock API Key / Client ID</label>
                          <input
                            type="password"
                            placeholder="mock_api_key_..."
                            value={intConfigs[int.provider]?.[Object.keys(intConfigs[int.provider])[0]] || ''}
                            onChange={(e) => {
                              const keyName = Object.keys(intConfigs[int.provider])[0];
                              setIntConfigs(prev => ({
                                ...prev,
                                [int.provider]: { ...prev[int.provider], [keyName]: e.target.value }
                              }));
                            }}
                            className="w-full bg-black/40 border border-gray-800 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500/50"
                          />
                        </div>
                      )}
                      <div className="flex justify-end gap-2 pt-2">
                        <button
                          type="button"
                          onClick={() => setExpandedInt(null)}
                          className="px-3 py-1 bg-gray-900 border border-gray-800 hover:border-gray-700 text-gray-400 rounded text-[10px] font-medium transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          disabled={isSaving}
                          onClick={() => handleConnectIntegration(int.provider)}
                          className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-[10px] font-semibold transition-colors"
                        >
                          {isSaving ? 'Connecting...' : 'Save Keys'}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Actions Bar */}
                  {!isExpanded && (
                    <div className="mt-5 pt-3 border-t border-white/[0.03] flex items-center gap-2">
                      {isConnected ? (
                        <>
                          <button
                            type="button"
                            disabled={isSaving}
                            onClick={() => handleDisconnectIntegration(int.provider)}
                            className="px-3 py-1.5 bg-gray-900/60 hover:bg-red-950/30 border border-gray-800 hover:border-red-500/20 text-gray-400 hover:text-red-400 rounded-lg text-xs font-semibold transition-colors cursor-pointer shrink-0"
                          >
                            Disconnect
                          </button>
                          {(int.provider === 'github' || int.provider === 'slack') && (
                            <button
                              type="button"
                              disabled={isSyncing}
                              onClick={() => handleSyncIntegration(int.provider)}
                              className="px-3 py-1.5 bg-blue-600/15 hover:bg-blue-600/25 border border-blue-500/20 text-blue-400 rounded-lg text-xs font-semibold transition-colors cursor-pointer flex-1 flex items-center justify-center gap-1.5"
                            >
                              {isSyncing ? (
                                <>
                                  <div className="w-3.5 h-3.5 border border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
                                  Syncing...
                                </>
                              ) : (
                                <>📥 Sync Data</>
                              )}
                            </button>
                          )}
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setExpandedInt(int.provider)}
                          className="w-full py-1.5 bg-white/[0.02] hover:bg-white/[0.05] border border-white/[0.02] hover:border-white/10 text-white rounded-lg text-xs font-semibold transition-all cursor-pointer"
                        >
                          Connect Integration
                        </button>
                      )}
                    </div>
                  )}

                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
