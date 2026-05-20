"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Bot,
  Boxes,
  CheckCircle2,
  ChevronDown,
  Copy,
  Download,
  FileDown,
  FileText,
  GitBranch,
  Layers3,
  Loader2,
  MonitorSmartphone,
  Play,
  Plus,
  Save,
  Send,
  TestTube2
} from "lucide-react";
import { AdjustmentResponse, Artefact, PendingApproval, Project, ProjectDetail, api } from "@/lib/api";

const workspaceTabs = [
  { key: "overview", label: "Product Overview", icon: Layers3 },
  { key: "prd", label: "PRD", icon: FileText },
  { key: "user_flow", label: "User Flow", icon: GitBranch },
  { key: "prototype", label: "Prototype", icon: MonitorSmartphone },
  { key: "qa", label: "QA Criteria", icon: TestTube2 }
];

const demoPrompt = "为智能通知摘要功能生成 PRD、用户流、可交互原型和 QA 标准，覆盖 Notification shade、Settings opt-in、empty/error/success 状态。";

type ActivityItem = {
  id: string;
  status: "received" | "working" | "success" | "pending" | "failed" | "cancelled";
  title: string;
  body: string;
  approval?: PendingApproval;
};

function parseVersion(version: string) {
  return version
    .replace(/^v/i, "")
    .split(".")
    .map((part) => Number.parseInt(part, 10))
    .map((part) => (Number.isFinite(part) ? part : 0));
}

function compareVersions(a: string, b: string) {
  const left = parseVersion(a);
  const right = parseVersion(b);
  const length = Math.max(left.length, right.length);
  for (let index = 0; index < length; index += 1) {
    const difference = (left[index] || 0) - (right[index] || 0);
    if (difference !== 0) return difference;
  }
  return a.localeCompare(b);
}

function shortText(value: string, maxLength = 96) {
  const normalized = value.replace(/\s+/g, " ").trim();
  if (normalized.length <= maxLength) return normalized;
  return `${normalized.slice(0, maxLength - 1).trimEnd()}...`;
}

