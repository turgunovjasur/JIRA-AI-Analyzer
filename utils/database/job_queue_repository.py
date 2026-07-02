"""
Background job queue repository helpers.

API process webhook/manual triggerlarni DB navbatga yozadi, worker esa shu
navbatdan olib bajaradi.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from utils.database.repository_common import (
    execute as _execute,
    row_to_dict as _row_to_dict,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_job_queue_tables(conn) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS job_queue (
            id BIGSERIAL PRIMARY KEY,
            job_type TEXT NOT NULL,
            task_key TEXT NOT NULL,
            company_id BIGINT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            dedupe_key TEXT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            attempts INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 3,
            worker_name TEXT NULL,
            scheduled_at TIMESTAMPTZ NOT NULL,
            started_at TIMESTAMPTZ NULL,
            finished_at TIMESTAMPTZ NULL,
            last_error TEXT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS job_queue_runs (
            id BIGSERIAL PRIMARY KEY,
            job_id BIGINT NOT NULL REFERENCES job_queue(id) ON DELETE CASCADE,
            job_type TEXT NOT NULL,
            task_key TEXT NOT NULL,
            company_id BIGINT NULL,
            worker_name TEXT NULL,
            attempt_number INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL,
            error_message TEXT NULL,
            started_at TIMESTAMPTZ NULL,
            finished_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL
        )
        """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_queue_status_scheduled ON job_queue(status, scheduled_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_queue_dedupe ON job_queue(dedupe_key)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_queue_runs_job_id ON job_queue_runs(job_id)"
    )
    conn.commit()


def enqueue_job(
    conn,
    *,
    job_type: str,
    task_key: str,
    company_id: int | None,
    payload: Optional[dict[str, Any]] = None,
    dedupe_key: str | None = None,
    scheduled_at: str | None = None,
    max_attempts: int = 3,
) -> dict[str, Any]:
    now = _now_iso()
    scheduled_value = scheduled_at or now
    payload_json = json.dumps(payload or {}, ensure_ascii=True)

    if dedupe_key:
        existing = _execute(
            conn,
            """
            SELECT * FROM job_queue
            WHERE dedupe_key = ?
              AND status IN ('queued', 'running')
            ORDER BY id DESC
            LIMIT 1
            """,
            [dedupe_key],
        ).fetchone()
        if existing:
            return _row_to_dict(existing)

    row = _execute(
        conn,
        """
        INSERT INTO job_queue (
            job_type, task_key, company_id, payload_json, dedupe_key,
            status, attempts, max_attempts, worker_name,
            scheduled_at, started_at, finished_at, last_error,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, 'queued', 0, ?, NULL, ?, NULL, NULL, NULL, ?, ?)
        RETURNING *
        """,
        [
            job_type,
            task_key,
            company_id,
            payload_json,
            dedupe_key,
            max(1, int(max_attempts)),
            scheduled_value,
            now,
            now,
        ],
    ).fetchone()
    conn.commit()
    return _row_to_dict(row)


def claim_next_job(conn, *, worker_name: str) -> dict[str, Any] | None:
    now = _now_iso()

    row = _execute(
        conn,
        """
        WITH next_job AS (
            SELECT id
            FROM job_queue
            WHERE status = 'queued'
              AND scheduled_at <= ?
            ORDER BY scheduled_at ASC, id ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        )
        UPDATE job_queue jq
        SET status = 'running',
            attempts = jq.attempts + 1,
            worker_name = ?,
            started_at = ?,
            updated_at = ?,
            finished_at = NULL
        FROM next_job
        WHERE jq.id = next_job.id
        RETURNING jq.*
        """,
        [now, worker_name, now, now],
    ).fetchone()
    conn.commit()
    return _row_to_dict(row) if row else None


