"""
P2: Versiyalangan migratsiya runner testlari.

Real PostgreSQL talab qiladi (conftest `APP_TEST_POSTGRES_DSN` bilan sozlaydi;
bo'lmasa skip). `no_db` marker QO'YILMAGAN — conftest fixture'i `init_db()` orqali
migratsiyani allaqachon ishga tushiradi.
"""
from utils.database.migrations import run_migrations
from utils.database.runtime import connect_processing_db


def _table_exists(conn, name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=%s",
            [name],
        )
        return cur.fetchone() is not None


def test_schema_migrations_table_records_baseline():
    conn = connect_processing_db(row_factory=True)
    try:
        assert _table_exists(conn, "schema_migrations")
        with conn.cursor() as cur:
            cur.execute("SELECT version FROM schema_migrations")
            versions = {row["version"] for row in cur.fetchall()}
        assert "001_initial_schema" in versions
    finally:
        conn.close()


def test_runtime_tables_created_by_migrations():
    # Run-repo + auth runtime jadvallar (001 baseline'da yo'q) startup'da yaratilgan.
    conn = connect_processing_db()
    try:
        for table in (
            "checker_runs",
            "checker_agent_runs",
            "checker_run_events",
            "analysis_runs",
            "job_queue",
            "web_sessions",
        ):
            assert _table_exists(conn, table), f"{table} yaratilmagan"
    finally:
        conn.close()


def test_run_migrations_is_idempotent():
    # force=True bilan qayta ishlatish xato bermaydi va versiyani takrorlamaydi.
    run_migrations(force=True)
    run_migrations(force=True)
    conn = connect_processing_db(row_factory=True)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS n FROM schema_migrations WHERE version=%s",
                ["001_initial_schema"],
            )
            assert cur.fetchone()["n"] == 1
    finally:
        conn.close()
