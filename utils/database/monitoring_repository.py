"""
Monitoring repository helpers.

UI qatlamidan SQL querylarni ajratish uchun vaqtinchalik repository.
Keyingi bosqichda shu modul `PostgreSQL` backendga ko'chiriladi.
"""
import pandas as pd
from utils.database.repository_common import (
    uses_postgres_params as _uses_postgres_params,
    prepare_query as _prepare_query,
    execute as _execute,
)


def _fetch_df(conn, query: str, params=None) -> pd.DataFrame:
    cursor = _execute(conn, query, params or [])
    rows = cursor.fetchall()
    columns = [column[0] for column in cursor.description] if cursor.description else []
    return pd.DataFrame(rows, columns=columns)


def _fetch_one_dict(conn, query: str, params=None):
    cursor = _execute(conn, query, params or [])
    row = cursor.fetchone()
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    columns = [column[0] for column in cursor.description] if cursor.description else []
    return dict(zip(columns, row))


def _where_clause(company_id) -> tuple[str, list]:
    if company_id is None:
        return "", []
    return "WHERE company_id = ?", [company_id]


def get_overall_stats_df(conn, company_id):
    where_clause, params = _where_clause(company_id)
    query = f"""
    SELECT
        COUNT(*) as total_tasks,
        SUM(CASE WHEN task_status = 'completed' THEN 1 ELSE 0 END) as completed,
        SUM(CASE WHEN task_status = 'progressing' THEN 1 ELSE 0 END) as progressing,
        SUM(CASE WHEN task_status = 'returned' THEN 1 ELSE 0 END) as returned,
        SUM(CASE WHEN task_status = 'error' THEN 1 ELSE 0 END) as error,
        SUM(CASE WHEN task_status = 'blocked' THEN 1 ELSE 0 END) as blocked,
        SUM(CASE WHEN COALESCE(skip_detected, FALSE) THEN 1 ELSE 0 END) as skipped,
        AVG(compliance_score) as avg_compliance,
        SUM(return_count) as total_returns
    FROM task_processing {where_clause}
    """
    return _fetch_df(conn, query, params=params)


def get_task_status_counts_df(conn, company_id):
    where_clause, params = _where_clause(company_id)
    query = f"""
    SELECT
        task_status,
        COUNT(*) as count
    FROM task_processing {where_clause}
    GROUP BY task_status
    """
    return _fetch_df(conn, query, params=params)


def get_service_status_counts_df(conn, company_id):
    where_clause, params = _where_clause(company_id)
    query = f"""
    SELECT
        service1_status,
        service2_status,
        COUNT(*) as count
    FROM task_processing {where_clause}
    GROUP BY service1_status, service2_status
    """
    return _fetch_df(conn, query, params=params)


def get_recent_tasks_df(conn, company_id, selected_status: str):
    base_cols = """
        task_id, task_status, service1_status, service2_status,
        compliance_score, return_count, skip_detected, last_processed_at, updated_at
    """
    conditions = []
    params = []
    if company_id is not None:
        conditions.append("company_id = ?")
        params.append(company_id)
    if selected_status != 'Barchasi':
        conditions.append("task_status = ?")
        params.append(selected_status)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    query = f"SELECT {base_cols} FROM task_processing {where_clause} ORDER BY updated_at DESC"
    return _fetch_df(conn, query, params=params)


def get_errors_log_df(conn, company_id):
    cid_clause = "AND company_id = ?" if company_id is not None else ""
    params = [company_id] if company_id is not None else []
    query = f"""
    SELECT
        task_id,
        task_status,
        error_message,
        service1_error,
        service2_error,
        updated_at
    FROM task_processing
    WHERE (error_message IS NOT NULL
       OR service1_error IS NOT NULL
       OR service2_error IS NOT NULL)
    {cid_clause}
    ORDER BY updated_at DESC
    LIMIT 10
    """
    return _fetch_df(conn, query, params=params)


def get_blocked_tasks_df(conn, company_id):
    cid_clause = "AND company_id = ?" if company_id is not None else ""
    params = [company_id] if company_id is not None else []
    query = f"""
    SELECT
        task_id,
        service1_status,
        service2_status,
        block_reason,
        blocked_at,
        blocked_retry_at,
        updated_at
    FROM task_processing
    WHERE task_status = 'blocked'
    {cid_clause}
    ORDER BY blocked_retry_at ASC
    """
    return _fetch_df(conn, query, params=params)


def get_task_for_delete_check(conn, task_key: str, company_id):
    if company_id is not None:
        return _fetch_one_dict(
            conn,
            "SELECT task_id, task_status, service1_status, service2_status FROM task_processing WHERE task_id = ? AND company_id = ?",
            [task_key, company_id],
        )
    return _fetch_one_dict(
        conn,
        "SELECT task_id, task_status, service1_status, service2_status FROM task_processing WHERE task_id = ?",
        [task_key],
    )


def task_exists(conn, task_key: str) -> bool:
    return _fetch_one_dict(conn, "SELECT task_id FROM task_processing WHERE task_id = ?", [task_key]) is not None
