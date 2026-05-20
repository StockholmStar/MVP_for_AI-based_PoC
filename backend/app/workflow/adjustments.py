from __future__ import annotations

from dataclasses import dataclass
from typing import Any


STATE_KEYS = {
    "prd": "prd_markdown",
    "user_flow": "ux_flow_markdown",
    "flowchart": "mermaid_flowchart",
    "prototype": "prototype_html",
    "qa": "qa_criteria",
    "qa_criteria": "qa_criteria",
    "traceability": "traceability_markdown",
}

TRACE_ROW = (
    "| Adjustment coverage. | ADJ-01 Applied request: {summary}. | "
    "`{focus}` prototype focus and aligned planning notes. | QA validates surface, entry, "
    "device state, privacy, power, OTA, region, model, and owner-boundary behavior. |"
)


@dataclass(frozen=True)
class AdjustmentPlan:
    focus: str
    impacted: tuple[str, ...]
    risky: bool
    rationale: str
    summary: str


def route_adjustment(message: str, selected_tab: str | None = None) -> AdjustmentPlan:
    lower = message.lower()
    focus = "notification_summary_card"
    impacted = {"prd", "user_flow", "prototype", "qa", "traceability"}

    focus_markers = (
        ("empty", "empty_state"),
        ("no notification", "empty_state"),
        ("error", "error_state"),
        ("offline", "error_state"),
        ("settings", "settings_toggle"),
        ("toggle", "settings_toggle"),
        ("notification shade", "notification_summary_card"),
        ("shade", "notification_summary_card"),
        ("privacy", "privacy_fallback"),
        ("permission", "privacy_fallback"),
        ("owner boundary", "owner_boundary"),
        ("owner-boundary", "owner_boundary"),
        ("ota", "device_state"),
        ("power", "device_state"),
        ("region", "device_state"),
        ("model", "device_state"),
        ("device state", "device_state"),
    )
    for marker, routed_focus in focus_markers:
        if marker in lower:
            focus = routed_focus
            break

    if "prototype" in lower:
        impacted = {"prototype", "prd", "user_flow", "qa", "traceability"}
    elif "prd" in lower or "requirement" in lower:
        impacted = {"prd", "user_flow", "qa", "traceability"}
    elif "qa" in lower or "acceptance" in lower or "test" in lower:
        impacted = {"qa", "prd", "traceability"}
    elif "user flow" in lower or "flow" in lower:
        impacted = {"user_flow", "flowchart", "prd", "qa", "traceability"}

    if selected_tab in STATE_KEYS and selected_tab not in {"overview"}:
        impacted.add(selected_tab)

    risky_markers = (
        "all",
        "everything",
        "rewrite",
        "replace",
        "remove privacy",
        "disable privacy",
        "lock screen",
        "launch",
        "rollout",
        "region",
        "owner boundary",
        "owner-boundary",
        "ota",
        "power",
        "model",
    )
    risky = any(marker in lower for marker in risky_markers)
    summary = summarize_request(message)
    rationale = (
        "Broad or system-sensitive change. Human confirmation is needed before applying to versioned artefacts."
        if risky
        else "Targeted deterministic update. Applying to selected artefacts and alignment outputs."
    )
    return AdjustmentPlan(focus=focus, impacted=tuple(sorted(impacted)), risky=risky, rationale=rationale, summary=summary)


def summarize_request(message: str) -> str:
    normalized = " ".join(message.strip().split())
    if len(normalized) <= 140:
        return normalized
    return f"{normalized[:137].rstrip()}..."


