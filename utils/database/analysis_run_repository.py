"""
Generic analysis run repository — barcha modullar (testcase, checker, kelajakdagilar)
uchun run/agent/event holatini PostgreSQL da saqlaydi.

`module_key` bilan modul ajratiladi ("testcase_generator", "tz_pr_checker", ...).
Struktura ataylab checker_run_repository bilan bir xil — SQL logikasi umumiy
`run_repository_base` da, bu modul faqat analysis jadval konfiguratsiyasi bilan
yupqa wrapper (checker keyin shu generic jadvalga oson ko'chadi).
"""
from __future__ import annotations

from typing import Any

from utils.database.repository_common import execute as _execute
from utils.database.run_repository_base import (
    RunTablesConfig,
    append_run_event,
    build_run_snapshot,
    create_run,
    ensure_run_tables,
    get_agent_run,
    get_run,
    list_agent_runs,
    list_run_events,
    save_run_final_result,
    seed_agent_runs,
    update_agent_run,
    update_run,
)

ANALYSIS_RUN_TABLES = RunTablesConfig(
    runs_table="analysis_runs",
    agent_runs_table="analysis_agent_runs",
    events_table="analysis_run_events",
    index_prefix="analysis",
    has_module_key=True,
    failed_status_message="Run xato yoki block holatida tugadi",
)


def ensure_analysis_run_tables(conn) -> None:
    ensure_run_tables(conn, ANALYSIS_RUN_TABLES)


def create_analysis_run(
    conn,
    *,
    run_id: str,
    module_key: str,
    task_key: str,
    company_id: int | None,
    user_id: int | None,
    source: str,
    execution_mode: str,
    requested_output_profile: str,
    request_payload: dict[str, Any],
    commit: bool = True,
) -> dict[str, Any]:
    return create_run(
        conn,
        ANALYSIS_RUN_TABLES,
        run_id=run_id,
        module_key=module_key,
        task_key=task_key,
        company_id=company_id,
        user_id=user_id,
        source=source,
        execution_mode=execution_mode,
        requested_output_profile=requested_output_profile,
        request_payload=request_payload,
        commit=commit,
        execute=_execute,
    )


def seed_analysis_agent_runs(
    conn,
    *,
    run_id: str,
    agents: list[dict[str, Any]],
    commit: bool = True,
) -> None:
    seed_agent_runs(conn, ANALYSIS_RUN_TABLES, run_id=run_id, agents=agents, commit=commit, execute=_execute)


def update_analysis_run(conn, run_id: str, **fields: Any) -> dict[str, Any] | None:
    return update_run(conn, ANALYSIS_RUN_TABLES, run_id, execute=_execute, **fields)


def update_analysis_agent_run(
    conn,
    run_id: str,
    agent_key: str,
    **fields: Any,
) -> dict[str, Any] | None:
    return update_agent_run(conn, ANALYSIS_RUN_TABLES, run_id, agent_key, execute=_execute, **fields)


def append_analysis_run_event(
    conn,
    *,
    run_id: str,
    level: str,
    event_type: str,
    message: str,
    agent_key: str | None = None,
    meta: dict[str, Any] | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    return append_run_event(
        conn,
        ANALYSIS_RUN_TABLES,
        run_id=run_id,
        level=level,
        event_type=event_type,
        message=message,
        agent_key=agent_key,
        meta=meta,
        commit=commit,
        execute=_execute,
    )


def save_analysis_run_final_result(
    conn,
    run_id: str,
    *,
    run_state: str,
    final_result: dict[str, Any] | None,
    error_message: str | None = None,
) -> dict[str, Any] | None:
    return save_run_final_result(
        conn,
        ANALYSIS_RUN_TABLES,
        run_id,
        run_state=run_state,
        final_result=final_result,
        error_message=error_message,
        execute=_execute,
    )


def get_analysis_run(conn, run_id: str) -> dict[str, Any] | None:
    return get_run(conn, ANALYSIS_RUN_TABLES, run_id, execute=_execute)


def get_analysis_agent_run(conn, run_id: str, agent_key: str) -> dict[str, Any] | None:
    return get_agent_run(conn, ANALYSIS_RUN_TABLES, run_id, agent_key, execute=_execute)


def list_analysis_agent_runs(conn, run_id: str) -> list[dict[str, Any]]:
    return list_agent_runs(conn, ANALYSIS_RUN_TABLES, run_id, execute=_execute)


def list_analysis_run_events(conn, run_id: str) -> list[dict[str, Any]]:
    return list_run_events(conn, ANALYSIS_RUN_TABLES, run_id, execute=_execute)


def build_analysis_run_snapshot(conn, run_id: str) -> dict[str, Any] | None:
    return build_run_snapshot(conn, ANALYSIS_RUN_TABLES, run_id, execute=_execute)
