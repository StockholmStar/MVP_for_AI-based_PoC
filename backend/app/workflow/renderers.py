from __future__ import annotations

from html import escape

from app.domain.workspace import ProductWorkspaceState


def render_prd(workspace: ProductWorkspaceState) -> str:
    req_rows = "\n".join(
        f"| {req['id']} | {req['title']} | {req['description']} | {', '.join(req.get('prototype_states', []))} |"
        for req in workspace.functional_requirements
    )
    owners = "\n".join(f"- {item['owner']}: {item['boundary']}" for item in workspace.owner_boundaries)
    adjustments = [item.removeprefix("Applied adjustment: ").strip() for item in workspace.assumptions if item.startswith("Applied adjustment:")]
    adjustment_section = ""
    if adjustments:
        adjustment_section = "\n\n## Applied Adjustment\n" + "\n".join(
            [
                f"- Request: {adjustments[-1]}",
                "- Surface and entry: keep Notification shade and Settings entry behavior explicit.",
                "- Privacy and owner boundary: keep notification content inside system-owned components and preserve ownership.",
                "- Power, OTA, region, and model constraints remain part of release review.",
            ]
        )
    return f"""# PRD vDraft: {workspace.metadata.get("name", "Smart Notification Summary")}

## Product Overview
{workspace.source_brief}

Smart Notification Summary reduces notification overload by grouping low-priority notifications into a compact card while keeping urgent notifications immediately visible.

## Goals
{bullet_list(workspace.goals)}

## Non-goals
{bullet_list(workspace.non_goals)}

## Target Users and Scenarios
{bullet_list(workspace.user_segments)}

## System Entry Points
{bullet_list(workspace.entry_points)}

## Functional Requirements
| ID | Capability | Requirement | Prototype experience |
| --- | --- | --- | --- |
{req_rows}

## Device States and Edge Cases
{bullet_list(workspace.device_states)}

## Privacy, Performance, Region, and OTA Constraints
{bullet_list([risk["description"] for risk in workspace.risks])}

## Owner Boundaries
{owners}

## Assumptions
{bullet_list(workspace.assumptions)}

## Questions to Confirm
{bullet_list(workspace.open_questions)}
{adjustment_section}
"""


def render_user_flow(workspace: ProductWorkspaceState) -> tuple[str, str]:
    states = "\n".join(f"- {state['id']}: {state['name']} - {state['description']}" for state in workspace.ux_states)
    main_flow = "\n".join(f"{index + 1}. {step['label']}" for index, step in enumerate(workspace.flows))
    mermaid_edges = "\n".join(f"    {step['from']} --> {step['to']}[{step['label']}]" for step in workspace.flows)
    markdown = f"""# UX Flow: {workspace.metadata.get("name", "Smart Notification Summary")}

## Main Flow
{main_flow}

## Prototype Screens and States
{states}
"""
    mermaid = f"""```mermaid
flowchart TD
{mermaid_edges}
```"""
    return markdown, mermaid


def render_prototype(workspace: ProductWorkspaceState) -> str:
    state_cards = "\n".join(
        f"""
        <div id="{escape(screen['state_id'])}" data-feature="{escape(screen['state_id'])}" class="state-card hidden rounded-md bg-white p-4 shadow-sm">
          <div class="font-semibold">{escape(screen['title'])}</div>
          <p class="mt-1 text-sm text-slate-600">{escape(screen['body'])}</p>
        </div>"""
        for screen in workspace.prototype_screens
    )
    buttons = "\n".join(
        f"""<button onclick="showState('{escape(screen['state_id'])}')" class="rounded bg-white/15 px-3 py-2 text-sm">{escape(screen['label'])}</button>"""
        for screen in workspace.prototype_screens
    )
    default_state = workspace.prototype_screens[0]["state_id"] if workspace.prototype_screens else "notification_summary_card"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(workspace.metadata.get("name", "Smart Notification Summary"))} Prototype</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body {{ background: #f4f6f8; color: #17202a; }}
    .phone {{ width: min(390px, 96vw); min-height: 720px; border: 10px solid #111827; border-radius: 34px; background: #eef2f7; overflow: hidden; box-shadow: 0 18px 55px rgba(17,24,39,.22); }}
    .focus-ring {{ outline: 3px solid #0f766e; outline-offset: 4px; }}
  </style>
</head>
<body>
  <main class="min-h-screen flex items-center justify-center p-4">
    <section class="phone">
      <div class="bg-slate-950 px-5 pb-3 pt-4 text-white">
        <div class="flex justify-between text-xs opacity-80"><span>9:41</span><span>5G 82%</span></div>
        <div class="mt-5 flex flex-wrap gap-2">{buttons}</div>
      </div>
      <div class="p-4 space-y-3">
        <div class="text-sm font-semibold text-slate-600">Notification and Settings workflow</div>
        {state_cards}
        <div class="rounded-md bg-white p-4 shadow-sm">
          <div class="font-medium">Calendar</div>
          <p class="text-sm text-slate-600">Design review starts in 15 minutes.</p>
        </div>
      </div>
    </section>
  </main>
  <script>
    const states = Array.from(document.querySelectorAll('.state-card')).map((node) => node.id);
    function showState(id) {{
      states.forEach((state) => document.getElementById(state).classList.toggle('hidden', state !== id));
      location.hash = id;
    }}
    const focus = new URLSearchParams(location.search).get('focus') || location.hash.replace('#','') || '{default_state}';
    showState(states.includes(focus) ? focus : '{default_state}');
    const target = document.querySelector(`[data-feature="${{focus}}"]`);
    if (target) target.classList.add('focus-ring');
  </script>
</body>
</html>"""


def render_qa(workspace: ProductWorkspaceState) -> str:
    grouped = "\n".join(f"- {item['id']} ({item['requirement_id']}): {item['criterion']}" for item in workspace.qa_criteria)
    return f"""# QA Acceptance Criteria

## Coverage
{grouped}

## Required Risk Sweeps
- Privacy and permission behavior.
- Power and performance behavior.
- OTA migration behavior.
- Region and model eligibility.
- Owner-boundary handoff behavior.
"""


def render_traceability(workspace: ProductWorkspaceState) -> str:
    rows = "\n".join(
        "| {outcome} | {requirement_id} {requirement} | `{prototype_state}` | {qa_id} {qa} |".format(**link)
        for link in workspace.trace_links
    )
    return f"""# Traceability Matrix

| Product outcome | PRD requirement | User flow / prototype state | QA criterion |
| --- | --- | --- | --- |
{rows}
"""


def render_all(workspace: ProductWorkspaceState) -> dict[str, str]:
    ux_markdown, mermaid = render_user_flow(workspace)
    return {
        "prd_markdown": render_prd(workspace),
        "ux_flow_markdown": ux_markdown,
        "mermaid_flowchart": mermaid,
        "prototype_html": render_prototype(workspace),
        "qa_criteria": render_qa(workspace),
        "traceability_markdown": render_traceability(workspace),
    }


def bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- To be confirmed."
