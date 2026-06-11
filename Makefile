DB_TEST ?= jira_ai_test

.PHONY: help test test-setup test-all up down build backup restore

help:
	@echo "Buyruqlar:"
	@echo ""
	@echo "  Test:"
	@echo "    make test-setup      — Test DB yaratish va schema qo'llash"
	@echo "    make test            — DB testlarini ishga tushirish"
	@echo "    make test-all        — setup + test"
	@echo ""
	@echo "  Docker:"
	@echo "    make up              — docker compose up --build -d"
	@echo "    make down            — docker compose down"
	@echo "    make build           — docker compose build"
	@echo ""
	@echo "  DB:"
	@echo "    make backup          — DB backup (./backups/ ga saqlaydi)"
	@echo "    make restore FILE=x  — DB restore (make restore FILE=backups/x.sql.gz)"

# ── Test ──────────────────────────────────────────────────
test-setup:
	bash scripts/setup_test_db.sh $(DB_TEST)

test:
	@if [ -z "$$APP_TEST_POSTGRES_DSN" ]; then \
		echo "Xato: APP_TEST_POSTGRES_DSN o'rnatilmagan."; \
		echo "Avval: make test-setup  yoki  export APP_TEST_POSTGRES_DSN=postgresql://localhost/$(DB_TEST)"; \
		exit 1; \
	fi
	python -m pytest $(ARGS)

test-all: test-setup
	APP_TEST_POSTGRES_DSN=postgresql://localhost/$(DB_TEST) python -m pytest $(ARGS)

# ── Docker ───────────────────────────────────────────────
up:
	docker compose up --build -d

down:
	docker compose down

build:
	docker compose build

# ── DB backup / restore ──────────────────────────────────
backup:
	bash scripts/backup_db.sh

restore:
	@if [ -z "$(FILE)" ]; then echo "Foydalanish: make restore FILE=backups/jira_ai_XXXX.sql.gz"; exit 1; fi
	bash scripts/restore_db.sh $(FILE)
