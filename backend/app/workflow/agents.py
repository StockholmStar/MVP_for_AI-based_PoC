from __future__ import annotations

import json
from typing import Any, Callable

from app.core.config import LLM_MODEL
from app.domain.workspace import AgentDefinition, ProductWorkspaceState
from app.services.llm import ModelClient
from app.services.storage import now_iso


def agent_definitions() -> list[AgentDefinition]:
    return [
        AgentDefinition(
            id="coordinator",
            name="Coordinator Agent",
            role="Understands the request, identifies phase and affected canonical state areas, and coordinates workflow transitions.",
            input_contract="User request, current canonical state, and workflow status.",
            output_contract="Workflow intent, affected artefact families, and stage notes.",
            system_prompt="You are the workflow coordinator for a role-aware product workspace. Return concise structured JSON only.",
            deterministic_fallback_policy="Classify generation or adjustment intent from keywords and keep all artefacts derived from canonical state.",
            quality_checklist=["No raw debug output", "Keeps product-safe artefact set", "Routes risky changes to approval"],
        ),
        AgentDefinition(
            id="input_checker",
            name="Input Checker Agent",
            role="Checks whether the source product brief has enough information to create reviewable product workflow outputs.",
            input_contract="Source brief and existing project metadata.",
            output_contract="Missing information, assumptions, clarification questions, and readiness status.",
            system_prompt="Check product brief readiness for PM, UX, engineering, and QA pre-review. Return JSON only.",
            deterministic_fallback_policy="Use the built-in phone system demo brief when the prompt is only an instruction; otherwise preserve the user's product idea.",
            quality_checklist=["Names missing launch/device/privacy scope", "Adds assumptions", "Does not block useful demos"],
        ),
        AgentDefinition(
            id="prd",
            name="PRD Agent",
            role="Generates and refines structured product requirements inside the canonical state.",
            input_contract="Canonical brief, assumptions, open questions, and context pack.",
            output_contract="Goals, non-goals, requirements, surfaces, risks, and owner boundaries.",
            system_prompt="Create structured product requirements for a system software product workflow. Return JSON patch only.",
            deterministic_fallback_policy="Populate a stable Smart Notification Summary requirement model with PM/engineering/QA boundaries.",
            quality_checklist=["Goals and non-goals are explicit", "Requirements have IDs", "Owner boundaries are clear"],
        ),
        AgentDefinition(
            id="ux_flow",
            name="UX Flow Agent",
            role="Generates and refines user flows, UX states, and Mermaid-compatible flow structure.",
            input_contract="Canonical requirements, surfaces, entry points, and device states.",
            output_contract="UX states and flow transitions mapped to requirements.",
            system_prompt="Create UX flow state models that map back to requirements. Return JSON patch only.",
            deterministic_fallback_policy="Create settings opt-in, notification shade, loading, empty, error, privacy fallback, and success states.",
            quality_checklist=["Every key state maps to a requirement", "Covers alternate/failure states", "Produces Mermaid-safe labels"],
        ),
        AgentDefinition(
            id="prototype",
            name="Prototype Agent",
            role="Generates and refines prototype screen/state models and rendered HTML.",
            input_contract="Canonical UX states, requirements, surfaces, and focus state.",
            output_contract="Prototype screens/states derived from canonical state.",
            system_prompt="Create inspectable prototype screen models for a phone system feature. Return JSON patch only.",
            deterministic_fallback_policy="Map canonical UX states to HTML prototype regions and data-feature identifiers.",
            quality_checklist=["Screens map to UX states", "Empty/error/success states exist", "No fake external integration claims"],
        ),
        AgentDefinition(
            id="qa",
            name="QA Agent",
            role="Generates QA acceptance criteria and regression coverage from canonical requirements and states.",
            input_contract="Canonical requirements, UX states, prototype screens, risks, and device constraints.",
            output_contract="QA criteria linked to requirements and risk categories.",
            system_prompt="Create QA criteria for product, UX, engineering, privacy, power, OTA, region, and model constraints. Return JSON patch only.",
            deterministic_fallback_policy="Create coverage for normal path, boundaries, failure states, privacy, power, OTA, region, and model constraints.",
            quality_checklist=["Each requirement has QA coverage", "Risk categories are covered", "Critical notifications remain protected"],
        ),
        AgentDefinition(
            id="traceability",
            name="Traceability Agent",
            role="Maintains links across product outcome, requirement, UX state/prototype screen, and QA criterion.",
            input_contract="Canonical requirements, UX states, prototype screens, and QA criteria.",
            output_contract="Trace links suitable for a product-safe review status view.",
            system_prompt="Create traceability links across product outcomes, requirements, UX/prototype states, and QA. Return JSON patch only.",
            deterministic_fallback_policy="Create one trace row per functional requirement using canonical IDs.",
            quality_checklist=["No orphan requirements", "No orphan QA criteria", "Product-safe status wording"],
        ),
        AgentDefinition(
            id="output_checker",
            name="Output Checker / Gate Agent",
            role="Evaluates structured outputs and decides pass, revise, human approval, or fail.",
            input_contract="Canonical state, target gate, and revision attempts.",
            output_contract="Gate result with failed checks, feedback, revision target, and status.",
            system_prompt="Evaluate workflow gate quality. Return gate result JSON only.",
            deterministic_fallback_policy="Apply deterministic completeness and alignment checks with bounded revision attempts.",
            quality_checklist=["Uses conditional routing", "Provides target feedback", "Escalates risky unresolved issues"],
        ),
        AgentDefinition(
            id="human_approval",
            name="Human Approval Agent",
            role="Pauses broad or sensitive changes for explicit user approval before versioned publishing.",
            input_contract="Proposed canonical state, risk rationale, and gate result.",
            output_contract="Pending approval request or approved/cancelled decision.",
            system_prompt="Prepare a concise human approval request for risky product workflow changes.",
            deterministic_fallback_policy="Create pending approvals for broad rewrite, privacy, lock screen, rollout, owner, OTA, power, and gate needs_human cases.",
            quality_checklist=["Previous version is preserved", "Approval rationale is clear", "No artefacts publish before approval"],
        ),
    ]