function formatUpdatedAt(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function isGenericWorkspaceDescription(value: string) {
  return value.trim().toLowerCase() === ["created", "from", "ai", "product", "workspace"].join(" ");
}

function escapeHtml(markdown: string) {
  return markdown.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function renderMarkdownLite(markdown: string) {
  const withoutMermaid = markdown.replace(/```mermaid[\s\S]*?```/g, "");
  const html = escapeHtml(withoutMermaid)
    .replace(/^# (.*)$/gm, "<h1>$1</h1>")
    .replace(/^## (.*)$/gm, "<h2>$1</h2>")
    .replace(/^### (.*)$/gm, "<h3>$1</h3>")
    .replace(/^\|(.+)\|$/gm, "<pre>|$1|</pre>")
    .replace(/^- (.*)$/gm, "<li>$1</li>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n\n/g, "<br/><br/>");
  return { __html: html };
}

function mermaidSourceFrom(content: string) {
  const fenced = content.match(/```mermaid\s*([\s\S]*?)```/);
  return (fenced?.[1] || content).trim();
}

function sectionFrom(markdown: string, heading: string) {
  const escaped = heading.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = markdown.match(new RegExp(`## ${escaped}\\n([\\s\\S]*?)(?=\\n## |$)`));
  return match?.[1]?.trim() || "";
}

function traceRowsFrom(markdown: string) {
  return markdown
    .split("\n")
    .filter((line) => line.startsWith("|") && !line.includes("---") && !line.includes("Product outcome"))
    .map((line) => line.split("|").slice(1, -1).map((cell) => cell.trim()))
    .filter((cells) => cells.length >= 4)
    .map(([outcome, requirement, screen, qa]) => ({ outcome, requirement, screen, qa }));
}

function MermaidDiagram({ source }: { source: string }) {
  const [svg, setSvg] = useState("");
  const [error, setError] = useState("");
  const renderId = useRef(0);

  useEffect(() => {
    let cancelled = false;
    const id = `smart-summary-flow-${Date.now()}-${renderId.current++}`;

    async function render() {
      if (!source.trim()) return;
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "base" });
        const result = await mermaid.render(id, source);
        if (!cancelled) {
          setSvg(result.svg);
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setSvg("");
          setError((err as Error).message);
        }
      }
    }

    render();
    return () => {
      cancelled = true;
    };
  }, [source]);

  if (error) {
    return <div className="rounded border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">Flowchart render failed: {error}</div>;
  }

  if (!svg) {
    return <div className="rounded border border-dashed border-slate-300 p-6 text-sm text-slate-600">Rendering flowchart...</div>;
  }

  return <div className="mermaid-frame" dangerouslySetInnerHTML={{ __html: svg }} />;
}

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [selectedTab, setSelectedTab] = useState("overview");
  const [input, setInput] = useState(demoPrompt);
  const [busy, setBusy] = useState(false);
  const [activity, setActivity] = useState<ActivityItem[]>([
    {
      id: "ready",
      status: "success",
      title: "Workspace ready",
      body: "Open the demo project, run the workflow, or ask for a targeted artefact adjustment."
    }
  ]);
  const [focus, setFocus] = useState("notification_summary_card");
  const [newName, setNewName] = useState("Smart Notification Summary");
  const [newDescription, setNewDescription] = useState("Phone system software workflow for notification overload, Settings control, privacy, and QA.");
  const [selectedVersion, setSelectedVersion] = useState("");
  const [artefactContentById, setArtefactContentById] = useState<Record<string, string>>({});
  const [projectDraft, setProjectDraft] = useState({ name: "", description: "", product_idea: "" });
  const [savingProject, setSavingProject] = useState(false);

  function pushActivity(item: Omit<ActivityItem, "id">) {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setActivity((items) => [{ id, ...item }, ...items]);
    return id;
  }

  function updateActivity(id: string, patch: Partial<ActivityItem>) {
    setActivity((items) => items.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }

  function describeAdjustment(result: AdjustmentResponse) {
    const impacted = result.plan?.impacted?.join(", ");
    const focus = result.plan?.focus ? ` Focus: ${result.plan.focus}.` : "";
    return impacted ? `${result.message} Updated: ${impacted}.${focus}` : result.message;
  }

  async function refresh(projectId?: string) {
    const list = await api.listProjects();
    setProjects(list);
    const id = projectId || detail?.project.id || list[0]?.id;
    if (id) {
      setDetail(await api.getProject(id));
    }
  }

  useEffect(() => {
    api
      .demoProject()
      .then((project) => refresh(project.id))
      .catch((error) => pushActivity({ status: "failed", title: "Project load failed", body: error.message }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const versions = useMemo(
    () => Array.from(new Set((detail?.artefacts || []).map((item) => item.version))).sort(compareVersions).reverse(),
    [detail]
  );

  useEffect(() => {
    if (!detail) return;
    setSelectedVersion((previous) => {
      if (previous && versions.includes(previous)) return previous;
      return detail.project.current_version || versions[0] || "";
    });
    setProjectDraft({
      name: detail.project.name,
      description: detail.project.description,
      product_idea: detail.project.product_idea
    });
  }, [detail, versions]);

  const selectedVersionArtefacts = useMemo(() => {
    if (!detail || !selectedVersion) return [];
    return detail.artefacts.filter((item) => item.version === selectedVersion);
  }, [detail, selectedVersion]);

  const artefactsByKind = useMemo(() => {
    return selectedVersionArtefacts.reduce<Record<string, Artefact>>((items, artefact) => {
      items[artefact.kind] = artefact;
      return items;
    }, {});
  }, [selectedVersionArtefacts]);

  useEffect(() => {
    if (!detail) return;
    selectedVersionArtefacts.forEach((artefact) => {
      if (artefact.id in artefactContentById) return;
      api
        .getArtefactContent(detail.project.id, artefact.id)
        .then((content) => {
          setArtefactContentById((items) => ({ ...items, [artefact.id]: content }));
        })
        .catch((error) => pushActivity({ status: "failed", title: "Artefact load failed", body: error.message }));
    });
  }, [artefactContentById, detail, selectedVersionArtefacts]);

  function content(kind: string) {
    const artefact = artefactsByKind[kind];
    return artefact ? artefactContentById[artefact.id] || "" : "";
  }

  const prd = content("prd");
  const userFlow = content("ux_flow");
  const flowchart = mermaidSourceFrom(content("flowchart"));
  const qaCriteria = content("qa_criteria");
  const traceability = content("traceability");
  const traceRows = traceRowsFrom(traceability);
  const activePrototype = artefactsByKind.prototype;
  const activeArtefact = selectedTab === "prd" ? artefactsByKind.prd : selectedTab === "user_flow" ? artefactsByKind.ux_flow : selectedTab === "qa" ? artefactsByKind.qa_criteria : selectedTab === "prototype" ? activePrototype : artefactsByKind.traceability;
  const activeMarkdown = selectedTab === "prd" ? prd : selectedTab === "user_flow" ? userFlow : selectedTab === "qa" ? qaCriteria : selectedTab === "overview" ? traceability : "";
  const prototypeSrc = detail && selectedVersion ? api.prototypeUrl(detail.project.id, selectedVersion, focus) : "";
  const overview = sectionFrom(prd, "Product Overview") || detail?.project.product_idea || "Run the workflow to generate a product overview.";
  const versionLabel = selectedVersion ? (selectedVersion === detail?.project.current_version ? `Latest (${selectedVersion})` : selectedVersion) : "No version";
  const projectSubtitle = useMemo(() => {
    if (!detail) return "Loading project context";

    const { project } = detail;
    const description = isGenericWorkspaceDescription(project.description) ? "" : project.description;
    const summary = shortText(description || project.product_idea);
    const updatedAt = formatUpdatedAt(project.updated_at);
    const metadata = [project.current_version ? `Current ${project.current_version}` : "", updatedAt ? `Updated ${updatedAt}` : ""].filter(Boolean);

    return [summary, ...metadata].filter(Boolean).join(" · ");
  }, [detail]);

  async function runAgent() {
    if (!input.trim()) return;
    setBusy(true);
    const activityId = pushActivity({
      status: "working",
      title: "Workflow started",
      body: "Generating Product Overview, PRD, User Flow, Prototype, QA Criteria, and traceability as a synchronized version."
    });
    try {
      const activeProject = detail?.project || (await api.demoProject());
      if (!detail) {
        await refresh(activeProject.id);
      }

      const result = await api.runWorkflow(activeProject.id, input.trim());
      const version = (result as { run: { version: string; message: string } }).run.version;
      updateActivity(activityId, {
        status: "success",
        title: `Workflow completed: ${version}`,
        body: (result as { run: { message: string } }).run.message
      });
      setSelectedVersion(version);
      await refresh(activeProject.id);
      setSelectedTab("overview");
    } catch (error) {
      updateActivity(activityId, { status: "failed", title: "Workflow failed", body: (error as Error).message });
    } finally {
      setBusy(false);
    }
  }

  async function submitAdjustment(event: FormEvent) {
    event.preventDefault();
    if (!input.trim()) return;
    setBusy(true);
    const receivedId = pushActivity({
      status: "received",
      title: "Message received",
      body: "Routing request to the relevant artefacts and checking whether approval is needed."
    });
    try {
      const activeProject = detail?.project || (await api.demoProject());
      updateActivity(receivedId, {
        status: "working",
        title: "Adjustment in progress",
        body: "Preparing a deterministic update across PRD, user flow, prototype, QA criteria, and traceability where applicable."
      });
      const result = await api.adjustProject(activeProject.id, {
        message: input.trim(),
        selected_version: selectedVersion || activeProject.current_version,
        selected_tab: selectedTab
      });

      if (result.status === "pending_approval" && result.approval) {
        updateActivity(receivedId, {
          status: "pending",
          title: "Approval needed",
          body: describeAdjustment(result),
          approval: result.approval
        });
        return;
      }

      const version = result.run?.version || result.project?.current_version || activeProject.current_version;
      updateActivity(receivedId, {
        status: "success",
        title: `Adjustment applied: ${version}`,
        body: describeAdjustment(result)
      });
      setSelectedVersion(version);
      await refresh(activeProject.id);
      if (result.plan?.focus) setFocus(result.plan.focus);
    } catch (error) {
      updateActivity(receivedId, { status: "failed", title: "Adjustment failed", body: (error as Error).message });
    } finally {
      setBusy(false);
    }
  }

  async function resolveApproval(item: ActivityItem, action: "apply" | "cancel") {
    if (!detail || !item.approval) return;
    setBusy(true);
    updateActivity(item.id, {
      status: "working",
      title: action === "apply" ? "Approval accepted" : "Approval rejected",
      body: action === "apply" ? "Applying the approved change as a new version." : "Cancelling the pending change without modifying artefacts."
    });
    try {
      const result = action === "apply" ? await api.applyApproval(detail.project.id, item.approval.id) : await api.cancelApproval(detail.project.id, item.approval.id);
      if (action === "apply") {
        const version = result.run?.version || result.project?.current_version || detail.project.current_version;
        updateActivity(item.id, { status: "success", title: `Approved change applied: ${version}`, body: describeAdjustment(result), approval: undefined });
        setSelectedVersion(version);
        await refresh(detail.project.id);
        if (result.plan?.focus) setFocus(result.plan.focus);
      } else {
        updateActivity(item.id, { status: "cancelled", title: "Pending change cancelled", body: result.message, approval: undefined });
      }
    } catch (error) {
      updateActivity(item.id, { status: "failed", title: "Approval action failed", body: (error as Error).message });
    } finally {
      setBusy(false);
    }
  }

  async function createProject(event: FormEvent) {
    event.preventDefault();
    const project = await api.createProject({
      name: newName || "Untitled Product",
      description: newDescription,
      product_idea: input
    });
    setSelectedVersion(project.current_version);
    await refresh(project.id);
    pushActivity({ status: "success", title: "Project created", body: project.name });
  }

  async function saveProject(event: FormEvent) {
    event.preventDefault();
    if (!detail) return;
    setSavingProject(true);
    try {
      const project = await api.updateProject(detail.project.id, projectDraft);
      setInput(project.product_idea);
      await refresh(project.id);
      pushActivity({ status: "success", title: "Project context saved", body: project.name });
    } catch (error) {
      pushActivity({ status: "failed", title: "Save failed", body: (error as Error).message });
    } finally {
      setSavingProject(false);
    }
  }

  async function copyActiveArtefact() {
    const value = selectedTab === "prototype" ? prototypeSrc : activeMarkdown;
    if (!value) return;
    await navigator.clipboard.writeText(value);
    pushActivity({ status: "success", title: "Copied artefact", body: workspaceTabs.find((item) => item.key === selectedTab)?.label || "Selected artefact" });
  }

  function MarkdownPanel({ markdown, empty }: { markdown: string; empty: string }) {
    if (markdown) {
      return <div className="markdown" dangerouslySetInnerHTML={renderMarkdownLite(markdown)} />;
    }
    return <div className="rounded border border-dashed border-slate-300 p-6 text-sm text-slate-600">{empty}</div>;
  }

  function ActivityIcon({ status }: { status: ActivityItem["status"] }) {
    if (status === "working") return <Loader2 size={15} className="animate-spin text-teal-700" />;
    if (status === "failed") return <AlertTriangle size={15} className="text-rose-700" />;
    if (status === "pending") return <AlertTriangle size={15} className="text-amber-700" />;
    return <CheckCircle2 size={15} className={status === "cancelled" ? "text-slate-500" : "text-teal-700"} />;
  }

  return (
    <main className="flex h-screen min-h-[760px] bg-[#f5f7fa] text-ink">
      <aside className="w-72 shrink-0 border-r border-slate-200 bg-white p-4 flex flex-col gap-4">
        <div>
          <div className="flex items-center gap-2 text-lg font-bold">
            <Boxes size={20} /> AI Product Workspace
          </div>
        </div>

        <form onSubmit={createProject} className="space-y-2">
          <input aria-label="New project name" value={newName} onChange={(event) => setNewName(event.target.value)} className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
          <textarea aria-label="New project description" value={newDescription} onChange={(event) => setNewDescription(event.target.value)} className="h-16 w-full resize-none rounded border border-slate-300 px-3 py-2 text-sm" />
          <button className="flex w-full items-center justify-center gap-2 rounded bg-slate-900 px-3 py-2 text-sm font-medium text-white">
            <Plus size={15} /> New project
          </button>
        </form>

        <div className="min-h-0 flex-1 overflow-auto">
          <div className="mb-2 text-xs font-semibold uppercase text-slate-500">Projects</div>
          <div className="space-y-1">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => {
                  setSelectedVersion(project.current_version);
                  refresh(project.id);
                }}
                className={`w-full rounded px-3 py-2 text-left text-sm ${detail?.project.id === project.id ? "bg-teal-50 text-teal-950" : "hover:bg-slate-100"}`}
              >
                <div className="font-medium">{project.name}</div>
                <div className="mt-1 text-xs text-slate-500">Current plan: {project.current_version}</div>
              </button>
            ))}
          </div>
        </div>

      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-slate-200 bg-white px-5 py-3">
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="font-semibold">{detail?.project.name || "Loading project"}</div>
              {projectSubtitle ? <div className="text-xs text-slate-500">{projectSubtitle}</div> : null}
            </div>
            <div className="flex items-center gap-2">
              <label className="relative">
                <span className="sr-only">Version</span>
                <select value={selectedVersion} onChange={(event) => setSelectedVersion(event.target.value)} className="appearance-none rounded border border-slate-300 bg-white py-2 pl-3 pr-8 text-sm">
                  {versions.length ? (
                    versions.map((version, index) => (
                      <option key={version} value={version}>
                        {index === 0 ? `Latest (${version})` : version}
                      </option>
                    ))
                  ) : (
                    <option value="">No version</option>
                  )}
                </select>
                <ChevronDown size={15} className="pointer-events-none absolute right-2 top-2.5 text-slate-500" />
              </label>
              <select value={focus} onChange={(event) => setFocus(event.target.value)} className="rounded border border-slate-300 px-2 py-2 text-sm">
                <option value="notification_summary_card">Notification shade</option>
                <option value="settings_toggle">Settings opt-in</option>
                <option value="empty_state">Empty state</option>
                <option value="error_state">Error state</option>
                <option value="success_feedback">Success feedback</option>
              </select>
              <button type="button" onClick={copyActiveArtefact} disabled={!activeArtefact && selectedTab !== "prototype"} className="flex items-center gap-2 rounded border border-slate-300 bg-white px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50">
                <Copy size={15} /> Copy
              </button>
              {detail && activeArtefact ? (
                <a href={api.artefactUrl(detail.project.id, activeArtefact.id)} download className="flex items-center gap-2 rounded border border-slate-300 bg-white px-3 py-2 text-sm">
                  <Download size={15} /> Download
                </a>
              ) : selectedTab === "prototype" && prototypeSrc ? (
                <a href={prototypeSrc} target="_blank" rel="noreferrer" className="flex items-center gap-2 rounded border border-slate-300 bg-white px-3 py-2 text-sm">
                  <FileDown size={15} /> Open
                </a>
              ) : null}
            </div>
          </div>

          <nav className="mt-3 flex gap-1 overflow-x-auto">
            {workspaceTabs.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setSelectedTab(key)}
                className={`flex shrink-0 items-center gap-2 rounded px-3 py-2 text-sm ${selectedTab === key ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"}`}
              >
                <Icon size={15} /> {label}
              </button>
            ))}
          </nav>
        </header>

        <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_minmax(360px,44%)] gap-0">
          <article className="min-w-0 overflow-auto border-r border-slate-200 bg-white p-5">
            <div className="mb-4 flex items-center justify-between">
              <h1 className="text-base font-bold">{workspaceTabs.find((item) => item.key === selectedTab)?.label}</h1>
              <span className="rounded bg-slate-100 px-2 py-1 text-xs">{versionLabel}</span>
            </div>

            {selectedTab === "overview" && (
              <div className="space-y-4">
                <form onSubmit={saveProject} className="rounded border border-slate-200 bg-slate-50 p-3">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <h2 className="text-sm font-semibold text-slate-900">Project context</h2>
                    <button type="submit" disabled={savingProject || !detail} className="flex items-center gap-2 rounded bg-white px-3 py-2 text-sm font-medium text-slate-800 ring-1 ring-slate-300 disabled:cursor-not-allowed disabled:opacity-50">
                      {savingProject ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} Save
                    </button>
                  </div>
                  <div className="grid gap-2">
                    <input
                      aria-label="Project name"
                      value={projectDraft.name}
                      onChange={(event) => setProjectDraft((draft) => ({ ...draft, name: event.target.value }))}
                      className="rounded border border-slate-300 bg-white px-3 py-2 text-sm"
                    />
                    <textarea
                      aria-label="Project description"
                      value={projectDraft.description}
                      onChange={(event) => setProjectDraft((draft) => ({ ...draft, description: event.target.value }))}
                      className="h-16 resize-none rounded border border-slate-300 bg-white px-3 py-2 text-sm"
                    />
                    <textarea
                      aria-label="Product idea"
                      value={projectDraft.product_idea}
                      onChange={(event) => setProjectDraft((draft) => ({ ...draft, product_idea: event.target.value }))}
                      className="h-24 resize-none rounded border border-slate-300 bg-white px-3 py-2 text-sm"
                    />
                  </div>
                </form>
                <section>
                  <h2 className="text-sm font-semibold text-slate-900">Product direction</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{overview}</p>
                </section>
                <section className="rounded border border-slate-200">
                  <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2">
                    <div className="flex items-center gap-2 text-sm font-semibold">
                      <CheckCircle2 size={16} className="text-teal-700" /> Output set
                    </div>
                    <span className="rounded bg-teal-50 px-2 py-1 text-xs font-medium text-teal-800">Ready for PM demo</span>
                  </div>
                  <p className="px-3 py-3 text-sm leading-6 text-slate-700">PRD, user flow, prototype, and QA criteria are generated as a synchronized set for the selected version.</p>
                </section>
                <section>
                  <h2 className="text-sm font-semibold text-slate-900">Traceability snapshot</h2>
                  <div className="mt-2 overflow-auto rounded border border-slate-200">
                    <table className="trace-table">
                      <thead>
                        <tr>
                          <th>Product outcome</th>
                          <th>Requirement</th>
                          <th>Prototype screen</th>
                          <th>QA check</th>
                        </tr>
                      </thead>
                      <tbody>
                        {traceRows.length ? traceRows.map((row) => (
                          <tr key={row.outcome}>
                            <td>{row.outcome}</td>
                            <td>{row.requirement}</td>
                            <td>{row.screen}</td>
                            <td>{row.qa}</td>
                          </tr>
                        )) : (
                          <tr>
                            <td colSpan={4}>Run the workflow to generate traceability across product outcomes, PRD requirements, user flow, prototype states, and QA criteria.</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </section>
              </div>
            )}

            {selectedTab === "prd" && <MarkdownPanel markdown={prd} empty={`PRD was not generated for ${selectedVersion || "the selected version"}.`} />}

            {selectedTab === "user_flow" && (
              <div className="space-y-5">
                {flowchart ? (
                  <section>
                    <div className="mb-2 text-sm font-semibold text-slate-900">Rendered smartphone system flow</div>
                    <MermaidDiagram source={flowchart} />
                  </section>
                ) : (
                  <div className="rounded border border-dashed border-slate-300 p-6 text-sm text-slate-600">Flowchart was not generated for this version.</div>
                )}
                <MarkdownPanel markdown={userFlow} empty="User flow was not generated for this version." />
              </div>
            )}

            {selectedTab === "prototype" && (
              <div className="space-y-4">
                <p className="text-sm leading-6 text-slate-700">Use the preview panel to inspect Notification shade, Settings opt-in, empty, loading, success, error, permission, privacy, and system-state behavior. The selected focus keeps the prototype view tied to the planning scenario.</p>
                <div className="overflow-auto rounded border border-slate-200">
                  <table className="trace-table">
                    <thead>
                      <tr>
                        <th>Screen/state</th>
                        <th>Why it matters</th>
                        <th>Trace target</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr><td>Notification shade</td><td>Primary user entry point for grouped low-priority updates.</td><td>PRD summary card requirement and QA normal path</td></tr>
                      <tr><td>Settings opt-in</td><td>Explicit control and privacy explanation before system summarization starts.</td><td>PRD permission handling and QA disabled state</td></tr>
                      <tr><td>Empty/error/success</td><td>Shows graceful behavior when ranking, content, or feedback state changes.</td><td>PRD edge cases and QA failure states</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {selectedTab === "qa" && <MarkdownPanel markdown={qaCriteria} empty={`QA criteria were not generated for ${selectedVersion || "the selected version"}.`} />}
          </article>

          <section className="min-w-0 overflow-auto bg-[#e9eef5] p-5">
            <div className="mb-3 flex items-center justify-between">
              <h1 className="text-base font-bold">Prototype Preview</h1>
              <span className="rounded bg-white px-2 py-1 text-xs">{versionLabel}</span>
            </div>
            {activePrototype ? (
              <iframe key={`${prototypeSrc}-${focus}`} src={prototypeSrc} className="h-[calc(100%-2rem)] min-h-[640px] w-full rounded border border-slate-300 bg-white" />
            ) : (
              <div className="flex h-[640px] items-center justify-center rounded border border-dashed border-slate-300 bg-white text-sm text-slate-600">
                Prototype will appear here after the first run.
              </div>
            )}
          </section>
        </div>

        <form onSubmit={submitAdjustment} className="grid min-h-[210px] grid-cols-[minmax(0,1fr)_minmax(360px,42%)] gap-4 border-t border-slate-200 bg-white p-4">
          <section className="min-h-0 rounded border border-slate-200 bg-slate-50">
            <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Bot size={16} /> AI response and activity
              </div>
              <span className="text-xs text-slate-500">Latest first</span>
            </div>
            <div className="max-h-44 space-y-2 overflow-auto p-3">
              {activity.slice(0, 8).map((item) => (
                <article key={item.id} className="rounded border border-slate-200 bg-white p-3">
                  <div className="flex items-start gap-2">
                    <ActivityIcon status={item.status} />
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-semibold text-slate-900">{item.title}</div>
                      <p className="mt-1 text-xs leading-5 text-slate-600">{item.body}</p>
                      {item.status === "pending" && item.approval ? (
                        <div className="mt-3 flex gap-2">
                          <button type="button" disabled={busy} onClick={() => resolveApproval(item, "apply")} className="rounded bg-teal-700 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-60">
                            Approve and apply
                          </button>
                          <button type="button" disabled={busy} onClick={() => resolveApproval(item, "cancel")} className="rounded border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 disabled:opacity-60">
                            Reject
                          </button>
                        </div>
                      ) : null}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="flex min-h-0 flex-col">
            <label className="mb-1 flex items-center gap-2 text-sm font-semibold">
              <Send size={16} /> Ask for an artefact adjustment
            </label>
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Example: Update the empty state copy and align PRD, user flow, prototype, QA, and traceability."
              className="min-h-28 flex-1 resize-none rounded border border-slate-300 px-3 py-2 text-sm"
            />
            <div className="mt-3 flex flex-wrap justify-end gap-2">
              <button type="button" onClick={runAgent} disabled={busy || !input.trim()} className="flex h-10 items-center gap-2 rounded border border-slate-300 bg-white px-4 text-sm font-medium text-slate-800 disabled:cursor-not-allowed disabled:opacity-60">
                <Play size={16} /> Run full workflow
              </button>
              <button type="submit" disabled={busy || !input.trim()} className="flex h-10 items-center gap-2 rounded bg-teal-700 px-4 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60">
                {busy ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />} Apply adjustment
              </button>
            </div>
          </section>
        </form>
      </section>
    </main>
  );
}
