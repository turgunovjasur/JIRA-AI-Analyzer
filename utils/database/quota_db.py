"""Global Gemini kvota — connection lifecycle bilan high-level helperlar."""
from __future__ import annotations

from utils.database.quota_repository import (
    GLOBAL_GEMINI_FREE_LIMIT,
    fetch_quota_used,
    increment_quota_used,
)
from utils.database.runtime import connect_processing_db
from utils.database.task_db import _get_db_settings  # type: ignore


def _connect():
    # P2: jadvallar startup migratsiyasida ensure qilinadi — bu yerda DDL yo'q.
    settings = _get_db_settings()
    return connect_processing_db(timeout=settings.db_connection_timeout, row_factory=True)


def _status(used: int) -> dict:
    limit = GLOBAL_GEMINI_FREE_LIMIT
    return {
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
        "exhausted": used >= limit,
    }


def get_global_quota_status(company_id: int, module_key: str) -> dict:
    """{used, limit, remaining, exhausted} — global kalit kvotasi (per company+module)."""
    conn = _connect()
    try:
        return _status(fetch_quota_used(conn, company_id, module_key))
    finally:
        conn.close()


def increment_global_quota(company_id: int, module_key: str) -> dict:
    """Bir global-kalit run hisobga olinadi (+1). Yangi statusni qaytaradi."""
    conn = _connect()
    try:
        return _status(increment_quota_used(conn, company_id, module_key))
    finally:
        conn.close()
