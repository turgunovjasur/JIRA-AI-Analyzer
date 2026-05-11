#!/usr/bin/env python3
"""
Validate PostgreSQL migration bundle artifacts.

Bu script quyidagilar bir-biriga mosligini tekshiradi:
- target schema SQL
- SQLite export manifest
- generated import.sql
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_EXPORT_FILES = {
    "auth__companies.json",
    "auth__users.json",
    "auth__company_settings.json",
    "auth__user_credentials.json",
    "auth__user_module_settings.json",
    "auth__global_settings.json",
    "auth__login_attempts.json",
    "auth__platform_admins.json",
    "auth__login_audit_logs.json",
    "auth__user_password_reset_tokens.json",
    "auth__company_subscriptions.json",
    "processing__task_processing.json",
    "processing__task_status_history.json",
}

REQUIRED_IMPORT_TABLES = {
    "companies",
    "users",
    "company_subscriptions",
    "global_settings",
    "login_attempts",
    "platform_admins",
    "login_audit_logs",
    "user_password_reset_tokens",
    "company_settings",
    "user_credentials",
    "user_module_settings",
    "task_processing",
    "task_status_history",
}


def _extract_schema_tables(schema_sql: str) -> set[str]:
    return set(
        re.findall(r"CREATE TABLE IF NOT EXISTS\s+([a-zA-Z_][a-zA-Z0-9_]*)", schema_sql)
    )


def _extract_import_tables(import_sql: str) -> set[str]:
    tables = set(re.findall(r"INSERT INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)", import_sql))
    tables.update(re.findall(r"--\s+[a-z_]+\.[a-z_]+\s+->\s+([a-zA-Z_][a-zA-Z0-9_]*)", import_sql))
    return tables


def validate_postgres_migration_bundle(
    schema_file: str | Path,
    export_dir: str | Path,
    import_sql_file: str | Path,
) -> dict:
    schema_path = Path(schema_file)
    export_path = Path(export_dir)
    import_path = Path(import_sql_file)

    errors: list[str] = []

    if not schema_path.exists():
        errors.append(f"Schema file topilmadi: {schema_path}")
    if not import_path.exists():
        errors.append(f"Import SQL file topilmadi: {import_path}")
    manifest_path = export_path / "manifest.json"
    if not manifest_path.exists():
        errors.append(f"Manifest topilmadi: {manifest_path}")

    if errors:
        return {"ok": False, "errors": errors}

    manifest = json.loads(manifest_path.read_text())
    export_files = {item["file"] for item in manifest.get("files", [])}
    missing_exports = sorted(REQUIRED_EXPORT_FILES - export_files)
    if missing_exports:
        errors.append(f"Export fayllar yetishmayapti: {', '.join(missing_exports)}")

    schema_tables = _extract_schema_tables(schema_path.read_text())
    missing_schema_tables = sorted(REQUIRED_IMPORT_TABLES - schema_tables)
    if missing_schema_tables:
        errors.append(f"Schema ichida target table yo'q: {', '.join(missing_schema_tables)}")

    import_tables = _extract_import_tables(import_path.read_text())
    missing_import_tables = sorted(REQUIRED_IMPORT_TABLES - import_tables)
    if missing_import_tables:
        errors.append(f"Import SQL ichida table yo'q: {', '.join(missing_import_tables)}")

    return {
        "ok": not errors,
        "errors": errors,
        "schema_tables": sorted(schema_tables),
        "import_tables": sorted(import_tables),
        "export_files": sorted(export_files),
    }


def main(argv: Iterable[str] | None = None) -> int:
    import sys

    args = list(argv or sys.argv[1:])
    schema_file = args[0] if len(args) >= 1 else "database/postgresql/001_initial_schema.sql"
    export_dir = args[1] if len(args) >= 2 else "data/postgres_export"
    import_sql_file = args[2] if len(args) >= 3 else "data/postgres_import/import.sql"

    result = validate_postgres_migration_bundle(schema_file, export_dir, import_sql_file)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
