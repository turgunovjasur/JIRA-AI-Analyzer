"""
Task processing repository helpers.

`task_db.py` ichidagi asosiy persistence querylarini bosqichma-bosqich
ajratish uchun repository qatlam.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from utils.database.repository_common import (
    uses_postgres_params as _uses_postgres_params,
    prepare_query as _prepare_query,
    execute as _execute,
    row_to_dict as _row_to_dict,
)


def fetch_task_by_id(
    connect_processing: Callable[..., Any],
    task_id: str,
    timeout: float,
) -> Optional[Dict[str, Any]]:
    conn = connect_processing(timeout=timeout, row_factory=True)
    if not _uses_postgres_params(conn):
        _execute(conn, "PRAGMA synchronous=FULL")
    cursor = _execute(
        conn,
        """
        SELECT * FROM task_processing
        WHERE task_id = ?
        """,
        [task_id],
    )
    row = cursor.fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def upsert_task_record(
    connect_processing: Callable[..., Any],
    task_id: str,
    fields: Dict[str, Any],
    timeout: float,
    busy_timeout: int,
) -> None:
    payload = dict(fields)
    conn = connect_processing(timeout=timeout)
    cursor = conn.cursor()
    if not _uses_postgres_params(conn):
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={busy_timeout}")
        cursor.execute("BEGIN IMMEDIATE")
    cursor.execute(_prepare_query(conn, "SELECT task_id FROM task_processing WHERE task_id = ?"), [task_id])
    exists = cursor.fetchone()
    payload["updated_at"] = datetime.now().isoformat()

    if exists:
        placeholder = "%s" if _uses_postgres_params(conn) else "?"
        set_clause = ", ".join(f"{key} = {placeholder}" for key in payload.keys())
        values = list(payload.values()) + [task_id]
        cursor.execute(
            _prepare_query(conn, f"UPDATE task_processing SET {set_clause} WHERE task_id = ?"),
            values,
        )
    else:
        payload["task_id"] = task_id
        payload["created_at"] = datetime.now().isoformat()
        columns = ", ".join(payload.keys())
        placeholders = ", ".join("%s" if _uses_postgres_params(conn) else "?" for _ in payload)
        values = list(payload.values())
        cursor.execute(f"INSERT INTO task_processing ({columns}) VALUES ({placeholders})", values)

    conn.commit()
    conn.close()


def fetch_blocked_tasks_ready_for_retry(
    connect_processing: Callable[..., Any],
) -> List[Dict[str, Any]]:
    conn = connect_processing(row_factory=True)
    now = datetime.now().isoformat()
    cursor = _execute(
        conn,
        """
        SELECT * FROM task_processing
        WHERE task_status = 'blocked'
          AND blocked_retry_at IS NOT NULL
          AND blocked_retry_at <= ?
        ORDER BY blocked_retry_at ASC
        """,
        [now],
    )
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_dict(row) for row in rows]


def delete_task_record(
    connect_processing: Callable[..., Any],
    task_id: str,
    company_id: Optional[int],
    timeout: float,
    busy_timeout: int,
) -> bool:
    conn = connect_processing(timeout=timeout)
    cursor = conn.cursor()
    if not _uses_postgres_params(conn):
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={busy_timeout}")
        cursor.execute("BEGIN IMMEDIATE")
    if company_id is None:
        cursor.execute(_prepare_query(conn, "SELECT task_id FROM task_processing WHERE task_id = ?"), [task_id])
    else:
        cursor.execute(
            _prepare_query(conn, "SELECT task_id FROM task_processing WHERE task_id = ? AND company_id = ?"),
            [task_id, company_id],
        )
    exists = cursor.fetchone()

    if not exists:
        conn.commit()
        conn.close()
        return False

    if company_id is None:
        cursor.execute(_prepare_query(conn, "DELETE FROM task_processing WHERE task_id = ?"), [task_id])
    else:
        cursor.execute(
            _prepare_query(conn, "DELETE FROM task_processing WHERE task_id = ? AND company_id = ?"),
            [task_id, company_id],
        )
    conn.commit()
    if not _uses_postgres_params(conn):
        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    if company_id is None:
        cursor.execute(_prepare_query(conn, "SELECT task_id FROM task_processing WHERE task_id = ?"), [task_id])
    else:
        cursor.execute(
            _prepare_query(conn, "SELECT task_id FROM task_processing WHERE task_id = ? AND company_id = ?"),
            [task_id, company_id],
        )
    still_exists = cursor.fetchone()
    conn.close()
    return still_exists is None


def fetch_stuck_tasks(
    connect_processing: Callable[..., Any],
    timeout_minutes: int,
) -> List[Dict[str, Any]]:
    conn = connect_processing(row_factory=True)
    cutoff_time = (datetime.now() - timedelta(minutes=timeout_minutes)).isoformat()
    if _uses_postgres_params(conn):
        query = """
        SELECT task_id, task_status, service1_status, service2_status,
               last_processed_at, updated_at,
               ROUND(EXTRACT(EPOCH FROM (NOW() - updated_at)) / 60.0) as stuck_minutes
        FROM task_processing
        WHERE task_status = 'progressing'
          AND updated_at < ?
        ORDER BY updated_at ASC
        """
    else:
        query = """
        SELECT task_id, task_status, service1_status, service2_status,
               last_processed_at, updated_at,
               ROUND((julianday('now') - julianday(updated_at)) * 1440) as stuck_minutes
        FROM task_processing
        WHERE task_status = 'progressing'
          AND updated_at < ?
        ORDER BY updated_at ASC
        """
    cursor = _execute(conn, query, [cutoff_time])
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_dict(row) for row in rows]


def insert_status_history(
    connect_processing: Callable[..., Any],
    task_id: str,
    from_status: Optional[str],
    to_status: str,
    changed_at_iso: str,
    assignee: Optional[str],
    story_points: Optional[float],
    issue_type: Optional[str],
    company_id: Optional[int],
    timeout: float,
) -> None:
    conn = connect_processing(timeout=timeout)
    if _uses_postgres_params(conn):
        cursor = _execute(
            conn,
            """
            INSERT INTO task_status_history
                (task_id, company_id, from_status, to_status, changed_at, assignee, story_points, issue_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [task_id, company_id, from_status, to_status, changed_at_iso, assignee, story_points, issue_type],
        )
    else:
        cursor = _execute(
            conn,
            """
            INSERT INTO task_status_history
                (task_id, from_status, to_status, changed_at, assignee, story_points, issue_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [task_id, from_status, to_status, changed_at_iso, assignee, story_points, issue_type],
        )
    conn.commit()
    conn.close()


def fetch_status_history_for_report(
    connect_processing: Callable[..., Any],
    days: int,
) -> List[Dict[str, Any]]:
    conn = connect_processing(row_factory=True)
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    cursor = _execute(
        conn,
        """
        SELECT
            id,
            task_id,
            from_status,
            to_status,
            changed_at,
            assignee,
            story_points,
            issue_type
        FROM task_status_history
        WHERE changed_at >= ?
        ORDER BY task_id, changed_at ASC
        """,
        [cutoff],
    )
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_dict(row) for row in rows]
