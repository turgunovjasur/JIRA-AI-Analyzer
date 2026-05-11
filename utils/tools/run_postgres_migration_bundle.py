#!/usr/bin/env python3
"""
Run PostgreSQL migration bundle.

Bu script schema SQL va generated import SQL ni ketma-ket PostgreSQL bazaga
qo'llash uchun poydevor beradi.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.database.runtime import connect_postgres, get_database_backend_config


def run_postgres_sql_file(sql_file: str | Path) -> None:
    sql_path = Path(sql_file)
    sql_text = sql_path.read_text()

    conn = connect_postgres()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql_text)
        conn.commit()
    finally:
        conn.close()


def run_postgres_migration_bundle(
    schema_file: str | Path = "database/postgresql/001_initial_schema.sql",
    import_file: str | Path = "data/postgres_import/import.sql",
) -> dict:
    config = get_database_backend_config()
    if not config.postgres_dsn:
        raise RuntimeError("APP_POSTGRES_DSN kiritilmagan.")

    run_postgres_sql_file(schema_file)
    import_path = Path(import_file)
    if import_path.exists():
        run_postgres_sql_file(import_path)

    return {
        "schema_file": str(schema_file),
        "import_file": str(import_file),
        "import_applied": import_path.exists(),
    }


def main(argv: Iterable[str] | None = None) -> int:
    import json
    import sys

    args = list(argv or sys.argv[1:])
    schema_file = args[0] if len(args) >= 1 else "database/postgresql/001_initial_schema.sql"
    import_file = args[1] if len(args) >= 2 else "data/postgres_import/import.sql"
    result = run_postgres_migration_bundle(schema_file, import_file)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
