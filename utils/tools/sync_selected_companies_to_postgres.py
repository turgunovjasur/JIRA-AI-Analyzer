#!/usr/bin/env python3
"""
Sync selected companies from SQLite auth/processing DBs into PostgreSQL.

Bu script mavjud PostgreSQL target bazaga faqat ko'rsatilgan kompaniyalar va
ular bilan bog'liq users/settings/tasks yozuvlarini upsert qiladi.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.database.runtime import connect_auth_sqlite, connect_postgres, connect_processing_sqlite


DEFAULT_COMPANY_CODES = ("xasan", "moxir", "jasur", "gws")


def _dict_rows(cursor) -> list[dict]:
    return [dict(row) for row in cursor.fetchall()]


def _json_loads(text: str | None, fallback):
    if not text:
        return fallback
    try:
        return json.loads(text)
    except Exception:
        return fallback


def _table_set(pg_conn) -> set[str]:
    with pg_conn.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        return {row[0] for row in cur.fetchall()}


def _column_set(pg_conn, table_name: str) -> set[str]:
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            """,
            [table_name],
        )
        return {row[0] for row in cur.fetchall()}


def _fetch_source_bundle(company_codes: list[str]) -> dict:
    auth_conn = connect_auth_sqlite()
    processing_conn = connect_processing_sqlite(row_factory=True)
    try:
        auth_cur = auth_conn.cursor()
        placeholders = ",".join("?" for _ in company_codes)
        auth_cur.execute(
            f"""
            SELECT *
            FROM companies
            WHERE company_code IN ({placeholders})
            ORDER BY id
            """,
            company_codes,
        )
        companies = _dict_rows(auth_cur)
        company_ids = [row["id"] for row in companies]
        if not company_ids:
            return {
                "companies": [],
                "users": [],
                "subscriptions": [],
                "company_settings": [],
                "user_credentials": [],
                "user_module_settings": [],
                "login_audit_logs": [],
                "login_attempts": [],
                "task_processing": [],
                "task_status_history": [],
            }

        company_ph = ",".join("?" for _ in company_ids)
        auth_cur.execute(
            f"SELECT * FROM users WHERE company_id IN ({company_ph}) ORDER BY company_id, id",
            company_ids,
        )
        users = _dict_rows(auth_cur)
        user_ids = [row["id"] for row in users]

        auth_cur.execute(
            f"SELECT * FROM company_subscriptions WHERE company_id IN ({company_ph}) ORDER BY company_id",
            company_ids,
        )
        subscriptions = _dict_rows(auth_cur)

        auth_cur.execute(
            f"SELECT * FROM company_settings WHERE company_id IN ({company_ph}) ORDER BY company_id",
            company_ids,
        )
        company_settings = _dict_rows(auth_cur)

        if user_ids:
            user_ph = ",".join("?" for _ in user_ids)
            auth_cur.execute(
                f"SELECT * FROM user_credentials WHERE user_id IN ({user_ph}) ORDER BY user_id",
                user_ids,
            )
            user_credentials = _dict_rows(auth_cur)

            auth_cur.execute(
                f"""
                SELECT user_id, module_key, settings_json, updated_at
                FROM user_module_settings
                WHERE user_id IN ({user_ph})
                ORDER BY user_id, module_key
                """,
                user_ids,
            )
            user_module_settings = _dict_rows(auth_cur)

            auth_cur.execute(
                f"""
                SELECT *
                FROM login_audit_logs
                WHERE company_id IN ({company_ph}) OR user_id IN ({user_ph})
                ORDER BY id
                """,
                [*company_ids, *user_ids],
            )
            login_audit_logs = _dict_rows(auth_cur)
        else:
            user_credentials = []
            user_module_settings = []
            login_audit_logs = []

        selected_usernames = [row["username"] for row in users]
        if selected_usernames:
            name_ph = ",".join("?" for _ in selected_usernames)
            auth_cur.execute(
                f"""
                SELECT *
                FROM login_attempts
                WHERE identifier IN ({name_ph})
                ORDER BY identifier
                """,
                selected_usernames,
            )
            login_attempts = _dict_rows(auth_cur)
        else:
            login_attempts = []

        proc_cur = processing_conn.cursor()
        proc_cur.execute(
            f"""
            SELECT *
            FROM task_processing
            WHERE company_id IN ({company_ph})
            ORDER BY task_id
            """,
            company_ids,
        )
        task_processing = _dict_rows(proc_cur)
        task_ids = [row["task_id"] for row in task_processing]
        if task_ids:
            task_ph = ",".join("?" for _ in task_ids)
            proc_cur.execute(
                f"""
                SELECT *
                FROM task_status_history
                WHERE task_id IN ({task_ph})
                ORDER BY id
                """,
                task_ids,
            )
            task_status_history = _dict_rows(proc_cur)
        else:
            task_status_history = []

        return {
            "companies": companies,
            "users": users,
            "subscriptions": subscriptions,
            "company_settings": company_settings,
            "user_credentials": user_credentials,
            "user_module_settings": user_module_settings,
            "login_audit_logs": login_audit_logs,
            "login_attempts": login_attempts,
            "task_processing": task_processing,
            "task_status_history": task_status_history,
        }
    finally:
        auth_conn.close()
        processing_conn.close()


