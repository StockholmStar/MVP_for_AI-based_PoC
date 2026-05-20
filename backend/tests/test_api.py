from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_demo_project_and_run():
    demo = client.get("/api/projects/demo")
    assert demo.status_code == 200
    project_id = demo.json()["id"]

    run = client.post(f"/api/projects/{project_id}/runs", json={"user_input": "为智能通知摘要功能生成 PRD 和原型。"})
    assert run.status_code == 200
    body = run.json()
    assert body["run"]["version"].startswith("v")
    assert any(item["kind"] == "prototype" for item in body["artefacts"])
    assert {item["kind"] for item in body["artefacts"]} == {"prd", "ux_flow", "flowchart", "prototype", "qa_criteria", "traceability"}

    detail = client.get(f"/api/projects/{project_id}")
    assert detail.status_code == 200
    assert "prd" in detail.json()["latest"]
    assert "traceability" in detail.json()["latest"]


def test_project_context_can_be_updated():
    created = client.post(
        "/api/projects",
        json={"name": "Camera Privacy", "description": "Initial", "product_idea": "Camera privacy indicators"},
    )
    assert created.status_code == 200
    project_id = created.json()["id"]

    updated = client.patch(
        f"/api/projects/{project_id}",
        json={
            "name": "Camera Privacy Controls",
            "description": "Settings and System UI privacy workflow",
            "product_idea": "Improve camera privacy indicators for Android system software.",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["name"] == "Camera Privacy Controls"
    assert updated.json()["description"] == "Settings and System UI privacy workflow"
    assert "camera privacy indicators" in updated.json()["product_idea"].lower()


def test_project_detail_orders_versions_numerically(monkeypatch):
    from app.services import storage

    project = storage.create_project("Version Sort", "test", "Generate a product workspace")

    monkeypatch.setattr(
        storage,
        "now_iso",
        lambda: "2026-05-19T00:00:00+00:00",
    )

    state = {
        "prd_markdown": "# PRD",
        "prototype_html": "<html><body>prototype</body></html>",
    }
    storage.save_run_and_artefacts(project["id"], "Generate", dict(state))
    for version in ["v1.1", "v1.2", "v1.13"]:
        monkeypatch.setattr(storage, "next_version", lambda current, version=version: version)
        storage.save_run_and_artefacts(project["id"], "Generate", dict(state))

    detail = client.get(f"/api/projects/{project['id']}")
    assert detail.status_code == 200

    versions = []
    for artefact in detail.json()["artefacts"]:
        if artefact["version"] not in versions:
            versions.append(artefact["version"])

    assert versions[:3] == ["v1.13", "v1.2", "v1.1"]
    assert detail.json()["latest"]["prd"]["version"] == "v1.13"
