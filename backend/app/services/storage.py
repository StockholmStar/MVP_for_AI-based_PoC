from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import DB_PATH, PROJECTS_DIR, ensure_data_dirs


ARTEFACT_SPECS = {
    "prd": ("requirements", "prd_{version}.md", "text/markdown", "prd_markdown"),
    "ux_flow": ("flows", "ux_flow_{version}.md", "text/markdown", "ux_flow_markdown"),
    "flowchart": ("flows", "flowchart_{version}.md", "text/markdown", "mermaid_flowchart"),
    "prototype": ("prototypes", "prototype_{version}.html", "text/html", "prototype_html"),
    "consistency_review": ("reviews", "consistency_review_{version}.md", "text/markdown", "consistency_report"),
    "qa_criteria": ("qa", "qa_criteria_{version}.md", "text/markdown", "qa_criteria"),
    "jira_stories_json": ("jira", "jira_stories_{version}.json", "application/json", "jira_stories"),
    "jira_stories_md": ("jira", "jira_stories_{version}.md", "text/markdown", "jira_stories_markdown"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    ensure_data_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                product_idea TEXT NOT NULL,
                current_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                version TEXT NOT NULL,
                user_input TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            CREATE TABLE IF NOT EXISTS artefacts (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                version TEXT NOT NULL,
                path TEXT NOT NULL,
                content_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            """
        )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def create_project(name: str, description: str, product_idea: str) -> dict[str, Any]:
    project_id = str(uuid.uuid4())
    ts = now_iso()
    with connect() as conn:
        conn.execute(
            "INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, name, description, product_idea, "v1.0", ts, ts),
        )
    (PROJECTS_DIR / project_id).mkdir(parents=True, exist_ok=True)
    for dirname in ["requirements", "prototypes", "flows", "qa", "jira", "reviews"]:
        (PROJECTS_DIR / project_id / dirname).mkdir(parents=True, exist_ok=True)
    return get_project(project_id)


def list_projects() -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM projects ORDER BY updated_at DESC")]


def get_project(project_id: str) -> dict[str, Any]:
    with connect() as conn:
        project = row_to_dict(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())
    if not project:
        raise KeyError(project_id)
    return project


def list_runs(project_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM runs WHERE project_id = ?", (project_id,))]
    return sorted(rows, key=version_sort_key, reverse=True)


def list_artefacts(project_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM artefacts WHERE project_id = ?", (project_id,))]
    return sorted(rows, key=version_sort_key, reverse=True)


def parse_version(version: str) -> tuple[int, ...]:
    normalized = version.removeprefix("v").removeprefix("V")
    parts: list[int] = []
    for part in normalized.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def version_sort_key(row: dict[str, Any]) -> tuple[tuple[int, ...], str]:
    return parse_version(row["version"]), row.get("created_at", "")


def next_version(current: str) -> str:
    major, minor = current.removeprefix("v").split(".")
    return f"v{major}.{int(minor) + 1}"


def save_run_and_artefacts(project_id: str, user_input: str, state: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    project = get_project(project_id)
    version = next_version(project["current_version"]) if list_artefacts(project_id) else "v1.0"
    state["version"] = version
    base = PROJECTS_DIR / project_id
    ts = now_iso()
    artefacts: list[dict[str, Any]] = []
    with connect() as conn:
        conn.execute("UPDATE projects SET current_version = ?, product_idea = ?, updated_at = ? WHERE id = ?", (version, state.get("product_idea", user_input), ts, project_id))
        for kind, (folder, filename, content_type, state_key) in ARTEFACT_SPECS.items():
            content = state.get(state_key)
            if content is None:
                continue
            if isinstance(content, (dict, list)):
                text = json.dumps(content, ensure_ascii=False, indent=2)
            else:
                text = str(content)
            path = base / folder / filename.format(version=version)
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            artefact = {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "kind": kind,
                "version": version,
                "path": str(path.relative_to(base)),
                "content_type": content_type,
                "created_at": ts,
            }
            conn.execute("INSERT INTO artefacts VALUES (?, ?, ?, ?, ?, ?, ?)", tuple(artefact.values()))
            artefacts.append(artefact)
        run = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "version": version,
            "user_input": user_input,
            "status": state.get("status", "completed"),
            "message": f"Generated {len(artefacts)} artefacts for {version}.",
            "created_at": ts,
        }
        conn.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)", tuple(run.values()))
    return run, artefacts, get_project(project_id)


def read_artefact(project_id: str, artefact_id: str) -> tuple[str, str]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM artefacts WHERE project_id = ? AND id = ?", (project_id, artefact_id)).fetchone()
    if not row:
        raise KeyError(artefact_id)
    artefact = dict(row)
    path = PROJECTS_DIR / project_id / artefact["path"]
    return path.read_text(encoding="utf-8"), artefact["content_type"]


def read_prototype(project_id: str, version: str) -> str:
    path = PROJECTS_DIR / project_id / "prototypes" / f"prototype_{version}.html"
    if not path.exists():
        raise KeyError(version)
    return path.read_text(encoding="utf-8")


def latest_by_kind(project_id: str) -> dict[str, Any]:
    latest: dict[str, Any] = {}
    for artefact in list_artefacts(project_id):
        if artefact["kind"] in latest:
            continue
        try:
            content = (PROJECTS_DIR / project_id / artefact["path"]).read_text(encoding="utf-8")
        except FileNotFoundError:
            content = ""
        latest[artefact["kind"]] = {**artefact, "content": content}
    return latest