def _upsert_companies(pg_conn, companies: list[dict]) -> None:
    if not companies:
        return
    with pg_conn.cursor() as cur:
        for row in companies:
            cur.execute(
                """
                INSERT INTO companies (id, company_code, company_name, seat_limit, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (id) DO UPDATE
                SET company_code = EXCLUDED.company_code,
                    company_name = EXCLUDED.company_name,
                    seat_limit = EXCLUDED.seat_limit,
                    is_active = EXCLUDED.is_active,
                    updated_at = NOW()
                """,
                [
                    row["id"],
                    row["company_code"],
                    row["company_name"],
                    row.get("seat_limit") or 1,
                    bool(row.get("is_active", 0)),
                    row.get("created_at"),
                ],
            )


def _upsert_users(pg_conn, users: list[dict]) -> None:
    if not users:
        return
    with pg_conn.cursor() as cur:
        for row in users:
            cur.execute(
                """
                INSERT INTO users (id, company_id, username, password_hash, role, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (id) DO UPDATE
                SET company_id = EXCLUDED.company_id,
                    username = EXCLUDED.username,
                    password_hash = EXCLUDED.password_hash,
                    role = EXCLUDED.role,
                    is_active = EXCLUDED.is_active,
                    updated_at = NOW()
                """,
                [
                    row["id"],
                    row["company_id"],
                    row["username"],
                    row["password_hash"],
                    row.get("role") or "user",
                    bool(row.get("is_active", 0)),
                    row.get("created_at"),
                ],
            )


def _upsert_subscriptions(pg_conn, subscriptions: list[dict], tables: set[str]) -> None:
    if not subscriptions:
        return
    table_name = "company_subscriptions" if "company_subscriptions" in tables else "subscriptions"
    with pg_conn.cursor() as cur:
        for row in subscriptions:
            cur.execute(
                f"""
                INSERT INTO {table_name} (
                    company_id, plan_name, subscription_status, billing_mode,
                    billing_start_date, billing_end_date, next_payment_date,
                    last_payment_date, last_payment_note, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (company_id) DO UPDATE
                SET plan_name = EXCLUDED.plan_name,
                    subscription_status = EXCLUDED.subscription_status,
                    billing_mode = EXCLUDED.billing_mode,
                    billing_start_date = EXCLUDED.billing_start_date,
                    billing_end_date = EXCLUDED.billing_end_date,
                    next_payment_date = EXCLUDED.next_payment_date,
                    last_payment_date = EXCLUDED.last_payment_date,
                    last_payment_note = EXCLUDED.last_payment_note,
                    updated_at = EXCLUDED.updated_at
                """,
                [
                    row["company_id"],
                    row.get("plan_name") or "trial",
                    row.get("subscription_status") or "trial",
                    row.get("billing_mode") or "manual",
                    row.get("billing_start_date") or None,
                    row.get("billing_end_date") or None,
                    row.get("next_payment_date") or None,
                    row.get("last_payment_date") or None,
                    row.get("last_payment_note") or "",
                    row.get("created_at"),
                    row.get("updated_at") or row.get("created_at"),
                ],
            )


