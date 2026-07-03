"""
User repository helpers.

`auth_db.py` ichidagi user CRUD, credentials va per-user settings querylarini
bosqichma-bosqich ajratish uchun repository qatlam.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

from utils.auth.credential_crypto import (
    can_encrypt_credentials,
    decrypt_sensitive_fields,
    encrypt_sensitive_fields,
    payload_requires_encryption,
)
from utils.auth.repository_common import execute, row_to_dict


def _column_names(conn, table_name: str) -> set[str]:
    try:
        rows = execute(
            conn,
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ?
            """,
            [table_name],
        ).fetchall()
        return {row[0] if not isinstance(row, dict) else row["column_name"] for row in rows}
    except Exception:
        return set()


def count_users_in_company(get_conn: Callable, company_id: int) -> int:
    try:
        conn = get_conn()
        result = execute(
            conn,
            "SELECT COUNT(*) FROM users WHERE company_id = ? AND role = ?",
            [company_id, "user"],
        ).fetchone()[0]
        conn.close()
        return int(result)
    except Exception:
        return 0


def insert_user(
    get_conn: Callable,
    company_id: int,
    full_username: str,
    password_hash: str,
    role: str,
) -> Tuple[Optional[int], Optional[str]]:
    try:
        conn = get_conn()
        payload = [company_id, full_username, password_hash, role]
        row = execute(
            conn,
            "INSERT INTO users (company_id, username, password_hash, role) VALUES (?,?,?,?) RETURNING id",
            payload,
        ).fetchone()
        user_id = row["id"] if isinstance(row, dict) else row[0]
        conn.commit()
        conn.close()
        return user_id, None
    except Exception as exc:
        error_text = str(exc).lower()
        if "unique" in error_text or "duplicate" in error_text:
            return None, f"Bu username allaqachon mavjud: '{full_username}'"
        return None, f"Xato yuz berdi: {exc}"


def fetch_user_by_id(get_conn: Callable, user_id: int) -> Optional[Dict]:
    try:
        conn = get_conn()
        row = execute(conn, "SELECT * FROM users WHERE id = ?", [user_id]).fetchone()
        conn.close()
        return row_to_dict(row) if row else None
    except Exception:
        return None


def fetch_user_by_id_and_company(get_conn: Callable, user_id: int, company_id: int) -> Optional[Dict]:
    try:
        conn = get_conn()
        row = execute(conn, "SELECT * FROM users WHERE id = ? AND company_id = ?", [user_id, company_id]).fetchone()
        conn.close()
        return row_to_dict(row) if row else None
    except Exception:
        return None


def fetch_user_by_full_username(get_conn: Callable, full_username: str) -> Optional[Dict]:
    try:
        conn = get_conn()
        row = execute(conn, "SELECT * FROM users WHERE username = ?", [full_username.strip().lower()]).fetchone()
        conn.close()
        return row_to_dict(row) if row else None
    except Exception:
        return None


def fetch_users_by_company(get_conn: Callable, company_id: int) -> List[Dict]:
    try:
        conn = get_conn()
        rows = execute(
            conn,
            "SELECT * FROM users WHERE company_id = ? "
            "ORDER BY CASE role WHEN 'company_admin' THEN 0 ELSE 1 END, created_at ASC",
            [company_id]
        ).fetchall()
        conn.close()
        return [row_to_dict(r) for r in rows]
    except Exception:
        return []


