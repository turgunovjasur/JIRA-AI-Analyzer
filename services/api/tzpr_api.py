"""
Internal TZ-PR API endpoints.
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.module_start_preflight import get_module_start_status, run_start_preflight
from services.api.session_scope import load_api_session, require_customer_scope
from services.api.task_key_normalizer import MissingProjectKeySetting, normalize_manual_task_key
from services.checkers.tzpr_multi_agent import (
    create_multi_agent_run,
    execute_multi_agent_run,
    is_stalled_multi_agent_run,
    recover_stalled_multi_agent_run,
)
from utils.database.checker_run_db import get_checker_run_snapshot
from utils.database.task_db import enqueue_background_job

router = APIRouter(prefix="/api/tzpr", tags=["tz-pr"])


class CreateRunRequest(BaseModel):
    task_key: str
    user_id: int | None = None
    company_id: int | None = None
    max_files: int | None = None
    show_full_diff: bool = True
    use_smart_patch: bool | None = None
    output_profile: str | None = None


def _worker_queue_enabled() -> bool:
    raw = (os.getenv("APP_WEBHOOK_EXECUTION_MODE") or "inline").strip().lower()
    return raw == "queue"


@router.post("/runs")
async def create_tzpr_run(
    payload: CreateRunRequest,
    background_tasks: BackgroundTasks,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    try:
        session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin", "user"})
        user_id, company_id = require_customer_scope(
            session,
            payload.user_id,
            payload.company_id,
        )
        try:
            task_key = normalize_manual_task_key(payload.task_key, company_id)
        except MissingProjectKeySetting as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        preflight = run_start_preflight(
            module_key="tz_pr_checker",
            task_key=task_key,
            company_id=company_id,
            user_id=user_id,
            source="manual",
        )
        if not preflight.ok:
            return JSONResponse(status_code=400, content=preflight.to_error_payload())

        user_id = preflight.user_id
        company_id = preflight.company_id
        run = create_multi_agent_run(
            task_key=task_key,
            company_id=company_id,
            user_id=user_id,
            source="manual",
            output_profile=(payload.output_profile or "ui").strip().lower() or "ui",
            show_full_diff=payload.show_full_diff,
            use_smart_patch=payload.use_smart_patch,
            max_files=payload.max_files,
        )
        run_id = str(run.get("run_id") or "")
        if not run_id:
            raise RuntimeError("Run yaratilmadi")

        preflight_quota = getattr(preflight, "quota", None)
        using_global = bool(preflight_quota and preflight_quota.get("using_global") and company_id is not None)

        if _worker_queue_enabled():
            enqueue_background_job(
                "tzpr_multi_agent_run",
                task_key,
                company_id=company_id,
                payload={"run_id": run_id, "task_key": task_key},
                dedupe_key=f"tzpr_multi_agent_run:{run_id}",
                max_attempts=3,
            )
        else:
            background_tasks.add_task(execute_multi_agent_run, run_id, increment_quota=using_global)

        snapshot = get_checker_run_snapshot(run_id) or run
        if isinstance(snapshot, dict) and preflight_quota is not None:
            snapshot["gemini_quota"] = preflight_quota
        return snapshot
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TZ-PR run create error: {exc}") from exc


@router.get("/start-status")
async def tzpr_start_status(
    user_id: int | None = None,
    company_id: int | None = None,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    """Modul ochilganda credential + Gemini kvota holati (run'dan oldin banner uchun)."""
    try:
        session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin", "user"})
        resolved_user_id, resolved_company_id = require_customer_scope(session, user_id, company_id)
        return get_module_start_status(
            module_key="tz_pr_checker",
            company_id=resolved_company_id,
            user_id=resolved_user_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TZ-PR start-status error: {exc}") from exc


@router.get("/runs/{run_id}")
async def get_tzpr_run(
    run_id: str,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    try:
        session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin", "user"})
        scoped_user_id, scoped_company_id = require_customer_scope(
            session,
            None,
            None,
            module_key="tz_pr_checker",
        )
        snapshot = get_checker_run_snapshot(run_id.strip())
        if not snapshot:
            raise HTTPException(status_code=404, detail="Checker run topilmadi")
        if is_stalled_multi_agent_run(snapshot):
            snapshot = recover_stalled_multi_agent_run(run_id.strip()) or snapshot
        role = str(((session or {}).get("auth") or {}).get("role") or "").strip().lower()
        if role != "super_admin":
            run_company_id = snapshot.get("company_id")
            run_user_id = snapshot.get("user_id")
            if scoped_company_id not in (None, run_company_id):
                raise HTTPException(status_code=403, detail="Bu checker run scope sizga tegishli emas")
            if role == "user" and scoped_user_id not in (None, run_user_id):
                raise HTTPException(status_code=403, detail="Bu checker run user scope sizga tegishli emas")
        return snapshot
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TZ-PR run read error: {exc}") from exc
