from datetime import timedelta

import pytest

from tests.test_team_analytics import BASE


def test_failed_sync_does_not_advance_success_checkpoint(monkeypatch):
    from services import team_analytics_sync as sync
    from utils.database.runtime import connect_processing_db

    monkeypatch.setattr(
        sync,
        "get_company_settings",
        lambda company: {"jira_server": "https://jira.example", "jira_project_keys": "TEST"},
    )

    class FailingClient:
        source = "https://jira.example"

        def __init__(self, config):
            pass

        def search(self, *args):
            raise RuntimeError("source unavailable")

    monkeypatch.setattr(sync, "JiraAnalyticsClient", FailingClient)
    conn = connect_processing_db()
    try:
        conn.execute("DELETE FROM team_analytics_sync_state WHERE company_id=321")
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RuntimeError, match="source unavailable"):
        sync.sync_company(321, initial=True)
    conn = connect_processing_db(row_factory=True)
    try:
        row = conn.execute("SELECT * FROM team_analytics_sync_state WHERE company_id=321").fetchone()
        assert row["last_success_at"] is None
        assert "source unavailable" in row["last_error"]
    finally:
        conn.close()


def test_import_uses_open_tasks_and_existing_history_and_is_repeatable(monkeypatch):
    from services import team_analytics_sync as sync
    from utils.database.runtime import connect_processing_db
    from utils.database.team_analytics_repository import get_snapshot

    monkeypatch.setattr(
        sync,
        "get_company_settings",
        lambda company: {"jira_server": "https://jira.example", "jira_project_keys": "TEST"},
    )
    seen = []
    read_keys = []

    class Client:
        source = "https://jira.example"

        def __init__(self, config):
            pass

        def search(self, jql, *args):
            seen.append(jql)
            return iter([{"key": "TEST-OPEN"}])

        def discover_fields(self, project):
            return ("sp", "sprint")

        def issue(self, key, *args):
            read_keys.append(key)
            return {
                "id": key,
                "key": key,
                "fields": {
                    "created": BASE.isoformat(),
                    "updated": (BASE + timedelta(hours=2)).isoformat(),
                    "status": {"name": "Done"},
                    "assignee": {"accountId": "ali", "displayName": "Ali"},
                    "sp": 2,
                    "sprint": [],
                },
            }

        def changelog(self, key):
            return [
                {
                    "id": "3",
                    "created": (BASE + timedelta(hours=2)).isoformat(),
                    "items": [{"field": "status", "fromString": "In Progress", "toString": "Done"}],
                }
            ]

        def get(self, *args):
            return {}

    monkeypatch.setattr(sync, "JiraAnalyticsClient", Client)
    conn = connect_processing_db()
    try:
        conn.execute("DELETE FROM team_analytics_events WHERE company_id=321")
        conn.execute("DELETE FROM team_analytics_tasks WHERE company_id=321")
        conn.execute("DELETE FROM team_analytics_settings WHERE company_id=321")
        conn.execute(
            "INSERT INTO task_status_history(company_id,task_id,to_status,changed_at) VALUES(321,'TEST-HISTORY','Ready to Test',now())"
        )
        conn.commit()
    finally:
        conn.close()
    first = sync.sync_company(321, initial=True)
    second = sync.sync_company(321, initial=True)
    assert first["tasks"] == 2
    assert second["inserted_events"] == 0
    assert get_snapshot(321)["summary"]["worked_seconds"] == 14400
    assert "statusCategory != Done" in seen[0]
    # Discovery scope changes must not strand a previously tracked working issue.
    conn = connect_processing_db()
    try:
        conn.execute(
            "UPDATE team_analytics_tasks SET snapshot=jsonb_set(snapshot,'{is_working}','true') WHERE company_id=321 AND issue_key='TEST-OPEN'"
        )
        conn.commit()
    finally:
        conn.close()
    read_keys.clear()
    monkeypatch.setattr(Client, "search", lambda *args: iter([]))
    monkeypatch.setattr(
        sync,
        "get_company_settings",
        lambda company: {"jira_server": "https://jira.example", "jira_project_keys": "OTHER"},
    )
    monkeypatch.setattr(sync, "get_effective_company_modules", lambda company: {"team_analytics": True})
    monkeypatch.setattr(sync, "is_company_subscription_active", lambda company: (True, "active"))
    sync.sync_company(321)
    assert "TEST-OPEN" in read_keys
