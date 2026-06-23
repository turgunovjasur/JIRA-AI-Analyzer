"""
High-level helpers for TZ-PR checker run storage.

UI va worker bir xil persisted run snapshot contract bilan ishlashi uchun
repository chaqiriqlarini connection lifecycle bilan o'raydi.
"""
from __future__ import annotations

from typing import Any

from core.logger import get_logger
from utils.database.runtime import connect_processing_db
from utils.database.checker_run_repository import (
    append_checker_run_event as repo_append_checker_run_event,
    build_checker_run_snapshot as repo_build_checker_run_snapshot,
    create_checker_run as repo_create_checker_run,
    save_checker_run_final_result as repo_save_checker_run_final_result,
    seed_checker_agent_runs as repo_seed_checker_agent_runs,
    update_checker_agent_run as repo_update_checker_agent_run,
    update_checker_run as repo_update_checker_run,
)
from utils.database.task_db import _get_db_settings  # type: ignore

log = get_logger("checker.run.db")


def _connect():
    # P2: jadvallar startup migratsiyasida ensure qilinadi — bu yerda DDL yo'q.
    settings = _get_db_settings()
    return connect_processing_db(timeout=settings.db_connection_timeout, row_factory=True)


def create_checker_run_record(
    *,
    run_id: str,
    task_key: str,
    company_id: int | None,
    user_id: int | None,
    source: str,
    execution_mode: str,
    requested_output_profile: str,
    request_payload: dict[str, Any],
    agents: list[dict[str, Any]],
) -> dict[str, Any]:
    conn = _connect()
    try:
        run = repo_create_checker_run(
            conn,
            run_id=run_id,
            task_key=task_key,
            company_id=company_id,
            user_id=user_id,
            source=source,
            execution_mode=execution_mode,
            requested_output_profile=requested_output_profile,
            request_payload=request_payload,
            commit=False,
        )
        repo_seed_checker_agent_runs(
            conn,
            run_id=run_id,
            agents=agents,
            commit=False,
        )
        repo_append_checker_run_event(
            conn,
            run_id=run_id,
            level="info",
            event_type="run_created",
            message="Checker run yaratildi",
            meta={"execution_mode": execution_mode, "source": source},
            commit=False,
        )
        conn.commit()
        return repo_build_checker_run_snapshot(conn, run_id) or run
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_checker_run_record(run_id: str, **fields: Any) -> dict[str, Any] | None:
    conn = _connect()
    try:
        return repo_update_checker_run(conn, run_id, **fields)
    finally:
        conn.close()


def update_checker_agent_record(run_id: str, agent_key: str, **fields: Any) -> dict[str, Any] | None:
    conn = _connect()
    try:
        return repo_update_checker_agent_run(conn, run_id, agent_key, **fields)
    finally:
        conn.close()


def append_checker_run_event(
    *,
    run_id: str,
    level: str,
    event_type: str,
    message: str,
    agent_key: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    conn = _connect()
    try:
        return repo_append_checker_run_event(
            conn,
            run_id=run_id,
            level=level,
            event_type=event_type,
            message=message,
            agent_key=agent_key,
            meta=meta,
        )
    finally:
        conn.close()


def save_checker_run_final_result(
    run_id: str,
    *,
    run_state: str,
    final_result: dict[str, Any] | None,
    error_message: str | None = None,
) -> dict[str, Any] | None:
    conn = _connect()
    try:
        return repo_save_checker_run_final_result(
            conn,
            run_id,
            run_state=run_state,
            final_result=final_result,
            error_message=error_message,
        )
    finally:
        conn.close()


def get_checker_run_snapshot(run_id: str) -> dict[str, Any] | None:
    conn = _connect()
    try:
        return repo_build_checker_run_snapshot(conn, run_id)
    finally:
        conn.close()