AGENTS = {agent.id: agent for agent in agent_definitions()}


class AgentExecutor:
    def __init__(self, client: ModelClient | None = None) -> None:
        self.client = client or ModelClient()

    @property
    def runtime_mode(self) -> dict[str, Any]:
        if self.client.enabled:
            return {"llm_enabled": True, "mode": "LLM mode: enabled", "model": LLM_MODEL, "workflow": "single-model multi-agent workflow"}
        return {"llm_enabled": False, "mode": "LLM mode: deterministic fallback", "model": None, "workflow": "deterministic multi-agent workflow"}

    def run(
        self,
        agent_id: str,
        workspace: ProductWorkspaceState,
        fallback: Callable[[ProductWorkspaceState], dict[str, Any]],
        extra_context: dict[str, Any] | None = None,
    ) -> tuple[ProductWorkspaceState, dict[str, Any]]:
        definition = AGENTS[agent_id]
        llm_patch: dict[str, Any] = {}
        if self.client.enabled:
            response = self.client.complete(
                definition.system_prompt,
                json.dumps({"state": workspace.model_dump(), "context": extra_context or {}}, ensure_ascii=False),
            )
            try:
                parsed = json.loads(response) if response else {}
                if isinstance(parsed, dict):
                    llm_patch = parsed
            except json.JSONDecodeError:
                llm_patch = {}

        patch = fallback(workspace)
        if llm_patch:
            patch.update({key: value for key, value in llm_patch.items() if key in ProductWorkspaceState.model_fields})

        updated = workspace.model_copy(update=patch)
        run_record = {
            "agent_id": agent_id,
            "agent_name": definition.name,
            "runtime": self.runtime_mode["mode"],
            "model": self.runtime_mode["model"],
            "used_llm": self.client.enabled and bool(llm_patch),
            "timestamp": now_iso(),
            "summary": f"{definition.name} updated canonical state.",
        }
        updated.agent_run_history.append(run_record)
        return updated, run_record

