"""
Company repository helpers.

`auth_db.py` ichidagi company/subscription/settings querylarini bosqichma-bosqich
ajratish uchun vaqtinchalik repository qatlam.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from core.logger import get_logger
from utils.auth.credential_crypto import (
    can_encrypt_credentials,
    decrypt_sensitive_fields,
    encrypt_sensitive_fields,
    payload_requires_encryption,
)
from utils.auth.repository_common import execute, row_to_dict

log = get_logger("auth.company_repo")

SUBSCRIPTION_DATE_FIELDS = {
    "billing_start_date",
    "billing_end_date",
    "next_payment_date",
    "last_payment_date",
}


def _ensure_companies_seat_limit_allows_zero(conn) -> None:
    """
    Legacy PostgreSQL sxemalarda `companies_seat_limit_check` >=1 bo'lishi mumkin.
    Yangi product qoidasiga ko'ra seat_limit 0 ham ruxsat etiladi.
    """
    try:
        execute(conn, "ALTER TABLE companies DROP CONSTRAINT IF EXISTS companies_seat_limit_check")
        execute(
            conn,
            "ALTER TABLE companies ADD CONSTRAINT companies_seat_limit_check CHECK (seat_limit >= 0)",
        )
    except Exception as exc:
        log.error(f"failed to align companies_seat_limit_check for >=0 | err={exc}", exc_info=True)
        raise


def _table_exists(conn, table_name: str) -> bool:
    try:
        row = execute(
            conn,
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = ?
            """,
            [table_name],
        ).fetchone()
        return row is not None
    except Exception:
        return False


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


def _ensure_company_settings_runtime_columns(conn) -> None:
    if not _table_exists(conn, "company_settings"):
        return
    columns = _column_names(conn, "company_settings")
    changed = False
    if "webhook_secret" not in columns:
        execute(conn, "ALTER TABLE company_settings ADD COLUMN webhook_secret TEXT NOT NULL DEFAULT ''")
        changed = True
    if "ai_monthly_budget_usd" not in columns:
        # F2-5: 003 migratsiya qo'llanmagan legacy/test DB'lar uchun ham ustun bo'lsin.
        execute(conn, "ALTER TABLE company_settings ADD COLUMN ai_monthly_budget_usd NUMERIC(12, 2)")
        changed = True
    if changed:
        conn.commit()


def _ensure_company_webhook_project_keys_table(conn) -> None:
    execute(
        conn,
        """
        CREATE TABLE IF NOT EXISTS company_webhook_project_keys (
            company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            project_key VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (company_id, project_key),
            UNIQUE(project_key)
        )
        """,
    )


def _fetch_registry_project_key_conflicts(conn, company_id: int, project_keys: List[str]) -> List[str]:
    if not project_keys or not _table_exists(conn, "company_webhook_project_keys"):
        return []
    rows = execute(
        conn,
        """
        SELECT c.company_code, w.project_key
        FROM company_webhook_project_keys w
        JOIN companies c ON c.id = w.company_id
        WHERE w.company_id != ?
          AND c.is_active = TRUE
          AND w.project_key = ANY(?)
        ORDER BY c.company_code, w.project_key
        """,
        [company_id, project_keys],
    ).fetchall()
    return [f"{row_to_dict(row)['company_code']}: {row_to_dict(row)['project_key']}" for row in rows]


def _sync_company_webhook_project_keys(conn, company_id: int, project_keys: List[str]) -> None:
    _ensure_company_webhook_project_keys_table(conn)
    execute(conn, "DELETE FROM company_webhook_project_keys WHERE company_id = ?", [company_id])
    for project_key in project_keys:
        execute(
            conn,
            """
            INSERT INTO company_webhook_project_keys (company_id, project_key)
            VALUES (?, ?)
            """,
            [company_id, project_key],
        )