def _upsert_company_settings(pg_conn, company_settings: list[dict], tables: set[str]) -> None:
    if not company_settings:
        return
    if "company_settings" in tables:
        columns = [
            "company_id", "jira_server", "jira_email", "jira_token", "jira_project_keys", "github_token", "github_org",
            "figma_token", "figma_tokens", "gemini_api_key_1", "gemini_api_key_2", "gemini_model",
            "webhook_jira_server", "webhook_jira_email", "webhook_jira_token", "webhook_github_token",
            "webhook_github_org", "webhook_figma_token", "webhook_figma_tokens",
            "webhook_gemini_api_key_1", "webhook_gemini_api_key_2", "webhook_gemini_model",
            "enabled_modules", "webhook_project_keys", "webhook_trigger_status", "webhook_trigger_aliases",
            "webhook_return_status", "webhook_allowed_issue_types", "webhook_excluded_assignees",
            "webhook_auto_return_enabled", "webhook_return_threshold", "webhook_module_settings", "updated_at",
        ]
        set_clause = ", ".join(f"{col} = EXCLUDED.{col}" for col in columns[1:])
        query = f"""
            INSERT INTO company_settings ({", ".join(columns)})
            VALUES ({", ".join(["%s"] * len(columns))})
            ON CONFLICT (company_id) DO UPDATE
            SET {set_clause}
        """
        with pg_conn.cursor() as cur:
            for row in company_settings:
                cur.execute(query, [row.get(col) for col in columns])
        return

    with pg_conn.cursor() as cur:
        for row in company_settings:
            company_id = row["company_id"]
            updated_at = row.get("updated_at")

            enabled_modules = _json_loads(row.get("enabled_modules"), {})
            for module_key, is_enabled in enabled_modules.items():
                cur.execute(
                    """
                    INSERT INTO company_module_access (company_id, module_key, is_enabled, enabled_by, created_at, updated_at)
                    VALUES (%s, %s, %s, NULL, NOW(), %s)
                    ON CONFLICT (company_id, module_key) DO UPDATE
                    SET is_enabled = EXCLUDED.is_enabled,
                        updated_at = EXCLUDED.updated_at
                    """,
                    [company_id, module_key, bool(is_enabled), updated_at],
                )

            if "company_webhook_settings" in tables:
                cur.execute(
                    """
                    INSERT INTO company_webhook_settings (
                        company_id, project_keys, trigger_status, trigger_aliases, return_status,
                        allowed_issue_types, excluded_assignees, auto_return_enabled,
                        return_threshold, module_settings_json, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (company_id) DO UPDATE
                    SET project_keys = EXCLUDED.project_keys,
                        trigger_status = EXCLUDED.trigger_status,
                        trigger_aliases = EXCLUDED.trigger_aliases,
                        return_status = EXCLUDED.return_status,
                        allowed_issue_types = EXCLUDED.allowed_issue_types,
                        excluded_assignees = EXCLUDED.excluded_assignees,
                        auto_return_enabled = EXCLUDED.auto_return_enabled,
                        return_threshold = EXCLUDED.return_threshold,
                        module_settings_json = EXCLUDED.module_settings_json,
                        updated_at = EXCLUDED.updated_at
                    """,
                    [
                        company_id,
                        row.get("webhook_project_keys") or "",
                        row.get("webhook_trigger_status") or "",
                        row.get("webhook_trigger_aliases") or "",
                        row.get("webhook_return_status") or "",
                        row.get("webhook_allowed_issue_types") or "",
                        row.get("webhook_excluded_assignees") or "",
                        bool(row.get("webhook_auto_return_enabled", 0)),
                        row.get("webhook_return_threshold") or 60,
                        row.get("webhook_module_settings") or "{}",
                        updated_at,
                    ],
                )

            if "company_integrations" not in tables:
                continue

            providers = {
                "jira": {
                    "jira_server": row.get("jira_server") or "",
                    "jira_email": row.get("jira_email") or "",
                    "jira_token": row.get("jira_token") or "",
                    "jira_project_keys": row.get("jira_project_keys") or "",
                },
                "github": {
                    "github_token": row.get("github_token") or "",
                    "github_org": row.get("github_org") or "",
                },
                "figma": {
                    "figma_token": row.get("figma_token") or "",
                    "figma_tokens": row.get("figma_tokens") or "[]",
                },
                "gemini": {
                    "gemini_api_key_1": row.get("gemini_api_key_1") or "",
                    "gemini_api_key_2": row.get("gemini_api_key_2") or "",
                    "gemini_model": row.get("gemini_model") or "",
                },
                "webhook_jira": {
                    "jira_server": row.get("webhook_jira_server") or "",
                    "jira_email": row.get("webhook_jira_email") or "",
                    "jira_token": row.get("webhook_jira_token") or "",
                    "project_keys": row.get("webhook_project_keys") or "",
                },
                "webhook_github": {
                    "github_token": row.get("webhook_github_token") or "",
                    "github_org": row.get("webhook_github_org") or "",
                },
                "webhook_figma": {
                    "figma_token": row.get("webhook_figma_token") or "",
                    "figma_tokens": row.get("webhook_figma_tokens") or "[]",
                },
                "webhook_gemini": {
                    "gemini_api_key_1": row.get("webhook_gemini_api_key_1") or "",
                    "gemini_api_key_2": row.get("webhook_gemini_api_key_2") or "",
                    "gemini_model": row.get("webhook_gemini_model") or "",
                },
            }
            for provider, config in providers.items():
                has_value = any(str(value or "").strip() for value in config.values())
                if not has_value:
                    continue
                cur.execute(
                    """
                    INSERT INTO company_integrations (company_id, provider, config_json, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s::jsonb, %s, NOW(), %s)
                    ON CONFLICT (company_id, provider) DO UPDATE
                    SET config_json = EXCLUDED.config_json,
                        is_active = EXCLUDED.is_active,
                        updated_at = EXCLUDED.updated_at
                    """,
                    [company_id, provider, json.dumps(config), True, updated_at],
                )


