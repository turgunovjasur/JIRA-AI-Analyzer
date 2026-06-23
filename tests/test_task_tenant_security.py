import pytest

from utils.database import task_repository

pytestmark = pytest.mark.no_db


class _FakeCursor:
    def __init__(self, rows=None):
        self.calls = []
        self.rows = list(rows or [])

    def execute(self, query, params=None):
        self.calls.append((query, list(params or [])))

    def fetchone(self):
        if self.rows:
            return self.rows.pop(0)
        return None


class _FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False
        self.committed = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True

    def commit(self):
        self.committed = True


def test_fetch_task_by_id_scopes_by_company_id_when_provided():
    cursor = _FakeCursor(rows=[{"task_id": "DEV-1", "company_id": 42}])
    conn = _FakeConn(cursor)

    result = task_repository.fetch_task_by_id(
        lambda **_kwargs: conn,
        "DEV-1",
        timeout=30,
        company_id=42,
    )

    query, params = cursor.calls[0]
    assert "WHERE task_id = %s AND company_id = %s" in " ".join(query.split())
    assert params == ["DEV-1", 42]
    assert result["company_id"] == 42


def test_upsert_task_record_updates_by_row_id_inside_company_scope():
    cursor = _FakeCursor(rows=[(7,)])
    conn = _FakeConn(cursor)

    task_repository.upsert_task_record(
        lambda **_kwargs: conn,
        "DEV-1",
        {"task_status": "completed"},
        timeout=30,
        company_id=42,
    )

    select_query, select_params = cursor.calls[0]
    update_query, update_params = cursor.calls[1]
    assert "WHERE task_id = %s AND company_id = %s" in " ".join(select_query.split())
    assert select_params == ["DEV-1", 42]
    assert "WHERE id = %s" in " ".join(update_query.split())
    assert update_params[-1] == 7
    assert 42 in update_params