def _default_company_settings_payload() -> Dict[str, Any]:
    return {
        "jira_server": "",
        "jira_email": "",
        "jira_token": "",
        "jira_project_keys": "",
        "github_token": "",
        "github_org": "",
        "figma_token": "",
        "figma_tokens": "[]",
        "gemini_api_key_1": "",
        "gemini_api_key_2": "",
        "webhook_jira_server": "",
        "webhook_jira_email": "",
        "webhook_jira_token": "",
        "webhook_github_token": "",
        "webhook_github_org": "",
        "webhook_figma_token": "",
        "webhook_figma_tokens": "[]",
        "webhook_gemini_api_key_1": "",
        "webhook_gemini_api_key_2": "",
        "webhook_secret": "",
        "enabled_modules": "{}",
        "webhook_project_keys": "",
        "webhook_trigger_status": "",
        "webhook_trigger_aliases": "",
        "webhook_return_status": "",
        "webhook_allowed_issue_types": "",
        "webhook_excluded_assignees": "",
        "webhook_auto_return_enabled": 0,
        "webhook_return_threshold": 60,
        "webhook_module_settings": "{}",
    }


def _normalize_json_text(value: Any, default: str) -> str:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=True)
    except Exception:
        return default


def _extract_integrations_company_settings(conn, company_id: int) -> Dict[str, Any]:
    settings = _default_company_settings_payload()

    if _table_exists(conn, "company_integrations"):
        rows = execute(
            conn,
            """
            SELECT provider, config_json, is_active
            FROM company_integrations
            WHERE company_id = ?
            """,
            [company_id],
        ).fetchall()
        for row in rows:
            row_dict = row_to_dict(row)
            config = row_dict.get("config_json") or {}
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except Exception:
                    config = {}
            provider = (row_dict.get("provider") or "").strip()
            if provider == "jira":
                settings["jira_server"] = config.get("jira_server", settings["jira_server"])
                settings["jira_email"] = config.get("jira_email", settings["jira_email"])
                settings["jira_token"] = config.get("jira_token", settings["jira_token"])
                settings["jira_project_keys"] = config.get("jira_project_keys", settings["jira_project_keys"])
            elif provider == "github":
                settings["github_token"] = config.get("github_token", settings["github_token"])
                settings["github_org"] = config.get("github_org", settings["github_org"])
            elif provider == "figma":
                settings["figma_token"] = config.get("figma_token", settings["figma_token"])
                settings["figma_tokens"] = _normalize_json_text(config.get("figma_tokens"), "[]")
            elif provider == "gemini":
                settings["gemini_api_key_1"] = config.get("gemini_api_key_1", settings["gemini_api_key_1"])
                settings["gemini_api_key_2"] = config.get("gemini_api_key_2", settings["gemini_api_key_2"])
            elif provider == "webhook_jira":
                settings["webhook_jira_server"] = config.get("jira_server", settings["webhook_jira_server"])
                settings["webhook_jira_email"] = config.get("jira_email", settings["webhook_jira_email"])
                settings["webhook_jira_token"] = config.get("jira_token", settings["webhook_jira_token"])
                settings["webhook_project_keys"] = config.get("project_keys", settings["webhook_project_keys"])
            elif provider == "webhook_github":
                settings["webhook_github_token"] = config.get("github_token", settings["webhook_github_token"])
                settings["webhook_github_org"] = config.get("github_org", settings["webhook_github_org"])
            elif provider == "webhook_figma":
                settings["webhook_figma_token"] = config.get("figma_token", settings["webhook_figma_token"])
                settings["webhook_figma_tokens"] = _normalize_json_text(config.get("figma_tokens"), "[]")
            elif provider == "webhook_gemini":
                settings["webhook_gemini_api_key_1"] = config.get("gemini_api_key_1", settings["webhook_gemini_api_key_1"])
                settings["webhook_gemini_api_key_2"] = config.get("gemini_api_key_2", settings["webhook_gemini_api_key_2"])

    if _table_exists(conn, "company_module_access"):
        rows = execute(
            conn,
            """
            SELECT module_key, is_enabled
            FROM company_module_access
            WHERE company_id = ?
            ORDER BY module_key
            """,
            [company_id],
        ).fetchall()
        settings["enabled_modules"] = json.dumps(
            {row_to_dict(row)["module_key"]: bool(row_to_dict(row).get("is_enabled")) for row in rows},
            ensure_ascii=True,
        )

    if _table_exists(conn, "company_webhook_settings"):
        row = execute(
            conn,
            """
            SELECT *
            FROM company_webhook_settings
            WHERE company_id = ?
            """,
            [company_id],
        ).fetchone()
        if row:
            row_dict = row_to_dict(row)
            settings["webhook_project_keys"] = row_dict.get("project_keys", settings["webhook_project_keys"])
            settings["webhook_trigger_status"] = row_dict.get("trigger_status", settings["webhook_trigger_status"])
            settings["webhook_trigger_aliases"] = row_dict.get("trigger_aliases", settings["webhook_trigger_aliases"])
            settings["webhook_return_status"] = row_dict.get("return_status", settings["webhook_return_status"])
            settings["webhook_allowed_issue_types"] = row_dict.get("allowed_issue_types", settings["webhook_allowed_issue_types"])
            settings["webhook_excluded_assignees"] = row_dict.get("excluded_assignees", settings["webhook_excluded_assignees"])
            settings["webhook_auto_return_enabled"] = bool(row_dict.get("auto_return_enabled", settings["webhook_auto_return_enabled"]))
            settings["webhook_return_threshold"] = row_dict.get("return_threshold", settings["webhook_return_threshold"])
            settings["webhook_module_settings"] = _normalize_json_text(
                row_dict.get("module_settings_json"),
                "{}",
            )

    return settings