def _upsert_user_credentials(pg_conn, user_credentials: list[dict], tables: set[str]) -> None:
    if not user_credentials or "user_credentials" not in tables:
        return
    columns = _column_set(pg_conn, "user_credentials")
    uses_encrypted_columns = "jira_token_encrypted" in columns
    with pg_conn.cursor() as cur:
        for row in user_credentials:
            if uses_encrypted_columns:
                cur.execute(
                    """
                    INSERT INTO user_credentials (
                        user_id, jira_server, jira_email, jira_token_encrypted, jira_project_keys,
                        github_token_encrypted, github_org, figma_token_encrypted, figma_tokens_encrypted,
                        gemini_api_key_1_encrypted, gemini_api_key_2_encrypted, gemini_model, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE
                    SET jira_server = EXCLUDED.jira_server,
                        jira_email = EXCLUDED.jira_email,
                        jira_token_encrypted = EXCLUDED.jira_token_encrypted,
                        jira_project_keys = EXCLUDED.jira_project_keys,
                        github_token_encrypted = EXCLUDED.github_token_encrypted,
                        github_org = EXCLUDED.github_org,
                        figma_token_encrypted = EXCLUDED.figma_token_encrypted,
                        figma_tokens_encrypted = EXCLUDED.figma_tokens_encrypted,
                        gemini_api_key_1_encrypted = EXCLUDED.gemini_api_key_1_encrypted,
                        gemini_api_key_2_encrypted = EXCLUDED.gemini_api_key_2_encrypted,
                        gemini_model = EXCLUDED.gemini_model,
                        updated_at = EXCLUDED.updated_at
                    """,
                    [
                        row["user_id"],
                        row.get("jira_server") or "",
                        row.get("jira_email") or "",
                        row.get("jira_token") or "",
                        row.get("jira_project_keys") or "",
                        row.get("github_token") or "",
                        row.get("github_org") or "",
                        row.get("figma_token") or "",
                        row.get("figma_tokens") or "[]",
                        row.get("gemini_api_key_1") or "",
                        row.get("gemini_api_key_2") or "",
                        row.get("gemini_model") or "",
                        row.get("updated_at"),
                    ],
                )
            else:
                cur.execute(
                    """
                    INSERT INTO user_credentials (
                        user_id, jira_server, jira_email, jira_token, jira_project_keys,
                        github_token, github_org, figma_token, figma_tokens,
                        gemini_api_key_1, gemini_api_key_2, gemini_model, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE
                    SET jira_server = EXCLUDED.jira_server,
                        jira_email = EXCLUDED.jira_email,
                        jira_token = EXCLUDED.jira_token,
                        jira_project_keys = EXCLUDED.jira_project_keys,
                        github_token = EXCLUDED.github_token,
                        github_org = EXCLUDED.github_org,
                        figma_token = EXCLUDED.figma_token,
                        figma_tokens = EXCLUDED.figma_tokens,
                        gemini_api_key_1 = EXCLUDED.gemini_api_key_1,
                        gemini_api_key_2 = EXCLUDED.gemini_api_key_2,
                        gemini_model = EXCLUDED.gemini_model,
                        updated_at = EXCLUDED.updated_at
                    """,
                    [
                        row["user_id"],
                        row.get("jira_server") or "",
                        row.get("jira_email") or "",
                        row.get("jira_token") or "",
                        row.get("jira_project_keys") or "",
                        row.get("github_token") or "",
                        row.get("github_org") or "",
                        row.get("figma_token") or "",
                        row.get("figma_tokens") or "[]",
                        row.get("gemini_api_key_1") or "",
                        row.get("gemini_api_key_2") or "",
                        row.get("gemini_model") or "",
                        row.get("updated_at"),
                    ],
                )


