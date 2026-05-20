from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.domain.workspace import ProductWorkspaceState
from app.services.context_loader import load_context_pack
from app.workflow.agents import AgentExecutor, agent_definitions
from app.workflow.gates import append_gate, gate_result, latest_attempt
from app.workflow.renderers import render_all


class ProductState(TypedDict, total=False):
    project_id: str
    user_input: str
    product_idea: str
    canonical_state: dict[str, Any]
    prd_markdown: str
    ux_flow_markdown: str
    mermaid_flowchart: str
    prototype_html: str
    traceability_markdown: str
    qa_criteria: str
    version: str
    status: str
    errors: list[str]
    context_pack: str
    runtime_mode: dict[str, Any]
    gate_results: list[dict[str, Any]]
    agent_run_history: list[dict[str, Any]]
    pending_approval_request: dict[str, Any] | None


DEMO_IDEA = (
    "Smart Notification Summary: a phone system feature that groups low-priority "
    "notifications into a summary card in Notification shade, with Settings controls, "
    "privacy safeguards, empty/error states, and QA-ready acceptance criteria."
)

AGENT_INSTRUCTION_MARKERS = (
    "agent",
    "generate",
    "create",
    "build",
    "workflow",
    "prd",
    "prototype",
    "jira",
    "story",
    "stories",
    "生成",
    "原型",
    "运行",
)

WORKFLOW_CONDITIONAL_ROUTES = [
    "input_gate",
    "prd_gate",
    "ux_prototype_gate",
    "qa_gate",
    "final_alignment_gate",
]


def product_summary_from_input(user_input: str) -> str:
    candidate = user_input.strip()
    if not candidate:
        return DEMO_IDEA
    lower_candidate = candidate.lower()
    if any(marker in lower_candidate for marker in AGENT_INSTRUCTION_MARKERS):
        return DEMO_IDEA
    return candidate


def workspace_from_state(state: ProductState) -> ProductWorkspaceState:
    existing = state.get("canonical_state") or {}
    if existing:
        return ProductWorkspaceState.model_validate(existing)
    return ProductWorkspaceState(project_id=state["project_id"], source_brief=product_summary_from_input(state.get("user_input", "")))


def state_from_workspace(state: ProductState, workspace: ProductWorkspaceState) -> ProductState:
    rendered = render_all(workspace)
    return {
        **state,
        **rendered,
        "product_idea": workspace.source_brief,
        "canonical_state": workspace.model_dump(),
        "gate_results": workspace.gate_results,
        "agent_run_history": workspace.agent_run_history,
    }


def run_agent(state: ProductState, agent_id: str, fallback) -> ProductState:
    workspace = workspace_from_state(state)
    executor = AgentExecutor()
    updated, _ = executor.run(agent_id, workspace, fallback, {"context_pack": state.get("context_pack", "")})
    next_state = state_from_workspace(state, updated)
    next_state["runtime_mode"] = executor.runtime_mode
    return next_state


def coordinator_node(state: ProductState) -> ProductState:
    def fallback(workspace: ProductWorkspaceState) -> dict[str, Any]:
        return {
            "metadata": {
                **workspace.metadata,
                "name": "Smart Notification Summary",
                "workflow_phase": "full_generation",
                "affected_artefacts": ["prd", "user_flow", "prototype", "qa_criteria", "traceability"],
            },
            "source_brief": product_summary_from_input(state.get("user_input", "")),
        }

    next_state = run_agent({**state, "context_pack": load_context_pack()}, "coordinator", fallback)
    next_state["status"] = "coordinated"
    return next_state


def input_checker_node(state: ProductState) -> ProductState:
    def fallback(workspace: ProductWorkspaceState) -> dict[str, Any]:
        return {
            "assumptions": [
                "Feature ships as an opt-in system experience for Android 15+ devices.",
                "Notification ranking runs on-device where possible; cloud calls are out of scope for the PoC.",
                "System UI owns Notification shade surfaces; Settings owns persistent controls.",
                "Low-priority categorization uses existing notification channels and user behavior signals.",
            ],
            "open_questions": [
                "Which regions, device tiers, and Android/OTA versions are in launch scope?",
                "Should summary ranking be fully on-device or can it call a server model?",
                "What notification categories must never be summarized?",
                "Which telemetry events are acceptable under privacy policy?",
                "What is the fallback if ranking data is unavailable?",
            ],
            "user_segments": [
                "Power users with high daily notification volume.",
                "Users who want promotional and low-priority updates batched.",
                "QA and support teams validating notification behavior across device states.",
            ],
        }

    next_state = run_agent(state, "input_checker", fallback)
    next_state["status"] = "input_checked"
    return next_state


