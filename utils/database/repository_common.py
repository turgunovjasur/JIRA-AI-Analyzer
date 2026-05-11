"""
Shared helpers for database repositories.

SQLite va PostgreSQL placeholder/row farqlarini monitoring, sprint report va
task repositorylarida bitta joyda ushlash uchun.
"""
from __future__ import annotations

from typing import Any, Optional


def uses_postgres_params(conn_or_cursor) -> bool:
    module_name = conn_or_cursor.__class__.__module__
    return module_name.startswith("psycopg")


def prepare_query(conn_or_cursor, query: str) -> str:
    if uses_postgres_params(conn_or_cursor):
        return query.replace("?", "%s")
    return query


def execute(conn_or_cursor, query: str, params: Optional[list[Any] | tuple[Any, ...]] = None):
    if hasattr(conn_or_cursor, "cursor"):
        cursor = conn_or_cursor.cursor()
    else:
        cursor = conn_or_cursor
    cursor.execute(prepare_query(conn_or_cursor, query), params or [])
    return cursor


def row_to_dict(row) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    return dict(row)
