from app.workflow.product_graph import run_product_workflow


def test_workflow_generates_core_artefacts():
    state = run_product_workflow("test-project", "Generate Smart Notification Summary")
    assert state["status"] == "completed"
    assert "Functional Requirements" in state["prd_markdown"]
    assert "```mermaid" in state["mermaid_flowchart"]
    assert "notification_summary_card" in state["prototype_html"]
    assert state["jira_stories"][0]["prototype_feature_id"]


def test_product_overview_does_not_echo_agent_instruction():
    instruction = "Generate PRD, prototype, QA and Jira stories for Smart Notification Summary"

    state = run_product_workflow("test-project", instruction)

    overview = state["prd_markdown"].split("## Background and Problem Definition", 1)[0]
    assert instruction not in overview
    assert "phone system feature" in overview