def _upsert_user_module_settings(pg_conn, rows: list[dict], tables: set[str]) -> None:
    if not rows or "user_module_settings" not in tables:
        return
    with pg_conn.cursor() as cur:
        for row in rows:
            cur.execute(
                """
                INSERT INTO user_module_settings (user_id, module_key, settings_json, updated_at)
                VALUES (%s, %s, %s::jsonb, %s)
                ON CONFLICT (user_id, module_key) DO UPDATE
                SET settings_json = EXCLUDED.settings_json,
                    updated_at = EXCLUDED.updated_at
                """,
                [
                    row["user_id"],
                    row["module_key"],
                    row.get("settings_json") or "{}",
                    row.get("updated_at"),
                ],
            )


def _upsert_login_audit_logs(pg_conn, rows: list[dict], tables: set[str]) -> None:
    if not rows or "login_audit_logs" not in tables:
        return
    with pg_conn.cursor() as cur:
        for row in rows:
            cur.execute(
                """
                INSERT INTO login_audit_logs (id, identifier, user_id, company_id, role, success, reason, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET identifier = EXCLUDED.identifier,
                    user_id = EXCLUDED.user_id,
                    company_id = EXCLUDED.company_id,
                    role = EXCLUDED.role,
                    success = EXCLUDED.success,
                    reason = EXCLUDED.reason,
                    created_at = EXCLUDED.created_at
                """,
                [
                    row["id"],
                    row["identifier"],
                    row.get("user_id"),
                    row.get("company_id"),
                    row.get("role"),
                    bool(row.get("success", 0)),
                    row.get("reason") or "",
                    row.get("created_at"),
                ],
            )