def input_gate_node(state: ProductState) -> ProductState:
    workspace = workspace_from_state(state)
    failed = []
    if len(workspace.source_brief.strip()) < 24:
        failed.append("Source brief is too short to establish product intent.")
    if not workspace.assumptions:
        failed.append("Assumptions are missing.")
    status = "needs_human" if failed else "pass"
    result = gate_result("input_readiness", status, failed, "Clarify product scope before generation.", "input_checker")
    append_gate(workspace, result)
    next_state = state_from_workspace(state, workspace)
    next_state["status"] = "input_ready" if status == "pass" else "needs_human"
    return next_state


def prd_node(state: ProductState) -> ProductState:
    def fallback(workspace: ProductWorkspaceState) -> dict[str, Any]:
        return {
            "goals": [
                "Reduce Notification shade clutter without hiding critical notifications.",
                "Give users explicit opt-in control from Settings and inline summary actions.",
                "Provide clear empty, loading, error, privacy fallback, and success states.",
                "Generate reviewable outputs for PM, UX, engineering, and QA.",
            ],
            "non_goals": [
                "Rewriting Android notification ranking infrastructure.",
                "Sending notification content to third-party services.",
                "Building real Figma, Jira, or proxy integrations in this foundation.",
            ],
            "surfaces": ["Notification shade", "Settings > Notifications", "System privacy controls"],
            "entry_points": [
                "Notification shade summary card appears above eligible low-priority groups.",
                "Settings contains opt-in toggle and category controls.",
                "Lock screen summary text remains out of scope unless privacy review approves redaction behavior.",
            ],
            "device_states": [
                "Loading while ranking prepares cached notification metadata.",
                "Empty when no eligible notifications exist or all categories are excluded.",
                "Error/offline when classifier data cannot be prepared.",
                "Disabled/no permission when the user has not opted in.",
                "OTA migration, low-memory, region policy, and model eligibility states preserve safe fallback behavior.",
            ],
            "functional_requirements": [
                {"id": "FR-01", "title": "Summary card", "description": "Show a summary card in Notification shade when low-priority notifications exist.", "prototype_states": ["notification_summary_card"]},
                {"id": "FR-02", "title": "Settings control", "description": "Provide Settings opt-in toggle and category controls.", "prototype_states": ["settings_toggle"]},
                {"id": "FR-03", "title": "Empty state", "description": "Show empty state when no summarizable notifications exist.", "prototype_states": ["empty_state"]},
                {"id": "FR-04", "title": "Error state", "description": "Show error/offline state when ranking data cannot be prepared.", "prototype_states": ["error_state"]},
                {"id": "FR-05", "title": "Success feedback", "description": "Show success feedback after useful/tuning actions.", "prototype_states": ["success_feedback"]},
            ],
            "risks": [
                {"id": "R-privacy", "description": "Notification content must remain inside system-owned components and sensitive categories must be redacted or excluded."},
                {"id": "R-power", "description": "Avoid background wakeups when Notification shade is closed and keep cached generation under 500 ms."},
                {"id": "R-ota", "description": "OTA migration must preserve opt-in and category selections."},
                {"id": "R-region-model", "description": "Region policy and eligible device/model scope must be confirmed before rollout."},
            ],
            "owner_boundaries": [
                {"owner": "System UI", "boundary": "Notification shade card, state rendering, and inline actions."},
                {"owner": "Settings", "boundary": "Opt-in toggle and category controls."},
                {"owner": "Platform notification team", "boundary": "Ranking and notification metadata contract."},
                {"owner": "Data/logging", "boundary": "Privacy-safe telemetry events."},
                {"owner": "QA", "boundary": "Regression matrix across device states, app categories, and OTA paths."},
            ],
        }

    next_state = run_agent(state, "prd", fallback)
    next_state["status"] = "prd_generated"
    return next_state


