"""
Internal Test Case Generator API endpoints.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from pydantic import BaseModel, Field

from services.generators.testcase_run import create_testcase_run, execute_testcase_run
from services.api.session_scope import load_api_session, require_customer_scope
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
            module_key="testcase_generator",
        )
        task_key = payload.task_key.strip().upper()
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

        if _worker_queue_enabled():
            enqueue_background_job(
                JOB_TESTCASE_MULTI_AGENT_RUN,
                task_key,
                company_id=company_id,
                payload={"run_id": run_id, "task_key": task_key},
                dedupe_key=f"{JOB_TESTCASE_MULTI_AGENT_RUN}:{run_id}",
                max_attempts=3,
            )
        else:
            background_tasks.add_task(execute_testcase_run, run_id)

        snapshot = get_analysis_run_snapshot(run_id)
        return snapshot or run
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Testcase run create error: {exc}") from exc


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