def _upsert_login_attempts(pg_conn, rows: list[dict], tables: set[str]) -> None:
    if not rows or "login_attempts" not in tables:
        return
    with pg_conn.cursor() as cur:
        for row in rows:
            cur.execute(
                """
                INSERT INTO login_attempts (identifier, failed_count, locked_until, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (identifier) DO UPDATE
                SET failed_count = EXCLUDED.failed_count,
                    locked_until = EXCLUDED.locked_until,
                    updated_at = EXCLUDED.updated_at
                """,
                [
                    row["identifier"],
                    row.get("failed_count") or 0,
                    row.get("locked_until") or None,
                    row.get("updated_at"),
                ],
            )


def _upsert_task_processing(pg_conn, rows: list[dict], tables: set[str]) -> None:
    if not rows or "task_processing" not in tables:
        return
    with pg_conn.cursor() as cur:
        for row in rows:
            cur.execute(
                """
                INSERT INTO task_processing (
                    task_id, company_id, task_status, task_update_time, return_count,
                    return_reason, last_jira_status, last_processed_at, error_message,
                    skip_detected, service1_status, service2_status, service1_error,
                    service2_error, service1_done_at, service2_done_at, compliance_score,
                    assignee, task_type, feature_name, technology_stack, blocked_at,
                    blocked_retry_at, block_reason, created_at, updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                ON CONFLICT (task_id) DO UPDATE
                SET company_id = EXCLUDED.company_id,
                    task_status = EXCLUDED.task_status,
                    task_update_time = EXCLUDED.task_update_time,
                    return_count = EXCLUDED.return_count,
                    return_reason = EXCLUDED.return_reason,
                    last_jira_status = EXCLUDED.last_jira_status,
                    last_processed_at = EXCLUDED.last_processed_at,
                    error_message = EXCLUDED.error_message,
                    skip_detected = EXCLUDED.skip_detected,
                    service1_status = EXCLUDED.service1_status,
                    service2_status = EXCLUDED.service2_status,
                    service1_error = EXCLUDED.service1_error,
                    service2_error = EXCLUDED.service2_error,
                    service1_done_at = EXCLUDED.service1_done_at,
                    service2_done_at = EXCLUDED.service2_done_at,
                    compliance_score = EXCLUDED.compliance_score,
                    assignee = EXCLUDED.assignee,
                    task_type = EXCLUDED.task_type,
                    feature_name = EXCLUDED.feature_name,
                    technology_stack = EXCLUDED.technology_stack,
                    blocked_at = EXCLUDED.blocked_at,
                    blocked_retry_at = EXCLUDED.blocked_retry_at,
                    block_reason = EXCLUDED.block_reason,
                    updated_at = EXCLUDED.updated_at
                """,
                [
                    row["task_id"],
                    row.get("company_id"),
                    row.get("task_status") or "none",
                    row.get("task_update_time"),
                    row.get("return_count") or 0,
                    row.get("return_reason"),
                    row.get("last_jira_status"),
                    row.get("last_processed_at"),
                    row.get("error_message"),
                    bool(row.get("skip_detected", 0)),
                    row.get("service1_status") or "pending",
                    row.get("service2_status") or "pending",
                    row.get("service1_error"),
                    row.get("service2_error"),
                    row.get("service1_done_at"),
                    row.get("service2_done_at"),
                    row.get("compliance_score"),
                    row.get("assignee"),
                    row.get("task_type"),
                    row.get("feature_name"),
                    row.get("technology_stack"),
                    row.get("blocked_at"),
                    row.get("blocked_retry_at"),
                    row.get("block_reason"),
                    row.get("created_at"),
                    row.get("updated_at"),
                ],
            )