def _record_job_run(conn, job: dict[str, Any], status: str, error_message: str = "") -> None:
    finished_at = _now_iso()
    _execute(
        conn,
        """
        INSERT INTO job_queue_runs (
            job_id, job_type, task_key, company_id, worker_name,
            attempt_number, status, error_message, started_at, finished_at, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            job["id"],
            job["job_type"],
            job["task_key"],
            job.get("company_id"),
            job.get("worker_name"),
            job.get("attempts") or 1,
            status,
            error_message or None,
            job.get("started_at"),
            finished_at,
            finished_at,
        ],
    )


def mark_job_done(conn, job: dict[str, Any]) -> None:
    now = _now_iso()
    _record_job_run(conn, job, "done")
    _execute(
        conn,
        """
        UPDATE job_queue
        SET status = 'done',
            finished_at = ?,
            updated_at = ?,
            last_error = NULL
        WHERE id = ?
        """,
        [now, now, job["id"]],
    )
    conn.commit()


def mark_job_retry(conn, job: dict[str, Any], error_message: str, delay_seconds: int) -> None:
    now = _now_iso()
    next_time = (datetime.now(timezone.utc) + timedelta(seconds=max(1, int(delay_seconds)))).isoformat()
    _record_job_run(conn, job, "retry", error_message)
    _execute(
        conn,
        """
        UPDATE job_queue
        SET status = 'queued',
            scheduled_at = ?,
            started_at = NULL,
            finished_at = NULL,
            updated_at = ?,
            last_error = ?
        WHERE id = ?
        """,
        [next_time, now, error_message, job["id"]],
    )
    conn.commit()


def mark_job_failed(conn, job: dict[str, Any], error_message: str) -> None:
    now = _now_iso()
    _record_job_run(conn, job, "failed", error_message)
    _execute(
        conn,
        """
        UPDATE job_queue
        SET status = 'failed',
            finished_at = ?,
            updated_at = ?,
            last_error = ?
        WHERE id = ?
        """,
        [now, now, error_message, job["id"]],
    )
    conn.commit()


def requeue_stale_running_jobs(conn, *, stale_seconds: int) -> dict[str, int]:
    """Worker crash tufayli 'running'da qotib qolgan joblarni tiklash.

    ``claim_next_job`` faqat ``status='queued'`` joblarni oladi, shuning uchun
    worker run o'rtasida o'lsa, uning jobi abadiy ``running`` qoladi va o'sha
    task uchun dedupe keyingi webhook'larni bloklaydi. Bu funksiya ``started_at``
    ``stale_seconds`` dan eski bo'lgan running joblarni:
      - urinishlar qolgan bo'lsa → ``queued`` (boshqa worker qayta oladi)
      - urinishlar tugagan bo'lsa → ``failed``
    ga o'tkazadi.

    ``stale_seconds`` eng uzun normal run'dan (multi-agent ~3-8 daqiqa) sezilarli
    katta bo'lishi shart — aks holda hali ishlayotgan job xato requeue qilinadi.

    Returns:
        {"requeued": N, "failed": M}
    """
    now = _now_iso()
    cutoff = (
        datetime.now(timezone.utc) - timedelta(seconds=max(1, int(stale_seconds)))
    ).isoformat()

    requeued = _execute(
        conn,
        """
        UPDATE job_queue
        SET status = 'queued',
            worker_name = NULL,
            started_at = NULL,
            finished_at = NULL,
            updated_at = ?,
            last_error = 'reaped: stale running job requeued'
        WHERE status = 'running'
          AND started_at IS NOT NULL
          AND started_at < ?
          AND attempts < max_attempts
        RETURNING id
        """,
        [now, cutoff],
    ).fetchall()

    failed = _execute(
        conn,
        """
        UPDATE job_queue
        SET status = 'failed',
            finished_at = ?,
            updated_at = ?,
            last_error = 'reaped: stale running job exceeded max_attempts'
        WHERE status = 'running'
          AND started_at IS NOT NULL
          AND started_at < ?
          AND attempts >= max_attempts
        RETURNING id
        """,
        [now, now, cutoff],
    ).fetchall()

    conn.commit()
    return {"requeued": len(requeued or []), "failed": len(failed or [])}


def fetch_queue_snapshot(conn) -> dict[str, Any]:
    cursor = _execute(
        conn,
        """
        SELECT
            SUM(CASE WHEN status = 'queued' THEN 1 ELSE 0 END) AS queued,
            SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) AS running,
            SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) AS done,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed
        FROM job_queue
        """,
    )
    row = _row_to_dict(cursor.fetchone())
    return {
        "queued": int(row.get("queued") or 0),
        "running": int(row.get("running") or 0),
        "done": int(row.get("done") or 0),
        "failed": int(row.get("failed") or 0),
    }
