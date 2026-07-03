"""
Admin job console (DLQ) API — faqat super_admin.

Failed/queued/running joblarni ko'rish, failed jobni qayta navbatga qo'yish
va terminal joblarni o'chirish uchun.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

from services.api.session_scope import load_api_session
from utils.database.job_queue_repository import (
    TERMINAL_JOB_STATUSES,
    delete_job,
    get_job,
    list_jobs,
    requeue_failed_job,
)
from utils.database.runtime import connect_processing_db

router = APIRouter(prefix="/api/admin/jobs", tags=["admin-jobs"])


def _connect():
    return connect_processing_db(timeout=30.0, row_factory=True)


@router.get("")
def list_admin_jobs(
    status: Optional[str] = Query(default=None, description="Vergul bilan ajratilgan statuslar"),
    company_id: Optional[int] = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    load_api_session(x_session_id, allowed_roles={"super_admin"})

    statuses = None
    if status:
        statuses = [item.strip().lower() for item in status.split(",") if item.strip()]

    try:
        conn = _connect()
        try:
            result = list_jobs(
                conn,
                statuses=statuses,
                company_id=company_id,
                limit=limit,
                offset=offset,
            )
        finally:
            conn.close()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Job list error: {exc}") from exc

    return {
        "success": True,
        "jobs": result["jobs"],
        "total": result["total"],
        "limit": limit,
        "offset": offset,
    }


@router.post("/{job_id}/requeue")
def requeue_admin_job(
    job_id: int,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    load_api_session(x_session_id, allowed_roles={"super_admin"})

    try:
        conn = _connect()
        try:
            job = get_job(conn, job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job topilmadi")
            if job.get("status") != "failed":
                raise HTTPException(
                    status_code=409,
                    detail=f"Faqat failed job requeue qilinadi (hozirgi: {job.get('status')})",
                )
            requeued = requeue_failed_job(conn, job_id)
            if not requeued:
                raise HTTPException(status_code=409, detail="Job requeue bo'lmadi (holat o'zgargan)")
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Job requeue error: {exc}") from exc

    return {"success": True, "job": requeued}


@router.delete("/{job_id}")
def delete_admin_job(
    job_id: int,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    load_api_session(x_session_id, allowed_roles={"super_admin"})

    try:
        conn = _connect()
        try:
            job = get_job(conn, job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job topilmadi")
            if job.get("status") not in TERMINAL_JOB_STATUSES:
                raise HTTPException(
                    status_code=409,
                    detail=f"Faqat terminal (failed/done) job o'chiriladi (hozirgi: {job.get('status')})",
                )
            deleted = delete_job(conn, job_id)
            if not deleted:
                raise HTTPException(status_code=409, detail="Job o'chirilmadi (holat o'zgargan)")
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Job delete error: {exc}") from exc

    return {"success": True, "job_id": job_id}
