#!/usr/bin/env python3
"""
SQLite -> PostgreSQL migration export tool.

Hozircha bu script `auth.db` va `processing.db` dan ma'lumotlarni JSON
ko'rinishida chiqarib beradi. Keyingi bosqichda shu export Postgres import
script bilan juft ishlaydi.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.database.runtime import connect_auth_sqlite, connect_processing_sqlite


EXPORT_TABLES = {
    "auth": [
        "companies",
        "users",
        "company_settings",
        "user_module_settings",
        "user_credentials",
        "global_settings",
        "login_attempts",
        "platform_admins",
        "login_audit_logs",
        "user_password_reset_tokens",
        "company_subscriptions",
    ],
    "processing": [
        "task_processing",
        "task_status_history",
    ],
}


def _fetch_table_rows(conn, table_name: str) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    return [dict(row) for row in cursor.fetchall()]


def export_sqlite_for_postgres(output_dir: str | Path) -> dict:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    exported_at = datetime.now().isoformat()
    manifest = {
        "exported_at": exported_at,
        "files": [],
    }

    auth_conn = connect_auth_sqlite()
    processing_conn = connect_processing_sqlite(row_factory=True)

    try:
        for db_name, tables in EXPORT_TABLES.items():
            conn = auth_conn if db_name == "auth" else processing_conn
            for table_name in tables:
                rows = _fetch_table_rows(conn, table_name)
                file_name = f"{db_name}__{table_name}.json"
                file_path = output_path / file_name
                payload = {
                    "database": db_name,
                    "table": table_name,
                    "exported_at": exported_at,
                    "row_count": len(rows),
                    "rows": rows,
                }
                file_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2))
                manifest["files"].append({
                    "database": db_name,
                    "table": table_name,
                    "file": file_name,
                    "row_count": len(rows),
                })
    finally:
        auth_conn.close()
        processing_conn.close()

    manifest_path = output_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2))
    return manifest


def main(argv: Iterable[str] | None = None) -> int:
    import sys

    args = list(argv or sys.argv[1:])
    target_dir = args[0] if args else "data/postgres_export"
    manifest = export_sqlite_for_postgres(target_dir)
    print(json.dumps(manifest, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
