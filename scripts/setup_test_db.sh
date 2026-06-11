#!/usr/bin/env bash
# Test PostgreSQL DB yaratish va schema qo'llash.
# Birinchi marta ishlatganda yoki schema o'zgarganda qayta ishlatiladi.
#
# Foydalanish:
#   bash scripts/setup_test_db.sh
#   bash scripts/setup_test_db.sh my_test_db    # DB nomi berib
#
# Kerak:
#   - PostgreSQL server ishlab turishi (psql PATH'da bo'lishi)
#   - PGUSER yoki joriy foydalanuvchining superuser yoki DB yaratish huquqi

set -euo pipefail

DB_NAME="${1:-jira_ai_test}"
SCHEMA_FILE="database/postgresql/001_initial_schema.sql"

cd "$(dirname "$0")/.."

if ! command -v psql &>/dev/null; then
    echo "Xato: psql topilmadi. PostgreSQL o'rnatilganligini tekshiring." >&2
    exit 1
fi

if [ ! -f "$SCHEMA_FILE" ]; then
    echo "Xato: $SCHEMA_FILE topilmadi." >&2
    exit 1
fi

echo "=== Test DB: $DB_NAME ==="

# DB mavjud bo'lmasa yaratamiz
if psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "DB allaqachon mavjud: $DB_NAME"
else
    echo "DB yaratilmoqda..."
    createdb "$DB_NAME"
    echo "OK: $DB_NAME yaratildi"
fi

echo "Schema qo'llanmoqda..."
psql "$DB_NAME" -f "$SCHEMA_FILE" -q
echo "OK: schema qo'llandi"

DSN="postgresql://localhost/$DB_NAME"
echo ""
echo "Test DSN:"
echo "  export APP_TEST_POSTGRES_DSN=\"$DSN\""
echo ""
echo "Yoki .env.test faylga qo'shing:"
echo "  APP_TEST_POSTGRES_DSN=$DSN"