def update_user_password_hash(get_conn: Callable, user_id: int, password_hash: str) -> bool:
    try:
        conn = get_conn()
        execute(conn, "UPDATE users SET password_hash = ? WHERE id = ?", [password_hash, user_id])
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def update_user_status_value(get_conn: Callable, user_id: int, is_active: bool) -> bool:
    try:
        conn = get_conn()
        execute(conn, "UPDATE users SET is_active = ? WHERE id = ?", [bool(is_active), user_id])
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def update_user_role_value(get_conn: Callable, user_id: int, role: str) -> bool:
    try:
        conn = get_conn()
        execute(conn, "UPDATE users SET role = ? WHERE id = ?", [role, user_id])
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def delete_user_by_id(get_conn: Callable, user_id: int) -> bool:
    try:
        conn = get_conn()
        execute(conn, "DELETE FROM users WHERE id = ?", [user_id])
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def fetch_user_credentials(get_conn: Callable, user_id: int) -> Dict:
    try:
        conn = get_conn()
        row = execute(conn, "SELECT * FROM user_credentials WHERE user_id = ?", [user_id]).fetchone()
        columns = _column_names(conn, "user_credentials")
        conn.close()
        if not row:
            return {}
        row_dict = row_to_dict(row)
        if "jira_token_encrypted" in columns:
            row_dict = {
                "user_id": row_dict.get("user_id"),
                "jira_server": row_dict.get("jira_server", ""),
                "jira_email": row_dict.get("jira_email", ""),
                "jira_token": row_dict.get("jira_token_encrypted", ""),
                "jira_project_keys": row_dict.get("jira_project_keys", ""),
                "github_token": row_dict.get("github_token_encrypted", ""),
                "github_org": row_dict.get("github_org", ""),
                "figma_token": row_dict.get("figma_token_encrypted", ""),
                "figma_tokens": row_dict.get("figma_tokens_encrypted", "[]")
                if isinstance(row_dict.get("figma_tokens_encrypted"), str)
                else json.dumps(row_dict.get("figma_tokens_encrypted") or [], ensure_ascii=True),
                "gemini_api_key_1": row_dict.get("gemini_api_key_1_encrypted", ""),
                "gemini_api_key_2": row_dict.get("gemini_api_key_2_encrypted", ""),
                "updated_at": row_dict.get("updated_at"),
            }
        result = decrypt_sensitive_fields(row_dict)
        result.pop("gemini_model", None)
        return result
    except Exception:
        return {}


