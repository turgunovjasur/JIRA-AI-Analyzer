"""
TZ-PR checker run repository helpers.

Multi-agent checker UI uchun run, agent va event holatlarini PostgreSQLda
saqlaydi. SQL logikasi `run_repository_base` da — bu modul faqat checker
jadval konfiguratsiyasi bilan yupqa wrapper.
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

CHECKER_RUN_TABLES = RunTablesConfig(
    runs_table="checker_runs",
    agent_runs_table="checker_agent_runs",
    events_table="checker_run_events",
    index_prefix="checker",
    has_module_key=False,
    failed_status_message="Run manual review yoki block holatida tugadi",
)


def ensure_checker_run_tables(conn) -> None:
    ensure_run_tables(conn, CHECKER_RUN_TABLES)


def create_checker_run(
    conn,
    *,
    run_id: str,
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
        CHECKER_RUN_TABLES,
        run_id=run_id,
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


def seed_checker_agent_runs(
    conn,
    *,
    run_id: str,
    agents: list[dict[str, Any]],
    commit: bool = True,
) -> None:
    seed_agent_runs(conn, CHECKER_RUN_TABLES, run_id=run_id, agents=agents, commit=commit, execute=_execute)


def update_checker_run(conn, run_id: str, **fields: Any) -> dict[str, Any] | None:
    return update_run(conn, CHECKER_RUN_TABLES, run_id, execute=_execute, **fields)


def update_checker_agent_run(
    conn,
    run_id: str,
    agent_key: str,
    **fields: Any,
) -> dict[str, Any] | None:
    return update_agent_run(conn, CHECKER_RUN_TABLES, run_id, agent_key, execute=_execute, **fields)


def append_checker_run_event(
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
        CHECKER_RUN_TABLES,
        run_id=run_id,
        level=level,
        event_type=event_type,
        message=message,
        agent_key=agent_key,
        meta=meta,
        commit=commit,
        execute=_execute,
    )


def save_checker_run_final_result(
    conn,
    run_id: str,
    *,
    run_state: str,
    final_result: dict[str, Any] | None,
    error_message: str | None = None,
) -> dict[str, Any] | None:
    return save_run_final_result(
        conn,
        CHECKER_RUN_TABLES,
        run_id,
        run_state=run_state,
        final_result=final_result,
        error_message=error_message,
        execute=_execute,
    )


def get_checker_run(conn, run_id: str) -> dict[str, Any] | None:
    return get_run(conn, CHECKER_RUN_TABLES, run_id, execute=_execute)


def get_checker_agent_run(conn, run_id: str, agent_key: str) -> dict[str, Any] | None:
    return get_agent_run(conn, CHECKER_RUN_TABLES, run_id, agent_key, execute=_execute)


def list_checker_agent_runs(conn, run_id: str) -> list[dict[str, Any]]:
    return list_agent_runs(conn, CHECKER_RUN_TABLES, run_id, execute=_execute)


def list_checker_run_events(conn, run_id: str) -> list[dict[str, Any]]:
    return list_run_events(conn, CHECKER_RUN_TABLES, run_id, execute=_execute)


def build_checker_run_snapshot(conn, run_id: str) -> dict[str, Any] | None:
    return build_run_snapshot(conn, CHECKER_RUN_TABLES, run_id, execute=_execute)
