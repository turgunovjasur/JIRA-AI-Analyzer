"""
Auth DB schema and migration helpers.

`auth_db.py` ichidagi init/migration bo'limlarini ajratish uchun vaqtinchalik
modul. Keyingi bosqichda bu qatlam `PostgreSQL` schema migratsiyalariga
almashtiriladi.
"""
from __future__ import annotations

from datetime import datetime
import sqlite3


def create_core_auth_tables(conn: sqlite3.Connection) -> None:
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS companies (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            company_code TEXT    UNIQUE NOT NULL,
            company_name TEXT    NOT NULL,
            seat_limit   INTEGER DEFAULT 1,
            is_active    INTEGER DEFAULT 1,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id    INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            username      TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            role          TEXT    NOT NULL DEFAULT 'user',
            is_active     INTEGER DEFAULT 1,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_company ON users(company_id)")

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS company_settings (
            company_id       INTEGER PRIMARY KEY REFERENCES companies(id) ON DELETE CASCADE,
            jira_server      TEXT DEFAULT '',
            jira_email       TEXT DEFAULT '',
            jira_token       TEXT DEFAULT '',
            jira_project_keys TEXT DEFAULT '',
            github_token     TEXT DEFAULT '',
            github_org       TEXT DEFAULT '',
            figma_token      TEXT DEFAULT '',
            figma_tokens     TEXT DEFAULT '[]',
            gemini_api_key_1 TEXT DEFAULT '',
            gemini_api_key_2 TEXT DEFAULT '',
            gemini_model     TEXT DEFAULT '',
            webhook_jira_server      TEXT DEFAULT '',
            webhook_jira_email       TEXT DEFAULT '',
            webhook_jira_token       TEXT DEFAULT '',
            webhook_github_token     TEXT DEFAULT '',
            webhook_github_org       TEXT DEFAULT '',
            webhook_figma_token      TEXT DEFAULT '',
            webhook_figma_tokens     TEXT DEFAULT '[]',
            webhook_gemini_api_key_1 TEXT DEFAULT '',
            webhook_gemini_api_key_2 TEXT DEFAULT '',
            webhook_gemini_model     TEXT DEFAULT '',
            enabled_modules  TEXT DEFAULT '{}',
            webhook_project_keys        TEXT DEFAULT '',
            webhook_trigger_status      TEXT DEFAULT '',
            webhook_trigger_aliases     TEXT DEFAULT '',
            webhook_return_status       TEXT DEFAULT '',
            webhook_allowed_issue_types TEXT DEFAULT '',
            webhook_excluded_assignees  TEXT DEFAULT '',
            webhook_auto_return_enabled INTEGER DEFAULT 0,
            webhook_return_threshold    INTEGER DEFAULT 60,
            webhook_module_settings     TEXT DEFAULT '{}',
            updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS user_module_settings (
            user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            module_key    TEXT    NOT NULL,
            settings_json TEXT    NOT NULL DEFAULT '{}',
            updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, module_key)
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS user_credentials (
            user_id          INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            jira_server      TEXT DEFAULT '',
            jira_email       TEXT DEFAULT '',
            jira_token       TEXT DEFAULT '',
            github_token     TEXT DEFAULT '',
            github_org       TEXT DEFAULT '',
            figma_token      TEXT DEFAULT '',
            gemini_api_key_1 TEXT DEFAULT '',
            gemini_api_key_2 TEXT DEFAULT '',
            updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (table_name,))
    return c.fetchone() is not None


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in c.fetchall()}


def migrate_user_credentials(conn: sqlite3.Connection) -> None:
    c = conn.cursor()
    if not _table_exists(conn, "user_credentials"):
        c.execute(
            """
            CREATE TABLE user_credentials (
                user_id            INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                jira_server        TEXT DEFAULT '',
                jira_email         TEXT DEFAULT '',
                jira_token         TEXT DEFAULT '',
                jira_project_keys  TEXT DEFAULT '',
                github_token       TEXT DEFAULT '',
                github_org         TEXT DEFAULT '',
                figma_token        TEXT DEFAULT '',
                gemini_api_key_1   TEXT DEFAULT '',
                gemini_api_key_2   TEXT DEFAULT '',
                updated_at         DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        return

    cols = _table_columns(conn, "user_credentials")
    if "jira_project_keys" not in cols:
        c.execute("ALTER TABLE user_credentials ADD COLUMN jira_project_keys TEXT DEFAULT ''")
    if "figma_tokens" not in cols:
        c.execute("ALTER TABLE user_credentials ADD COLUMN figma_tokens TEXT DEFAULT '[]'")
    conn.commit()


def migrate_figma_tokens(conn: sqlite3.Connection) -> None:
    c = conn.cursor()
    for table in ("company_settings", "user_credentials"):
        cols = _table_columns(conn, table)
        if table == "company_settings" and "jira_project_keys" not in cols:
            c.execute("ALTER TABLE company_settings ADD COLUMN jira_project_keys TEXT DEFAULT ''")
        if "figma_tokens" not in cols:
            c.execute(f"ALTER TABLE {table} ADD COLUMN figma_tokens TEXT DEFAULT '[]'")
    conn.commit()


def migrate_global_settings(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "global_settings"):
        return
    conn.execute(
        """
        CREATE TABLE global_settings (
            key   TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        )
        """
    )
    conn.commit()


def migrate_platform_admins(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "platform_admins"):
        return
    conn.execute(
        """
        CREATE TABLE platform_admins (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_active     INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def migrate_gemini_model(conn: sqlite3.Connection) -> None:
    c = conn.cursor()
    for table in ("user_credentials", "company_settings"):
        cols = _table_columns(conn, table)
        if "gemini_model" not in cols:
            c.execute(f"ALTER TABLE {table} ADD COLUMN gemini_model TEXT DEFAULT ''")
    conn.commit()


def migrate_webhook_credentials(conn: sqlite3.Connection) -> None:
    c = conn.cursor()
    cols = _table_columns(conn, "company_settings")
    desired_columns = {
        "webhook_jira_server": "TEXT DEFAULT ''",
        "webhook_jira_email": "TEXT DEFAULT ''",
        "webhook_jira_token": "TEXT DEFAULT ''",
        "webhook_github_token": "TEXT DEFAULT ''",
        "webhook_github_org": "TEXT DEFAULT ''",
        "webhook_figma_token": "TEXT DEFAULT ''",
        "webhook_figma_tokens": "TEXT DEFAULT '[]'",
        "webhook_gemini_api_key_1": "TEXT DEFAULT ''",
        "webhook_gemini_api_key_2": "TEXT DEFAULT ''",
        "webhook_gemini_model": "TEXT DEFAULT ''",
    }
    for column_name, column_sql in desired_columns.items():
        if column_name not in cols:
            c.execute(f"ALTER TABLE company_settings ADD COLUMN {column_name} {column_sql}")
    conn.commit()


def migrate_login_attempts(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "login_attempts"):
        return
    conn.execute(
        """
        CREATE TABLE login_attempts (
            identifier   TEXT PRIMARY KEY,
            failed_count INTEGER DEFAULT 0,
            locked_until TEXT    DEFAULT NULL,
            updated_at   TEXT    DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def migrate_login_audit_logs(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "login_audit_logs"):
        return
    conn.execute(
        """
        CREATE TABLE login_audit_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier TEXT NOT NULL,
            user_id    INTEGER DEFAULT NULL,
            company_id INTEGER DEFAULT NULL,
            role       TEXT DEFAULT '',
            success    INTEGER NOT NULL DEFAULT 0,
            reason     TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def migrate_user_password_reset_tokens(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "user_password_reset_tokens"):
        return
    conn.execute(
        """
        CREATE TABLE user_password_reset_tokens (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            used_at    TEXT DEFAULT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def migrate_web_sessions(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "web_sessions"):
        return
    conn.execute(
        """
        CREATE TABLE web_sessions (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            session_token_hash TEXT NOT NULL UNIQUE,
            user_id            INTEGER DEFAULT NULL REFERENCES users(id) ON DELETE CASCADE,
            company_id         INTEGER DEFAULT NULL REFERENCES companies(id) ON DELETE CASCADE,
            role               TEXT DEFAULT '',
            auth_payload       TEXT NOT NULL DEFAULT '{}',
            company_modules    TEXT NOT NULL DEFAULT '{}',
            expires_at         TEXT NOT NULL,
            last_seen_at       TEXT DEFAULT CURRENT_TIMESTAMP,
            revoked_at         TEXT DEFAULT NULL,
            created_at         TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_web_sessions_expires_at ON web_sessions(expires_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_web_sessions_user_id ON web_sessions(user_id)")
    conn.commit()


def migrate_user_roles(conn: sqlite3.Connection) -> None:
    if "role" in _table_columns(conn, "users"):
        return
    conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
    conn.commit()


def migrate_company_subscriptions(
    conn: sqlite3.Connection,
    default_plan_name: str,
    default_billing_mode: str,
) -> None:
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS company_subscriptions (
            company_id          INTEGER PRIMARY KEY REFERENCES companies(id) ON DELETE CASCADE,
            plan_name           TEXT DEFAULT 'base',
            subscription_status TEXT DEFAULT 'trial',
            billing_mode        TEXT DEFAULT 'manual',
            billing_start_date  TEXT DEFAULT '',
            billing_end_date    TEXT DEFAULT '',
            next_payment_date   TEXT DEFAULT '',
            last_payment_date   TEXT DEFAULT '',
            last_payment_note   TEXT DEFAULT '',
            created_at          TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at          TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute(
        """
        INSERT INTO company_subscriptions (
            company_id, plan_name, subscription_status, billing_mode,
            billing_start_date, billing_end_date, next_payment_date, updated_at
        )
        SELECT
            id, ?, 'active', ?, '', '', '', ?
        FROM companies
        WHERE id NOT IN (SELECT company_id FROM company_subscriptions)
        """,
        (default_plan_name, default_billing_mode, datetime.now().isoformat()),
    )
    conn.commit()
