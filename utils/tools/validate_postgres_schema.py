#!/usr/bin/env python3
"""
Validate PostgreSQL schema artifact.
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


REQUIRED_TABLES = {
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


def validate_postgres_schema(schema_file: str | Path) -> dict:
    schema_path = Path(schema_file)
    errors: list[str] = []

    if not schema_path.exists():
        return {"ok": False, "errors": [f"Schema file topilmadi: {schema_path}"]}

    schema_tables = _extract_schema_tables(schema_path.read_text())
    missing_schema_tables = sorted(REQUIRED_TABLES - schema_tables)
    if missing_schema_tables:
        errors.append(f"Schema ichida target table yo'q: {', '.join(missing_schema_tables)}")

    return {
        "ok": not errors,
        "errors": errors,
        "schema_tables": sorted(schema_tables),
    }


def main(argv: Iterable[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    schema_file = args[0] if args else "database/postgresql/001_initial_schema.sql"

    result = validate_postgres_schema(schema_file)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
