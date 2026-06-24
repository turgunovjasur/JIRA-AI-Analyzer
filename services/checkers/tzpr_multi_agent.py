"""Public facade for the run-based multi-agent TZ-PR checker."""
from __future__ import annotations

import uuid
from typing import Any

from services.checkers.tzpr_constants import (
    AGENT_SEQUENCE,
    EXECUTION_MODE_MULTI,
    build_agent_sequence,
)
from services.checkers.tzpr_lifecycle import is_stalled_multi_agent_snapshot
from services.checkers.tzpr_orchestrator import _TZPRMultiAgentExecutor
from utils.database.checker_run_db import (
    create_checker_run_record,
    get_checker_run_snapshot,
)


def create_multi_agent_run(
    *,
    task_key: str,
    company_id: int | None,
    user_id: int | None,
    source: str,
    output_profile: str,
    show_full_diff: bool,
    use_smart_patch: bool | None,
    max_files: int | None,
    task_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_id = f"tzpr-{uuid.uuid4().hex}"
    agents = AGENT_SEQUENCE
    try:
        from config.app_settings import get_app_settings, get_app_settings_for_company, get_app_settings_for_user

        if user_id is not None and company_id is not None:
            checker_settings = get_app_settings_for_user(user_id, company_id).tz_pr_checker
        elif company_id is not None:
            checker_settings = get_app_settings_for_company(company_id).webhook_tz_pr
        else:
            checker_settings = get_app_settings().tz_pr_checker
        agents = build_agent_sequence(checker_settings)
    except Exception:
        agents = AGENT_SEQUENCE
    request_payload = {
        "task_key": task_key,
        "output_profile": output_profile,
        "show_full_diff": show_full_diff,
        "use_smart_patch": use_smart_patch,
        "max_files": max_files,
        "execution_mode": EXECUTION_MODE_MULTI,
    }
    if isinstance(task_details, dict) and task_details:
        request_payload["task_details"] = task_details

    return create_checker_run_record(
        run_id=run_id,
        task_key=task_key,
        company_id=company_id,
        user_id=user_id,
        source=source,
        execution_mode=EXECUTION_MODE_MULTI,
        requested_output_profile=output_profile,
        request_payload=request_payload,
        agents=agents,
    )


def execute_multi_agent_run(run_id: str, *, increment_quota: bool = False) -> dict[str, Any] | None:
    snapshot = get_checker_run_snapshot(run_id)
    if not snapshot:
        raise RuntimeError(f"Checker run topilmadi: {run_id}")
    executor = _TZPRMultiAgentExecutor(snapshot)
    result = executor.run()
    if increment_quota and (result or {}).get("run_state") == "completed":
        company_id = snapshot.get("company_id")
        if company_id is not None:
            try:
                from utils.database.quota_db import increment_global_quota
                import logging as _log
                q = increment_global_quota(int(company_id), "tz_pr_checker")
                _log.getLogger(__name__).info("quota incremented [tz_pr_checker] company=%s remaining=%s", company_id, q.get("remaining"))
            except Exception:
                import logging as _log
                _log.getLogger(__name__).warning("increment_global_quota failed silently [tz_pr_checker]")
    return result


def run_multi_agent_for_webhook(run_id: str):
    """Run'ni bajaradi va JONLI `TZPRAnalysisResult` obyektini qaytaradi.

    UI yo'li (`execute_multi_agent_run`) snapshot dict qaytaradi — uni brauzer
    o'qiydi. Webhook esa natijani JIRA comment formatter'iga (ichki dataclass'lar
    bilan) uzatadi, shuning uchun asdict dict emas, jonli obyekt kerak.
    Engine bir xil — faqat qaytariladigan ko'rinish farq qiladi.
    """
    snapshot = get_checker_run_snapshot(run_id)
    if not snapshot:
        raise RuntimeError(f"Checker run topilmadi: {run_id}")
    executor = _TZPRMultiAgentExecutor(snapshot)
    executor.run()
    return executor.final_result_obj


def is_stalled_multi_agent_run(snapshot: dict[str, Any] | None) -> bool:
    return is_stalled_multi_agent_snapshot(snapshot)


def recover_stalled_multi_agent_run(run_id: str) -> dict[str, Any] | None:
    snapshot = get_checker_run_snapshot(run_id)
    if not is_stalled_multi_agent_run(snapshot):
        return snapshot
    executor = _TZPRMultiAgentExecutor(snapshot or {})
    return executor.recover_stalled_run()
