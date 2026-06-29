"""
Internal monitoring API endpoints.

These endpoints are primarily intended to help split the current Streamlit UI
from backend persistence without changing business logic.
"""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd
from fastapi import APIRouter, Header, HTTPException, Query

from services.api.session_scope import load_api_session, require_company_scope
from utils.database.monitoring_repository import (
    get_blocked_tasks_df,
    get_errors_log_df,
    get_overall_stats_df,
    get_recent_tasks_df,
    get_service_status_counts_df,
    get_task_for_delete_check,
    get_task_status_counts_df,
    task_exists,
)
from utils.database.runtime import (
    connect_processing_db,
    get_db_backend,
)

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


def _df_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    cleaned = df.astype(object).where(pd.notnull(df), None)
    return cleaned.to_dict(orient="records")


def _ensure_monitoring_storage_ready() -> None:
    return None


def _build_source_info() -> dict[str, Any]:
    return {
        "backend": get_db_backend(),
        "source_label": "PostgreSQL",
        "db_exists": True,
        "db_size_kb": None,
    }


@router.get("/source-info")
async def get_monitoring_source_info(
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin"})
    return _build_source_info()


@router.get("/snapshot")
async def get_monitoring_snapshot(
    company_id: Optional[int] = Query(default=None, ge=1),
    status: str = Query(default="Barchasi"),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    _ensure_monitoring_storage_ready()
    session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin"})
    scoped_company_id = require_company_scope(session, company_id)

    try:
        conn = connect_processing_db(timeout=30.0, row_factory=True)

        overall_stats = get_overall_stats_df(conn, scoped_company_id)
        task_status_counts = get_task_status_counts_df(conn, scoped_company_id)
        service_status_counts = get_service_status_counts_df(conn, scoped_company_id)
        recent_tasks = get_recent_tasks_df(conn, scoped_company_id, status)
        errors_log = get_errors_log_df(conn, scoped_company_id)
        blocked_tasks = get_blocked_tasks_df(conn, scoped_company_id)

        payload = {
            **_build_source_info(),
            "overall_stats": _df_records(overall_stats),
            "task_status_counts": _df_records(task_status_counts),
            "service_status_counts": _df_records(service_status_counts),
            "recent_tasks": _df_records(recent_tasks),
            "errors_log": _df_records(errors_log),
            "blocked_tasks": _df_records(blocked_tasks),
        }
        conn.close()
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Monitoring snapshot error ({get_db_backend()}): {exc}") from exc


@router.post("/bootstrap")
async def bootstrap_monitoring_storage(
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    load_api_session(x_session_id, allowed_roles={"super_admin"})
    try:
        from utils.database.task_db import init_db

        init_db()
        return {"success": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Monitoring bootstrap error: {exc}") from exc


@router.get("/tasks/{task_key}")
async def get_monitoring_task(
    task_key: str,
    company_id: Optional[int] = Query(default=None, ge=1),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    _ensure_monitoring_storage_ready()
    session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin"})
    scoped_company_id = require_company_scope(session, company_id)

    try:
        conn = connect_processing_db(timeout=30.0, row_factory=True)
        task = get_task_for_delete_check(conn, task_key.strip().upper(), scoped_company_id)
        conn.close()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Task fetch error: {exc}") from exc


@router.delete("/tasks/{task_key}")
async def delete_monitoring_task(
    task_key: str,
    company_id: Optional[int] = Query(default=None, ge=1),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    normalized_task_key = task_key.strip().upper()
    session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin"})
    scoped_company_id = require_company_scope(session, company_id)
    try:
        from utils.database.task_db import delete_task

        deleted = delete_task(normalized_task_key, company_id=scoped_company_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Task not found or delete failed")

        verify_conn = connect_processing_db(timeout=30.0)
        still_exists = task_exists(verify_conn, normalized_task_key) if scoped_company_id is None else bool(
            get_task_for_delete_check(verify_conn, normalized_task_key, scoped_company_id)
        )
        verify_conn.close()

        if still_exists:
            raise HTTPException(status_code=500, detail="Task still exists after delete")

        return {"success": True, "task_id": normalized_task_key}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Task delete error: {exc}") from exc
