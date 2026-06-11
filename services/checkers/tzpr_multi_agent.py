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
    return create_checker_run_record(
        run_id=run_id,
        task_key=task_key,
        company_id=company_id,
        user_id=user_id,
        source=source,
        execution_mode=EXECUTION_MODE_MULTI,
        requested_output_profile=output_profile,
        request_payload={
            "task_key": task_key,
            "output_profile": output_profile,
            "show_full_diff": show_full_diff,
            "use_smart_patch": use_smart_patch,
            "max_files": max_files,
            "execution_mode": EXECUTION_MODE_MULTI,
        },
        agents=agents,
    )


def execute_multi_agent_run(run_id: str) -> dict[str, Any] | None:
    snapshot = get_checker_run_snapshot(run_id)
    if not snapshot:
        raise RuntimeError(f"Checker run topilmadi: {run_id}")
    executor = _TZPRMultiAgentExecutor(snapshot)
    return executor.run()


def is_stalled_multi_agent_run(snapshot: dict[str, Any] | None) -> bool:
    return is_stalled_multi_agent_snapshot(snapshot)


def recover_stalled_multi_agent_run(run_id: str) -> dict[str, Any] | None:
    snapshot = get_checker_run_snapshot(run_id)
    if not is_stalled_multi_agent_run(snapshot):
        return snapshot
    executor = _TZPRMultiAgentExecutor(snapshot or {})
    return executor.recover_stalled_run()