def apply_adjustment_to_state(base_state: dict[str, Any], message: str, selected_tab: str | None = None) -> tuple[dict[str, Any], AdjustmentPlan]:
    plan = route_adjustment(message, selected_tab)
    state = dict(base_state)
    summary = plan.summary

    if "prd" in plan.impacted:
        state["prd_markdown"] = append_section(
            state.get("prd_markdown", "# PRD"),
            "Applied Adjustment",
            [
                f"Request: {summary}",
                f"Prototype focus: `{plan.focus}`.",
                "Surface and entry: keep Notification shade and Settings entry behavior explicit.",
                "Device state: cover low memory, offline, classifier unavailable, and OTA migration behavior.",
                "Privacy and owner boundary: keep notification content inside system-owned components and preserve Settings/System UI/platform ownership.",
                "Power, region, and model constraints: avoid background wakeups; confirm region policy and eligible device/model scope before rollout.",
            ],
        )

    if "user_flow" in plan.impacted:
        state["ux_flow_markdown"] = append_section(
            state.get("ux_flow_markdown", "# UX Flow"),
            "Adjustment Flow",
            [
                f"User or PM requests: {summary}",
                f"Workspace routes the change to `{plan.focus}` and updates the selected artefact set.",
                "Flow review checks Notification shade entry, Settings opt-in, device state fallback, privacy fallback, and owner handoff.",
            ],
        )

    if "flowchart" in plan.impacted:
        state["mermaid_flowchart"] = state.get("mermaid_flowchart") or "```mermaid\nflowchart TD\n    A[Adjustment requested] --> B[Apply aligned artefact update]\n```"

    if "prototype" in plan.impacted:
        state["prototype_html"] = update_prototype(state.get("prototype_html", ""), summary, plan.focus)

    if "qa" in plan.impacted:
        state["qa_criteria"] = append_section(
            state.get("qa_criteria", "# QA Acceptance Criteria"),
            "Adjustment Regression Checks",
            [
                f"Validate requested change: {summary}",
                f"Confirm `{plan.focus}` renders expected copy/state in the prototype.",
                "Re-run privacy, power, OTA, region, model eligibility, and owner-boundary checks before release approval.",
            ],
        )

    if "traceability" in plan.impacted:
        traceability = state.get("traceability_markdown", "# Traceability Matrix\n\n| Product outcome | PRD requirement | User flow / prototype state | QA criterion |\n| --- | --- | --- | --- |\n")
        row = TRACE_ROW.format(summary=summary.replace("|", "/"), focus=plan.focus)
        state["traceability_markdown"] = f"{traceability.rstrip()}\n{row}\n"

    state["status"] = "adjustment_prepared" if plan.risky else "adjustment_applied"
    state["adjustment_plan"] = {
        "focus": plan.focus,
        "impacted": list(plan.impacted),
        "risky": plan.risky,
        "rationale": plan.rationale,
        "summary": plan.summary,
    }
    return state, plan


def append_section(markdown: str, heading: str, bullets: list[str]) -> str:
    body = "\n".join(f"- {bullet}" for bullet in bullets)
    return f"{markdown.rstrip()}\n\n## {heading}\n{body}\n"


def update_prototype(html: str, summary: str, focus: str) -> str:
    if not html:
        html = "<!doctype html><html><body><main><section>Prototype placeholder</section></main></body></html>"

    note = (
        '<div id="applied-adjustment" data-feature="adjustment_note" '
        'class="rounded-md bg-indigo-50 p-4 border border-indigo-200">'
        '<div class="font-semibold text-indigo-950">Applied adjustment</div>'
        f'<p class="text-sm text-indigo-800 mt-1">{escape_html(summary)}</p>'
        f'<p class="text-xs text-indigo-700 mt-2">Focus: {escape_html(focus)}. Review privacy, power, OTA, region, model, and owner boundaries.</p>'
        "</div>"
    )
    if 'id="applied-adjustment"' in html:
        start = html.find('<div id="applied-adjustment"')
        end = html.find("</div>", html.find("</div>", start) + 6)
        if start != -1 and end != -1:
            return f"{html[:start]}{note}{html[end + 6:]}"

    anchor = '<div class="rounded-md bg-white p-4 shadow-sm">'
    if anchor in html:
        return html.replace(anchor, f"{note}\n        {anchor}", 1)
    return html.replace("</body>", f"{note}\n</body>")


def escape_html(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