def fetch_company_by_id(get_conn: Callable, company_id: int) -> Optional[Dict]:
    try:
        conn = get_conn()
        row = execute(conn, "SELECT * FROM companies WHERE id = ?", [company_id]).fetchone()
        conn.close()
        return row_to_dict(row) if row else None
    except Exception:
        return None


def fetch_company_by_code(get_conn: Callable, company_code: str) -> Optional[Dict]:
    try:
        conn = get_conn()
        row = execute(conn, "SELECT * FROM companies WHERE company_code = ?", [company_code.strip().lower()]).fetchone()
        conn.close()
        return row_to_dict(row) if row else None
    except Exception:
        return None


def fetch_all_companies(get_conn: Callable) -> List[Dict]:
    try:
        conn = get_conn()
        rows = execute(conn, "SELECT * FROM companies ORDER BY created_at DESC").fetchall()
        conn.close()
        return [row_to_dict(r) for r in rows]
    except Exception:
        return []


def create_company_record(get_conn: Callable, company_code: str, company_name: str, seat_limit: int) -> Optional[int]:
    try:
        conn = get_conn()
        _ensure_companies_seat_limit_allows_zero(conn)
        payload = [company_code.strip().lower(), company_name.strip(), max(0, int(seat_limit))]
        row = execute(
            conn,
            "INSERT INTO companies (company_code, company_name, seat_limit) VALUES (?,?,?) RETURNING id",
            payload,
        ).fetchone()
        company_id = row["id"] if isinstance(row, dict) else row[0]
        conn.commit()
        conn.close()
        return company_id
    except Exception as exc:
        log.error(
            f"create_company_record failed | code={company_code.strip().lower()} | "
            f"name={company_name.strip()} | seat_limit={seat_limit} | err={exc}",
            exc_info=True,
        )
        return None


def insert_company_module_settings(get_conn: Callable, company_id: int, modules_json: str) -> bool:
    try:
        conn = get_conn()
        if _table_exists(conn, "company_settings"):
            execute(
                conn,
                "INSERT INTO company_settings (company_id, enabled_modules) VALUES (?,?)",
                [company_id, modules_json]
            )
        else:
            modules = json.loads(modules_json or "{}")
            now = datetime.now().isoformat()
            for module_key, is_enabled in modules.items():
                execute(
                    conn,
                    """
                    INSERT INTO company_module_access (company_id, module_key, is_enabled, enabled_by, created_at, updated_at)
                    VALUES (?, ?, ?, NULL, ?, ?)
                    ON CONFLICT(company_id, module_key) DO UPDATE SET
                        is_enabled = excluded.is_enabled,
                        updated_at = excluded.updated_at
                    """,
                    [company_id, module_key, bool(is_enabled), now, now],
                )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        log.error(
            f"insert_company_module_settings failed | company_id={company_id} | err={exc}",
            exc_info=True,
        )
        return False


