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


def test_import_uses_all_tasks_and_existing_history_and_is_repeatable(monkeypatch):
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
    assert seen[0] == 'project in ("TEST")'
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


@pytest.mark.parametrize("initial", [True, False])
def test_first_import_includes_old_done_tasks_with_company_field_mapping(monkeypatch, initial):
    from services import team_analytics_sync as sync
    from utils.database.runtime import connect_processing_db
    from utils.database.team_analytics_repository import get_snapshot

    source = "https://tenant-import.example"
    monkeypatch.setattr(sync, "get_company_settings", lambda company: {
        "jira_server": source, "jira_project_keys": "OPS,APP",
    })
    monkeypatch.setattr(sync, "get_effective_company_modules", lambda company: {"team_analytics": True})
    monkeypatch.setattr(sync, "is_company_subscription_active", lambda company: (True, "active"))

    class Client:
        def __init__(self, config):
            self.source = config["jira_server"]

        def search(self, jql, *args):
            # These issues were finished long before analytics was enabled.
            assert jql.startswith('project in ("OPS","APP")')
            if "statusCategory" in jql or "updated >=" in jql:
                return iter([])
            return iter([{"key": "OPS-101"}, {"key": "APP-202"}])

        def discover_fields(self, project):
            return (project.lower() + "_points", project.lower() + "_sprint")

        def issue(self, key, *args):
            return {"id": key, "key": key, "fields": {
                "created": BASE.isoformat(), "updated": (BASE + timedelta(hours=2)).isoformat(),
                "status": {"name": "検証待ち", "statusCategory": {"key": "done"}},
                "assignee": {"accountId": "tenant-account", "displayName": "Tenant Person"},
                key.split("-")[0].lower() + "_points": 7,
                key.split("-")[0].lower() + "_sprint": [{"id": 29, "name": "Delivery", "state": "active"}],
            }}

        def changelog(self, key):
            return []

        def get(self, path, params=None):
            return {"id": 29, "name": "Delivery", "state": "active", "startDate": BASE.isoformat()}

    monkeypatch.setattr(sync, "JiraAnalyticsClient", Client)
    conn = connect_processing_db()
    try:
        conn.execute("DELETE FROM team_analytics_sync_state WHERE company_id=321 AND jira_source=%s", [source])
        conn.commit()
    finally:
        conn.close()
    sync.sync_company(321, initial=initial)
    snapshot = get_snapshot(321, assignee_id="tenant-account", jira_source=source,
                            sprint_id=29, sprint_source=source)
    assert {task["issue_key"] for task in snapshot["tasks"]} == {"OPS-101", "APP-202"}
    assert snapshot["summary"]["task_points"] == 14
    assert all(task["status_name"] == "検証待ち" for task in snapshot["tasks"])
    assert {task["points_field"] for task in snapshot["tasks"]} == {"ops_points", "app_points"}


def test_incremental_sync_repairs_missing_done_tasks_in_active_sprints(monkeypatch):
    from services import team_analytics_sync as sync
    from utils.database.runtime import connect_processing_db
    from utils.database.team_analytics_repository import get_snapshot, save_sprints

    source = "https://active-repair.example"
    monkeypatch.setattr(sync, "get_company_settings", lambda company: {
        "jira_server": source, "jira_project_keys": "OPS",
    })
    monkeypatch.setattr(sync, "get_effective_company_modules", lambda company: {"team_analytics": True})
    monkeypatch.setattr(sync, "is_company_subscription_active", lambda company: (True, "active"))
    conn = connect_processing_db()
    try:
        # Keep repeat runs independent of the sprint-move history below.
        for table in ["team_analytics_events", "team_analytics_tasks", "team_analytics_sprints"]:
            conn.execute(f"DELETE FROM {table} WHERE company_id=321 AND jira_source=%s", [source])
        conn.execute("""INSERT INTO team_analytics_sync_state(company_id,jira_source,last_success_at)
            VALUES(321,%s,now()) ON CONFLICT(company_id,jira_source) DO UPDATE SET last_success_at=now()""", [source])
        conn.commit()
    finally:
        conn.close()
    save_sprints(321, source, [{"id": 29, "name": "Delivery", "state": "active", "started_at": BASE.isoformat()}])

    class Client:
        allow_read = True
        moved = False

        def __init__(self, config):
            self.source = source

        def search(self, jql, *args):
            # An unchanged old task will not match the incremental time window.
            if self.moved:
                return iter([])
            return iter([{"key": "OPS-303", "fields": {"updated": (BASE + timedelta(hours=1)).isoformat()}}]) if "sprint in (29)" in jql else iter([])

        def discover_fields(self, project):
            return ("effort", "iteration")

        def issue(self, key, *args):
            assert self.allow_read, "Unchanged stopped tasks must not re-download their changelog every sync"
            return {"id": key, "key": key, "fields": {
                "created": BASE.isoformat(), "updated": (BASE + timedelta(hours=2 if self.moved else 1)).isoformat(),
                "status": {"name": "Released", "statusCategory": {"key": "done"}},
                "assignee": {"accountId": "repair-account", "displayName": "Repair Person"},
                "effort": 3, "iteration": [{"id": 30 if self.moved else 29, "name": "Delivery", "state": "active"}],
            }}

        def changelog(self, key):
            return []

        def get(self, path, params=None):
            return {"id": int(path.rsplit("/", 1)[1]), "name": "Delivery", "state": "active", "startDate": BASE.isoformat()}

    monkeypatch.setattr(sync, "JiraAnalyticsClient", Client)
    sync.sync_company(321)
    snapshot = get_snapshot(321, assignee_id="repair-account", jira_source=source,
                            sprint_id=29, sprint_source=source)
    assert [task["issue_key"] for task in snapshot["tasks"]] == ["OPS-303"]
    assert snapshot["tasks"][0]["status_name"] == "Released"
    Client.allow_read = False
    repeated = sync.sync_company(321)
    assert repeated["inserted_events"] == 0
    # A missed old sprint-move webhook must be repaired even when neither the
    # old sprint nor the recent-update search returns this stopped task.
    Client.allow_read = True
    Client.moved = True
    sync.sync_company(321)
    assert get_snapshot(321, assignee_id="repair-account", jira_source=source,
                        sprint_id=29, sprint_source=source)["total"] == 0
