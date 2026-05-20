from fastapi import APIRouter, HTTPException, Response

from app.models.schemas import AdjustmentCreate, ProjectCreate, ProjectUpdate, RunCreate
from app.services import storage
from app.workflow.adjustments import apply_adjustment_to_state
from app.workflow.agents import AgentExecutor, agent_definitions
from app.workflow.product_graph import DEMO_IDEA, WORKFLOW_CONDITIONAL_ROUTES, run_product_workflow

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/platform")
def platform_status():
    executor = AgentExecutor()
    return {
        "runtime_mode": executor.runtime_mode,
        "agents": [agent.model_dump() for agent in agent_definitions()],
        "gates": [
            {"id": "input_readiness", "name": "Input Readiness Gate", "routes": ["pass -> PRD", "needs_human -> approval"]},
            {"id": "prd_quality", "name": "PRD Quality Gate", "routes": ["pass -> UX", "fail -> PRD revise", "needs_human -> approval"]},
            {"id": "ux_prototype_alignment", "name": "UX / Prototype Alignment Gate", "routes": ["pass -> QA", "fail -> UX or Prototype revise", "needs_human -> approval"]},
            {"id": "qa_coverage", "name": "QA Coverage Gate", "routes": ["pass -> Traceability", "fail -> QA revise", "needs_human -> approval"]},
            {"id": "final_alignment", "name": "Final Alignment Gate", "routes": ["pass -> publish", "fail -> Traceability revise", "needs_human -> approval"]},
        ],
        "conditional_routes": WORKFLOW_CONDITIONAL_ROUTES,
    }


@router.post("/projects")
def create_project(payload: ProjectCreate):
    return storage.create_project(payload.name, payload.description, payload.product_idea or DEMO_IDEA)


@router.get("/projects")
def list_projects():
    return storage.list_projects()


@router.get("/projects/demo")
def get_or_create_demo():
    for project in storage.list_projects():
        if project["name"] == "Smart Notification Summary":
            return project
    return storage.create_project("Smart Notification Summary", "Built-in phone system software demo case.", DEMO_IDEA)


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    try:
        project = storage.get_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    return {
        "project": project,
        "artefacts": storage.list_artefacts(project_id),
        "runs": storage.list_runs(project_id),
        "latest": storage.latest_by_kind(project_id),
        "canonical": storage.latest_canonical_state(project_id, project["current_version"]).get("canonical_state"),
        "gate_results": storage.list_gate_results(project_id, project["current_version"]),
        "agent_runs": storage.list_agent_runs(project_id, project["current_version"]),
        "runtime_mode": AgentExecutor().runtime_mode,
    }


@router.patch("/projects/{project_id}")
def update_project(project_id: str, payload: ProjectUpdate):
    try:
        return storage.update_project(project_id, payload.name, payload.description, payload.product_idea)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post("/projects/{project_id}/runs")
def run_workflow(project_id: str, payload: RunCreate):
    try:
        storage.get_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    state = run_product_workflow(project_id, payload.user_input)
    run, artefacts, project = storage.save_run_and_artefacts(project_id, payload.user_input, dict(state))
    return {"run": run, "project": project, "artefacts": artefacts, "state": state}


@router.post("/projects/{project_id}/adjustments")
def create_adjustment(project_id: str, payload: AdjustmentCreate):
    try:
        project = storage.get_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc

    base_state = storage.latest_state(project_id, payload.selected_version or project["current_version"])
    if not base_state:
        state = run_product_workflow(project_id, project["product_idea"] or DEMO_IDEA)
        base_state = dict(state)

    proposed_state, plan = apply_adjustment_to_state(base_state, payload.message, payload.selected_tab)
    proposed_state["product_idea"] = project["product_idea"]
    if plan.risky:
        approval = storage.create_pending_approval(project_id, payload.message, plan.rationale, proposed_state)
        return {
            "status": "pending_approval",
            "message": "Message received. This change affects broad or sensitive system behavior and needs approval before a new version is created.",
            "approval": approval,
            "plan": proposed_state["adjustment_plan"],
        }

    run, artefacts, updated_project = storage.save_run_and_artefacts(project_id, payload.message, proposed_state)
    return {
        "status": "applied",
        "message": f"Adjustment applied to {run['version']}. Updated {', '.join(plan.impacted)} and selected the new version.",
        "run": run,
        "project": updated_project,
        "artefacts": artefacts,
        "plan": proposed_state["adjustment_plan"],
    }


@router.post("/projects/{project_id}/approvals/{approval_id}/apply")
def apply_approval(project_id: str, approval_id: str):
    try:
        approval = storage.get_pending_approval(project_id, approval_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Approval not found") from exc
    if approval["status"] != "pending":
        raise HTTPException(status_code=409, detail="Approval is no longer pending")

    run, artefacts, project = storage.save_run_and_artefacts(project_id, approval["user_input"], approval["proposed_state"])
    updated_approval = storage.update_pending_approval(project_id, approval_id, "applied")
    return {
        "status": "applied",
        "message": f"Approved adjustment applied to {run['version']}.",
        "approval": updated_approval,
        "run": run,
        "project": project,
        "artefacts": artefacts,
        "plan": approval["proposed_state"].get("adjustment_plan", {}),
    }


@router.post("/projects/{project_id}/approvals/{approval_id}/cancel")
def cancel_approval(project_id: str, approval_id: str):
    try:
        approval = storage.get_pending_approval(project_id, approval_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Approval not found") from exc
    if approval["status"] != "pending":
        raise HTTPException(status_code=409, detail="Approval is no longer pending")
    updated_approval = storage.update_pending_approval(project_id, approval_id, "cancelled")
    return {"status": "cancelled", "message": "Pending adjustment cancelled. No artefacts were changed.", "approval": updated_approval}


@router.get("/projects/{project_id}/artefacts")
def list_artefacts(project_id: str):
    return storage.list_artefacts(project_id)


@router.get("/projects/{project_id}/artefacts/{artefact_id}")
def get_artefact(project_id: str, artefact_id: str):
    try:
        content, content_type = storage.read_artefact(project_id, artefact_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Artefact not found") from exc
    return Response(content=content, media_type=content_type)


@router.get("/projects/{project_id}/prototype/{version}")
def get_prototype(project_id: str, version: str):
    try:
        content = storage.read_prototype(project_id, version)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Prototype not found") from exc
    return Response(content=content, media_type="text/html")
