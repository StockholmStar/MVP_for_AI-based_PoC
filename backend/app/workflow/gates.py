from __future__ import annotations

from app.domain.workspace import GateResult, ProductWorkspaceState
from app.services.storage import now_iso


def gate_result(
    gate_id: str,
    status: str,
    failed_checks: list[str] | None = None,
    feedback: str = "",
    revision_target: str | None = None,
    attempt_count: int = 1,
) -> dict:
    checks = failed_checks or []
    result = GateResult(
        gate_id=gate_id,
        status=status,  # type: ignore[arg-type]
        score=max(0, 100 - 25 * len(checks)),
        severity="high" if status == "needs_human" else "medium" if checks else "low",
        failed_checks=checks,
        feedback=feedback,
        revision_target=revision_target,
        attempt_count=attempt_count,
        timestamp=now_iso(),
    )
    return result.model_dump()


def append_gate(workspace: ProductWorkspaceState, result: dict) -> ProductWorkspaceState:
    workspace.gate_results.append(result)
    return workspace


def latest_attempt(workspace: ProductWorkspaceState, gate_id: str) -> int:
    return 1 + sum(1 for result in workspace.gate_results if result.get("gate_id") == gate_id)

