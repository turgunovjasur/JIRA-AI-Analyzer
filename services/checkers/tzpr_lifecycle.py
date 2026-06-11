from __future__ import annotations

from typing import Any

from services.checkers.tzpr_constants import (
    RUN_BASED_EXECUTION_MODES,
    normalize_execution_mode,
)


def is_stalled_multi_agent_snapshot(snapshot: dict[str, Any] | None) -> bool:
    if not snapshot:
        return False
    execution_mode = normalize_execution_mode(snapshot.get("execution_mode"))
    if execution_mode not in RUN_BASED_EXECUTION_MODES:
        return False
    run_state = str(snapshot.get("run_state") or "").strip().lower()
    if run_state not in {"running", "failed"}:
        return False
    if snapshot.get("final_result"):
        return False
    if str(snapshot.get("active_phase") or "").strip().lower() == "recovery":
        return False
    if run_state == "running" and snapshot.get("finished_at"):
        return False
    if run_state == "failed":
        error_message = str(snapshot.get("error_message") or "").strip().lower()
        if "json serializable" not in error_message:
            return False

    agent_runs = list(snapshot.get("agent_runs") or [])
    if len(agent_runs) < 3:
        return False
    terminal_states = {"completed", "failed", "blocked", "skipped"}
    if not all(str(item.get("state") or "").strip().lower() in terminal_states for item in agent_runs):
        return False

    events = list(snapshot.get("run_events") or [])
    if any(str(item.get("event_type") or "").strip() == "run_finished" for item in events):
        return False

    agent3 = next((item for item in agent_runs if item.get("agent_key") == "agent3_arbiter"), None) or {}
    artifact = agent3.get("artifact") or {}
    return bool((artifact.get("requirements") or []) and artifact.get("run_state"))
