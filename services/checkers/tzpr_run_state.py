from __future__ import annotations

from dataclasses import asdict
from typing import Any

from services.checkers.tzpr_constants import (
    FALLBACK_MODEL_NAME,
    PRO_MODEL_NAME,
    execution_mode_display_label as _execution_mode_display_label,
)
from services.checkers.tzpr_helpers import (
    build_artifact_preview as _build_artifact_preview,
    now_iso as _now_iso,
)
from services.checkers.tzpr_lifecycle import is_stalled_multi_agent_snapshot as is_stalled_multi_agent_run
from utils.database.checker_run_db import (
    append_checker_run_event,
    get_checker_run_snapshot,
    save_checker_run_final_result,
    update_checker_agent_record,
    update_checker_run_record,
)


class RunStateMixin:
    def _status_updater(self, *, emit_events: bool = True, update_run_state: bool = True):
        def update(level: str, message: str):
            if emit_events:
                self._event(level, "input_status", message)
            if update_run_state:
                self._set_run_state("running", status_message=message)

        return update

    def recover_stalled_run(self) -> dict[str, Any] | None:
        snapshot = get_checker_run_snapshot(self.run_id) or self.snapshot
        if not is_stalled_multi_agent_run(snapshot):
            return snapshot

        update_checker_run_record(
            self.run_id,
            active_phase="recovery",
            status_message=f"Stuck {_execution_mode_display_label(self.execution_mode).lower()} run recovery qilinmoqda",
        )
        self._event(
            "warning",
            "run_recovery_started",
            f"Stuck {_execution_mode_display_label(self.execution_mode).lower()} run recovery boshlandi",
            meta={
                "previous_phase": snapshot.get("active_phase"),
                "previous_run_state": snapshot.get("run_state"),
            },
        )

        try:
            context = self._collect_context(emit_events=False)
            if context.get("error_result"):
                error_result = context["error_result"]
                self._mark_run_finished(
                    error_result.run_state or "blocked",
                    asdict(error_result),
                    error_result.error_message,
                )
                return get_checker_run_snapshot(self.run_id)

            agent1, agent2, agent3 = self._recover_agents_from_snapshot(snapshot)
            self._event(
                "info",
                "run_finalizing",
                "Recovery: agent artefaktlari final resultga yig'ilmoqda",
                meta={
                    "requirements_total": len(agent1.get("requirements") or []),
                    "verifications_total": len(agent2.get("verifications") or []),
                    "requirements_result_total": len(agent3.get("requirements") or []),
                },
            )
            final_result = self._build_final_result(
                context=context,
                agent1=agent1,
                agent2=agent2,
                agent3=agent3,
            )
            final_state = str(agent3.get("run_state") or final_result.run_state or "manual_review")
            self._mark_run_finished(final_state, asdict(final_result), final_result.error_message)
            self._event(
                "warning",
                "run_recovery_finished",
                f"Stuck {_execution_mode_display_label(self.execution_mode).lower()} run recovery yakunlandi",
                meta={"run_state": final_state},
            )
            return get_checker_run_snapshot(self.run_id)
        except Exception as exc:
            self._handle_unexpected_run_failure(exc, context=None)
            return get_checker_run_snapshot(self.run_id)

    def _recover_agents_from_snapshot(
        self,
        snapshot: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        agent_map = {
            str(item.get("agent_key") or ""): item
            for item in list(snapshot.get("agent_runs") or [])
        }
        agent1_row = agent_map.get("agent1_scope_builder") or {}
        agent2_row = agent_map.get("agent2_verifier") or {}
        agent3_row = agent_map.get("agent3_arbiter") or {}

        agent1_artifact = dict(agent1_row.get("artifact") or {})
        agent1_requirements = list(agent1_artifact.get("requirements") or [])
        agent1 = {
            "success": str(agent1_row.get("state") or "").strip().lower() == "completed",
            "summary": str(agent1_artifact.get("summary") or "").strip(),
            "requirements": agent1_requirements,
            "effective_requirements": list(agent1_requirements),
            "warnings": list(agent1_row.get("warnings") or []),
        }

        agent2_artifact = dict(agent2_row.get("artifact") or {})
        agent2 = {
            "success": str(agent2_row.get("state") or "").strip().lower() == "completed",
            "summary": str(agent2_artifact.get("summary") or "").strip(),
            "verifications": list(agent2_artifact.get("verifications") or []),
            "extra": list(agent2_artifact.get("extra") or []),
            "warnings": list(agent2_row.get("warnings") or []),
        }

        agent3_artifact = dict(agent3_row.get("artifact") or {})
        agent3 = {
            "success": str(agent3_row.get("state") or "").strip().lower() == "completed",
            "summary": str(agent3_artifact.get("summary") or "").strip(),
            "run_state": str(agent3_artifact.get("run_state") or "manual_review").strip() or "manual_review",
            "verdict": str(agent3_artifact.get("verdict") or "manual_review").strip() or "manual_review",
            "verdict_label": str(agent3_artifact.get("verdict_label") or "Manual Review").strip() or "Manual Review",
            "verdict_reason": str(agent3_artifact.get("verdict_reason") or "Recovery mode finalization.").strip(),
            "quality_status": str(agent3_artifact.get("quality_status") or "ok").strip() or "ok",
            "total_requirements": int(agent3_artifact.get("total_requirements") or 0),
            "completed_count": int(agent3_artifact.get("completed_count") or 0),
            "failed_count": int(agent3_artifact.get("failed_count") or 0),
            "completed": list(agent3_artifact.get("completed") or []),
            "failed": list(agent3_artifact.get("failed") or []),
            "missing": list(agent3_artifact.get("missing") or []),
            "invalid": list(agent3_artifact.get("invalid") or []),
            "extra": list(agent3_artifact.get("extra") or []),
            "extra_code_risk": str(agent3_artifact.get("extra_code_risk") or "none").strip() or "none",
            "requirements": list(agent3_artifact.get("requirements") or []),
            "warnings": list(agent3_row.get("warnings") or []),
        }
        return agent1, agent2, agent3

    def _set_run_state(
        self,
        run_state: str,
        *,
        active_phase: str | None = None,
        status_message: str | None = None,
        started: bool = False,
    ) -> None:
        fields: dict[str, Any] = {"run_state": run_state}
        if active_phase is not None:
            fields["active_phase"] = active_phase
        if status_message is not None:
            fields["status_message"] = status_message
        if started:
            fields["started_at"] = _now_iso()
        update_checker_run_record(self.run_id, **fields)

    def _mark_run_finished(
        self,
        run_state: str,
        final_result: dict[str, Any] | None,
        error_message: str | None,
    ) -> None:
        snapshot = get_checker_run_snapshot(self.run_id) or {}
        if final_result:
            final_result["agent_runs"] = snapshot.get("agent_runs", [])
            final_result["run_events"] = snapshot.get("run_events", [])
        save_checker_run_final_result(
            self.run_id,
            run_state=run_state,
            final_result=final_result,
            error_message=error_message,
        )
        self._event(
            "info" if run_state == "completed" else "warning",
            "run_finished",
            f"Checker run {run_state} holatida yakunlandi",
            meta={"run_state": run_state},
        )

    def _start_agent(self, agent_key: str, message: str) -> None:
        self._set_run_state("running", active_phase=agent_key, status_message=message)
        self._set_agent_state(agent_key, "running", started_at=_now_iso(), attempts=1)
        self._event(
            "info",
            "agent_started",
            message,
            agent_key=agent_key,
            meta={"state": "running"},
        )

    def _finish_agent(
        self,
        agent_key: str,
        *,
        state: str,
        input_summary: str | None = None,
        output_summary: str | None = None,
        error_text: str | None = None,
        warnings: list[str] | None = None,
        artifact: dict[str, Any] | None = None,
    ) -> None:
        helper = getattr(self, "_agent_helpers", {}).get(agent_key)
        if helper is None:
            primary_model, fallback_model = (
                self._model_names_for_agent(agent_key)
                if hasattr(self, "_model_names_for_agent")
                else (PRO_MODEL_NAME, FALLBACK_MODEL_NAME)
            )
        else:
            primary_model = getattr(helper, "last_primary_model_name", PRO_MODEL_NAME)
            fallback_model = getattr(helper, "last_fallback_model_name", FALLBACK_MODEL_NAME)
        actual_model = getattr(helper, "last_model_used", primary_model) if helper else primary_model
        used_fallback = bool(getattr(helper, "last_used_fallback", False)) if helper else False
        self._set_agent_state(
            agent_key,
            state,
            input_summary=input_summary,
            output_summary=output_summary,
            error_text=error_text,
            warnings_json=warnings or [],
            artifact_json=artifact or {},
            actual_model=actual_model,
            primary_model=primary_model,
            fallback_model=fallback_model,
            used_fallback=used_fallback,
            finished_at=_now_iso(),
        )
        level = "error" if state in {"failed", "blocked"} else "info"
        message = output_summary or error_text or f"{agent_key} {state} holatiga o'tdi"
        self._event(
            level,
            "agent_finished",
            message,
            agent_key=agent_key,
            meta={
                "state": state,
                "input_summary": input_summary or "",
                "output_summary": output_summary or "",
                "error_text": error_text or "",
                "warnings": warnings or [],
                "actual_model": actual_model,
                "primary_model": primary_model,
                "fallback_model": fallback_model,
                "used_fallback": used_fallback,
                "artifact_preview": _build_artifact_preview(artifact or {}),
            },
        )

    def _set_agent_state(self, agent_key: str, state: str, **fields: Any) -> None:
        update_checker_agent_record(self.run_id, agent_key, state=state, **fields)

    def _skip_agent(self, agent_key: str, reason: str) -> None:
        self._set_agent_state(
            agent_key,
            "skipped",
            output_summary=reason,
            warnings_json=[],
            artifact_json={},
            finished_at=_now_iso(),
        )
        self._event(
            "info",
            "agent_finished",
            reason,
            agent_key=agent_key,
            meta={"state": "skipped"},
        )

    def _block_remaining_agents(self, reason: str) -> None:
        for agent_key in ("agent1_scope_builder", "agent2_verifier", "agent3_arbiter"):
            snapshot = get_checker_run_snapshot(self.run_id) or {}
            agent_row = next((item for item in snapshot.get("agent_runs", []) if item.get("agent_key") == agent_key), None)
            if agent_row and agent_row.get("state") == "pending":
                self._set_agent_state(agent_key, "blocked", error_text=reason, finished_at=_now_iso())

    def _event(
        self,
        level: str,
        event_type: str,
        message: str,
        *,
        agent_key: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        append_checker_run_event(
            run_id=self.run_id,
            level=level,
            event_type=event_type,
            message=message,
            agent_key=agent_key,
            meta=meta,
        )
