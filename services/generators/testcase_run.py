"""
Testcase (Servis-2) run driver — run/state/progress lifecycle.

Naqsh checker'nikiga mos (`services/checkers/tzpr_multi_agent.py`):
- create_testcase_run(): run yaratadi (queued holat) → snapshot qaytaradi.
- execute_testcase_run(): run'ni boshqaradi (running → completed/error), progress
  event'larini yozadi. SINXRON — fonda ishlatish API qatlamida (keyingi bosqich).

DB qatlami: generic `utils.database.analysis_run_db` (module_key="testcase_generator").
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Optional

from core.logger import get_logger
from utils.database.analysis_run_db import (
    append_analysis_run_event,
    create_analysis_run_record,
    get_analysis_run_snapshot,
    save_analysis_run_final_result,
    update_analysis_agent_record,
    update_analysis_run_record,
)

log = get_logger("testcase.run")

MODULE_KEY = "testcase_generator"
EXECUTION_MODE = "multi_agent"

# Seed qilinadigan agentlar (testcase 2-agentli: talab ajratuvchi + test case yozuvchi).
_AGENTS = [
    {"agent_key": "agent1_requirements", "agent_label": "Agent1 — Talablar", "agent_order": 1, "state": "pending"},
    {"agent_key": "agent2_testcase", "agent_label": "Agent2 — Test case", "agent_order": 2, "state": "pending"},
]


def _now() -> str:
    return datetime.now().isoformat()


def create_testcase_run(
    *,
    task_key: str,
    company_id: int | None,
    user_id: int | None,
    source: str = "manual",
    test_types: Optional[list] = None,
    custom_context: str = "",
    output_profile: str = "ui",
) -> dict[str, Any]:
    """Testcase run yaratadi (queued). Snapshot qaytaradi (run_id ichida)."""
    run_id = f"tc-{uuid.uuid4().hex}"
    return create_analysis_run_record(
        run_id=run_id,
        module_key=MODULE_KEY,
        task_key=task_key,
        company_id=company_id,
        user_id=user_id,
        source=source,
        execution_mode=EXECUTION_MODE,
        requested_output_profile=output_profile,
        request_payload={
            "task_key": task_key,
            "test_types": list(test_types or []),
            "custom_context": custom_context or "",
            "execution_mode": EXECUTION_MODE,
        },
        agents=_AGENTS,
    )


def execute_testcase_run(run_id: str) -> dict[str, Any] | None:
    """Yaratilgan run'ni boshqaradi (sinxron). Yakuniy snapshot qaytaradi."""
    snapshot = get_analysis_run_snapshot(run_id)
    if not snapshot:
        raise RuntimeError(f"Testcase run topilmadi: {run_id}")
    return _TestcaseRunExecutor(snapshot).run()


class _TestcaseRunExecutor:
    def __init__(self, snapshot: dict[str, Any]):
        self.run_id = snapshot["run_id"]
        self.payload = snapshot.get("request_payload") or {}
        self.company_id = snapshot.get("company_id")
        self.user_id = snapshot.get("user_id")
        self.task_key = snapshot.get("task_key")
        self._agent1_started = False
        self._agent2_started = False

    def run(self) -> dict[str, Any] | None:
        update_analysis_run_record(
            self.run_id,
            run_state="running",
            active_phase="agent1_requirements",
            status_message="Boshlandi",
            started_at=_now(),
        )
        append_analysis_run_event(
            run_id=self.run_id, level="info", event_type="run_started",
            message="Testcase run boshlandi",
        )

        try:
            from services.generators.testcase_generator import TestCaseGeneratorService

            service = TestCaseGeneratorService(company_id=self.company_id, user_id=self.user_id)
            result = service.generate_test_cases(
                task_key=self.task_key,
                test_types=(self.payload.get("test_types") or None),
                custom_context=(self.payload.get("custom_context") or ""),
                status_callback=self._on_status,
            )
        except Exception as exc:
            log.log_error(self.task_key or "?", "testcase_run", str(exc))
            return self._finish(run_state="error", final_result=None, error_message=f"Kutilmagan xatolik: {exc}")

        if not getattr(result, "success", False):
            self._fail_active_agent(getattr(result, "error_message", "") or "")
            return self._finish(
                run_state="error",
                final_result=_result_to_dict(result),
                error_message=getattr(result, "error_message", "") or "Testcase yaratilmadi",
            )

        # Muvaffaqiyat: ikkala agent ham tugadi
        for agent_key in ("agent1_requirements", "agent2_testcase"):
            update_analysis_agent_record(self.run_id, agent_key, state="completed", finished_at=_now())
        return self._finish(run_state="completed", final_result=_result_to_dict(result), error_message=None)

    def _on_status(self, status_type: str, message: str) -> None:
        """generate_test_cases status_callback → event + agent holati.

        Agent chegaralari testcase_generator progress matnlaridan aniqlanadi
        ("(Agent1)" / "(Agent2)") — matnlar o'zgarsa shu yer yangilanadi.
        """
        msg = str(message or "")
        level = "warning" if str(status_type).lower() == "warning" else "info"
        append_analysis_run_event(run_id=self.run_id, level=level, event_type="progress", message=msg[:500])
        try:
            if "(Agent1)" in msg and not self._agent1_started:
                self._agent1_started = True
                update_analysis_run_record(self.run_id, active_phase="agent1_requirements", status_message=msg[:300])
                update_analysis_agent_record(self.run_id, "agent1_requirements", state="running", started_at=_now())
            elif "(Agent2)" in msg and not self._agent2_started:
                self._agent2_started = True
                update_analysis_agent_record(self.run_id, "agent1_requirements", state="completed", finished_at=_now())
                update_analysis_run_record(self.run_id, active_phase="agent2_testcase", status_message=msg[:300])
                update_analysis_agent_record(self.run_id, "agent2_testcase", state="running", started_at=_now())
            else:
                update_analysis_run_record(self.run_id, status_message=msg[:300])
        except Exception as exc:  # progress yangilanishi run'ni yiqitmasin
            log.warning(f"[{self.run_id}] progress update xatosi: {exc}")

    def _fail_active_agent(self, error_text: str) -> None:
        agent_key = "agent2_testcase" if self._agent2_started else "agent1_requirements"
        try:
            update_analysis_agent_record(
                self.run_id, agent_key, state="failed", error_text=(error_text or "")[:1000], finished_at=_now()
            )
        except Exception:
            pass

    def _finish(self, *, run_state: str, final_result: dict | None, error_message: str | None) -> dict[str, Any] | None:
        append_analysis_run_event(
            run_id=self.run_id,
            level=("info" if run_state == "completed" else "error"),
            event_type="run_finished",
            message=("Testcase run yakunlandi" if run_state == "completed" else f"Run xato: {error_message or ''}"[:500]),
        )
        return save_analysis_run_final_result(
            self.run_id, run_state=run_state, final_result=final_result, error_message=error_message
        )


def _result_to_dict(result: Any) -> dict[str, Any]:
    """TestCaseGenerationResult (dataclass) → JSON-saqlanadigan dict."""
    if is_dataclass(result):
        return asdict(result)
    if isinstance(result, dict):
        return result
    return {"success": bool(getattr(result, "success", False))}
