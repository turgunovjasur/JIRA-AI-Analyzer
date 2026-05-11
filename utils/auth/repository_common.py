"""
Shared helpers for auth repositories.

SQLite va PostgreSQL placeholder/row farqlarini bitta joyda ushlash uchun.
"""
from __future__ import annotations

from typing import Any


def uses_postgres_params(conn) -> bool:
    module_name = conn.__class__.__module__
    return module_name.startswith("psycopg")


def prepare_query(conn, query: str) -> str:
    if uses_postgres_params(conn):
        return query.replace("?", "%s")
    return query


def execute(conn, query: str, params: list[Any] | tuple[Any, ...] | None = None):
    cursor = conn.cursor()
    cursor.execute(prepare_query(conn, query), params or [])
    return cursor


def row_to_dict(row) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    return dict(row)