def _upsert_task_status_history(pg_conn, rows: list[dict], task_company_map: dict[str, int], tables: set[str]) -> None:
    if not rows or "task_status_history" not in tables:
        return
    with pg_conn.cursor() as cur:
        for row in rows:
            cur.execute(
                """
                INSERT INTO task_status_history (
                    id, task_id, company_id, from_status, to_status, changed_at,
                    assignee, story_points, issue_type
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET task_id = EXCLUDED.task_id,
                    company_id = EXCLUDED.company_id,
                    from_status = EXCLUDED.from_status,
                    to_status = EXCLUDED.to_status,
                    changed_at = EXCLUDED.changed_at,
                    assignee = EXCLUDED.assignee,
                    story_points = EXCLUDED.story_points,
                    issue_type = EXCLUDED.issue_type
                """,
                [
                    row["id"],
                    row["task_id"],
                    task_company_map.get(row["task_id"]),
                    row.get("from_status"),
                    row.get("to_status"),
                    row.get("changed_at"),
                    row.get("assignee"),
                    row.get("story_points"),
                    row.get("issue_type"),
                ],
            )


def _reset_sequences(pg_conn, tables: set[str]) -> None:
    sequence_targets = [
        ("companies", "id"),
        ("users", "id"),
        ("login_audit_logs", "id"),
        ("user_module_settings", "id"),
        ("task_processing", "id"),
        ("task_status_history", "id"),
        ("subscriptions", "id"),
        ("company_subscriptions", "id"),
        ("company_integrations", "id"),
        ("company_module_access", "id"),
    ]
    with pg_conn.cursor() as cur:
        for table_name, pk_column in sequence_targets:
            if table_name not in tables:
                continue
            cur.execute(
                """
                SELECT setval(
                    pg_get_serial_sequence(%s, %s),
                    COALESCE((SELECT MAX(%s) FROM %s), 1),
                    (SELECT COALESCE(MAX(%s), 0) > 0 FROM %s)
                )
                """
                % ("%s", "%s", pk_column, table_name, pk_column, table_name),
                [table_name, pk_column],
            )


def sync_selected_companies(company_codes: list[str]) -> dict:
    source = _fetch_source_bundle(company_codes)
    pg_conn = connect_postgres()
    try:
        tables = _table_set(pg_conn)
        _upsert_companies(pg_conn, source["companies"])
        _upsert_users(pg_conn, source["users"])
        _upsert_subscriptions(pg_conn, source["subscriptions"], tables)
        _upsert_company_settings(pg_conn, source["company_settings"], tables)
        _upsert_user_credentials(pg_conn, source["user_credentials"], tables)
        _upsert_user_module_settings(pg_conn, source["user_module_settings"], tables)
        _upsert_login_audit_logs(pg_conn, source["login_audit_logs"], tables)
        _upsert_login_attempts(pg_conn, source["login_attempts"], tables)
        _upsert_task_processing(pg_conn, source["task_processing"], tables)
        task_company_map = {row["task_id"]: row["company_id"] for row in source["task_processing"]}
        _upsert_task_status_history(pg_conn, source["task_status_history"], task_company_map, tables)
        _reset_sequences(pg_conn, tables)
        pg_conn.commit()
    except Exception:
        pg_conn.rollback()
        raise
    finally:
        pg_conn.close()

    return {
        "company_codes": company_codes,
        "companies": len(source["companies"]),
        "users": len(source["users"]),
        "subscriptions": len(source["subscriptions"]),
        "company_settings": len(source["company_settings"]),
        "user_credentials": len(source["user_credentials"]),
        "user_module_settings": len(source["user_module_settings"]),
        "login_audit_logs": len(source["login_audit_logs"]),
        "login_attempts": len(source["login_attempts"]),
        "task_processing": len(source["task_processing"]),
        "task_status_history": len(source["task_status_history"]),
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--company-codes",
        default=",".join(DEFAULT_COMPANY_CODES),
        help="Comma-separated company codes to sync.",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    company_codes = [item.strip().lower() for item in args.company_codes.split(",") if item.strip()]
    result = sync_selected_companies(company_codes)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
