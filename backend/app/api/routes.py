from fastapi import APIRouter, HTTPException, Response

from app.models.schemas import ProjectCreate, RunCreate
from app.services import storage
from app.workflow.product_graph import DEMO_IDEA, run_product_workflow

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok"}


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
    }


@router.post("/projects/{project_id}/runs")
def run_workflow(project_id: str, payload: RunCreate):
    try:
        storage.get_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    state = run_product_workflow(project_id, payload.user_input)
    run, artefacts, project = storage.save_run_and_artefacts(project_id, payload.user_input, dict(state))
    return {"run": run, "project": project, "artefacts": artefacts, "state": state}


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