def create_default_company_subscription(
    get_conn: Callable,
    company_id: int,
    plan_name: str,
    subscription_status: str,
    billing_mode: str,
    trial_days: int,
) -> bool:
    try:
        now = datetime.now()
        end = now + timedelta(days=trial_days)
        conn = get_conn()
        table_name = "company_subscriptions" if _table_exists(conn, "company_subscriptions") else "subscriptions"
        execute(
            conn,
            f"""
            INSERT INTO {table_name} (
                company_id, plan_name, subscription_status, billing_mode,
                billing_start_date, billing_end_date, next_payment_date, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                company_id,
                plan_name,
                subscription_status,
                billing_mode,
                now.date().isoformat(),
                end.date().isoformat(),
                end.date().isoformat(),
                now.isoformat(),
            ],
        )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        log.error(
            f"create_default_company_subscription failed | company_id={company_id} | "
            f"plan={plan_name} | status={subscription_status} | mode={billing_mode} | err={exc}",
            exc_info=True,
        )
        return False


def update_company_active_flag(get_conn: Callable, company_id: int, is_active: bool) -> bool:
    try:
        conn = get_conn()
        execute(conn, "UPDATE companies SET is_active = ? WHERE id = ?", [bool(is_active), company_id])
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def update_company_seat_limit_value(get_conn: Callable, company_id: int, seat_limit: int) -> bool:
    try:
        conn = get_conn()
        _ensure_companies_seat_limit_allows_zero(conn)
        execute(conn, "UPDATE companies SET seat_limit = ? WHERE id = ?", [max(0, int(seat_limit)), company_id])
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def delete_company_by_id(get_conn: Callable, company_id: int) -> bool:
    try:
        conn = get_conn()
        execute(conn, "DELETE FROM companies WHERE id = ?", [company_id])
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def fetch_company_subscription(get_conn: Callable, company_id: int) -> Dict:
    try:
        conn = get_conn()
        table_name = "company_subscriptions" if _table_exists(conn, "company_subscriptions") else "subscriptions"
        row = execute(conn, f"SELECT * FROM {table_name} WHERE company_id = ?", [company_id]).fetchone()
        conn.close()
        return row_to_dict(row) if row else {}
    except Exception:
        return {}


def upsert_company_subscription(get_conn: Callable, company_id: int, normalized: Dict) -> bool:
    payload = {
        key: (None if key in SUBSCRIPTION_DATE_FIELDS and value == "" else value)
        for key, value in dict(normalized).items()
    }
    payload['updated_at'] = datetime.now().isoformat()
    try:
        conn = get_conn()
        table_name = "company_subscriptions" if _table_exists(conn, "company_subscriptions") else "subscriptions"
        c = execute(conn, f"SELECT company_id FROM {table_name} WHERE company_id = ?", [company_id])
        exists = c.fetchone()
        if exists:
            set_clause = ", ".join(f"{k} = %s" for k in payload)
            values = list(payload.values()) + [company_id]
            execute(conn, f"UPDATE {table_name} SET {set_clause} WHERE company_id = ?", values)
        else:
            payload['company_id'] = company_id
            cols = ", ".join(payload.keys())
            placeholders = ", ".join("%s" for _ in payload)
            execute(
                conn,
                f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})",
                list(payload.values())
            )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        log.error(
            f"upsert_company_subscription failed | company_id={company_id} | err={exc}",
            exc_info=True,
        )
        return False


def expire_overdue_subscriptions(get_conn: Callable) -> int:
    """billing_end_date o'tgan trial/active obunalarni suspended ga o'tkazadi."""
    today = datetime.now().date().isoformat()
    try:
        conn = get_conn()
        table_name = "company_subscriptions" if _table_exists(conn, "company_subscriptions") else "subscriptions"
        result = execute(
            conn,
            f"""
            UPDATE {table_name}
            SET subscription_status = 'suspended', updated_at = %s
            WHERE subscription_status IN ('trial', 'active')
              AND billing_end_date IS NOT NULL
              AND billing_end_date < %s
            """,
            [datetime.now().isoformat(), today],
        )
        count = result.rowcount if hasattr(result, "rowcount") else 0
        conn.commit()
        conn.close()
        return count
    except Exception:
        return 0


def fetch_company_settings(get_conn: Callable, company_id: int) -> Dict:
    try:
        conn = get_conn()
        if _table_exists(conn, "company_settings"):
            _ensure_company_settings_runtime_columns(conn)
            row = execute(conn, "SELECT * FROM company_settings WHERE company_id = ?", [company_id]).fetchone()
            conn.close()
            return decrypt_sensitive_fields(row_to_dict(row)) if row else {}
        settings = _extract_integrations_company_settings(conn, company_id)
        conn.close()
        return decrypt_sensitive_fields(settings)
    except Exception:
        return {}


def fetch_company_ai_budget(get_conn: Callable, company_id: int) -> Optional[float]:
    """Kompaniya oylik AI budjeti (USD). None yoki <=0 = cheksiz (F2-5)."""
    try:
        conn = get_conn()
        try:
            if not _table_exists(conn, "company_settings"):
                return None
            _ensure_company_settings_runtime_columns(conn)
            row = execute(
                conn,
                "SELECT ai_monthly_budget_usd FROM company_settings WHERE company_id = ?",
                [company_id],
            ).fetchone()
        finally:
            conn.close()
        value = row_to_dict(row).get("ai_monthly_budget_usd") if row else None
        return float(value) if value is not None else None
    except Exception as exc:
        log.error(f"fetch_company_ai_budget xato | company_id={company_id} | err={exc}")
        raise


def update_company_ai_budget(get_conn: Callable, company_id: int, budget_usd: Any) -> bool:
    """Oylik AI budjetni saqlash. None/''/0 = cheksiz (NULL sifatida saqlanadi)."""
    normalized: Optional[float] = None
    if budget_usd not in (None, ""):
        try:
            value = float(budget_usd)
        except (TypeError, ValueError):
            return False
        if value < 0:
            return False
        normalized = value if value > 0 else None
    try:
        conn = get_conn()
        try:
            if not _table_exists(conn, "company_settings"):
                return False
            _ensure_company_settings_runtime_columns(conn)
            exists = execute(
                conn,
                "SELECT company_id FROM company_settings WHERE company_id = ?",
                [company_id],
            ).fetchone()
            now = datetime.now().isoformat()
            if exists:
                execute(
                    conn,
                    "UPDATE company_settings SET ai_monthly_budget_usd = ?, updated_at = ? WHERE company_id = ?",
                    [normalized, now, company_id],
                )
            else:
                execute(
                    conn,
                    "INSERT INTO company_settings (company_id, ai_monthly_budget_usd) VALUES (?, ?)",
                    [company_id, normalized],
                )
            conn.commit()
        finally:
            conn.close()
        return True
    except Exception as exc:
        log.error(f"update_company_ai_budget xato | company_id={company_id} | err={exc}")
        return False


def fetch_company_modules(get_conn: Callable, company_id: int, default_modules: Dict[str, bool]) -> Dict[str, bool]:
    settings = fetch_company_settings(get_conn, company_id)
    raw = settings.get('enabled_modules', '{}')
    try:
        if isinstance(raw, dict):
            modules = raw
        else:
            modules = json.loads(raw) if raw else {}
    except (json.JSONDecodeError, TypeError):
        modules = {}
    result = {**default_modules}
    for key, value in modules.items():
        if key in result:
            result[key] = bool(value)
    return result


def upsert_company_modules(get_conn: Callable, company_id: int, modules: Dict[str, bool], default_modules: Dict[str, bool]) -> bool:
    full = {**default_modules, **modules}
    try:
        conn = get_conn()
        now = datetime.now().isoformat()
        if _table_exists(conn, "company_settings"):
            c = execute(conn, "SELECT company_id FROM company_settings WHERE company_id = ?", [company_id])
            exists = c.fetchone()
            if exists:
                execute(
                    conn,
                    "UPDATE company_settings SET enabled_modules = ?, updated_at = ? WHERE company_id = ?",
                    [json.dumps(full), now, company_id]
                )
            else:
                execute(
                    conn,
                    "INSERT INTO company_settings (company_id, enabled_modules) VALUES (?,?)",
                    [company_id, json.dumps(full)]
                )
        else:
            for module_key, is_enabled in full.items():
                execute(
                    conn,
                    """
                    INSERT INTO company_module_access (company_id, module_key, is_enabled, enabled_by, created_at, updated_at)
                    VALUES (?, ?, ?, NULL, ?, ?)
                    ON CONFLICT(company_id, module_key) DO UPDATE SET
                        is_enabled = excluded.is_enabled,
                        updated_at = excluded.updated_at
                    """,
                    [company_id, module_key, bool(is_enabled), now, now],
                )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def upsert_company_settings(
    get_conn: Callable,
    company_id: int,
    filtered_settings: Dict,
    project_key_conflict_checker: Callable[[object, int, list], list],
    project_key_normalizer: Callable[[str], list],
) -> bool:
    if not filtered_settings:
        return False

    conn = None
    try:
        conn = get_conn()
        payload = dict(filtered_settings)
        normalized_project_keys: List[str] | None = None
        if 'jira_project_keys' in payload:
            normalized_keys = project_key_normalizer(str(payload['jira_project_keys']))
            payload['jira_project_keys'] = ', '.join(normalized_keys)
        if 'webhook_project_keys' in payload:
            normalized_keys = project_key_normalizer(str(payload['webhook_project_keys']))
            payload['webhook_project_keys'] = ', '.join(normalized_keys)
            normalized_project_keys = normalized_keys
            _ensure_company_webhook_project_keys_table(conn)
            conflicts = (
                project_key_conflict_checker(conn, company_id, normalized_keys)
                + _fetch_registry_project_key_conflicts(conn, company_id, normalized_keys)
            )
            if conflicts:
                log.warning(
                    f"webhook project key conflict | company_id={company_id} | conflicts={conflicts}"
                )
                conn.close()
                return False
        if payload_requires_encryption(payload) and not can_encrypt_credentials():
            conn.close()
            return False

        if _table_exists(conn, "company_settings"):
            _ensure_company_settings_runtime_columns(conn)
            payload = encrypt_sensitive_fields(payload)
            payload['updated_at'] = datetime.now().isoformat()
            c = execute(conn, "SELECT company_id FROM company_settings WHERE company_id = ?", [company_id])
            exists = c.fetchone()
            if exists:
                set_clause = ", ".join(f"{k} = %s" for k in payload)
                values = list(payload.values()) + [company_id]
                execute(conn, f"UPDATE company_settings SET {set_clause} WHERE company_id = ?", values)
            else:
                payload['company_id'] = company_id
                cols = ", ".join(payload.keys())
                placeholders = ", ".join("%s" for _ in payload)
                execute(
                    conn,
                    f"INSERT INTO company_settings ({cols}) VALUES ({placeholders})",
                    list(payload.values())
                )

            # Legacy compatibility: ayrim muhitlarda o'qish company_webhook_settings
            # jadvalidan ketadi. Shu sabab webhook_* payload bo'lsa u yerga ham sync qilamiz.
            webhook_keys = {
                "webhook_project_keys",
                "webhook_trigger_status",
                "webhook_trigger_aliases",
                "webhook_return_status",
                "webhook_allowed_issue_types",
                "webhook_excluded_assignees",
                "webhook_auto_return_enabled",
                "webhook_return_threshold",
                "webhook_module_settings",
            }
            if _table_exists(conn, "company_webhook_settings") and any(k in payload for k in webhook_keys):
                legacy_row = execute(
                    conn,
                    "SELECT * FROM company_webhook_settings WHERE company_id = ?",
                    [company_id],
                ).fetchone()
                legacy = row_to_dict(legacy_row) if legacy_row else {}

                def _pick(payload_key: str, legacy_key: str, default: Any):
                    if payload_key in payload:
                        return payload.get(payload_key)
                    return legacy.get(legacy_key, default)

                module_settings_json = _normalize_json_text(
                    _pick("webhook_module_settings", "module_settings_json", "{}"),
                    "{}",
                )
                legacy_updated_at = datetime.now().isoformat()

                execute(
                    conn,
                    """
                    INSERT INTO company_webhook_settings (
                        company_id, project_keys, trigger_status, trigger_aliases, return_status,
                        allowed_issue_types, excluded_assignees, auto_return_enabled,
                        return_threshold, module_settings_json, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?)
                    ON CONFLICT(company_id) DO UPDATE SET
                        project_keys = excluded.project_keys,
                        trigger_status = excluded.trigger_status,
                        trigger_aliases = excluded.trigger_aliases,
                        return_status = excluded.return_status,
                        allowed_issue_types = excluded.allowed_issue_types,
                        excluded_assignees = excluded.excluded_assignees,
                        auto_return_enabled = excluded.auto_return_enabled,
                        return_threshold = excluded.return_threshold,
                        module_settings_json = excluded.module_settings_json,
                        updated_at = excluded.updated_at
                    """,
                    [
                        company_id,
                        str(_pick("webhook_project_keys", "project_keys", "") or ""),
                        str(_pick("webhook_trigger_status", "trigger_status", "") or ""),
                        str(_pick("webhook_trigger_aliases", "trigger_aliases", "") or ""),
                        str(_pick("webhook_return_status", "return_status", "") or ""),
                        str(_pick("webhook_allowed_issue_types", "allowed_issue_types", "") or ""),
                        str(_pick("webhook_excluded_assignees", "excluded_assignees", "") or ""),
                        bool(_pick("webhook_auto_return_enabled", "auto_return_enabled", 0)),
                        int(_pick("webhook_return_threshold", "return_threshold", 60) or 60),
                        module_settings_json,
                        legacy_updated_at,
                    ],
                )
            if normalized_project_keys is not None:
                _sync_company_webhook_project_keys(conn, company_id, normalized_project_keys)
        else:
            merged = fetch_company_settings(get_conn, company_id)
            merged.update(payload)
            merged = encrypt_sensitive_fields(merged)
            updated_at = datetime.now().isoformat()

            if _table_exists(conn, "company_webhook_settings"):
                execute(
                    conn,
                    """
                    INSERT INTO company_webhook_settings (
                        company_id, project_keys, trigger_status, trigger_aliases, return_status,
                        allowed_issue_types, excluded_assignees, auto_return_enabled,
                        return_threshold, module_settings_json, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?)
                    ON CONFLICT(company_id) DO UPDATE SET
                        project_keys = excluded.project_keys,
                        trigger_status = excluded.trigger_status,
                        trigger_aliases = excluded.trigger_aliases,
                        return_status = excluded.return_status,
                        allowed_issue_types = excluded.allowed_issue_types,
                        excluded_assignees = excluded.excluded_assignees,
                        auto_return_enabled = excluded.auto_return_enabled,
                        return_threshold = excluded.return_threshold,
                        module_settings_json = excluded.module_settings_json,
                        updated_at = excluded.updated_at
                    """,
                    [
                        company_id,
                        merged.get("webhook_project_keys") or "",
                        merged.get("webhook_trigger_status") or "",
                        merged.get("webhook_trigger_aliases") or "",
                        merged.get("webhook_return_status") or "",
                        merged.get("webhook_allowed_issue_types") or "",
                        merged.get("webhook_excluded_assignees") or "",
                        bool(merged.get("webhook_auto_return_enabled", 0)),
                        int(merged.get("webhook_return_threshold") or 60),
                        merged.get("webhook_module_settings") or "{}",
                        updated_at,
                    ],
                )

            if _table_exists(conn, "company_integrations"):
                provider_payloads = {
                    "jira": {
                        "jira_server": merged.get("jira_server") or "",
                        "jira_email": merged.get("jira_email") or "",
                        "jira_token": merged.get("jira_token") or "",
                        "jira_project_keys": merged.get("jira_project_keys") or "",
                    },
                    "github": {
                        "github_token": merged.get("github_token") or "",
                        "github_org": merged.get("github_org") or "",
                    },
                    "figma": {
                        "figma_token": merged.get("figma_token") or "",
                        "figma_tokens": merged.get("figma_tokens") or "[]",
                    },
                    "gemini": {
                        "gemini_api_key_1": merged.get("gemini_api_key_1") or "",
                        "gemini_api_key_2": merged.get("gemini_api_key_2") or "",
                    },
                    "webhook_jira": {
                        "jira_server": merged.get("webhook_jira_server") or "",
                        "jira_email": merged.get("webhook_jira_email") or "",
                        "jira_token": merged.get("webhook_jira_token") or "",
                        "project_keys": merged.get("webhook_project_keys") or "",
                    },
                    "webhook_github": {
                        "github_token": merged.get("webhook_github_token") or "",
                        "github_org": merged.get("webhook_github_org") or "",
                    },
                    "webhook_figma": {
                        "figma_token": merged.get("webhook_figma_token") or "",
                        "figma_tokens": merged.get("webhook_figma_tokens") or "[]",
                    },
                    "webhook_gemini": {
                        "gemini_api_key_1": merged.get("webhook_gemini_api_key_1") or "",
                        "gemini_api_key_2": merged.get("webhook_gemini_api_key_2") or "",
                    },
                }
                for provider, config in provider_payloads.items():
                    is_active = any(str(value or "").strip() for value in config.values())
                    execute(
                        conn,
                        """
                        INSERT INTO company_integrations (company_id, provider, config_json, is_active, created_at, updated_at)
                        VALUES (?, ?, ?::jsonb, ?, NOW(), ?)
                        ON CONFLICT(company_id, provider) DO UPDATE SET
                            config_json = excluded.config_json,
                            is_active = excluded.is_active,
                            updated_at = excluded.updated_at
                        """,
                        [company_id, provider, json.dumps(config, ensure_ascii=True), bool(is_active), updated_at],
                    )
            if normalized_project_keys is not None:
                _sync_company_webhook_project_keys(conn, company_id, normalized_project_keys)

        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        log.error(
            "company settings save failed | "
            f"company_id={company_id} | "
            f"keys={sorted(str(key) for key in filtered_settings.keys())} | "
            f"err={exc}",
            exc_info=True,
        )
        try:
            if conn is not None:
                conn.rollback()
        except Exception:
            pass
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass
        return False


def fetch_company_by_project_key(
    get_conn: Callable,
    project_key: str,
    project_key_normalizer: Callable[[str], list],
) -> Optional[Dict]:
    try:
        conn = get_conn()
        key_upper = project_key.strip().upper()
        if _table_exists(conn, "company_settings"):
            rows = execute(conn, """
                SELECT c.*, cs.jira_project_keys FROM companies c
                JOIN company_settings cs ON cs.company_id = c.id
                WHERE c.is_active = TRUE
                  AND cs.jira_project_keys != ''
            """).fetchall()
        else:
            rows = []
        conn.close()
        matches = []
        for row in rows:
            row_dict = row_to_dict(row)
            keys = project_key_normalizer(row_dict.get("jira_project_keys") or "")
            if key_upper in keys:
                matches.append(row_dict)
        if len(matches) == 1:
            return matches[0]
        return None
    except Exception:
        return None


def find_project_key_conflicts(
    conn,
    company_id: int,
    project_keys: List[str],
    project_key_normalizer: Callable[[str], list],
) -> List[str]:
    if not project_keys:
        return []

    conflicts = _fetch_registry_project_key_conflicts(conn, company_id, project_keys)

    if _table_exists(conn, "company_settings"):
        rows = execute(
            conn,
            """
            SELECT c.company_code, cs.webhook_project_keys
            FROM companies c
            JOIN company_settings cs ON cs.company_id = c.id
            WHERE c.id != ?
              AND c.is_active = TRUE
              AND cs.webhook_project_keys != ''
            """,
            [company_id],
        ).fetchall()
    else:
        rows = execute(
            conn,
            """
            SELECT c.company_code, ws.project_keys AS webhook_project_keys
            FROM companies c
            JOIN company_webhook_settings ws ON ws.company_id = c.id
            WHERE c.id != ?
              AND c.is_active = TRUE
              AND ws.project_keys != ''
            """,
            [company_id],
        ).fetchall()

    wanted = set(project_keys)
    for row in rows:
        row_dict = row_to_dict(row)
        overlap = wanted.intersection(project_key_normalizer(row_dict.get("webhook_project_keys", "")))
        if overlap:
            conflicts.append(f"{row_dict['company_code']}: {', '.join(sorted(overlap))}")
    return sorted(set(conflicts))
