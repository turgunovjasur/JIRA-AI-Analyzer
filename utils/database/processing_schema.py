"""
Processing DB schema and migration helpers.

`task_db.py` ichidagi sqlite init/migration bo'limlarini ajratish uchun
vaqtinchalik modul. Keyingi bosqichda bu qatlam `PostgreSQL` migratsiya
qatlamiga almashtiriladi.
"""
from __future__ import annotations

import sqlite3


def apply_sqlite_processing_pragmas(conn: sqlite3.Connection, busy_timeout: int) -> None:
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute(f"PRAGMA busy_timeout={busy_timeout}")
    cursor.execute("PRAGMA foreign_keys=ON")


def create_core_processing_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS task_processing (
            task_id TEXT PRIMARY KEY,
            task_status TEXT DEFAULT 'none',
            task_update_time DATETIME,
            return_count INTEGER DEFAULT 0,
            last_jira_status TEXT,
            last_processed_at DATETIME,
            error_message TEXT NULL,
            skip_detected INTEGER DEFAULT 0,
            service1_status TEXT DEFAULT 'pending',
            service2_status TEXT DEFAULT 'pending',
            service1_error TEXT NULL,
            service2_error TEXT NULL,
            service1_done_at DATETIME NULL,
            service2_done_at DATETIME NULL,
            compliance_score INTEGER NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            assignee TEXT NULL,
            task_type TEXT NULL,
            feature_name TEXT NULL,
            technology_stack TEXT NULL,
            blocked_at DATETIME NULL,
            blocked_retry_at DATETIME NULL,
            block_reason TEXT NULL,
            company_id INTEGER NULL,
            return_reason TEXT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_task_status
        ON task_processing(task_status)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_service1_status
        ON task_processing(service1_status)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_service2_status
        ON task_processing(service2_status)
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS task_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT NOT NULL,
            changed_at DATETIME NOT NULL,
            assignee TEXT,
            story_points REAL,
            issue_type TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_history_task_id
        ON task_status_history(task_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_history_changed_at
        ON task_status_history(changed_at)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_history_assignee
        ON task_status_history(assignee)
        """
    )

    conn.commit()


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def migrate_task_processing_company_id(conn: sqlite3.Connection) -> None:
    if "company_id" in _table_columns(conn, "task_processing"):
        return
    conn.execute("ALTER TABLE task_processing ADD COLUMN company_id INTEGER NULL")
    conn.commit()


def migrate_task_processing_return_reason(conn: sqlite3.Connection) -> None:
    if "return_reason" in _table_columns(conn, "task_processing"):
        return
    conn.execute("ALTER TABLE task_processing ADD COLUMN return_reason TEXT NULL")
    conn.commit()
