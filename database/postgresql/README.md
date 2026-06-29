# PostgreSQL Schema

Bu papka production-ready `PostgreSQL` schema artefaktlarini saqlaydi.

## Fayllar

- [001_initial_schema.sql](/Users/mac/Documents/projects/QA-Assistant/database/postgresql/001_initial_schema.sql)
  - birinchi target schema
  - auth, billing, integrations, ops va processing jadvallarini o'z ichiga oladi

## Maqsad

Bu SQL production runtime uchun PostgreSQL source-of-truth schema bo'lib xizmat qiladi.

## Eslatma

- Hozircha bu schema migration artifact sifatida qo'shildi
- keyingi bosqichda shu fayl `Alembic` yoki shunga o'xshash migration tool bilan boshqariladigan formatga o'tkaziladi

## Runtime va Tekshiruv

- schema validator:
  - [utils/tools/validate_postgres_schema.py](/Users/mac/Documents/projects/QA-Assistant/utils/tools/validate_postgres_schema.py)
- migration runner:
  - [utils/tools/run_postgres_migration_bundle.py](/Users/mac/Documents/projects/QA-Assistant/utils/tools/run_postgres_migration_bundle.py)
- readiness checker:
  - [utils/tools/check_postgres_ready.py](/Users/mac/Documents/projects/QA-Assistant/utils/tools/check_postgres_ready.py)
- `runtime.py` ichida:
  - postgres driver availability check
  - postgres connect helperlar
  - `connect_auth_db()` va `connect_processing_db()`

## Minimal Setup

- Python driver:
  - `psycopg[binary]`
- kerakli env:
  - `APP_POSTGRES_DSN=postgresql://USER:PASSWORD@HOST:5432/DBNAME`
- preflight checker:
  - [utils/tools/check_postgres_ready.py](/Users/mac/Documents/projects/QA-Assistant/utils/tools/check_postgres_ready.py)

## Dry Run Natijasi

- local `PostgreSQL` dry-run muvaffaqiyatli o'tdi
- asosiy row countlar tekshirildi:
  - `companies`: 5
  - `users`: 4
  - `subscriptions`: 5
  - `task_processing`: 38
  - `task_status_history`: 382
