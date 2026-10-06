from datetime import datetime, timedelta

from services.team_analytics import normalize_event
from tests.test_team_analytics import BASE


def body(hour, status="In Progress", person="ali", key="TEST-ANALYTICS-1"):
    return {
        "timestamp": int((BASE + timedelta(hours=hour)).timestamp() * 1000),
        "webhookEvent": "jira:issue_updated",
        "changelog": {"id": str(hour + 10), "items": []},
        "issue": {
            "id": key,
            "key": key,
            "fields": {
                "summary": key,
                "status": {"id": status, "name": status},
                "assignee": {"accountId": person, "displayName": person},
                "sp": 4,
                "sprint": [{"id": 17, "name": "Pilot", "state": "active"}],
            },
        },
    }


def test_projection_late_event_duplicate_and_tenant_filter(monkeypatch):
    from utils.database import team_analytics_repository as repo
    from utils.database.runtime import connect_processing_db

    conn = connect_processing_db()
    try:
        conn.execute("DELETE FROM team_analytics_events WHERE company_id=321")
        conn.execute("DELETE FROM team_analytics_settings WHERE company_id=321")
        conn.execute("DELETE FROM team_analytics_tasks WHERE company_id=321")
        conn.commit()
    finally:
        conn.close()
    repo.record_event(321, "https://jira.example", body(4, "Done", "vali"), "sp", "sprint")
    repo.record_event(321, "https://jira.example", body(0), "sp", "sprint")
    repo.record_event(321, "https://jira.example", body(2, person="vali"), "sp", "sprint")
    repo.record_event(321, "https://jira.example", body(2, person="vali"), "sp", "sprint")
    selected = repo.get_snapshot(321, assignee_id="ali", jira_source="https://jira.example")
    assert selected["total"] == 1
    assert selected["summary"]["worked_seconds"] == 7200
    assert selected["tasks"][0]["sprint_ids"] == [17]
    assert repo.get_snapshot(321, assignee_id="ali", jira_source="https://other.example")["total"] == 0
    assert repo.get_snapshot(999999)["total"] == 0
    conn = connect_processing_db()
    try:
        assert conn.execute("SELECT count(*) FROM team_analytics_events WHERE company_id=321").fetchone()[0] == 3
        assert (
            conn.execute(
                "SELECT count(*) FROM team_analytics_sprints WHERE company_id=321 AND jira_source='https://jira.example' AND sprint_id=17"
            ).fetchone()[0]
            == 1
        )
    finally:
        conn.close()


def test_page_totals_cover_more_than_one_page():
    from utils.database import team_analytics_repository as repo
    from utils.database.runtime import connect_processing_db

    conn = connect_processing_db()
    try:
        conn.execute("DELETE FROM team_analytics_events WHERE company_id=321")
        conn.execute("DELETE FROM team_analytics_tasks WHERE company_id=321")
        conn.commit()
    finally:
        conn.close()
    for index in range(3):
        events = [
            normalize_event(body(h, status, key=f"TEST-ANALYTICS-{index}"), "sp", "sprint", BASE)
            for h, status in [(0, "In Progress"), (1, "Done")]
        ]
        repo.persist_events(321, "https://jira.example", events)
    page = repo.get_snapshot(321, limit=1, offset=1)
    assert len(page["tasks"]) == 1
    assert page["total"] == 3
    assert page["summary"]["worked_seconds"] == 10800
    assert page["summary"]["task_points"] == 12
    assert len(page["summary"]["task_estimates"]) == 3
    assert page["summary"]["assignee_count"] == 1
    repo.record_event(321, "https://other.example", body(0, person="vali", key="TEST-ANALYTICS-OTHER"), "sp", "sprint")
    assert repo.get_snapshot(321, limit=1)["summary"]["assignee_count"] == 2


