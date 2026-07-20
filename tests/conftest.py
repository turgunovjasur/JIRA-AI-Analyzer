"""
pytest fixtures - Barcha testlar uchun umumiy sozlamalar.
"""
import importlib
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(autouse=True)
def isolate_test_databases(monkeypatch, request):
    """DB testlarini alohida PostgreSQL test DSN bilan ishlatish."""
    if request.node.get_closest_marker("no_db"):
        yield {}
        return

    test_dsn = (os.getenv("APP_TEST_POSTGRES_DSN") or "").strip()
    if not test_dsn:
        pytest.skip("APP_TEST_POSTGRES_DSN kerak: DB testlari production DSN bilan ishlatilmaydi")

    import utils.database.runtime as runtime

    monkeypatch.setenv("APP_POSTGRES_DSN", test_dsn)
    monkeypatch.setattr(runtime, "DB_BACKEND", "postgres", raising=False)
    monkeypatch.setattr(runtime, "POSTGRES_DSN", test_dsn, raising=False)

    import utils.auth.auth_db as auth_db
    import utils.database.task_db as task_db

    task_db = importlib.reload(task_db)
    auth_db = importlib.reload(auth_db)

    _align_postgres_test_schema(runtime)
    task_db.init_db()
    auth_db.init_auth_db()

    importlib.invalidate_caches()
    yield {
        "task_db": task_db,
        "auth_db": auth_db,
    }


def _align_postgres_test_schema(runtime):
    conn = runtime.connect_postgres()
    try:
        conn.execute("ALTER TABLE task_processing ALTER COLUMN company_id DROP NOT NULL")
        conn.execute(
            """
            INSERT INTO companies (id, company_code, company_name, seat_limit, is_active)
            VALUES (321, 'pytest321', 'Pytest Company 321', 10, TRUE)
            ON CONFLICT (id) DO NOTHING
            """
        )
        conn.execute(
            """
            INSERT INTO company_subscriptions (
                company_id, plan_name, subscription_status, billing_mode,
                billing_start_date, billing_end_date, last_payment_note
            )
            VALUES (321, 'base', 'active', 'manual', CURRENT_DATE, CURRENT_DATE + INTERVAL '30 days', '')
            ON CONFLICT (company_id) DO NOTHING
            """
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def ensure_db(isolate_test_databases):
    """Har DB test uchun runtime jadvallar initialized bo'lishi."""
    if not isolate_test_databases:
        yield
        return

    task_db = isolate_test_databases["task_db"]

    from datetime import date, timedelta

    from utils.auth.auth_db import (
        create_company,
        get_company_by_code,
        init_auth_db,
        save_company_settings,
        save_company_subscription,
        save_company_webhook_module_settings,
    )

    task_db.init_db()
    init_auth_db()
    company = get_company_by_code("pytestco") or create_company(
        "pytestco",
        "Pytest Company",
        enabled_modules={"webhook": True}
    )
    if not company:
        raise RuntimeError("Test fixture company `pytestco` yaratilmadi")

    # create_company avtomatik trial obuna beradi — u tugagach webhook obuna
    # tekshiruvi 'ignored' qaytaradi. Testlar vaqtdan mustaqil bo'lishi uchun
    # har run'da obunani faol + uzoq muddatli qilib yangilaymiz.
    if not save_company_subscription(company["id"], {
        "plan_name": "base",
        "subscription_status": "active",
        "billing_mode": "manual",
        "billing_start_date": date.today().isoformat(),
        "billing_end_date": (date.today() + timedelta(days=3650)).isoformat(),
    }):
        raise RuntimeError("`pytestco` company subscription saqlanmadi")

    if not save_company_settings(company["id"], {
        "webhook_project_keys": "TEST",
        "jira_project_keys": "TEST",
        "webhook_secret": "pytest-webhook-secret",
        "webhook_trigger_status": "READY TO TEST",
        "webhook_trigger_aliases": "READY TO TEST,Ready To Test",
    }):
        raise RuntimeError("`pytestco` company settings saqlanmadi")
    if not save_company_webhook_module_settings(company["id"], "webhook_testcase", {
        "auto_comment_enabled": True,
        "auto_comment_trigger_status": "READY TO TEST",
        "auto_comment_trigger_aliases": "READY TO TEST,Ready To Test",
    }):
        raise RuntimeError("`pytestco` webhook testcase settings saqlanmadi")
    yield


@pytest.fixture(autouse=True)
def cleanup_test_tasks(ensure_db):
    """Test oldi/keyin test ma'lumotlarini DB dan tozalash."""
    _cleanup_postgres_test_data()
    yield
    _cleanup_postgres_test_data()


def _cleanup_postgres_test_data():
    try:
        from utils.database.runtime import connect_processing_db

        conn = connect_processing_db()
        conn.execute(
            """
            DELETE FROM job_queue
            WHERE task_key LIKE 'TEST-%'
               OR task_key LIKE 'PYTEST-%'
               OR dedupe_key LIKE 'job:test%'
            """
        )
        conn.execute(
            """
            DELETE FROM checker_runs
            WHERE task_key LIKE 'TEST-%'
               OR task_key LIKE 'PYTEST-%'
               OR run_id LIKE 'tzpr-%'
            """
        )
        conn.execute("DELETE FROM task_processing WHERE task_id LIKE 'TEST-%'")
        conn.execute("DELETE FROM task_processing WHERE task_id LIKE 'PYTEST-%'")
        conn.commit()
        conn.close()
    except Exception:
        pass
