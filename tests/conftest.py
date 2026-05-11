"""
pytest fixtures - Barcha testlar uchun umumiy sozlamalar
"""
import sys
import os
import pytest
import sqlite3
import importlib

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(autouse=True)
def isolate_test_databases(tmp_path, monkeypatch):
    """Har test uchun auth/processing DB'larni vaqtinchalik SQLite fayllarga yo'naltirish."""
    import utils.database.runtime as runtime

    auth_db_path = tmp_path / "auth.db"
    processing_db_path = tmp_path / "processing.db"
    monkeypatch.setenv("APP_DB_BACKEND", "sqlite")
    monkeypatch.setenv("APP_POSTGRES_DSN", "")
    monkeypatch.setattr(runtime, "DB_BACKEND", "sqlite", raising=False)
    monkeypatch.setattr(runtime, "POSTGRES_DSN", "", raising=False)
    monkeypatch.setattr(runtime, "AUTH_DB_PATH", str(auth_db_path), raising=False)
    monkeypatch.setattr(runtime, "PROCESSING_DB_PATH", str(processing_db_path), raising=False)

    import utils.database.task_db as task_db
    import utils.auth.auth_bootstrap as auth_bootstrap
    import utils.auth.auth_db as auth_db

    task_db = importlib.reload(task_db)
    auth_bootstrap = importlib.reload(auth_bootstrap)
    auth_db = importlib.reload(auth_db)

    monkeypatch.setattr(task_db, "DB_FILE", str(processing_db_path), raising=False)
    monkeypatch.setattr(auth_bootstrap, "AUTH_DB_FILE", str(auth_db_path), raising=False)
    monkeypatch.setattr(auth_db, "AUTH_DB_FILE", str(auth_db_path), raising=False)
    task_db.init_db()
    auth_db.init_auth_db()

    importlib.invalidate_caches()
    yield {
        "task_db": task_db,
        "auth_db": auth_db,
    }


@pytest.fixture(autouse=True)
def ensure_db(isolate_test_databases):
    """Har test uchun DB initialized bo'lishi"""
    task_db = isolate_test_databases["task_db"]
    auth_db = isolate_test_databases["auth_db"]

    from utils.auth.auth_db import (
        init_auth_db,
        create_company,
        get_company_by_code,
        save_company_settings,
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
    if company:
        if not save_company_settings(company["id"], {
            "webhook_project_keys": "TEST",
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
def cleanup_test_tasks():
    """Test keyin test task'larni DB dan tozalash"""
    yield
    try:
        from utils.database.task_db import DB_FILE
        conn = sqlite3.connect(DB_FILE)
        conn.execute("DELETE FROM task_processing WHERE task_id LIKE 'TEST-%'")
        conn.execute("DELETE FROM task_processing WHERE task_id LIKE 'PYTEST-%'")
        conn.commit()
        conn.close()
    except Exception:
        pass
