"""
Shared helpers for database repositories.

Repositorylarda PostgreSQL placeholder va row konversiyasini bitta joyda
ushlash uchun.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional


def uses_postgres_params(conn_or_cursor) -> bool:
    return True


def prepare_query(conn_or_cursor, query: str) -> str:
    return query.replace("?", "%s")


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
        data = dict(row)
    else:
        data = dict(row)
    return {
        key: value.isoformat() if isinstance(value, (datetime, date)) else value
        for key, value in data.items()
    }
