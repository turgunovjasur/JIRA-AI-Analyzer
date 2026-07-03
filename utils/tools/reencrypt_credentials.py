#!/usr/bin/env python3
"""
Re-encrypt stored credentials with the current master key.

Bu utility `APP_CREDENTIALS_MASTER_KEY` va ixtiyoriy
`APP_CREDENTIALS_OLD_MASTER_KEYS` yordamida mavjud credentiallarni o'qib,
hozirgi master key bilan qayta shifrlash uchun ishlatiladi.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.auth.credential_crypto import (
    can_decrypt_value,
    can_encrypt_credentials,
    get_sensitive_credential_fields,
    payload_needs_reencryption,
    reencrypt_sensitive_fields,
)
from utils.auth.repository_common import execute, row_to_dict, uses_postgres_params
from utils.database.runtime import connect_auth_db

USER_CREDENTIAL_FIELDS = get_sensitive_credential_fields()
COMPANY_CREDENTIAL_FIELDS = get_sensitive_credential_fields()


def _fetch_rows(conn, query: str, params: list | None = None) -> list[dict]:
    rows = execute(conn, query, params or []).fetchall()
    return [row_to_dict(row) for row in rows]


def _update_row(conn, table_name: str, key_column: str, key_value, payload: dict) -> None:
    filtered = {k: v for k, v in payload.items() if k != key_column}
    if not filtered:
        return
    placeholder = "%s" if uses_postgres_params(conn) else "?"
    set_clause = ", ".join(f"{column} = {placeholder}" for column in filtered)
    values = list(filtered.values()) + [key_value]
    execute(conn, f"UPDATE {table_name} SET {set_clause} WHERE {key_column} = ?", values)


def reencrypt_stored_credentials(*, apply: bool = False) -> dict:
    if not can_encrypt_credentials():
        raise RuntimeError("Credential encryption secret topilmadi. Avval APP_CREDENTIALS_MASTER_KEY ni kiriting.")

    conn = connect_auth_db(timeout=30)
    result = {
        "apply": apply,
        "user_credentials": {"scanned": 0, "updated": 0, "blocked": 0},
        "company_settings": {"scanned": 0, "updated": 0, "blocked": 0},
    }

    try:
        user_rows = _fetch_rows(conn, "SELECT * FROM user_credentials ORDER BY user_id ASC")
        company_rows = _fetch_rows(conn, "SELECT * FROM company_settings ORDER BY company_id ASC")

        result["user_credentials"]["scanned"] = len(user_rows)
        result["company_settings"]["scanned"] = len(company_rows)

        for row in user_rows:
            if not payload_needs_reencryption(row, USER_CREDENTIAL_FIELDS):
                continue
            needed_fields = [
                field for field in USER_CREDENTIAL_FIELDS
                if field in row and row[field] not in (None, "") and payload_needs_reencryption({field: row[field]}, {field})
            ]
            if not all(can_decrypt_value(row[field]) for field in needed_fields):
                result["user_credentials"]["blocked"] += 1
                continue
            result["user_credentials"]["updated"] += 1
            if apply:
                updated = reencrypt_sensitive_fields(row, USER_CREDENTIAL_FIELDS)
                _update_row(conn, "user_credentials", "user_id", row["user_id"], updated)

        for row in company_rows:
            if not payload_needs_reencryption(row, COMPANY_CREDENTIAL_FIELDS):
                continue
            needed_fields = [
                field for field in COMPANY_CREDENTIAL_FIELDS
                if field in row and row[field] not in (None, "") and payload_needs_reencryption({field: row[field]}, {field})
            ]
            if not all(can_decrypt_value(row[field]) for field in needed_fields):
                result["company_settings"]["blocked"] += 1
                continue
            result["company_settings"]["updated"] += 1
            if apply:
                updated = reencrypt_sensitive_fields(row, COMPANY_CREDENTIAL_FIELDS)
                _update_row(conn, "company_settings", "company_id", row["company_id"], updated)

        if apply:
            conn.commit()
        return result
    finally:
        conn.close()


def main(argv: Iterable[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    apply = "--apply" in args
    result = reencrypt_stored_credentials(apply=apply)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
