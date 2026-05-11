"""
Auth DB bootstrap helpers.

`auth_db.py` ichidagi sqlite-only init/backup/migration orchestration qismini
ajratish uchun vaqtinchalik modul.
"""
from __future__ import annotations

import os
import shutil
import time
from typing import Callable, Optional

from utils.database.runtime import get_auth_db_path, is_sqlite_backend
from utils.auth.auth_schema import (
    create_core_auth_tables,
    migrate_user_credentials,
    migrate_figma_tokens,
    migrate_global_settings,
    migrate_platform_admins,
    migrate_gemini_model,
    migrate_webhook_credentials,
    migrate_login_attempts,
    migrate_login_audit_logs,
    migrate_user_password_reset_tokens,
    migrate_web_sessions,
    migrate_user_roles,
    migrate_company_subscriptions,
)
from utils.auth.repository_common import execute


AUTH_DB_FILE = get_auth_db_path()


def is_old_auth_schema(conn) -> bool:
    """
    Eski schema (v3): companies bor, users yo'q.
    Yangi schema (v4): users jadvali mavjud.
    """
    has_users = execute(
        conn,
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'",
    ).fetchone() is not None
    if has_users:
        return False
    has_companies = execute(
        conn,
        "SELECT name FROM sqlite_master WHERE type='table' AND name='companies'",
    ).fetchone() is not None
    return has_companies


def backup_old_auth_db(auth_db_file: str = AUTH_DB_FILE) -> Optional[str]:
    if not os.path.exists(auth_db_file):
        return None
    ts = time.strftime('%Y%m%d_%H%M%S')
    backup_path = f"{auth_db_file}.old-{ts}"
    shutil.move(auth_db_file, backup_path)
    for suffix in ("-wal", "-shm"):
        wal = auth_db_file + suffix
        if os.path.exists(wal):
            shutil.move(wal, backup_path + suffix)
    return backup_path


def maybe_backup_legacy_auth_db(get_conn: Callable[[], object], auth_db_file: str = AUTH_DB_FILE) -> Optional[str]:
    if not is_sqlite_backend() or not os.path.exists(auth_db_file):
        return None
    conn = None
    try:
        conn = get_conn()
        if is_old_auth_schema(conn):
            return backup_old_auth_db(auth_db_file)
    except Exception:
        return None
    finally:
        if conn:
            conn.close()
    return None


def run_auth_schema_bootstrap(
    conn,
    *,
    default_plan_name: str,
    default_billing_mode: str,
) -> None:
    if not is_sqlite_backend():
        _ensure_postgres_auth_runtime_tables(conn)
        return
    create_core_auth_tables(conn)
    migrate_user_credentials(conn)
    migrate_figma_tokens(conn)
    migrate_gemini_model(conn)
    migrate_webhook_credentials(conn)
    migrate_login_attempts(conn)
    migrate_login_audit_logs(conn)
    migrate_user_password_reset_tokens(conn)
    migrate_web_sessions(conn)
    migrate_global_settings(conn)
    migrate_platform_admins(conn)
    migrate_user_roles(conn)
    migrate_company_subscriptions(conn, default_plan_name, default_billing_mode)


def _ensure_postgres_auth_runtime_tables(conn) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS platform_admins (
            id BIGSERIAL PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_password_reset_tokens (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMPTZ NOT NULL,
            used_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS web_sessions (
            id BIGSERIAL PRIMARY KEY,
            session_token_hash TEXT NOT NULL UNIQUE,
            user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
            company_id BIGINT REFERENCES companies(id) ON DELETE CASCADE,
            role TEXT NOT NULL DEFAULT '',
            auth_payload TEXT NOT NULL DEFAULT '{}',
            company_modules TEXT NOT NULL DEFAULT '{}',
            expires_at TIMESTAMPTZ NOT NULL,
            last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            revoked_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_web_sessions_expires_at ON web_sessions(expires_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_web_sessions_user_id ON web_sessions(user_id)")
    conn.commit()
