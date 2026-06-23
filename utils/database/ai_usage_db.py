"""
High-level AI usage ledger helpers.
"""
from __future__ import annotations

from typing import Any

from core.logger import get_logger
from utils.database.ai_usage_repository import (
    fetch_ai_usage_dashboard as repo_fetch_ai_usage_dashboard,
    fetch_ai_usage_summary as repo_fetch_ai_usage_summary,
    record_ai_usage_event as repo_record_ai_usage_event,
)
from utils.database.runtime import connect_processing_db
from utils.database.task_db import _get_db_settings  # type: ignore

log = get_logger("ai.usage.db")


def _connect():
    # P2: jadvallar startup migratsiyasida ensure qilinadi — bu yerda DDL yo'q.
    settings = _get_db_settings()
    return connect_processing_db(timeout=settings.db_connection_timeout, row_factory=True)


def record_ai_usage_event(**fields: Any) -> dict[str, Any] | None:
    conn = _connect()
    try:
        return repo_record_ai_usage_event(conn, **fields)
    finally:
        conn.close()


def fetch_ai_usage_summary(
    *,
    company_id: int | None = None,
    module_key: str | None = None,
) -> dict[str, Any]:
    conn = _connect()
    try:
        return repo_fetch_ai_usage_summary(
            conn,
            company_id=company_id,
            module_key=module_key,
        )
    finally:
        conn.close()


def fetch_ai_usage_dashboard(*, limit: int = 20) -> dict[str, Any]:
    conn = _connect()
    try:
        return repo_fetch_ai_usage_dashboard(conn, limit=limit)
    finally:
        conn.close()
