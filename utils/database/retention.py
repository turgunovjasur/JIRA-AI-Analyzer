"""
DB retention: eski terminal run/job/usage yozuvlarini davriy tozalash.

Audit HIGH (Baza): `checker_runs`, `analysis_runs`, `job_queue`, `ai_usage_events`
hech qachon tozalanmaydi → oylar davomida DB shishadi va monitoring so'rovlari
sekinlashadi (faqat `web_sessions` tozalanardi). Worker davriy (default kuniga
bir) shu tozalashni chaqiradi.

Bola-jadvallar FK `ON DELETE CASCADE` bilan avtomatik o'chadi
(`checker_agent_runs`, `checker_run_events`, `analysis_*`, `job_queue_runs`) —
shuning uchun faqat parent jadvallardan o'chiramiz.

Vaqt oynasi env orqali sozlanadi. `ai_usage_events` — xarajat/billing leggeri,
shuning uchun ancha uzunroq default (per-company oylik hisobot uchun kerak).
"""
from __future__ import annotations

import os

from core.logger import get_logger
from utils.database.repository_common import execute
from utils.database.runtime import connect_processing_db

log = get_logger("database.retention")


def _env_days(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def retention_enabled() -> bool:
    raw = (os.getenv("APP_RETENTION_ENABLED") or "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


# (jadval, yosh-ustuni ifodasi, kun-env, default-kun, qo'shimcha-shart)
# TIMESTAMPTZ ustunlar NOW() (timestamptz) bilan solishtiriladi — app yozuvi
# UTC-aware bo'lsa ham to'g'ri; retention oynasi (kunlar) uchun soatlik timezone
# nomuvofiqligi ahamiyatsiz.
def _retention_plan() -> list[tuple[str, str, int, str]]:
    run_days = _env_days("APP_RETENTION_RUN_DAYS", 90)
    job_days = _env_days("APP_RETENTION_JOB_DAYS", 30)
    usage_days = _env_days("APP_RETENTION_USAGE_DAYS", 365)
    return [
        ("checker_runs", "COALESCE(finished_at, updated_at, created_at)", run_days, ""),
        ("analysis_runs", "COALESCE(finished_at, updated_at, created_at)", run_days, ""),
        # Faqat terminal joblar; queued/running reaper zimmasida.
        ("job_queue", "COALESCE(finished_at, updated_at, created_at)", job_days, "status IN ('done', 'failed')"),
        ("ai_usage_events", "created_at", usage_days, ""),
    ]


def run_retention_cleanup() -> dict[str, int]:
    """Eski yozuvlarni o'chiradi. Har jadval alohida tranzaksiyada — biri fail
    bo'lsa qolganlariga xalal bermaydi. {jadval: o'chirilgan_soni} qaytaradi."""
    if not retention_enabled():
        return {}

    results: dict[str, int] = {}
    conn = connect_processing_db()
    try:
        for table, age_expr, days, extra in _retention_plan():
            where = f"WHERE {age_expr} < NOW() - make_interval(days => ?)"
            if extra:
                where += f" AND {extra}"
            try:
                cur = execute(conn, f"DELETE FROM {table} {where}", [days])
                deleted = cur.rowcount or 0
                conn.commit()
                if deleted:
                    results[table] = deleted
                    log.info(f"retention: {table} dan {deleted} ta eski yozuv o'chirildi (>{days}d)")
            except Exception:
                conn.rollback()
                log.warning(f"retention: {table} tozalash xatosi", exc_info=True)
    finally:
        conn.close()
    return results
