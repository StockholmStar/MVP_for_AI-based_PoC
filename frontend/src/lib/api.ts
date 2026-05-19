export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

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
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
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

export const api = {
  listProjects: () => request<Project[]>("/api/projects"),
  demoProject: () => request<Project>("/api/projects/demo"),
  getProject: (id: string) => request<ProjectDetail>(`/api/projects/${id}`),
  createProject: (payload: { name: string; description: string; product_idea: string }) =>
    request<Project>("/api/projects", { method: "POST", body: JSON.stringify(payload) }),
  runWorkflow: (id: string, user_input: string) =>
    request(`/api/projects/${id}/runs`, { method: "POST", body: JSON.stringify({ user_input }) }),
  prototypeUrl: (id: string, version: string, focus?: string) =>
    `${API_BASE_URL}/api/projects/${id}/prototype/${version}${focus ? `?focus=${encodeURIComponent(focus)}` : ""}`
};
