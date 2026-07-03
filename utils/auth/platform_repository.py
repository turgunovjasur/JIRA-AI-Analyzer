"""
Platform/auth supporting repository helpers.

Global settings va login attempt querylarini `auth_db.py`dan ajratish uchun.
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable, Dict, List

from utils.auth.credential_crypto import (
    can_encrypt_credentials,
    decrypt_value,
    encrypt_value,
    is_sensitive_credential_field,
)
from utils.auth.repository_common import execute, row_to_dict


def fetch_global_setting(get_conn: Callable, key: str, default: str = '') -> str:
    try:
        conn = get_conn()
        row = execute(conn, "SELECT value FROM global_settings WHERE key = ?", [key]).fetchone()
        conn.close()
        row_dict = row_to_dict(row) if row else {}
        if not row:
            return default
        value = (row_dict.get('value') or '').strip()
        if is_sensitive_credential_field(key):
            value = decrypt_value(value)
        return value
    except Exception:
        return default


def upsert_global_setting(get_conn: Callable, key: str, value: str) -> bool:
    try:
        conn = get_conn()
        stored_value = (value or '').strip()
        if is_sensitive_credential_field(key):
            if stored_value and not can_encrypt_credentials():
                conn.close()
                return False
            stored_value = encrypt_value(stored_value)
        execute(
            conn,
            "INSERT INTO global_settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            [key, stored_value]
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def fetch_login_attempt_state(get_conn: Callable, identifier: str) -> Dict | None:
    try:
        conn = get_conn()
        row = execute(conn, "SELECT * FROM login_attempts WHERE identifier = ?", [identifier]).fetchone()
        conn.close()
        return row_to_dict(row) if row else None
    except Exception:
        return None


def delete_login_attempt(get_conn: Callable, identifier: str) -> bool:
    try:
        conn = get_conn()
        execute(conn, "DELETE FROM login_attempts WHERE identifier = ?", [identifier])
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def upsert_login_attempt(get_conn: Callable, identifier: str, failed_count: int, locked_until: str | None) -> bool:
    try:
        conn = get_conn()
        execute(
            conn,
            """
            INSERT INTO login_attempts (identifier, failed_count, locked_until, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(identifier) DO UPDATE SET
                failed_count = excluded.failed_count,
                locked_until = excluded.locked_until,
                updated_at   = excluded.updated_at
            """,
            [identifier, failed_count, locked_until, datetime.now().isoformat()]
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def fetch_platform_admin_by_username(get_conn: Callable, username: str) -> Dict | None:
    try:
        conn = get_conn()
        row = execute(
            conn,
            "SELECT * FROM platform_admins WHERE username = ?",
            [(username or "").strip().lower()],
        ).fetchone()
        conn.close()
        return row_to_dict(row) if row else None
    except Exception:
        return None


def upsert_platform_admin(get_conn: Callable, username: str, password_hash: str, is_active: bool = True) -> bool:
    try:
        conn = get_conn()
        execute(
            conn,
            """
            INSERT INTO platform_admins (username, password_hash, is_active, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                password_hash = excluded.password_hash,
                is_active = excluded.is_active,
                updated_at = excluded.updated_at
            """,
            [
                (username or "").strip().lower(),
                password_hash,
                bool(is_active),
                datetime.now().isoformat(),
            ],
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def insert_login_audit_log(
    get_conn: Callable,
    *,
    identifier: str,
    success: bool,
    reason: str = "",
    user_id: int | None = None,
    company_id: int | None = None,
    role: str = "",
) -> bool:
    try:
        conn = get_conn()
        execute(
            conn,
            """
            INSERT INTO login_audit_logs
                (identifier, user_id, company_id, role, success, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (identifier or "").strip().lower(),
                user_id,
                company_id,
                role or "",
                1 if success else 0,
                reason or "",
                datetime.now().isoformat(),
            ],
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def fetch_login_audit_logs(
    get_conn: Callable,
    limit: int = 50,
    *,
    success: bool | None = None,
    identifier_contains: str = "",
) -> List[Dict]:
    try:
        conn = get_conn()
        conditions = []
        params = []
        if success is not None:
            conditions.append("success = ?")
            params.append(1 if success else 0)
        if identifier_contains.strip():
            conditions.append("LOWER(identifier) LIKE ?")
            params.append(f"%{identifier_contains.strip().lower()}%")
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = execute(
            conn,
            f"SELECT * FROM login_audit_logs {where_clause} ORDER BY created_at DESC LIMIT ?",
            params + [max(1, int(limit))],
        ).fetchall()
        conn.close()
        return [row_to_dict(row) for row in rows]
    except Exception:
        return []


def insert_password_reset_token(
    get_conn: Callable,
    *,
    user_id: int,
    token_hash: str,
    expires_at: str,
) -> bool:
    try:
        conn = get_conn()
        execute(
            conn,
            """
            INSERT INTO user_password_reset_tokens (user_id, token_hash, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            [user_id, token_hash, expires_at, datetime.now().isoformat()],
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def fetch_password_reset_token(get_conn: Callable, token_hash: str) -> Dict | None:
    try:
        conn = get_conn()
        row = execute(
            conn,
            "SELECT * FROM user_password_reset_tokens WHERE token_hash = ?",
            [token_hash],
        ).fetchone()
        conn.close()
        return row_to_dict(row) if row else None
    except Exception:
        return None


def mark_password_reset_token_used(get_conn: Callable, token_hash: str, *, used_at: str | None = None) -> bool:
    try:
        conn = get_conn()
        execute(
            conn,
            "UPDATE user_password_reset_tokens SET used_at = ? WHERE token_hash = ?",
            [used_at or datetime.now().isoformat(), token_hash],
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def insert_web_session(
    get_conn: Callable,
    *,
    session_token_hash: str,
    auth_payload: str,
    company_modules: str,
    expires_at: str,
    role: str = "",
    user_id: int | None = None,
    company_id: int | None = None,
) -> bool:
    try:
        now = datetime.now().isoformat()
        conn = get_conn()
        execute(
            conn,
            """
            INSERT INTO web_sessions (
                session_token_hash, user_id, company_id, role,
                auth_payload, company_modules, expires_at, last_seen_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                session_token_hash,
                user_id,
                company_id,
                role or "",
                auth_payload,
                company_modules,
                expires_at,
                now,
                now,
            ],
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def fetch_web_session(get_conn: Callable, session_token_hash: str) -> Dict | None:
    try:
        conn = get_conn()
        row = execute(
            conn,
            "SELECT * FROM web_sessions WHERE session_token_hash = ?",
            [session_token_hash],
        ).fetchone()
        conn.close()
        return row_to_dict(row) if row else None
    except Exception:
        return None


def touch_web_session(
    get_conn: Callable,
    session_token_hash: str,
    *,
    auth_payload: str,
    expires_at: str,
    last_seen_at: str | None = None,
    company_modules: str | None = None,
) -> bool:
    try:
        now = last_seen_at or datetime.now().isoformat()
        conn = get_conn()
        params = [auth_payload, expires_at, now]
        company_modules_sql = ""
        if company_modules is not None:
            company_modules_sql = ", company_modules = ?"
            params.append(company_modules)
        params.append(session_token_hash)
        execute(
            conn,
            f"""
            UPDATE web_sessions
            SET auth_payload = ?, expires_at = ?, last_seen_at = ?{company_modules_sql}
            WHERE session_token_hash = ? AND revoked_at IS NULL
            """,
            params,
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def revoke_web_session(
    get_conn: Callable,
    session_token_hash: str,
    *,
    revoked_at: str | None = None,
) -> bool:
    try:
        conn = get_conn()
        execute(
            conn,
            "UPDATE web_sessions SET revoked_at = ? WHERE session_token_hash = ? AND revoked_at IS NULL",
            [revoked_at or datetime.now().isoformat(), session_token_hash],
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def revoke_all_user_sessions(get_conn: Callable, user_id: int) -> int:
    """Foydalanuvchining barcha aktiv sessiyalarini bekor qilish. O'chirilgan soni qaytaradi."""
    try:
        now = datetime.now().isoformat()
        conn = get_conn()
        execute(
            conn,
            "UPDATE web_sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
            [now, user_id],
        )
        conn.commit()
        count = conn.execute(
            "SELECT changes()" if not hasattr(conn, "rowcount") else "SELECT 1"
        ).fetchone()
        conn.close()
        return count[0] if count else 0
    except Exception:
        return 0


def cleanup_expired_web_sessions(get_conn: Callable) -> int:
    """Muddati o'tgan va revoke qilingan sessiyalarni o'chirish. O'chirilgan soni qaytaradi."""
    try:
        now = datetime.now().isoformat()
        conn = get_conn()
        execute(
            conn,
            """
            DELETE FROM web_sessions
            WHERE expires_at < ?
               OR revoked_at IS NOT NULL
            """,
            [now],
        )
        conn.commit()
        count = conn.execute("SELECT changes()").fetchone()
        conn.close()
        return count[0] if count else 0
    except Exception:
        return 0


def insert_audit_log(
    get_conn: Callable,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str = "",
    company_id: int | None = None,
    actor_user_id: int | None = None,
    actor_role: str = "",
    event_payload: dict | None = None,
) -> bool:
    """audit_logs jadvaliga yozuv qo'shish."""
    import json as _json
    try:
        conn = get_conn()
        execute(
            conn,
            """
            INSERT INTO audit_logs
                (company_id, actor_user_id, actor_role, event_type, entity_type, entity_id, event_payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                company_id,
                actor_user_id,
                actor_role or "",
                event_type,
                entity_type,
                entity_id or "",
                _json.dumps(event_payload or {}),
                datetime.now().isoformat(),
            ],
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