def prd_gate_node(state: ProductState) -> ProductState:
    workspace = workspace_from_state(state)
    attempt = latest_attempt(workspace, "prd_quality")
    failed = []
    if len(workspace.functional_requirements) < 5:
        failed.append("Functional requirements do not cover the expected core states.")
    if not workspace.goals or not workspace.non_goals:
        failed.append("Goals and non-goals must both be explicit.")
    if not workspace.owner_boundaries:
        failed.append("Owner boundaries are missing.")
    status = "pass" if not failed else "needs_human" if attempt >= 2 else "fail"
    append_gate(workspace, gate_result("prd_quality", status, failed, "Revise PRD structure and owner boundaries.", "prd", attempt))
    next_state = state_from_workspace(state, workspace)
    next_state["status"] = "prd_gate_passed" if status == "pass" else status
    return next_state


def ux_node(state: ProductState) -> ProductState:
    def fallback(workspace: ProductWorkspaceState) -> dict[str, Any]:
        ux_states = [
            {"id": "settings_toggle", "name": "Settings opt-in", "description": "User enables or disables Smart Notification Summary."},
            {"id": "loading_state", "name": "Loading", "description": "System prepares cached on-device summary data."},
            {"id": "notification_summary_card", "name": "Notification shade summary card", "description": "Grouped low-priority updates appear while urgent alerts stay separate."},
            {"id": "empty_state", "name": "Empty state", "description": "No eligible notifications are available."},
            {"id": "error_state", "name": "Error state", "description": "Classifier or storage unavailable; normal notification list remains visible."},
            {"id": "privacy_fallback", "name": "Privacy fallback", "description": "Sensitive or lock-screen content is redacted or not summarized."},
            {"id": "success_feedback", "name": "Success feedback", "description": "User feedback has been saved."},
        ]
        flows = [
            {"from": "A", "to": "B", "label": "Settings opt-in entry"},
            {"from": "B", "to": "C", "label": "Permission and privacy checks"},
            {"from": "C", "to": "D", "label": "Open Notification shade"},
            {"from": "D", "to": "E", "label": "Loading state"},
            {"from": "E", "to": "F", "label": "Summary, empty, error, or privacy fallback"},
            {"from": "F", "to": "G", "label": "Feedback or manage categories"},
        ]
        return {"ux_states": ux_states, "flows": flows}

    next_state = run_agent(state, "ux_flow", fallback)
    next_state["status"] = "ux_generated"
    return next_state


def prototype_node(state: ProductState) -> ProductState:
    def fallback(workspace: ProductWorkspaceState) -> dict[str, Any]:
        screens = [
            {"state_id": "notification_summary_card", "label": "Shade", "title": "Smart summary", "body": "7 low-priority updates grouped from Shopping, News, and Social. Critical notifications remain outside the summary."},
            {"state_id": "settings_toggle", "label": "Settings", "title": "Smart Notification Summary", "body": "Opt-in toggle and category controls for low-priority notification summaries."},
            {"state_id": "empty_state", "label": "Empty", "title": "No summary right now", "body": "Low-priority updates will appear when eligible notifications exist."},
            {"state_id": "error_state", "label": "Error", "title": "Summary unavailable", "body": "Regular notifications are still shown. Try again later or review Settings."},
            {"state_id": "privacy_fallback", "label": "Privacy", "title": "Private content protected", "body": "Sensitive content is redacted or excluded before any summary appears."},
            {"state_id": "success_feedback", "label": "Saved", "title": "Preference saved", "body": "The system will tune future summaries from this feedback."},
        ]
        return {"prototype_screens": screens}

    next_state = run_agent(state, "prototype", fallback)
    next_state["status"] = "prototype_generated"
    return next_state


