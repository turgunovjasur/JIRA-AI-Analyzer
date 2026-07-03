"""
Background job queue repository helpers.

API process webhook/manual triggerlarni DB navbatga yozadi, worker esa shu
navbatdan olib bajaradi.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from utils.database.repository_common import (
    execute as _execute,
)
from utils.database.repository_common import (
    row_to_dict as _row_to_dict,
)

# F2-8: multi-worker claim serializatsiyasi uchun global advisory lock kaliti.
_CLAIM_ADVISORY_LOCK_KEY = 4917_2026_02


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _per_company_concurrency_enabled() -> bool:
    """Bir kompaniyaga bir vaqtda 1 ta running job (multi-worker uchun DB-level).

    Ilgari bu 'kompaniyaga 1 AI task' kafolati queue_manager in-process dict'da
    edi — N worker bilan yo'qolardi. Endi claim DB'da serializatsiya qilinadi.
    Bitta worker uchun no-op (ketma-ket claim). Env bilan o'chiriladi.
    """
    raw = (os.getenv("APP_QUEUE_PER_COMPANY_CONCURRENCY") or "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


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

    if not _per_company_concurrency_enabled():
        # Klassik claim: eng eski queued job, per-company cheklovsiz.
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

    # Multi-worker: kompaniyaga bir vaqtda faqat 1 ta running job.
    # pg_advisory_xact_lock barcha workerlarning claim'ini serializatsiya qiladi
    # → NOT EXISTS tekshiruvi TOCTOU'siz (ikki worker bir kompaniyaga bir vaqtda
    # ikki job olmaydi). Claim tez; lock tranzaksiya commit'ida ochiladi. AI ishi
    # claim'dan TASHQARIDA (boshqa ulanish, allaqachon yopilgan) — lock ushlab qolmaydi.
    _execute(conn, "SELECT pg_advisory_xact_lock(?)", [_CLAIM_ADVISORY_LOCK_KEY])
    row = _execute(
        conn,
        """
        WITH next_job AS (
            SELECT jq.id
            FROM job_queue jq
            WHERE jq.status = 'queued'
              AND jq.scheduled_at <= ?
              AND (
                  jq.company_id IS NULL
                  OR NOT EXISTS (
                      SELECT 1 FROM job_queue r
                      WHERE r.status = 'running'
                        AND r.company_id = jq.company_id
                  )
              )
            ORDER BY jq.scheduled_at ASC, jq.id ASC
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


TERMINAL_JOB_STATUSES = ("failed", "done")
_JOB_STATUSES = ("queued", "running", "done", "failed")

_JOB_LIST_COLUMNS = (
    "id, job_type, task_key, company_id, dedupe_key, status, attempts, "
    "max_attempts, worker_name, scheduled_at, started_at, finished_at, "
    "last_error, created_at, updated_at"
)


def get_job(conn, job_id: int) -> dict[str, Any] | None:
    row = _execute(
        conn,
        f"SELECT {_JOB_LIST_COLUMNS} FROM job_queue WHERE id = ?",
        [int(job_id)],
    ).fetchone()
    return _row_to_dict(row) if row else None


def list_jobs(
    conn,
    *,
    statuses: Optional[list[str]] = None,
    company_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Admin job console uchun joblar ro'yxati (rows + total)."""
    where: list[str] = []
    params: list[Any] = []
    if statuses:
        normalized = [s.strip().lower() for s in statuses if s and s.strip()]
        invalid = set(normalized) - set(_JOB_STATUSES)
        if invalid:
            raise ValueError(f"Noma'lum job status: {sorted(invalid)}")
        placeholders = ", ".join("?" for _ in normalized)
        where.append(f"status IN ({placeholders})")
        params.extend(normalized)
    if company_id is not None:
        where.append("company_id = ?")
        params.append(int(company_id))
    where_sql = f" WHERE {' AND '.join(where)}" if where else ""

    total_row = _execute(
        conn,
        f"SELECT COUNT(*) AS total FROM job_queue{where_sql}",
        params,
    ).fetchone()
    total = int(_row_to_dict(total_row).get("total") or 0)

    rows = _execute(
        conn,
        f"""
        SELECT {_JOB_LIST_COLUMNS}
        FROM job_queue{where_sql}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        params + [max(1, min(int(limit), 500)), max(0, int(offset))],
    ).fetchall()
    return {"jobs": [_row_to_dict(row) for row in rows or []], "total": total}


def requeue_failed_job(conn, job_id: int) -> dict[str, Any] | None:
    """Failed jobni qayta navbatga qo'yish (DLQ requeue).

    ``claim_next_job`` har claimda ``attempts``ni oshiradi va worker
    ``attempts >= max_attempts`` bo'lsa yana failed qiladi — shuning uchun
    attempts 0 ga qaytariladi (to'liq yangi retry sikli). scheduled_at=now →
    darhol claim qilinadi. last_error saqlanadi (nega failed bo'lgani ko'rinsin).
    """
    now = _now_iso()
    row = _execute(
        conn,
        """
        UPDATE job_queue
        SET status = 'queued',
            attempts = 0,
            worker_name = NULL,
            scheduled_at = ?,
            started_at = NULL,
            finished_at = NULL,
            updated_at = ?
        WHERE id = ?
          AND status = 'failed'
        RETURNING *
        """,
        [now, now, int(job_id)],
    ).fetchone()
    if not row:
        conn.rollback()
        return None
    job = _row_to_dict(row)
    _record_job_run(conn, job, "requeued", "admin requeue")
    conn.commit()
    return job


def delete_job(conn, job_id: int) -> bool:
    """Faqat terminal (failed/done) jobni o'chirish; job_queue_runs CASCADE."""
    row = _execute(
        conn,
        "DELETE FROM job_queue WHERE id = ? AND status IN ('failed', 'done') RETURNING id",
        [int(job_id)],
    ).fetchone()
    conn.commit()
    return bool(row)


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

    failed_rows = _execute(
        conn,
        """
        SELECT id, task_key, last_error, finished_at
        FROM job_queue
        WHERE status = 'failed'
        ORDER BY finished_at DESC NULLS LAST, id DESC
        LIMIT 10
        """,
    ).fetchall()
    recent_failed = [
        {
            "id": item.get("id"),
            "task_key": item.get("task_key"),
            "error": item.get("last_error"),
            "failed_at": item.get("finished_at"),
        }
        for item in (_row_to_dict(r) for r in failed_rows or [])
    ]

    return {
        "queued": int(row.get("queued") or 0),
        "running": int(row.get("running") or 0),
        "done": int(row.get("done") or 0),
        "failed": int(row.get("failed") or 0),
        "recent_failed": recent_failed,
    }
