"""
pytest fixtures - Barcha testlar uchun umumiy sozlamalar
"""
import sys
import os
import pytest
import sqlite3

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(autouse=True)
def ensure_db():
    """Har test uchun DB initialized bo'lishi"""
    from utils.database.task_db import init_db
    init_db()
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
