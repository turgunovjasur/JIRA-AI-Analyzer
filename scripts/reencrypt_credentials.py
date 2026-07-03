"""
Mavjud kompaniya credentials'larini joriy APP_CREDENTIALS_MASTER_KEY bilan
qayta shifrlash skripti.

Foydalanish holatlari:
  1. Master key rotatsiyasi: eski kalit APP_CREDENTIALS_OLD_MASTER_KEYS ga,
     yangi kalit APP_CREDENTIALS_MASTER_KEY ga o'tkazilganda.
  2. Plain text dan encrypted ga o'tish: ilgari master key yo'q edi,
     endi qo'shildi — mavjud plain text tokenlar encrypt qilinadi.

Foydalanish:
  python scripts/reencrypt_credentials.py [--dry-run]

  --dry-run: faqat nechta yozuv o'zgarishini ko'rsatadi, DB'ga yozmaydi.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from utils.auth.credential_crypto import (
    encrypt_sensitive_fields,
    get_sensitive_credential_fields,
    has_configured_master_key,
    payload_needs_reencryption,
    payload_requires_encryption,
    reencrypt_sensitive_fields,
)


def _get_all_company_settings_raw():
    from utils.database.runtime import connect_postgres
    conn = connect_postgres()
    try:
        rows = conn.execute("SELECT company_id, settings_json FROM company_settings").fetchall()
        return [{"company_id": r[0], "settings_json": r[1]} for r in rows]
    finally:
        conn.close()


def _update_company_settings_raw(company_id: int, settings_json: str) -> None:
    from utils.database.runtime import connect_postgres
    conn = connect_postgres()
    try:
        conn.execute(
            "UPDATE company_settings SET settings_json = ? WHERE company_id = ?",
            [settings_json, company_id],
        )
        conn.commit()
    finally:
        conn.close()


def main(dry_run: bool = False) -> None:
    if not has_configured_master_key():
        print("Xato: APP_CREDENTIALS_MASTER_KEY o'rnatilmagan.")
        sys.exit(1)

    import json

    sensitive_fields = get_sensitive_credential_fields()
    updated = 0
    skipped = 0

    rows = _get_all_company_settings_raw()
    print(f"Jami company_settings yozuvlari: {len(rows)}")

    for row in rows:
        company_id = row["company_id"]
        try:
            payload = json.loads(row["settings_json"] or "{}")
        except Exception:
            skipped += 1
            continue

        needs_work = payload_needs_reencryption(payload) or payload_requires_encryption(payload, sensitive_fields)
        if not needs_work:
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY-RUN] company_id={company_id} → qayta shifrlash kerak")
        else:
            new_payload = reencrypt_sensitive_fields(payload)
            new_payload = encrypt_sensitive_fields(new_payload)
            _update_company_settings_raw(company_id, json.dumps(new_payload))
            print(f"  company_id={company_id} → qayta shifrlandi")
        updated += 1

    print(f"\nNatija: {updated} ta yangilandi, {skipped} ta o'zgartirish kerak emas.")
    if dry_run:
        print("(--dry-run rejimi: hech narsa yozilmadi)")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
