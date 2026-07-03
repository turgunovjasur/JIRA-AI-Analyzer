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

# Seed qilinadigan agentlar (testcase: talab ajratuvchi + test case yozuvchi + auditor).
_AGENTS = [
    {
        "agent_key": "agent1_requirements",
        "agent_label": "Agent1 — Talablar",
        "agent_order": 1,
        "primary_model": "",
        "fallback_model": "",
        "state": "pending",
    },
    {
        "agent_key": "agent2_testcase",
        "agent_label": "Agent2 — Test case",
        "agent_order": 2,
        "primary_model": "",
        "fallback_model": "",
        "state": "pending",
    },
    {
        "agent_key": "agent3_audit",
        "agent_label": "Agent3 — Audit",
        "agent_order": 3,
        "primary_model": "",
        "fallback_model": "",
        "state": "pending",
    },
]

_AGENT_INPUT_SUMMARIES = {
    "agent1_requirements": "Real JIRA TZ va Figma talab-nomzodlari asosida talablar ajratiladi.",
    "agent2_testcase": "Agent1 ajratgan talablar, real TZ va user qo'shimcha buyrug'i asosida testcase yoziladi.",
    "agent3_audit": "Agent2 yozgan testcase'lar duplicate, expected result va scenario grouping bo'yicha tekshiriladi.",
}

_AGENT_MODEL_FIELDS = {
    "agent1_requirements": ("agent1_primary_model", "agent1_fallback_model"),
    "agent2_testcase": ("agent2_primary_model", "agent2_fallback_model"),
    "agent3_audit": ("agent3_primary_model", "agent3_fallback_model"),
}


def _resolve_agent_model_names(settings: Any, agent_key: str) -> tuple[str, str]:
    primary_field, fallback_field = _AGENT_MODEL_FIELDS.get(agent_key, ("", ""))
    primary = str(getattr(settings, primary_field, "") or "").strip()
    fallback = str(getattr(settings, fallback_field, "") or "").strip()
    return primary, fallback


def _build_testcase_agent_sequence(settings: Any | None = None) -> list[dict[str, Any]]:
    agents = []
    for item in _AGENTS:
        agent = dict(item)
        if settings is not None:
            primary, fallback = _resolve_agent_model_names(settings, str(agent.get("agent_key") or ""))
            agent["primary_model"] = primary
            agent["fallback_model"] = fallback
        agents.append(agent)
    return agents


def _resolve_testcase_settings(company_id: int | None, user_id: int | None):
    from config.app_settings import get_app_settings, get_app_settings_for_company, get_app_settings_for_user

    if user_id is not None and company_id is not None:
        return get_app_settings_for_user(user_id, company_id).testcase_generator
    if company_id is not None:
        return get_app_settings_for_company(company_id).webhook_testcase
    return get_app_settings().testcase_generator


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
    agents = _AGENTS
    try:
        agents = _build_testcase_agent_sequence(_resolve_testcase_settings(company_id, user_id))
    except Exception:
        agents = _AGENTS
    prompt_versions: dict[str, str] = {}
    try:
        from core.prompt_registry import get_prompt_versions_for

        prompt_versions = get_prompt_versions_for("testcase")
    except Exception:
        pass
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
            "prompt_versions": prompt_versions,
        },
        agents=agents,
    )


def execute_testcase_run(run_id: str, *, increment_quota: bool = False) -> dict[str, Any] | None:
    """Yaratilgan run'ni boshqaradi (sinxron). Yakuniy snapshot qaytaradi."""
    snapshot = get_analysis_run_snapshot(run_id)
    if not snapshot:
        raise RuntimeError(f"Testcase run topilmadi: {run_id}")
    return _TestcaseRunExecutor(snapshot, increment_quota=increment_quota).run()


def run_testcase_for_webhook(run_id: str):
    """Run'ni bajaradi va JONLI `TestCaseGenerationResult` obyektini qaytaradi.

    UI yo'li (`execute_testcase_run`) snapshot dict qaytaradi (brauzer o'qiydi).
    Webhook esa natijani JIRA comment formatter'iga uzatadi — engine bir xil,
    faqat qaytariladigan ko'rinish farq qiladi.
    """
    snapshot = get_analysis_run_snapshot(run_id)
    if not snapshot:
        raise RuntimeError(f"Testcase run topilmadi: {run_id}")
    executor = _TestcaseRunExecutor(snapshot)
    executor.run()
    return executor.final_result_obj


