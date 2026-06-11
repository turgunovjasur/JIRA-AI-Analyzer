"""
Auth DB bootstrap helpers.
"""
from __future__ import annotations


def run_auth_bootstrap(
    conn,
    *,
    default_plan_name: str,
    default_billing_mode: str,
) -> None:
    _ensure_postgres_auth_runtime_tables(conn)


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
