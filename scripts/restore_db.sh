#!/usr/bin/env bash
# PostgreSQL restore skripti.
#
# Foydalanish:
#   bash scripts/restore_db.sh backups/jira_ai_20260611_120000.sql.gz
#   bash scripts/restore_db.sh backups/jira_ai_20260611_120000.sql.gz my_target_db
#
# ⚠️  DIQQAT: Bu skript mavjud DB'ni to'liq qayta tiklaydi.
#     Ishlashdan oldin ma'lumotlaringizni backup qiling!

set -euo pipefail

cd "$(dirname "$0")/.."

BACKUP_FILE="${1:-}"
if [[ -z "$BACKUP_FILE" ]]; then
    echo "Foydalanish: bash scripts/restore_db.sh <backup_file.sql.gz> [db_name]" >&2
    exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "Xato: Fayl topilmadi: $BACKUP_FILE" >&2
    exit 1
fi

# DSN aniqlash
if [[ -n "${2:-}" ]]; then
    PG_ARGS=("$2")
elif [[ -n "${APP_POSTGRES_DSN:-}" ]]; then
    PG_ARGS=("$APP_POSTGRES_DSN")
elif [[ -f ".env" ]]; then
    DSN="$(grep -E '^APP_POSTGRES_DSN=' .env | tail -1 | cut -d= -f2- || true)"
    DSN="${DSN%$'\r'}"
    PG_ARGS=("${DSN:-postgresql://localhost/jira_ai_analyzer}")
else
    PG_ARGS=("postgresql://localhost/jira_ai_analyzer")
fi

echo "=== DB Restore ==="
echo "Fayl  : ${BACKUP_FILE}"
echo "Target: ${PG_ARGS[*]}"
echo ""
read -r -p "Davom etasizmi? (y/N): " confirm
if [[ "${confirm,,}" != "y" ]]; then
    echo "Bekor qilindi."
    exit 0
fi

echo "Restore qilinmoqda..."
gunzip -c "$BACKUP_FILE" | psql "${PG_ARGS[@]}" -q
echo "OK: Restore muvaffaqiyatli bajarildi."