def upsert_user_credentials(get_conn: Callable, user_id: int, filtered_data: Dict) -> bool:
    if not filtered_data:
        return False
    if payload_requires_encryption(filtered_data) and not can_encrypt_credentials():
        return False
    payload = encrypt_sensitive_fields(dict(filtered_data))
    payload['updated_at'] = datetime.now().isoformat()
    try:
        conn = get_conn()
        columns = _column_names(conn, "user_credentials")
        c = execute(conn, "SELECT user_id FROM user_credentials WHERE user_id = ?", [user_id])
        exists = c.fetchone()
        if "jira_token_encrypted" in columns:
            mapped_payload = {
                "jira_server": payload.get("jira_server", ""),
                "jira_email": payload.get("jira_email", ""),
                "jira_token_encrypted": payload.get("jira_token", ""),
                "jira_project_keys": payload.get("jira_project_keys", ""),
                "github_token_encrypted": payload.get("github_token", ""),
                "github_org": payload.get("github_org", ""),
                "figma_token_encrypted": payload.get("figma_token", ""),
                "figma_tokens_encrypted": payload.get("figma_tokens", "[]"),
                "gemini_api_key_1_encrypted": payload.get("gemini_api_key_1", ""),
                "gemini_api_key_2_encrypted": payload.get("gemini_api_key_2", ""),
                "updated_at": payload.get("updated_at"),
            }
            if exists:
                execute(
                    conn,
                    """
                    UPDATE user_credentials
                    SET jira_server = ?,
                        jira_email = ?,
                        jira_token_encrypted = ?,
                        jira_project_keys = ?,
                        github_token_encrypted = ?,
                        github_org = ?,
                        figma_token_encrypted = ?,
                        figma_tokens_encrypted = ?::jsonb,
                        gemini_api_key_1_encrypted = ?,
                        gemini_api_key_2_encrypted = ?,
                        updated_at = ?
                    WHERE user_id = ?
                    """,
                    [
                        mapped_payload["jira_server"],
                        mapped_payload["jira_email"],
                        mapped_payload["jira_token_encrypted"],
                        mapped_payload["jira_project_keys"],
                        mapped_payload["github_token_encrypted"],
                        mapped_payload["github_org"],
                        mapped_payload["figma_token_encrypted"],
                        mapped_payload["figma_tokens_encrypted"],
                        mapped_payload["gemini_api_key_1_encrypted"],
                        mapped_payload["gemini_api_key_2_encrypted"],
                        mapped_payload["updated_at"],
                        user_id,
                    ],
                )
            else:
                execute(
                    conn,
                    """
                    INSERT INTO user_credentials (
                        user_id, jira_server, jira_email, jira_token_encrypted, jira_project_keys,
                        github_token_encrypted, github_org, figma_token_encrypted,
                        figma_tokens_encrypted, gemini_api_key_1_encrypted,
                        gemini_api_key_2_encrypted, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?, ?, ?)
                    """,
                    [
                        user_id,
                        mapped_payload["jira_server"],
                        mapped_payload["jira_email"],
                        mapped_payload["jira_token_encrypted"],
                        mapped_payload["jira_project_keys"],
                        mapped_payload["github_token_encrypted"],
                        mapped_payload["github_org"],
                        mapped_payload["figma_token_encrypted"],
                        mapped_payload["figma_tokens_encrypted"],
                        mapped_payload["gemini_api_key_1_encrypted"],
                        mapped_payload["gemini_api_key_2_encrypted"],
                        mapped_payload["updated_at"],
                    ],
                )
        else:
            if exists:
                set_clause = ", ".join(f"{k} = %s" for k in payload)
                values = list(payload.values()) + [user_id]
                execute(conn, f"UPDATE user_credentials SET {set_clause} WHERE user_id = ?", values)
            else:
                payload['user_id'] = user_id
                cols = ", ".join(payload.keys())
                placeholders = ", ".join("%s" for _ in payload)
                execute(
                    conn,
                    f"INSERT INTO user_credentials ({cols}) VALUES ({placeholders})",
                    list(payload.values())
                )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def fetch_user_module_settings(get_conn: Callable, user_id: int, module_key: str = None) -> Dict:
    try:
        conn = get_conn()
        if module_key:
            row = execute(
                conn,
                "SELECT settings_json FROM user_module_settings WHERE user_id = ? AND module_key = ?",
                [user_id, module_key]
            ).fetchone()
            conn.close()
            if not row:
                return {}
            try:
                row_dict = row_to_dict(row)
                raw = row_dict['settings_json']
                if isinstance(raw, dict):
                    return raw
                return json.loads(raw) or {}
            except (json.JSONDecodeError, TypeError):
                return {}

        rows = execute(
            conn,
            "SELECT module_key, settings_json FROM user_module_settings WHERE user_id = ?",
            [user_id]
        ).fetchall()
        conn.close()
        result = {}
        for row in rows:
            row_dict = row_to_dict(row)
            try:
                raw = row_dict['settings_json']
                result[row_dict['module_key']] = raw if isinstance(raw, dict) else (json.loads(raw) or {})
            except (json.JSONDecodeError, TypeError):
                result[row_dict['module_key']] = {}
        return result
    except Exception:
        return {}


def upsert_user_module_settings(get_conn: Callable, user_id: int, module_key: str, data: dict) -> bool:
    try:
        conn = get_conn()
        execute(
            conn,
            """
            INSERT INTO user_module_settings (user_id, module_key, settings_json, updated_at)
            VALUES (?, ?, ?::jsonb, ?)
            ON CONFLICT(user_id, module_key) DO UPDATE SET
              settings_json = excluded.settings_json,
              updated_at    = excluded.updated_at
            """,
            [user_id, module_key, json.dumps(data or {}, ensure_ascii=True), datetime.now().isoformat()]
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
