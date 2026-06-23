import pytest

from utils.auth import company_repository

pytestmark = pytest.mark.no_db


class _DummyConn:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_upsert_company_settings_rejects_duplicate_webhook_project_keys(monkeypatch):
    conn = _DummyConn()
    calls = []

    monkeypatch.setattr(company_repository, "_ensure_company_webhook_project_keys_table", lambda _conn: None)
    monkeypatch.setattr(company_repository, "_fetch_registry_project_key_conflicts", lambda *_args: [])
    monkeypatch.setattr(company_repository, "payload_requires_encryption", lambda _payload: False)

    def conflict_checker(_conn, company_id, project_keys):
        calls.append((company_id, project_keys))
        return ["other-company: DEV"]

    ok = company_repository.upsert_company_settings(
        lambda: conn,
        321,
        {"webhook_project_keys": "dev, QA"},
        conflict_checker,
        lambda raw: [item.strip().upper() for item in raw.split(",") if item.strip()],
    )

    assert ok is False
    assert conn.closed is True
    assert calls == [(321, ["DEV", "QA"])]
