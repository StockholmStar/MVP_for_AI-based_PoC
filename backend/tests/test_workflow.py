from app.workflow.adjustments import apply_adjustment_to_state, route_adjustment
from app.workflow.product_graph import run_product_workflow


def test_workflow_generates_core_artefacts():
    state = run_product_workflow("test-project", "Generate Smart Notification Summary")
    assert state["status"] == "completed"
    assert "Functional Requirements" in state["prd_markdown"]
    assert "```mermaid" in state["mermaid_flowchart"]
    assert "notification_summary_card" in state["prototype_html"]
    assert "Traceability Matrix" in state["traceability_markdown"]
    assert "FR-01 Summary card" in state["traceability_markdown"]


def test_product_overview_does_not_echo_agent_instruction():
    instruction = "Generate PRD, prototype, QA and Jira stories for Smart Notification Summary"

    state = run_product_workflow("test-project", instruction)

    overview = state["prd_markdown"].split("## Background and Problem Definition", 1)[0]
    assert instruction not in overview
    assert "phone system feature" in overview


def test_adjustment_routes_common_pm_intents():
    plan = route_adjustment("Tweak the prototype empty state wording", "prototype")

    assert plan.focus == "empty_state"
    assert "prototype" in plan.impacted
    assert "prd" in plan.impacted
    assert not plan.risky


def test_adjustment_updates_aligned_artefacts():
    state = run_product_workflow("test-project", "Generate Smart Notification Summary")

    updated, plan = apply_adjustment_to_state(state, "Update privacy wording in the PRD", "prd")

    assert plan.focus == "privacy_fallback"
    assert "Applied Adjustment" in updated["prd_markdown"]
    assert "Privacy and owner boundary" in updated["prd_markdown"]
    assert "Adjustment coverage" in updated["traceability_markdown"]