class _TestcaseRunExecutor:
    def __init__(self, snapshot: dict[str, Any], *, increment_quota: bool = False):
        self.run_id = snapshot["run_id"]
        self.payload = snapshot.get("request_payload") or {}
        self.company_id = snapshot.get("company_id")
        self.user_id = snapshot.get("user_id")
        self.task_key = snapshot.get("task_key")
        self._increment_quota = increment_quota
        self._agent1_started = False
        self._agent2_started = False
        self._agent3_started = False
        self._agent_events: dict[str, list[dict[str, str]]] = {item["agent_key"]: [] for item in _AGENTS}
        # Webhook yetkazib berish qatlami uchun jonli natija obyekti (asdict EMAS).
        self.final_result_obj: Any | None = None

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

        # Webhook yetkazib berish qatlami jonli result obyektini oladi (success/fail farqsiz).
        self.final_result_obj = result

        if not getattr(result, "success", False):
            self._fail_active_agent(getattr(result, "error_message", "") or "")
            return self._finish(
                run_state="error",
                final_result=_result_to_dict(result),
                error_message=getattr(result, "error_message", "") or "Testcase yaratilmadi",
            )

        # Muvaffaqiyat: barcha agentlar tugadi, cardlarda ko'rinadigan summary/metrics yoziladi.
        final_result = _result_to_dict(result)
        self._finish_success_agents(final_result)
        return self._finish(run_state="completed", final_result=final_result, error_message=None)

    def _on_status(self, status_type: str, message: str) -> None:
        """generate_test_cases status_callback → event + agent holati.

        Agent chegaralari testcase_generator progress matnlaridan aniqlanadi
        ("(Agent1)" / "(Agent2)" / "(Agent3)") — matnlar o'zgarsa shu yer yangilanadi.
        """
        msg = str(message or "")
        level = "warning" if str(status_type).lower() == "warning" else "info"
        agent_key = self._agent_key_for_message(msg)
        append_analysis_run_event(
            run_id=self.run_id,
            level=level,
            event_type="progress",
            message=msg[:500],
            agent_key=agent_key,
            meta={"status_type": str(status_type or "progress")},
        )
        try:
            if agent_key == "agent1_requirements" and not self._agent1_started:
                self._agent1_started = True
                update_analysis_run_record(self.run_id, active_phase="agent1_requirements", status_message=msg[:300])
                self._start_agent("agent1_requirements", msg)
            elif agent_key == "agent2_testcase" and not self._agent2_started:
                self._agent2_started = True
                self._complete_agent_step("agent1_requirements", "Talablar ajratildi, Agent2 ga uzatildi.")
                update_analysis_run_record(self.run_id, active_phase="agent2_testcase", status_message=msg[:300])
                self._start_agent("agent2_testcase", msg)
            elif agent_key == "agent3_audit" and not self._agent3_started:
                self._agent3_started = True
                self._complete_agent_step("agent2_testcase", "Testcase'lar yozildi va backend validationdan o'tkazildi.")
                update_analysis_run_record(self.run_id, active_phase="agent3_audit", status_message=msg[:300])
                self._start_agent("agent3_audit", msg)
            else:
                update_analysis_run_record(self.run_id, status_message=msg[:300])
                if agent_key:
                    self._update_agent_progress(agent_key, msg)
        except Exception as exc:  # progress yangilanishi run'ni yiqitmasin
            log.warning(f"[{self.run_id}] progress update xatosi: {exc}")

    @staticmethod
    def _agent_key_for_message(message: str) -> str | None:
        text = str(message or "").casefold()
        if "agent1" in text:
            return "agent1_requirements"
        if "agent2" in text:
            return "agent2_testcase"
        if "agent3" in text:
            return "agent3_audit"
        return None

    def _remember_agent_event(self, agent_key: str, message: str) -> list[dict[str, str]]:
        events = self._agent_events.setdefault(agent_key, [])
        events.append({"at": _now(), "message": str(message or "")[:300]})
        del events[:-6]
        return list(events)

    def _start_agent(self, agent_key: str, message: str) -> None:
        activity = self._remember_agent_event(agent_key, message)
        update_analysis_agent_record(
            self.run_id,
            agent_key,
            state="running",
            started_at=_now(),
            attempts=1,
            input_summary=_AGENT_INPUT_SUMMARIES.get(agent_key, "Agent bosqichi boshlandi."),
            output_summary=str(message or "")[:500],
            artifact_json={"activity": activity, "metrics": {"event_count": len(activity)}},
        )

    def _update_agent_progress(self, agent_key: str, message: str) -> None:
        activity = self._remember_agent_event(agent_key, message)
        update_analysis_agent_record(
            self.run_id,
            agent_key,
            output_summary=str(message or "")[:500],
            artifact_json={"activity": activity, "metrics": {"event_count": len(activity)}},
        )

    def _complete_agent_step(self, agent_key: str, message: str) -> None:
        activity = self._remember_agent_event(agent_key, message)
        update_analysis_agent_record(
            self.run_id,
            agent_key,
            state="completed",
            output_summary=message[:500],
            artifact_json={"activity": activity, "metrics": {"event_count": len(activity)}},
            finished_at=_now(),
        )

    def _finish_success_agents(self, final_result: dict[str, Any]) -> None:
        requirements = list(final_result.get("requirements") or [])
        test_cases = list(final_result.get("test_cases") or [])
        coverage = dict(final_result.get("requirement_coverage") or {})
        scenarios = list(final_result.get("test_scenarios") or [])
        audit_findings = list(final_result.get("audit_findings") or [])
        warnings = [str(item) for item in (final_result.get("warnings") or []) if str(item).strip()]
        ai_model = str(final_result.get("ai_model") or "").strip()

        uncovered = list(coverage.get("uncovered_ids") or [])
        covered_count = int(coverage.get("covered_count") or 0)
        total_requirements = int(coverage.get("total_requirements") or len(requirements))
        repair_count = len([item for item in warnings if "repair" in item.casefold()])

        agent2_warnings = [
            item for item in warnings
            if any(token in item.casefold() for token in ("agent2", "qoplanmagan", "targetdan kam", "yaroqsiz", "ortiqcha"))
        ]
        agent3_warnings = [
            item for item in warnings
            if any(token in item.casefold() for token in ("agent3", "grouping", "scenario", "audit"))
        ]

        update_analysis_agent_record(
            self.run_id,
            "agent1_requirements",
            state="completed",
            actual_model=ai_model,
            primary_model=ai_model,
            input_summary=_AGENT_INPUT_SUMMARIES["agent1_requirements"],
            output_summary=f"{len(requirements)} ta talab ajratildi.",
            artifact_json={
                "activity": self._agent_events.get("agent1_requirements", []),
                "metrics": {"requirement_count": len(requirements)},
                "requirements_preview": requirements[:8],
            },
            finished_at=_now(),
        )
        update_analysis_agent_record(
            self.run_id,
            "agent2_testcase",
            state="completed",
            actual_model=ai_model,
            primary_model=ai_model,
            input_summary=_AGENT_INPUT_SUMMARIES["agent2_testcase"],
            output_summary=(
                f"{len(test_cases)} ta testcase yaratildi. "
                f"Coverage: {covered_count}/{total_requirements} talab."
                + (f" Qoplanmagan: {', '.join(uncovered)}." if uncovered else "")
            ),
            warnings_json=agent2_warnings,
            artifact_json={
                "activity": self._agent_events.get("agent2_testcase", []),
                "metrics": {
                    "requirement_count": total_requirements,
                    "test_case_count": len(test_cases),
                    "covered_requirement_count": covered_count,
                    "missing_requirement_count": len(uncovered),
                    "repair_count": repair_count,
                },
                "coverage": coverage,
                "testcase_preview": [
                    {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "test_type": item.get("test_type"),
                        "requirement_ids": item.get("requirement_ids"),
                    }
                    for item in test_cases[:8]
                    if isinstance(item, dict)
                ],
            },
            finished_at=_now(),
        )
        update_analysis_agent_record(
            self.run_id,
            "agent3_audit",
            state="completed",
            actual_model=ai_model,
            primary_model=ai_model,
            input_summary=_AGENT_INPUT_SUMMARIES["agent3_audit"],
            output_summary=(
                f"{len(scenarios)} ta scenario shakllantirildi, "
                f"{len(audit_findings)} ta audit finding qaytdi."
            ),
            warnings_json=agent3_warnings,
            artifact_json={
                "activity": self._agent_events.get("agent3_audit", []),
                "metrics": {
                    "scenario_count": len(scenarios),
                    "audit_finding_count": len(audit_findings),
                    "test_case_count": len(test_cases),
                },
                "scenario_preview": [
                    {
                        "scenario_title": item.get("scenario_title"),
                        "screen_or_flow": item.get("screen_or_flow"),
                        "requirement_ids": item.get("requirement_ids"),
                        "test_case_count": len(item.get("test_cases") or []),
                    }
                    for item in scenarios[:8]
                    if isinstance(item, dict)
                ],
                "audit_findings_preview": audit_findings[:8],
            },
            finished_at=_now(),
        )

    def _fail_active_agent(self, error_text: str) -> None:
        agent_key = (
            "agent3_audit"
            if self._agent3_started
            else "agent2_testcase" if self._agent2_started else "agent1_requirements"
        )
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
        if run_state == "completed" and self._increment_quota and self.company_id is not None:
            try:
                from utils.database.quota_db import increment_global_quota
                result = increment_global_quota(int(self.company_id), MODULE_KEY)
                log.info("quota incremented [%s] company=%s remaining=%s", MODULE_KEY, self.company_id, result.get("remaining"))
            except Exception:
                log.warning("increment_global_quota failed silently [%s]", MODULE_KEY)
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
