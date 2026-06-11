#!/usr/bin/env python3
"""
PostgreSQL readiness preflight checker.

Bu script real migratsiyani boshlashdan oldin quyidagilarni tekshiradi:
- driver bormi
- DSN bormi
- schema file bormi
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.database.runtime import (
    get_database_backend_config,
    is_postgres_driver_available,
)


def check_postgres_ready(
    schema_file: str | Path = "database/postgresql/001_initial_schema.sql",
) -> dict:
    config = get_database_backend_config()
    schema_path = Path(schema_file)

    checks = {
        "driver_available": is_postgres_driver_available(),
        "dsn_configured": bool(config.postgres_dsn),
        "schema_file_exists": schema_path.exists(),
    }

    missing = [name for name, ok in checks.items() if not ok]

    return {
        "ok": not missing,
        "backend": config.backend,
        "checks": checks,
        "missing": missing,
        "next_step": (
            "PostgreSQL schema bootstrapni ishga tushiring."
            if not missing
            else "Missing bandlarni to'ldiring, keyin schema bootstrapni ishga tushiring."
        ),
    }


def main(argv: Iterable[str] | None = None) -> int:
    import sys

    args = list(argv or sys.argv[1:])
    schema_file = args[0] if len(args) >= 1 else "database/postgresql/001_initial_schema.sql"

    result = check_postgres_ready(schema_file)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
