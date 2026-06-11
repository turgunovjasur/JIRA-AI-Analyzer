"""
Shared helpers for auth repositories.

Auth repositorylarda PostgreSQL placeholder va row konversiyasini bitta joyda
ushlash uchun.
"""
from __future__ import annotations

from typing import Any


def uses_postgres_params(conn) -> bool:
    return True


def prepare_query(conn, query: str) -> str:
    return query.replace("?", "%s")


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
