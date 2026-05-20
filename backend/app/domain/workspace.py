from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


GateStatus = Literal["pass", "fail", "needs_human", "skipped"]


class ProductWorkspaceState(BaseModel):
    project_id: str
    version: str = "draft"
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_brief: str = ""
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    user_segments: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    surfaces: list[str] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    device_states: list[str] = Field(default_factory=list)
    functional_requirements: list[dict[str, Any]] = Field(default_factory=list)
    ux_states: list[dict[str, Any]] = Field(default_factory=list)
    flows: list[dict[str, Any]] = Field(default_factory=list)
    prototype_screens: list[dict[str, Any]] = Field(default_factory=list)
    qa_criteria: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    owner_boundaries: list[dict[str, str]] = Field(default_factory=list)
    trace_links: list[dict[str, str]] = Field(default_factory=list)
    gate_results: list[dict[str, Any]] = Field(default_factory=list)
    human_approvals: list[dict[str, Any]] = Field(default_factory=list)
    agent_run_history: list[dict[str, Any]] = Field(default_factory=list)

    def public_summary(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "metadata": self.metadata,
            "source_brief": self.source_brief,
            "requirements": len(self.functional_requirements),
            "ux_states": len(self.ux_states),
            "prototype_screens": len(self.prototype_screens),
            "qa_criteria": len(self.qa_criteria),
            "gate_results": self.gate_results,
            "agent_run_history": self.agent_run_history,
            "human_approvals": self.human_approvals,
        }


class AgentDefinition(BaseModel):
    id: str
    name: str
    role: str
    input_contract: str
    output_contract: str
    system_prompt: str
    deterministic_fallback_policy: str
    model_config_ref: str = "default_openai_compatible_model"
    quality_checklist: list[str]


class GateResult(BaseModel):
    gate_id: str
    status: GateStatus
    score: int = 100
    severity: str = "low"
    failed_checks: list[str] = Field(default_factory=list)
    feedback: str = ""
    revision_target: str | None = None
    attempt_count: int = 1
    timestamp: str

