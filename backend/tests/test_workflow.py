from app.workflow.adjustments import apply_adjustment_to_state, route_adjustment
from app.workflow.product_graph import WORKFLOW_CONDITIONAL_ROUTES, build_graph, run_product_workflow


def test_workflow_generates_core_artefacts():
    state = run_product_workflow("test-project", "Generate Smart Notification Summary")
    assert state["status"] == "completed"
    assert state["canonical_state"]["functional_requirements"][0]["id"] == "FR-01"
    assert state["runtime_mode"]["mode"] == "LLM mode: deterministic fallback"
    assert "Functional Requirements" in state["prd_markdown"]
    assert "```mermaid" in state["mermaid_flowchart"]
    assert "notification_summary_card" in state["prototype_html"]
    assert "Traceability Matrix" in state["traceability_markdown"]
    assert "FR-01 Summary card" in state["traceability_markdown"]


def test_langgraph_uses_conditional_gate_routes():
    graph = build_graph()
    assert graph is not None
    assert WORKFLOW_CONDITIONAL_ROUTES == [
        "input_gate",
        "prd_gate",
        "ux_prototype_gate",
        "qa_gate",
        "final_alignment_gate",
    ]


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


def test_gate_failure_routes_to_revision_then_pass(monkeypatch):
    from app.workflow import product_graph

    original_prd_node = product_graph.prd_node
    calls = {"count": 0}

    def incomplete_once(state):
        next_state = original_prd_node(state)
        calls["count"] += 1
        if calls["count"] == 1:
            canonical = next_state["canonical_state"]
            canonical["functional_requirements"] = canonical["functional_requirements"][:2]
            next_state["canonical_state"] = canonical
        return next_state

    monkeypatch.setattr(product_graph, "prd_node", incomplete_once)
    state = product_graph.run_product_workflow("test-project", "Generate Smart Notification Summary")

    prd_results = [result for result in state["gate_results"] if result["gate_id"] == "prd_quality"]
    assert [result["status"] for result in prd_results] == ["fail", "pass"]
    assert state["status"] == "completed"
