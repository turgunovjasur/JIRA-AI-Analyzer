#!/usr/bin/env python3
"""
Generate PostgreSQL import SQL from SQLite export JSON files.

Bu script `export_sqlite_for_postgres.py` chiqargan JSON fayllardan
`PostgreSQL` uchun `INSERT` script yaratadi.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


IMPORT_ORDER = [
    ("auth", "companies", "companies"),
    ("auth", "users", "users"),
    ("auth", "company_subscriptions", "company_subscriptions"),
    ("auth", "global_settings", "global_settings"),
    ("auth", "login_attempts", "login_attempts"),
    ("auth", "platform_admins", "platform_admins"),
    ("auth", "login_audit_logs", "login_audit_logs"),
    ("auth", "user_password_reset_tokens", "user_password_reset_tokens"),
    ("auth", "company_settings", "company_settings"),
    ("auth", "user_credentials", "user_credentials"),
    ("auth", "user_module_settings", "user_module_settings"),
    ("processing", "task_processing", "task_processing"),
    ("processing", "task_status_history", "task_status_history"),
]

TRUNCATE_ORDER = [
    "task_status_history",
    "task_processing",
    "job_runs",
    "jobs",
    "audit_logs",
    "login_audit_logs",
    "user_password_reset_tokens",
    "platform_admins",
    "user_module_settings",
    "user_credentials",
    "company_settings",
    "company_module_access",
    "company_integrations",
    "login_attempts",
    "global_settings",
    "company_subscriptions",
    "users",
    "companies",
]


TABLE_COLUMN_MAP = {
    "companies": [
        "id", "company_code", "company_name", "seat_limit", "is_active", "created_at",
    ],
    "users": [
        "id", "company_id", "username", "password_hash", "role", "is_active", "created_at",
    ],
    "company_subscriptions": [
        "company_id", "plan_name", "subscription_status", "billing_mode",
        "billing_start_date", "billing_end_date", "next_payment_date",
        "last_payment_date", "last_payment_note", "created_at", "updated_at",
    ],
    "global_settings": ["key", "value"],
    "login_attempts": ["identifier", "failed_count", "locked_until", "updated_at"],
    "platform_admins": [
        "id", "username", "password_hash", "is_active", "created_at", "updated_at",
    ],
    "login_audit_logs": [
        "id", "identifier", "user_id", "company_id", "role", "success", "reason", "created_at",
    ],
    "user_password_reset_tokens": [
        "id", "user_id", "token_hash", "expires_at", "used_at", "created_at",
    ],
    "company_settings": [
        "company_id", "jira_server", "jira_email", "jira_token", "jira_project_keys", "github_token", "github_org",
        "figma_token", "figma_tokens", "gemini_api_key_1", "gemini_api_key_2", "gemini_model",
        "webhook_jira_server", "webhook_jira_email", "webhook_jira_token", "webhook_github_token",
        "webhook_github_org", "webhook_figma_token", "webhook_figma_tokens",
        "webhook_gemini_api_key_1", "webhook_gemini_api_key_2", "webhook_gemini_model",
        "enabled_modules", "webhook_project_keys", "webhook_trigger_status", "webhook_trigger_aliases",
        "webhook_return_status", "webhook_allowed_issue_types", "webhook_excluded_assignees",
        "webhook_auto_return_enabled", "webhook_return_threshold", "webhook_module_settings", "updated_at",
    ],
    "user_credentials": [
        "user_id", "jira_server", "jira_email", "jira_token", "jira_project_keys", "github_token",
        "github_org", "figma_token", "figma_tokens", "gemini_api_key_1", "gemini_api_key_2",
        "gemini_model", "updated_at",
    ],
    "user_module_settings": ["user_id", "module_key", "settings_json", "updated_at"],
    "task_processing": [
        "task_id", "company_id", "task_status", "task_update_time", "return_count",
        "return_reason", "last_jira_status", "last_processed_at", "error_message",
        "skip_detected", "service1_status", "service2_status", "service1_error",
        "service2_error", "service1_done_at", "service2_done_at", "compliance_score",
        "assignee", "task_type", "feature_name", "technology_stack", "blocked_at",
        "blocked_retry_at", "block_reason", "created_at", "updated_at",
    ],
    "task_status_history": [
        "task_id", "from_status", "to_status", "changed_at", "assignee", "story_points", "issue_type",
    ],
}

NULLABLE_TEMPORAL_COLUMNS = {
    "company_subscriptions": {
        "billing_start_date",
        "billing_end_date",
        "next_payment_date",
        "last_payment_date",
    },
    "login_attempts": {"locked_until"},
    "user_password_reset_tokens": {"used_at"},
    "task_processing": {
        "task_update_time",
        "last_processed_at",
        "service1_done_at",
        "service2_done_at",
        "blocked_at",
        "blocked_retry_at",
    },
}

SEQUENCE_RESET_TABLES = [
    ("companies", "id"),
    ("users", "id"),
    ("company_subscriptions", "id"),
    ("company_integrations", "id"),
    ("company_module_access", "id"),
    ("user_module_settings", "id"),
    ("platform_admins", "id"),
    ("login_audit_logs", "id"),
    ("user_password_reset_tokens", "id"),
    ("audit_logs", "id"),
    ("jobs", "id"),
    ("job_runs", "id"),
    ("task_processing", "id"),
    ("task_status_history", "id"),
]


def _sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    text = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
    escaped = text.replace("'", "''")
    return f"'{escaped}'"


def _normalize_nullable_temporal_values(target_table: str, row: dict) -> dict:
    normalized = dict(row)
    for column in NULLABLE_TEMPORAL_COLUMNS.get(target_table, set()):
        if normalized.get(column) == "":
            normalized[column] = None
    return normalized


def _transform_row(target_table: str, row: dict, context: dict | None = None) -> dict:
    transformed = _normalize_nullable_temporal_values(target_table, row)
    context = context or {}

    if target_table == "companies":
        transformed["is_active"] = bool(row.get("is_active", 0))

    if target_table == "users":
        transformed["is_active"] = bool(row.get("is_active", 0))

    if target_table == "platform_admins":
        transformed["is_active"] = bool(row.get("is_active", 0))

    if target_table == "login_audit_logs":
        transformed["success"] = bool(row.get("success", 0))
        valid_user_ids = context.get("valid_user_ids", set())
        valid_company_ids = context.get("valid_company_ids", set())
        if transformed.get("user_id") not in valid_user_ids:
            transformed["user_id"] = None
        if transformed.get("company_id") not in valid_company_ids:
            transformed["company_id"] = None

    if target_table == "company_settings":
        transformed = {
            "company_id": row.get("company_id"),
            "jira_server": row.get("jira_server", ""),
            "jira_email": row.get("jira_email", ""),
            "jira_token": row.get("jira_token", ""),
            "jira_project_keys": row.get("jira_project_keys", ""),
            "github_token": row.get("github_token", ""),
            "github_org": row.get("github_org", ""),
            "figma_token": row.get("figma_token", ""),
            "figma_tokens": row.get("figma_tokens", "[]"),
            "gemini_api_key_1": row.get("gemini_api_key_1", ""),
            "gemini_api_key_2": row.get("gemini_api_key_2", ""),
            "gemini_model": row.get("gemini_model", ""),
            "enabled_modules": row.get("enabled_modules", "{}"),
            "webhook_project_keys": row.get("webhook_project_keys", ""),
            "webhook_trigger_status": row.get("webhook_trigger_status", ""),
            "webhook_trigger_aliases": row.get("webhook_trigger_aliases", ""),
            "webhook_return_status": row.get("webhook_return_status", ""),
            "webhook_allowed_issue_types": row.get("webhook_allowed_issue_types", ""),
            "webhook_excluded_assignees": row.get("webhook_excluded_assignees", ""),
            "webhook_auto_return_enabled": bool(row.get("webhook_auto_return_enabled", 0)),
            "webhook_return_threshold": row.get("webhook_return_threshold", 60),
            "webhook_module_settings": row.get("webhook_module_settings", "{}"),
            "updated_at": row.get("updated_at"),
        }

    if target_table == "user_credentials":
        transformed = {
            "user_id": row.get("user_id"),
            "jira_server": row.get("jira_server", ""),
            "jira_email": row.get("jira_email", ""),
            "jira_token": row.get("jira_token", ""),
            "jira_project_keys": row.get("jira_project_keys", ""),
            "github_token": row.get("github_token", ""),
            "github_org": row.get("github_org", ""),
            "figma_token": row.get("figma_token", ""),
            "figma_tokens": row.get("figma_tokens", "[]"),
            "gemini_api_key_1": row.get("gemini_api_key_1", ""),
            "gemini_api_key_2": row.get("gemini_api_key_2", ""),
            "gemini_model": row.get("gemini_model", ""),
            "updated_at": row.get("updated_at"),
        }

    if target_table == "user_module_settings":
        transformed["settings_json"] = row.get("settings_json", "{}")

    if target_table == "task_processing":
        transformed["skip_detected"] = bool(row.get("skip_detected", 0))
        if transformed.get("company_id") in (None, "") and context.get("legacy_company_id") is not None:
            transformed["company_id"] = context["legacy_company_id"]

    return transformed


def _build_insert_statement(target_table: str, row: dict, context: dict | None = None) -> str:
    columns = TABLE_COLUMN_MAP[target_table]
    values = [_sql_literal(_transform_row(target_table, row, context).get(column)) for column in columns]
    return f"INSERT INTO {target_table} ({', '.join(columns)}) VALUES ({', '.join(values)});"


def _load_export_payloads(export_path: Path) -> tuple[dict, dict]:
    manifest = json.loads((export_path / "manifest.json").read_text())
    payloads = {}
    for item in manifest.get("files", []):
        file_name = item["file"]
        payloads[file_name] = json.loads((export_path / file_name).read_text())
    return manifest, payloads


def _build_migration_context(payloads: dict) -> dict:
    companies_payload = payloads.get("auth__companies.json", {"rows": []})
    users_payload = payloads.get("auth__users.json", {"rows": []})
    subscriptions_payload = payloads.get("auth__company_subscriptions.json", {"rows": []})
    task_processing_payload = payloads.get("processing__task_processing.json", {"rows": []})
    valid_company_ids = {
        row.get("id") for row in companies_payload.get("rows", [])
        if row.get("id") is not None
    }
    valid_user_ids = {
        row.get("id") for row in users_payload.get("rows", [])
        if row.get("id") is not None
    }

    orphan_rows = [
        row for row in task_processing_payload.get("rows", [])
        if row.get("company_id") in (None, "")
    ]
    if not orphan_rows:
        return {
            "valid_company_ids": valid_company_ids,
            "valid_user_ids": valid_user_ids,
        }

    existing_company_ids = [row.get("id", 0) for row in companies_payload.get("rows", []) if row.get("id") is not None]
    legacy_company_id = (max(existing_company_ids) if existing_company_ids else 0) + 1
    created_at = orphan_rows[0].get("created_at") or orphan_rows[0].get("updated_at")

    companies_payload.setdefault("rows", []).append({
        "id": legacy_company_id,
        "company_code": "legacy-import",
        "company_name": "Legacy Imported Tasks",
        "seat_limit": 1,
        "is_active": 1,
        "created_at": created_at,
    })
    subscriptions_payload.setdefault("rows", []).append({
        "company_id": legacy_company_id,
        "plan_name": "legacy",
        "subscription_status": "inactive",
        "billing_mode": "manual",
        "billing_start_date": None,
        "billing_end_date": None,
        "next_payment_date": None,
        "last_payment_date": None,
        "last_payment_note": "Auto-created during PostgreSQL migration for orphan task rows.",
        "created_at": created_at,
        "updated_at": created_at,
    })

    payloads["auth__companies.json"] = companies_payload
    payloads["auth__company_subscriptions.json"] = subscriptions_payload
    valid_company_ids.add(legacy_company_id)

    return {
        "legacy_company_id": legacy_company_id,
        "valid_company_ids": valid_company_ids,
        "valid_user_ids": valid_user_ids,
    }


def generate_postgres_import_sql(export_dir: str | Path, output_file: str | Path) -> Path:
    export_path = Path(export_dir)
    output_path = Path(output_file)

    lines = ["BEGIN;"]
    lines.append("-- Clean target tables before loading exported data")
    lines.append(f"TRUNCATE TABLE {', '.join(TRUNCATE_ORDER)} RESTART IDENTITY CASCADE;")
    manifest, payloads = _load_export_payloads(export_path)
    context = _build_migration_context(payloads)
    available = {item["file"]: item for item in manifest.get("files", [])}

    for source_db, source_table, target_table in IMPORT_ORDER:
        file_name = f"{source_db}__{source_table}.json"
        if file_name not in available:
            continue
        payload = payloads[file_name]
        lines.append(f"-- {source_db}.{source_table} -> {target_table}")
        for row in payload.get("rows", []):
            lines.append(_build_insert_statement(target_table, row, context))

    lines.append("-- Reset sequences after explicit id inserts")
    for table_name, pk_column in SEQUENCE_RESET_TABLES:
        lines.append(
            "SELECT setval("
            f"pg_get_serial_sequence('{table_name}', '{pk_column}'), "
            f"COALESCE((SELECT MAX({pk_column}) FROM {table_name}), 1), "
            f"(SELECT COALESCE(MAX({pk_column}), 0) > 0 FROM {table_name})"
            ");"
        )

    lines.append("COMMIT;")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n")
    return output_path


def main(argv: Iterable[str] | None = None) -> int:
    import sys

    args = list(argv or sys.argv[1:])
    export_dir = args[0] if len(args) >= 1 else "data/postgres_export"
    output_file = args[1] if len(args) >= 2 else "data/postgres_import/import.sql"
    path = generate_postgres_import_sql(export_dir, output_file)
    print(str(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
