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

    detail = client.get(f"/api/projects/{project_id}")
    assert detail.status_code == 200
    assert "prd" in detail.json()["latest"]
