#!/usr/bin/env bash
# PostgreSQL backup skripti.
#
# Foydalanish:
#   bash scripts/backup_db.sh                   # .env dan DSN oladi
#   bash scripts/backup_db.sh my_db             # DB nomi berib
#   BACKUP_DIR=/mnt/backups bash scripts/backup_db.sh
#
# Muhit o'zgaruvchilari:
#   APP_POSTGRES_DSN   — to'liq PostgreSQL DSN (ixtiyoriy; .env dan o'qiladi)
#   BACKUP_DIR         — backup saqlanadigan papka (default: ./backups)
#   KEEP_DAYS          — necha kunlik backuplarni saqlash (default: 7)

set -euo pipefail

cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# DSN aniqlash
if [[ -n "${1:-}" ]]; then
    DB_NAME="$1"
    PG_ARGS=("$DB_NAME")
elif [[ -n "${APP_POSTGRES_DSN:-}" ]]; then
    PG_ARGS=("$APP_POSTGRES_DSN")
elif [[ -f ".env" ]]; then
    APP_POSTGRES_DSN="$(grep -E '^APP_POSTGRES_DSN=' .env | tail -1 | cut -d= -f2- || true)"
    APP_POSTGRES_DSN="${APP_POSTGRES_DSN%$'\r'}"
    PG_ARGS=("${APP_POSTGRES_DSN:-postgresql://localhost/jira_ai_analyzer}")
else
    PG_ARGS=("postgresql://localhost/jira_ai_analyzer")
fi

if ! command -v pg_dump &>/dev/null; then
    echo "Xato: pg_dump topilmadi. PostgreSQL client o'rnatilganligini tekshiring." >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"

BACKUP_FILE="${BACKUP_DIR}/jira_ai_${TIMESTAMP}.sql.gz"
echo "=== DB backup: ${TIMESTAMP} ==="
echo "Fayl: ${BACKUP_FILE}"

pg_dump "${PG_ARGS[@]}" | gzip > "$BACKUP_FILE"
SIZE="$(du -sh "$BACKUP_FILE" | cut -f1)"
echo "OK: ${SIZE}"

# Eski backuplarni tozalash
if (( KEEP_DAYS > 0 )); then
    deleted=$(find "$BACKUP_DIR" -name "jira_ai_*.sql.gz" -mtime +"$KEEP_DAYS" -print -delete | wc -l)
    (( deleted > 0 )) && echo "Eski backuplar o'chirildi: ${deleted} ta"
fi

echo "Backup muvaffaqiyatli saqlandi: ${BACKUP_FILE}"