def ux_prototype_gate_node(state: ProductState) -> ProductState:
    workspace = workspace_from_state(state)
    attempt = latest_attempt(workspace, "ux_prototype_alignment")
    ux_ids = {item["id"] for item in workspace.ux_states}
    prototype_ids = {item["state_id"] for item in workspace.prototype_screens}
    failed = sorted(ux_ids - prototype_ids - {"loading_state"})
    status = "pass" if not failed else "needs_human" if attempt >= 2 else "fail"
    append_gate(workspace, gate_result("ux_prototype_alignment", status, failed, "Align UX states to prototype screens.", "prototype", attempt))
    next_state = state_from_workspace(state, workspace)
    next_state["status"] = "ux_prototype_gate_passed" if status == "pass" else status
    return next_state


def qa_node(state: ProductState) -> ProductState:
    def fallback(workspace: ProductWorkspaceState) -> dict[str, Any]:
        criteria = [
            {"id": "QA-01", "requirement_id": "FR-01", "criterion": "Summary card appears only with eligible low-priority notifications; critical alerts remain separate."},
            {"id": "QA-02", "requirement_id": "FR-02", "criterion": "Settings toggle persists across restart and disabled state prevents summary display."},
            {"id": "QA-03", "requirement_id": "FR-03", "criterion": "No eligible notifications shows empty state and normal notifications are unaffected."},
            {"id": "QA-04", "requirement_id": "FR-04", "criterion": "Ranking unavailable shows error state and preserves the standard notification list."},
            {"id": "QA-05", "requirement_id": "FR-05", "criterion": "Useful action shows success feedback without removing critical notifications."},
            {"id": "QA-06", "requirement_id": "R-privacy", "criterion": "Sensitive categories, lock-screen content, and permission revocation fail closed."},
            {"id": "QA-07", "requirement_id": "R-power", "criterion": "Cached generation meets latency budget and does not create background wakeups."},
            {"id": "QA-08", "requirement_id": "R-ota", "criterion": "OTA migration preserves opt-in state and category selections."},
            {"id": "QA-09", "requirement_id": "R-region-model", "criterion": "Region and eligible model constraints are enforced before rollout."},
        ]
        return {"qa_criteria": criteria}

    next_state = run_agent(state, "qa", fallback)
    next_state["status"] = "qa_generated"
    return next_state


def qa_gate_node(state: ProductState) -> ProductState:
    workspace = workspace_from_state(state)
    attempt = latest_attempt(workspace, "qa_coverage")
    covered = {item["requirement_id"] for item in workspace.qa_criteria}
    required = {item["id"] for item in workspace.functional_requirements}
    failed = sorted(required - covered)
    for risk in ["R-privacy", "R-power", "R-ota", "R-region-model"]:
        if risk not in covered:
            failed.append(f"{risk} coverage missing")
    status = "pass" if not failed else "needs_human" if attempt >= 2 else "fail"
    append_gate(workspace, gate_result("qa_coverage", status, failed, "Revise QA coverage for requirements and risk categories.", "qa", attempt))
    next_state = state_from_workspace(state, workspace)
    next_state["status"] = "qa_gate_passed" if status == "pass" else status
    return next_state


def traceability_node(state: ProductState) -> ProductState:
    def fallback(workspace: ProductWorkspaceState) -> dict[str, Any]:
        qa_by_req = {item["requirement_id"]: item for item in workspace.qa_criteria}
        links = []
        for req in workspace.functional_requirements:
            qa = qa_by_req.get(req["id"], {"id": "QA-TBD", "criterion": "Coverage to be confirmed."})
            links.append(
                {
                    "outcome": workspace.goals[0] if workspace.goals else "Product outcome to confirm.",
                    "requirement_id": req["id"],
                    "requirement": req["title"],
                    "prototype_state": (req.get("prototype_states") or ["state_tbd"])[0],
                    "qa_id": qa["id"],
                    "qa": qa["criterion"],
                }
            )
        return {"trace_links": links}

    next_state = run_agent(state, "traceability", fallback)
    next_state["status"] = "traceability_generated"
    return next_state


