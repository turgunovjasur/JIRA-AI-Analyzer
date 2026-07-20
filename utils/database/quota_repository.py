"""Global (QA ASSISTANT) Gemini kalit uchun bepul-urinish kvota hisoblagichi.

Kompaniya/user o'z Gemini kalitiga ega bo'lmasa, platforma (super-admin) global
default kalitidan foydalanadi. Har modul (tz_pr_checker / testcase_generator) uchun
ALOHIDA sozlanadigan miqdorda tekin run beriladi (per company_id).
Limit tugagach o'sha modul bloklanadi; ikkinchi modul o'z kvotasigacha ishlayveradi.
"""
from __future__ import annotations

from datetime import datetime, timezone

from utils.database.repository_common import execute

# Global setting hali saqlanmagan eski muhitlar uchun fallback.
DEFAULT_GLOBAL_GEMINI_FREE_LIMIT = 3
# Backward compatibility: mavjud import/testlar uchun alias.
GLOBAL_GEMINI_FREE_LIMIT = DEFAULT_GLOBAL_GEMINI_FREE_LIMIT


def ensure_quota_tables(conn) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS global_gemini_quota (
            company_id BIGINT NOT NULL,
            module_key TEXT NOT NULL,
            used_count INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (company_id, module_key)
        )
        """
    )
    conn.commit()


def _row_used(row) -> int:
    if not row:
        return 0
    if isinstance(row, dict):
        return int(row.get("used_count") or 0)
    return int(row[0] or 0)


def fetch_quota_used(conn, company_id: int, module_key: str) -> int:
    cursor = execute(
        conn,
        "SELECT used_count FROM global_gemini_quota WHERE company_id = ? AND module_key = ?",
        [int(company_id), str(module_key)],
    )
    return _row_used(cursor.fetchone())


def increment_quota_used(conn, company_id: int, module_key: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    execute(
        conn,
        """
        INSERT INTO global_gemini_quota (company_id, module_key, used_count, updated_at)
        VALUES (?, ?, 1, ?)
        ON CONFLICT (company_id, module_key)
        DO UPDATE SET used_count = global_gemini_quota.used_count + 1, updated_at = ?
        """,
        [int(company_id), str(module_key), now, now],
    )
    conn.commit()
    return fetch_quota_used(conn, company_id, module_key)
