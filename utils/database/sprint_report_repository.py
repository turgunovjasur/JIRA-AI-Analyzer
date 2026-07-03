"""
Sprint report repository helpers.

Sprint analytics querylarini API qatlamidan ajratish uchun vaqtinchalik
repository. Keyingi bosqichda shu modul `PostgreSQL` backendga ko'chiriladi.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from utils.database.repository_common import (
    prepare_query as _prepare_query,
)
from utils.database.repository_common import (
    row_to_dict as _row_to_dict,
)


def _cutoff_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def fetch_total_tasks(cursor, company_id: int, days: int) -> int:
    cursor.execute(
        _prepare_query(
            cursor,
            """
        SELECT COUNT(*) as total
        FROM task_processing
        WHERE company_id = ?
          AND created_at >= ?
        """,
        ),
        (company_id, _cutoff_iso(days)),
    )
    row = cursor.fetchone()
    row_dict = _row_to_dict(row) if row else {}
    return int(row_dict["total"]) if row and row_dict["total"] is not None else 0


def fetch_task_type_stats(cursor, company_id: int, days: int) -> List[Dict[str, Any]]:
    cursor.execute(
        _prepare_query(
            cursor,
            """
        SELECT
            COALESCE(task_type, 'other') as task_type,
            COUNT(*) as count
        FROM task_processing
        WHERE company_id = ?
          AND created_at >= ?
        GROUP BY task_type
        ORDER BY count DESC
        """,
        ),
        (company_id, _cutoff_iso(days)),
    )
    return [_row_to_dict(row) for row in cursor.fetchall()]


def fetch_top_features(cursor, company_id: int, days: int, limit: int) -> List[Dict[str, Any]]:
    cursor.execute(
        _prepare_query(
            cursor,
            """
        SELECT
            COALESCE(feature_name, 'unknown') as feature_name,
            COUNT(*) as total_tasks,
            SUM(CASE WHEN task_type = 'product' THEN 1 ELSE 0 END) as product,
            SUM(CASE WHEN task_type = 'client' THEN 1 ELSE 0 END) as client,
            SUM(CASE WHEN task_type = 'bug' THEN 1 ELSE 0 END) as bug,
            SUM(CASE WHEN task_type = 'error' THEN 1 ELSE 0 END) as error,
            SUM(CASE WHEN task_type = 'analiz' THEN 1 ELSE 0 END) as analiz,
            SUM(CASE WHEN task_type NOT IN ('product','client','bug','error','analiz')
                OR task_type IS NULL THEN 1 ELSE 0 END) as other
        FROM task_processing
        WHERE company_id = ?
          AND created_at >= ?
          AND feature_name IS NOT NULL
          AND feature_name != ''
        GROUP BY feature_name
        ORDER BY total_tasks DESC
        LIMIT ?
        """,
        ),
        (company_id, _cutoff_iso(days), limit),
    )
    return [_row_to_dict(row) for row in cursor.fetchall()]


def fetch_bug_distribution(cursor, company_id: int, days: int) -> List[Dict[str, Any]]:
    cursor.execute(
        _prepare_query(
            cursor,
            """
        SELECT
            COALESCE(feature_name, 'unknown') as feature_name,
            SUM(CASE WHEN task_type = 'bug' THEN 1 ELSE 0 END) as bug_count,
            SUM(CASE WHEN task_type = 'error' THEN 1 ELSE 0 END) as error_count,
            SUM(CASE WHEN task_type IN ('bug', 'error') THEN 1 ELSE 0 END) as total
        FROM task_processing
        WHERE company_id = ?
          AND created_at >= ?
          AND feature_name IS NOT NULL
          AND task_type IN ('bug', 'error')
        GROUP BY feature_name
        ORDER BY total DESC
        """,
        ),
        (company_id, _cutoff_iso(days)),
    )
    return [_row_to_dict(row) for row in cursor.fetchall()]


def fetch_developer_workload(cursor, company_id: int, days: int) -> List[Dict[str, Any]]:
    cursor.execute(
        _prepare_query(
            cursor,
            """
        SELECT
            COALESCE(assignee, 'Unassigned') as assignee,
            COUNT(*) as total_tasks,
            SUM(CASE WHEN task_status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN task_status = 'progressing' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN task_status = 'returned' THEN 1 ELSE 0 END) as returned,
            AVG(compliance_score) as avg_compliance_score
        FROM task_processing
        WHERE company_id = ?
          AND created_at >= ?
          AND assignee IS NOT NULL
        GROUP BY assignee
        ORDER BY total_tasks DESC
        """,
        ),
        (company_id, _cutoff_iso(days)),
    )
    return [_row_to_dict(row) for row in cursor.fetchall()]