def final_gate_node(state: ProductState) -> ProductState:
    workspace = workspace_from_state(state)
    attempt = latest_attempt(workspace, "final_alignment")
    req_ids = {item["id"] for item in workspace.functional_requirements}
    traced = {item["requirement_id"] for item in workspace.trace_links}
    failed = sorted(req_ids - traced)
    risky = any(result.get("status") == "needs_human" for result in workspace.gate_results)
    status = "needs_human" if risky else "pass" if not failed else "needs_human" if attempt >= 2 else "fail"
    append_gate(workspace, gate_result("final_alignment", status, failed, "Resolve traceability before publishing.", "traceability", attempt))
    next_state = state_from_workspace(state, workspace)
    next_state["status"] = "final_gate_passed" if status == "pass" else status
    return next_state


def human_approval_node(state: ProductState) -> ProductState:
    workspace = workspace_from_state(state)
    request = {
        "status": "pending",
        "rationale": "A gate or sensitive product change needs approval before publishing a new version.",
        "gate_results": [result for result in workspace.gate_results if result.get("status") == "needs_human"],
    }
    workspace.human_approvals.append(request)
    next_state = state_from_workspace(state, workspace)
    next_state["pending_approval_request"] = request
    next_state["status"] = "needs_human"
    return next_state


def publish_node(state: ProductState) -> ProductState:
    return {**state, "status": "completed", "pending_approval_request": None}


def route_gate(state: ProductState, pass_target: str) -> str:
    status = state.get("status")
    if status == "needs_human":
        return "human_approval"
    if status == "fail":
        latest = (state.get("gate_results") or [])[-1]
        return latest.get("revision_target") or pass_target
    return pass_target


def route_input_gate(state: ProductState) -> str:
    return route_gate(state, "prd")


def route_prd_gate(state: ProductState) -> str:
    return route_gate(state, "ux")


def route_ux_prototype_gate(state: ProductState) -> str:
    return route_gate(state, "qa")


def route_qa_gate(state: ProductState) -> str:
    return route_gate(state, "traceability")


def route_final_gate(state: ProductState) -> str:
    return route_gate(state, "publish")


def build_graph():
    graph = StateGraph(ProductState)
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("input_checker", input_checker_node)
    graph.add_node("input_gate", input_gate_node)
    graph.add_node("prd", prd_node)
    graph.add_node("prd_gate", prd_gate_node)
    graph.add_node("ux", ux_node)
    graph.add_node("prototype", prototype_node)
    graph.add_node("ux_prototype_gate", ux_prototype_gate_node)
    graph.add_node("qa", qa_node)
    graph.add_node("qa_gate", qa_gate_node)
    graph.add_node("traceability", traceability_node)
    graph.add_node("final_alignment_gate", final_gate_node)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("publish", publish_node)
    graph.add_edge(START, "coordinator")
    graph.add_edge("coordinator", "input_checker")
    graph.add_edge("input_checker", "input_gate")
    graph.add_conditional_edges("input_gate", route_input_gate, {"prd": "prd", "human_approval": "human_approval"})
    graph.add_edge("prd", "prd_gate")
    graph.add_conditional_edges("prd_gate", route_prd_gate, {"ux": "ux", "prd": "prd", "human_approval": "human_approval"})
    graph.add_edge("ux", "prototype")
    graph.add_edge("prototype", "ux_prototype_gate")
    graph.add_conditional_edges("ux_prototype_gate", route_ux_prototype_gate, {"qa": "qa", "ux": "ux", "prototype": "prototype", "human_approval": "human_approval"})
    graph.add_edge("qa", "qa_gate")
    graph.add_conditional_edges("qa_gate", route_qa_gate, {"traceability": "traceability", "qa": "qa", "human_approval": "human_approval"})
    graph.add_edge("traceability", "final_alignment_gate")
    graph.add_conditional_edges("final_alignment_gate", route_final_gate, {"publish": "publish", "traceability": "traceability", "human_approval": "human_approval"})
    graph.add_edge("publish", END)
    graph.add_edge("human_approval", END)
    return graph.compile()


def run_product_workflow(project_id: str, user_input: str) -> ProductState:
    graph = build_graph()
    initial: ProductState = {"project_id": project_id, "user_input": user_input, "status": "started", "errors": []}
    return graph.invoke(initial)
