"""
Internal Test Case Generator API endpoints.
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.module_start_preflight import get_module_start_status, run_start_preflight
from services.api.session_scope import load_api_session, require_customer_scope
from services.api.task_key_normalizer import MissingProjectKeySetting, normalize_manual_task_key
from services.generators.testcase_run import create_testcase_run, execute_testcase_run
from utils.database.analysis_run_db import get_analysis_run_snapshot
from utils.database.task_db import enqueue_background_job

router = APIRouter(prefix="/api/testcase", tags=["testcase"])

# Worker queue job turi (services/worker/main.py bilan bir xil bo'lishi shart).
JOB_TESTCASE_MULTI_AGENT_RUN = "testcase_multi_agent_run"


class CreateTestcaseRunRequest(BaseModel):
    task_key: str
    user_id: int | None = None
    company_id: int | None = None
    test_types: list[str] = Field(default_factory=list)
    custom_context: str = ""
    output_profile: str | None = None


def _worker_queue_enabled() -> bool:
    raw = (os.getenv("APP_WEBHOOK_EXECUTION_MODE") or "inline").strip().lower()
    return raw == "queue"


@router.post("/runs")
async def create_testcase_run_endpoint(
    payload: CreateTestcaseRunRequest,
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
            module_key="testcase_generator",
            task_key=task_key,
            company_id=company_id,
            user_id=user_id,
            source="manual",
        )
        if not preflight.ok:
            return JSONResponse(status_code=400, content=preflight.to_error_payload())

        user_id = preflight.user_id
        company_id = preflight.company_id
        run = create_testcase_run(
            task_key=task_key,
            company_id=company_id,
            user_id=user_id,
            source="manual",
            test_types=payload.test_types,
            custom_context=payload.custom_context,
            output_profile=(payload.output_profile or "ui").strip().lower() or "ui",
        )
        run_id = str(run.get("run_id") or "")
        if not run_id:
            raise RuntimeError("Run yaratilmadi")

        preflight_quota = getattr(preflight, "quota", None)
        using_global = bool(preflight_quota and preflight_quota.get("using_global") and company_id is not None)

        if _worker_queue_enabled():
            enqueue_background_job(
                JOB_TESTCASE_MULTI_AGENT_RUN,
                task_key,
                company_id=company_id,
                payload={
                    "run_id": run_id,
                    "task_key": task_key,
                    "increment_quota": using_global,
                },
                dedupe_key=f"{JOB_TESTCASE_MULTI_AGENT_RUN}:{run_id}",
                max_attempts=3,
            )
        else:
            background_tasks.add_task(execute_testcase_run, run_id, increment_quota=using_global)

        snapshot = get_analysis_run_snapshot(run_id) or run
        if isinstance(snapshot, dict) and preflight_quota is not None:
            snapshot["gemini_quota"] = preflight_quota
        return snapshot
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Testcase run create error: {exc}") from exc


@router.get("/start-status")
async def testcase_start_status(
    user_id: int | None = None,
    company_id: int | None = None,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    """Modul ochilganda credential + Gemini kvota holati (run'dan oldin banner uchun)."""
    try:
        session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin", "user"})
        resolved_user_id, resolved_company_id = require_customer_scope(session, user_id, company_id)
        return get_module_start_status(
            module_key="testcase_generator",
            company_id=resolved_company_id,
            user_id=resolved_user_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Testcase start-status error: {exc}") from exc


@router.get("/runs/{run_id}")
async def get_testcase_run_endpoint(
    run_id: str,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    try:
        session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin", "user"})
        scoped_user_id, scoped_company_id = require_customer_scope(
            session,
            None,
            None,
            module_key="testcase_generator",
        )
        snapshot = get_analysis_run_snapshot(run_id.strip())
        if not snapshot:
            raise HTTPException(status_code=404, detail="Testcase run topilmadi")
        role = str(((session or {}).get("auth") or {}).get("role") or "").strip().lower()
        if role != "super_admin":
            run_company_id = snapshot.get("company_id")
            run_user_id = snapshot.get("user_id")
            if scoped_company_id not in (None, run_company_id):
                raise HTTPException(status_code=403, detail="Bu testcase run scope sizga tegishli emas")
            if role == "user" and scoped_user_id not in (None, run_user_id):
                raise HTTPException(status_code=403, detail="Bu testcase run user scope sizga tegishli emas")
        return snapshot
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Testcase run read error: {exc}") from exc
