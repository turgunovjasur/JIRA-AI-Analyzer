"""
Internal TZ-PR API endpoints.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from pydantic import BaseModel

from services.checkers.tzpr_multi_agent import (
    create_multi_agent_run,
    execute_multi_agent_run,
    is_stalled_multi_agent_run,
    recover_stalled_multi_agent_run,
)
from services.api.session_scope import load_api_session, require_customer_scope
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
            module_key="tz_pr_checker",
        )
        run = create_multi_agent_run(
            task_key=payload.task_key.strip().upper(),
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

        if _worker_queue_enabled():
            enqueue_background_job(
                "tzpr_multi_agent_run",
                payload.task_key.strip().upper(),
                company_id=company_id,
                payload={"run_id": run_id, "task_key": payload.task_key.strip().upper()},
                dedupe_key=f"tzpr_multi_agent_run:{run_id}",
                max_attempts=3,
            )
        else:
            background_tasks.add_task(execute_multi_agent_run, run_id)

        snapshot = get_checker_run_snapshot(run_id)
        return snapshot or run
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TZ-PR run create error: {exc}") from exc


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
