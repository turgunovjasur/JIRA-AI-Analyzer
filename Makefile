DB_TEST ?= jira_ai_test

.PHONY: test test-setup test-all help

help:
	@echo "Buyruqlar:"
	@echo "  make test-setup   — Test DB yaratish va schema qo'llash"
	@echo "  make test         — DB testlarini ishga tushirish (APP_TEST_POSTGRES_DSN kerak)"
	@echo "  make test-all     — setup + test (birinchi marta yoki schema o'zganda)"

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
