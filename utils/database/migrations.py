"""
P2: Versiyalangan schema migratsiya runner.

Maqsad:
- `schema_migrations` jadvali qaysi SQL migratsiya qo'llanganini saqlaydi
  (har migratsiya bir martadan, tartib bilan).
- `database/postgresql/NNN_*.sql` fayllar raqam tartibida qo'llanadi.
- Runtime jadvallar (run-repo + auth web_sessions) startup'da BIR MARTA ensure
  qilinadi — endi har DB ulanishida emas (hot-path DDL olib tashlandi).

Bu funksiya barcha kirish nuqtalarida (webhook lifespan, worker, monitoring,
testlar) ishga tushishda chaqiriladi. Idempotent: takror chaqirish xavfsiz.
"""
from __future__ import annotations

import glob
import os
import threading

from core.logger import get_logger
from utils.database.runtime import connect_processing_db, get_postgres_dsn

log = get_logger("database.migrations")

_MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "database",
    "postgresql",
)

_SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

_lock = threading.Lock()
_applied_for_dsn: str | None = None


def _applied_versions(conn) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT version FROM schema_migrations")
        return {row[0] for row in cur.fetchall()}


def _record(conn, version: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO schema_migrations (version) VALUES (%s) "
            "ON CONFLICT (version) DO NOTHING",
            [version],
        )


def _sql_migration_files() -> list[tuple[str, str]]:
    """(version, path) — `NNN_*.sql` fayllar raqam bo'yicha tartiblangan."""
    paths = glob.glob(os.path.join(_MIGRATIONS_DIR, "[0-9][0-9][0-9]_*.sql"))
    out: list[tuple[str, str]] = []
    for path in sorted(paths, key=lambda p: os.path.basename(p)):
        version = os.path.splitext(os.path.basename(path))[0]
        out.append((version, path))
    return out


def _ensure_runtime_tables(conn) -> None:
    """Run-repo va auth runtime jadvallarini idempotent yaratish (startup'da bir marta).

    Bu jadvallar (checker_*, analysis_*, job_queue*, web_sessions) 001 baseline'da
    yo'q — ilgari har ulanishda `ensure_*` orqali yaratilardi (hot-path DDL).
    Endi faqat shu yerda, startup'da bir marta. Hammasi `CREATE TABLE IF NOT EXISTS`.
    """
    from utils.database.job_queue_repository import ensure_job_queue_tables
    from utils.database.checker_run_repository import ensure_checker_run_tables
    from utils.database.ai_usage_repository import ensure_ai_usage_tables
    from utils.database.analysis_run_repository import ensure_analysis_run_tables
    from utils.auth.auth_bootstrap import _ensure_postgres_auth_runtime_tables

    ensure_job_queue_tables(conn)
    ensure_checker_run_tables(conn)
    ensure_ai_usage_tables(conn)
    ensure_analysis_run_tables(conn)
    _ensure_postgres_auth_runtime_tables(conn)
    conn.commit()


def run_migrations(*, force: bool = False) -> None:
    """Pending SQL migratsiyalarni qo'llash + runtime jadvallarni ensure qilish.

    DSN bo'yicha keshlangan: bir xil DSN uchun startup'da bir marta bajariladi
    (DSN o'zgarsa — masalan testlar — qayta ishlaydi). `force=True` keshни chetlaydi.
    """
    global _applied_for_dsn
    dsn = get_postgres_dsn()
    if not dsn:
        raise RuntimeError("APP_POSTGRES_DSN bo'sh. Migratsiya ishga tushmaydi.")
    if not force and _applied_for_dsn == dsn:
        return

    with _lock:
        if not force and _applied_for_dsn == dsn:
            return

        conn = connect_processing_db()
        try:
            with conn.cursor() as cur:
                cur.execute(_SCHEMA_MIGRATIONS_DDL)
            conn.commit()

            applied = _applied_versions(conn)
            for version, path in _sql_migration_files():
                if version in applied:
                    continue
                with open(path, encoding="utf-8") as fh:
                    sql_text = fh.read()
                try:
                    # SQL fayl ko'p statementli + parametrsiz — xom cursor (simple protocol).
                    with conn.cursor() as cur:
                        cur.execute(sql_text)
                    _record(conn, version)
                    conn.commit()
                    log.info(f"migration applied: {version}")
                except Exception:
                    conn.rollback()
                    log.error(f"migration failed: {version}", exc_info=True)
                    raise

            _ensure_runtime_tables(conn)
        finally:
            conn.close()

        _applied_for_dsn = dsn
