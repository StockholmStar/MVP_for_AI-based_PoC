"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  Boxes,
  CheckCircle2,
  ChevronDown,
  FileText,
  GitBranch,
  Layers3,
  Loader2,
  MonitorSmartphone,
  Play,
  Plus,
  TestTube2
} from "lucide-react";
import { Artefact, Project, ProjectDetail, api, apiDisplayBaseUrl } from "@/lib/api";

const workspaceTabs = [
  { key: "overview", label: "Product Overview", icon: Layers3 },
  { key: "prd", label: "PRD", icon: FileText },
  { key: "user_flow", label: "User Flow", icon: GitBranch },
  { key: "prototype", label: "Prototype", icon: MonitorSmartphone },
  { key: "qa", label: "QA Criteria", icon: TestTube2 }
];

const demoPrompt = "为智能通知摘要功能生成 PRD 和原型，覆盖 Notification shade、Settings opt-in、empty/error/success 状态，并生成 QA 和 Jira stories。";

const traceRows = [
  {
    outcome: "Notification shade summary card",
    requirement: "Show a summary card when eligible low-priority notifications exist.",
    screen: "Notification shade",
    qa: "Card appears only with eligible notifications; critical alerts remain separate."
  },
  {
    outcome: "Settings opt-in and category control",
    requirement: "Provide an explicit Settings opt-in and category controls.",
    screen: "Settings > Notifications",
    qa: "Toggle persists and disabled state prevents summary display."
  },
  {
    outcome: "Empty/loading/success/error states",
    requirement: "Render stable states for unavailable, preparing, complete, and no-content moments.",
    screen: "Shade state surfaces",
    qa: "Normal, empty, error, offline, OTA, and privacy cases are covered."
  }
];

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
  const [log, setLog] = useState<string[]>(["Ready. Open the demo project or run the workflow."]);
  const [focus, setFocus] = useState("notification_summary_card");
  const [newName, setNewName] = useState("Smart Notification Summary");
  const [selectedVersion, setSelectedVersion] = useState("");
  const [artefactContentById, setArtefactContentById] = useState<Record<string, string>>({});
  const apiLabel = apiDisplayBaseUrl();

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
      .catch((error) => setLog((items) => [`API error: ${error.message}`, ...items]));
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
        .catch((error) => setLog((items) => [`Artefact load failed: ${error.message}`, ...items]));
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
  const activePrototype = artefactsByKind.prototype;
  const prototypeSrc = detail && selectedVersion ? api.prototypeUrl(detail.project.id, selectedVersion, focus) : "";
  const overview = sectionFrom(prd, "Product Overview") || detail?.project.product_idea || "Run the workflow to generate a product overview.";
  const versionLabel = selectedVersion ? (selectedVersion === detail?.project.current_version ? `Latest (${selectedVersion})` : selectedVersion) : "No version";

  async function runAgent(event: FormEvent) {
    event.preventDefault();
    if (!input.trim()) return;
    setBusy(true);
    try {
      const activeProject = detail?.project || (await api.demoProject());
      if (!detail) {
        await refresh(activeProject.id);
      }

      setLog((items) => [`Running product workflow for ${activeProject.name}...`, ...items]);
      const result = await api.runWorkflow(activeProject.id, input.trim());
      const version = (result as { run: { version: string; message: string } }).run.version;
      setLog((items) => [`Completed ${version}: ${(result as { run: { message: string } }).run.message}`, ...items]);
      setSelectedVersion(version);
      await refresh(activeProject.id);
      setSelectedTab("overview");
    } catch (error) {
      setLog((items) => [`Run failed: ${(error as Error).message}`, ...items]);
    } finally {
      setBusy(false);
    }
  }

  async function createProject(event: FormEvent) {
    event.preventDefault();
    const project = await api.createProject({
      name: newName || "Untitled Product",
      description: "Created from AI Product Workspace",
      product_idea: input
    });
    setSelectedVersion(project.current_version);
    await refresh(project.id);
    setLog((items) => [`Created project ${project.name}`, ...items]);
  }

  function MarkdownPanel({ markdown, empty }: { markdown: string; empty: string }) {
    if (markdown) {
      return <div className="markdown" dangerouslySetInnerHTML={renderMarkdownLite(markdown)} />;
    }
    return <div className="rounded border border-dashed border-slate-300 p-6 text-sm text-slate-600">{empty}</div>;
  }

  return (
    <main className="flex h-screen min-h-[760px] bg-[#f5f7fa] text-ink">
      <aside className="w-72 shrink-0 border-r border-slate-200 bg-white p-4 flex flex-col gap-4">
        <div>
          <div className="flex items-center gap-2 text-lg font-bold">
            <Boxes size={20} /> AI Product Workspace
          </div>
          <p className="mt-1 text-xs text-slate-500">Product planning workspace for PM, UX, R&D, and QA alignment.</p>
        </div>

        <form onSubmit={createProject} className="space-y-2">
          <input value={newName} onChange={(event) => setNewName(event.target.value)} className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
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
              <div className="text-xs text-slate-500">API: {apiLabel} · PRD, flow, prototype, and QA are kept aligned by the workflow</div>
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
                <section>
                  <h2 className="text-sm font-semibold text-slate-900">Product direction</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{overview}</p>
                </section>
                <section className="rounded border border-slate-200">
                  <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2">
                    <div className="flex items-center gap-2 text-sm font-semibold">
                      <CheckCircle2 size={16} className="text-teal-700" /> Alignment status
                    </div>
                    <span className="rounded bg-teal-50 px-2 py-1 text-xs font-medium text-teal-800">Workflow aligned</span>
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
                        {traceRows.map((row) => (
                          <tr key={row.outcome}>
                            <td>{row.outcome}</td>
                            <td>{row.requirement}</td>
                            <td>{row.screen}</td>
                            <td>{row.qa}</td>
                          </tr>
                        ))}
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
                <p className="text-sm leading-6 text-slate-700">Use the preview panel to inspect Notification shade, Settings opt-in, empty, loading, success, error, permission, privacy, and system-state behavior. The selected focus is reflected in the prototype URL through the same-origin API proxy.</p>
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

        <form onSubmit={runAgent} className="border-t border-slate-200 bg-white p-4">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="mb-1 flex items-center gap-2 text-sm font-semibold">
                <Bot size={16} /> Product brief
              </label>
              <textarea value={input} onChange={(event) => setInput(event.target.value)} className="h-20 w-full resize-none rounded border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <button type="submit" disabled={busy || !input.trim()} className="flex h-11 items-center gap-2 rounded bg-teal-700 px-4 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60">
              {busy ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />} Run workflow
            </button>
          </div>
          <div className="mt-3 flex gap-2 overflow-x-auto text-xs text-slate-600">
            {log.slice(0, 5).map((item, index) => (
              <span key={`${item}-${index}`} className="shrink-0 rounded bg-slate-100 px-2 py-1">{item}</span>
            ))}
          </div>
        </form>
      </section>
    </main>
  );
}