def test_settings_change_preserves_earlier_time_and_changes_future_status(monkeypatch):
    from utils.database import team_analytics_repository as repo
    from utils.database.runtime import connect_processing_db

    conn = connect_processing_db()
    try:
        conn.execute("DELETE FROM team_analytics_events WHERE company_id=321")
        conn.execute("DELETE FROM team_analytics_tasks WHERE company_id=321")
        conn.execute("DELETE FROM team_analytics_settings WHERE company_id=321")
        conn.commit()
    finally:
        conn.close()
    repo.persist_events(
        321,
        "https://jira.example",
        [normalize_event(body(h, status), "sp", "sprint", BASE) for h, status in [(0, "In Progress"), (4, "Done")]],
    )

    class Clock(datetime):
        at = BASE + timedelta(hours=2)

        @classmethod
        def now(cls, tz=None):
            return cls.at

    monkeypatch.setattr(repo, "datetime", Clock)
    # DB uses clock_timestamp for setting effective_at; align it with the test clock.
    repo.save_settings(321, "Done", None, 4)
    conn = connect_processing_db()
    try:
        conn.execute("UPDATE team_analytics_settings SET effective_at=%s WHERE company_id=321", [Clock.at])
        conn.commit()
    finally:
        conn.close()
    # Rebuild through the next real source event.
    Clock.at = BASE + timedelta(hours=5)
    repo.record_event(321, "https://jira.example", body(5, "Done"), "sp", "sprint")
    snapshot = repo.get_snapshot(321)
    assert snapshot["summary"]["worked_seconds"] == 10800
    assert snapshot["summary"]["work_days"] == 0.75
    assert snapshot["daily_hours"] == 4


def test_sprint_filter_clips_history_totals_and_detail_with_historical_membership():
    from utils.database import team_analytics_repository as repo
    from utils.database.runtime import connect_processing_db

    source = "https://sprint-filter.example"
    conn = connect_processing_db()
    try:
        conn.execute("DELETE FROM team_analytics_events WHERE company_id=321")
        conn.execute("DELETE FROM team_analytics_tasks WHERE company_id=321")
        conn.execute("DELETE FROM team_analytics_settings WHERE company_id=321")
        conn.commit()
    finally:
        conn.close()
    for index in range(2):
        start = body(0, key=f"TEST-SPRINT-{index}")
        finish = body(4, "Done", key=f"TEST-SPRINT-{index}")
        finish["issue"]["fields"]["sprint"] = [{"id": 18, "name": "Next"}]
        repo.persist_events(321, source, [normalize_event(start, "sp", "sprint", BASE),
                                         normalize_event(finish, "sp", "sprint", BASE)])
    repo.save_sprints(321, source, [{"id": 17, "name": "Pilot", "state": "closed", "started_at": (BASE + timedelta(hours=1)).isoformat(),
                                   "completed_at": (BASE + timedelta(hours=3)).isoformat()}])
    page = repo.get_snapshot(321, limit=1, sprint_id=17, sprint_source=source, assignee_id="ali", jira_source=source)
    assert page["total"] == 2
    assert len(page["tasks"]) == 1
    assert page["summary"]["worked_seconds"] == 14400
    assert page["summary"]["task_points"] == 8
    assert page["tasks"][0]["assignee_seconds"] == 7200
    assert page["tasks"][0]["intervals"][0]["started_at"] == (BASE + timedelta(hours=1)).isoformat()
    assert page["tasks"][0]["intervals"][0]["ended_at"] == (BASE + timedelta(hours=3)).isoformat()
    assert not page["tasks"][0]["intervals"][0]["is_open"]
    assert repo.get_snapshot(321)["summary"]["worked_seconds"] == 28800
    assert repo.get_snapshot(321, sprint_id=17, sprint_source=source, assignee_id="ali", jira_source="https://other.example")["total"] == 0
    import pytest
    with pytest.raises(ValueError):
        repo.get_snapshot(999999, sprint_id=17, sprint_source=source)
