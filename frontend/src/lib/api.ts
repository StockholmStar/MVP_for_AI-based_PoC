const CONFIGURED_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "";

function isLoopbackHost(hostname: string) {
  return ["localhost", "127.0.0.1", "0.0.0.0", "::1"].includes(hostname);
}

function apiBaseUrl() {
  if (!CONFIGURED_API_BASE_URL || typeof window === "undefined") {
    return CONFIGURED_API_BASE_URL;
  }

  const pageUrl = window.location;
  const pageIsLoopback = isLoopbackHost(pageUrl.hostname);

  try {
    const configuredUrl = new URL(CONFIGURED_API_BASE_URL);
    const apiIsLoopback = isLoopbackHost(configuredUrl.hostname);
    const wouldUseMixedContent = pageUrl.protocol === "https:" && configuredUrl.protocol === "http:";

    if ((apiIsLoopback && !pageIsLoopback) || wouldUseMixedContent) {
      return "";
    }
  } catch {
    return "";
  }

  return CONFIGURED_API_BASE_URL;
}

export type Project = {
  id: string;
  name: string;
  description: string;
  product_idea: string;
  current_version: string;
  created_at: string;
  updated_at: string;
};

export type Artefact = {
  id: string;
  project_id: string;
  kind: string;
  version: string;
  path: string;
  content_type: string;
  created_at: string;
  content?: string;
};

export type ProjectDetail = {
  project: Project;
  artefacts: Artefact[];
  runs: Array<{ id: string; version: string; status: string; message: string; created_at: string }>;
  latest: Record<string, Artefact>;
  canonical?: CanonicalState | null;
  gate_results?: GateResultRecord[];
  agent_runs?: AgentRunRecord[];
  runtime_mode?: RuntimeMode;
};

export type RuntimeMode = {
  llm_enabled: boolean;
  mode: string;
  model: string | null;
  workflow: string;
};

export type CanonicalState = {
  version: string;
  metadata: Record<string, unknown>;
  source_brief: string;
  functional_requirements: Array<Record<string, unknown>>;
  ux_states: Array<Record<string, unknown>>;
  prototype_screens: Array<Record<string, unknown>>;
  qa_criteria: Array<Record<string, unknown>>;
  gate_results: GateResult[];
  agent_run_history: Array<Record<string, unknown>>;
};

export type GateResult = {
  gate_id: string;
  status: "pass" | "fail" | "needs_human" | "skipped";
  score: number;
  severity: string;
  failed_checks: string[];
  feedback: string;
  revision_target?: string | null;
  attempt_count: number;
  timestamp: string;
};

export type GateResultRecord = {
  id: string;
  project_id: string;
  version: string;
  gate_id: string;
  status: string;
  created_at: string;
  result: GateResult;
};

export type AgentRunRecord = {
  id: string;
  project_id: string;
  version: string;
  agent_id: string;
  created_at: string;
  run: Record<string, unknown>;
};

export type AgentDefinition = {
  id: string;
  name: string;
  role: string;
  input_contract: string;
  output_contract: string;
  system_prompt: string;
  deterministic_fallback_policy: string;
  model_config_ref: string;
  quality_checklist: string[];
};

export type PlatformStatus = {
  runtime_mode: RuntimeMode;
  agents: AgentDefinition[];
  gates: Array<{ id: string; name: string; routes: string[] }>;
  conditional_routes: string[];
};

export type AdjustmentPlan = {
  focus: string;
  impacted: string[];
  risky: boolean;
  rationale: string;
  summary: string;
};

export type PendingApproval = {
  id: string;
  project_id: string;
  user_input: string;
  rationale: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type AdjustmentResponse = {
  status: "applied" | "pending_approval" | "cancelled";
  message: string;
  plan?: AdjustmentPlan;
  approval?: PendingApproval;
  run?: { id: string; version: string; message: string };
  project?: Project;
  artefacts?: Artefact[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {})
    },
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

async function requestText(path: string): Promise<string> {
  const response = await fetch(`${apiBaseUrl()}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.text();
}

export const api = {
  listProjects: () => request<Project[]>("/api/projects"),
  platform: () => request<PlatformStatus>("/api/platform"),
  demoProject: () => request<Project>("/api/projects/demo"),
  getProject: (id: string) => request<ProjectDetail>(`/api/projects/${id}`),
  createProject: (payload: { name: string; description: string; product_idea: string }) =>
    request<Project>("/api/projects", { method: "POST", body: JSON.stringify(payload) }),
  updateProject: (id: string, payload: { name?: string; description?: string; product_idea?: string }) =>
    request<Project>(`/api/projects/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  runWorkflow: (id: string, user_input: string) =>
    request(`/api/projects/${id}/runs`, { method: "POST", body: JSON.stringify({ user_input }) }),
  adjustProject: (id: string, payload: { message: string; selected_version?: string; selected_tab?: string }) =>
    request<AdjustmentResponse>(`/api/projects/${id}/adjustments`, { method: "POST", body: JSON.stringify(payload) }),
  applyApproval: (projectId: string, approvalId: string) =>
    request<AdjustmentResponse>(`/api/projects/${projectId}/approvals/${approvalId}/apply`, { method: "POST" }),
  cancelApproval: (projectId: string, approvalId: string) =>
    request<AdjustmentResponse>(`/api/projects/${projectId}/approvals/${approvalId}/cancel`, { method: "POST" }),
  getArtefactContent: (projectId: string, artefactId: string) => requestText(`/api/projects/${projectId}/artefacts/${artefactId}`),
  artefactUrl: (projectId: string, artefactId: string) => `${apiBaseUrl()}/api/projects/${projectId}/artefacts/${artefactId}`,
  prototypeUrl: (id: string, version: string, focus?: string) =>
    `${apiBaseUrl()}/api/projects/${id}/prototype/${version}${focus ? `?focus=${encodeURIComponent(focus)}` : ""}`
};
