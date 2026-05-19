"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Bot, Boxes, CheckCircle2, FileText, GitBranch, Loader2, Play, Plus, TestTube2, TicketCheck } from "lucide-react";
import { Artefact, Project, ProjectDetail, api, apiDisplayBaseUrl } from "@/lib/api";

const artefactTabs = [
  { key: "prd", label: "PRD", icon: FileText },
  { key: "ux_flow", label: "UX Flow", icon: GitBranch },
  { key: "consistency_review", label: "Consistency", icon: CheckCircle2 },
  { key: "qa_criteria", label: "QA Criteria", icon: TestTube2 },
  { key: "jira_stories_md", label: "Jira Stories", icon: TicketCheck }
];

const demoPrompt = "为智能通知摘要功能生成 PRD 和原型，覆盖 Notification shade、Settings opt-in、empty/error/success 状态，并生成 QA 和 Jira stories。";

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

function renderMarkdownLite(markdown: string) {
  const html = markdown
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/^# (.*)$/gm, "<h1>$1</h1>")
    .replace(/^## (.*)$/gm, "<h2>$1</h2>")
    .replace(/^\|(.+)\|$/gm, "<pre>|$1|</pre>")
    .replace(/^- (.*)$/gm, "<li>$1</li>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n\n/g, "<br/><br/>");
  return { __html: html };
}

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [selectedTab, setSelectedTab] = useState("prd");
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
      if (previous && versions.includes(previous) && previous === detail.project.current_version) return previous;
      return detail.project.current_version || versions[0] || "";
    });
  }, [detail, versions]);

  const selectedVersionArtefacts = useMemo(() => {
    if (!detail || !selectedVersion) return [];
    return detail.artefacts.filter((item) => item.version === selectedVersion);
  }, [detail, selectedVersion]);

  const activeArtefact: Artefact | undefined = useMemo(
    () => selectedVersionArtefacts.find((item) => item.kind === selectedTab),
    [selectedVersionArtefacts, selectedTab]
  );

  const activePrototype = selectedVersionArtefacts.find((item) => item.kind === "prototype");
  const activeArtefactContent = activeArtefact ? artefactContentById[activeArtefact.id] : undefined;
  const activeArtefactLoaded = activeArtefact ? activeArtefact.id in artefactContentById : false;
  const prototypeSrc = detail && selectedVersion ? api.prototypeUrl(detail.project.id, selectedVersion, focus) : "";

  useEffect(() => {
    if (!detail || !activeArtefact || activeArtefactLoaded) return;
    let ignore = false;
    api
      .getArtefactContent(detail.project.id, activeArtefact.id)
      .then((content) => {
        if (!ignore) {
          setArtefactContentById((items) => ({ ...items, [activeArtefact.id]: content }));
        }
      })
      .catch((error) => setLog((items) => [`Artefact load failed: ${error.message}`, ...items]));
    return () => {
      ignore = true;
    };
  }, [activeArtefact, activeArtefactLoaded, detail]);

  async function runAgent(event: FormEvent) {
    event.preventDefault();
    if (!input.trim()) return;
    setBusy(true);
    try {
      const activeProject = detail?.project || (await api.demoProject());
      if (!detail) {
        await refresh(activeProject.id);
      }

      setLog((items) => [`Running LangGraph workflow for ${activeProject.name}...`, ...items]);
      const result = await api.runWorkflow(activeProject.id, input.trim());
      const version = (result as { run: { version: string; message: string } }).run.version;
      setLog((items) => [`Completed ${version}: ${(result as { run: { message: string } }).run.message}`, ...items]);
      setSelectedVersion(version);
      await refresh(activeProject.id);
      setSelectedTab("prd");
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

  return (
    <main className="flex h-screen min-h-[760px] bg-[#f5f7fa] text-ink">
      <aside className="w-72 shrink-0 border-r border-slate-200 bg-white p-4 flex flex-col gap-4">
        <div>
          <div className="flex items-center gap-2 text-lg font-bold">
            <Boxes size={20} /> AI Product Workspace
          </div>
          <p className="mt-1 text-xs text-slate-500">LangGraph multi-agent product artefact alignment PoC</p>
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
                className={`w-full rounded px-3 py-2 text-left text-sm ${detail?.project.id === project.id ? "bg-teal-50 text-teal-900" : "hover:bg-slate-100"}`}
              >
                <div className="font-medium">{project.name}</div>
                <div className="text-xs text-slate-500">{project.current_version}</div>
              </button>
            ))}
          </div>

          <div className="mb-2 mt-5 text-xs font-semibold uppercase text-slate-500">Artefacts</div>
          <div className="space-y-1">
            {artefactTabs.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setSelectedTab(key)}
                className={`flex w-full items-center gap-2 rounded px-3 py-2 text-sm ${selectedTab === key ? "bg-slate-900 text-white" : "hover:bg-slate-100"}`}
              >
                <Icon size={15} /> {label}
              </button>
            ))}
          </div>

          <div className="mb-2 mt-5 text-xs font-semibold uppercase text-slate-500">Versions</div>
          <div className="flex flex-wrap gap-2">
            {versions.length ? versions.map((version) => (
              <button
                key={version}
                type="button"
                onClick={() => setSelectedVersion(version)}
                className={`rounded px-2 py-1 text-xs font-medium ${selectedVersion === version ? "bg-teal-700 text-white" : "bg-slate-100 hover:bg-slate-200"}`}
              >
                {version}
              </button>
            )) : <span className="text-xs text-slate-500">No runs yet</span>}
          </div>
        </div>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-5">
          <div>
            <div className="font-semibold">{detail?.project.name || "Loading project"}</div>
            <div className="text-xs text-slate-500">API: {apiLabel} · Human approval gates: PRD review, prototype review, Jira push pending</div>
          </div>
          <div className="flex items-center gap-2">
            <select value={focus} onChange={(event) => setFocus(event.target.value)} className="rounded border border-slate-300 px-2 py-2 text-sm">
              <option value="notification_summary_card">Summary card</option>
              <option value="settings_toggle">Settings toggle</option>
              <option value="empty_state">Empty state</option>
              <option value="error_state">Error state</option>
              <option value="success_feedback">Success feedback</option>
            </select>
          </div>
        </header>

        <div className="grid min-h-0 flex-1 grid-cols-2 gap-0">
          <article className="min-w-0 overflow-auto border-r border-slate-200 bg-white p-5">
            <div className="mb-3 flex items-center justify-between">
              <h1 className="text-base font-bold">{artefactTabs.find((item) => item.key === selectedTab)?.label}</h1>
              <span className="rounded bg-slate-100 px-2 py-1 text-xs">{selectedVersion || activeArtefact?.version || "not generated"}</span>
            </div>
            {activeArtefactLoaded ? (
              <div className="markdown" dangerouslySetInnerHTML={renderMarkdownLite(activeArtefactContent || "")} />
            ) : activeArtefact ? (
              <div className="rounded border border-dashed border-slate-300 p-6 text-sm text-slate-600">Loading artefact...</div>
            ) : (
              <div className="rounded border border-dashed border-slate-300 p-6 text-sm text-slate-600">This artefact was not generated for {selectedVersion || "the selected version"}.</div>
            )}
          </article>

          <section className="min-w-0 overflow-auto bg-[#e9eef5] p-5">
            <div className="mb-3 flex items-center justify-between">
              <h1 className="text-base font-bold">Prototype Preview</h1>
              <span className="rounded bg-white px-2 py-1 text-xs">{selectedVersion || "not generated"}</span>
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
              <label className="mb-1 flex items-center gap-2 text-sm font-semibold"><Bot size={16} /> Agent instruction</label>
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
