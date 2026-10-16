from datetime import datetime, timedelta

import pytest

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


def test_daily_and_weekly_limits_shared_across_tasks_and_pages():
    from datetime import timezone

    from utils.database import team_analytics_repository as repo

    source = "https://work-limits.example"
    monday = datetime(2026, 9, 20, 19, tzinfo=timezone.utc)  # Monday midnight in Tashkent.
    # Two concurrent tasks plus another person, on seven days and the next Monday.
    for index in range(3):
        events = []
        for day in range(8):
            for hours, status in [(0, "In Progress"), (12, "Done")]:
                person = "limit-other" if index == 2 else "limit-person"
                payload = body(day * 24 + hours, status, person=person, key=f"LIMIT-{index}")
                at = monday + timedelta(days=day, hours=hours)
                payload["timestamp"] = int(at.timestamp() * 1000)
                events.append(normalize_event(payload, "sp", "sprint", at))
        repo.persist_events(321, source, events)
    repo.save_settings(321, "In Progress", None, 8, 40)
    page = repo.get_snapshot(321, limit=1, assignee_id="limit-person", jira_source=source)
    other_page = repo.get_snapshot(321, limit=1, offset=1, assignee_id="limit-person", jira_source=source)
    assert page["daily_hours"] == 8
    assert page["weekly_hours"] == 40
    assert page["total"] == 2
    # First week capped at 40; the next Monday gets a new 8-hour allowance.
    assert page["summary"]["worked_seconds"] == pytest.approx(48 * 3600)
    assert other_page["summary"] == page["summary"]
    assert repo.get_snapshot(321, assignee_id="limit-other", jira_source=source)["summary"]["worked_seconds"] == pytest.approx(48 * 3600)
    for snapshot in [page, other_page]:
        task = snapshot["tasks"][0]
        assert task["assignee_seconds"] == pytest.approx(24 * 3600)
        assert sum(interval["counted_seconds"] for interval in task["intervals"]) == pytest.approx(24 * 3600)
        assert max(interval["counted_seconds"] for interval in task["intervals"]) <= 4 * 3600

    # Changing settings recalculates without rewriting the Jira history.
    repo.save_settings(321, "In Progress", None, 4, 20)
    changed = repo.get_snapshot(321, assignee_id="limit-person", jira_source=source)
    assert changed["summary"]["worked_seconds"] == pytest.approx(24 * 3600)


def test_projection_late_event_duplicate_and_tenant_filter(monkeypatch):
    from utils.database import team_analytics_repository as repo
    from utils.database.runtime import connect_processing_db

    conn = connect_processing_db()
    try:
        conn.execute("DELETE FROM team_analytics_events WHERE company_id=321")
        conn.execute("DELETE FROM team_analytics_settings WHERE company_id=321")
        conn.execute("DELETE FROM team_analytics_tasks WHERE company_id=321")
        conn.execute("DELETE FROM team_analytics_productivity_settings WHERE company_id=321")
        conn.commit()
    finally:
        conn.close()
    repo.record_event(321, "https://jira.example", body(4, "Done", "vali"), "sp", "sprint")
    repo.record_event(321, "https://jira.example", body(0), "sp", "sprint")
    repo.record_event(321, "https://jira.example", body(2, person="vali"), "sp", "sprint")
    repo.record_event(321, "https://jira.example", body(2, person="vali"), "sp", "sprint")
    selected = repo.get_snapshot(321, assignee_id="ali", jira_source="https://jira.example")
    # Jira's assignee filter uses the current owner, not historical work.
    assert selected["total"] == 0
    assert selected["summary"]["worked_seconds"] == 0
    current = repo.get_snapshot(321, assignee_id="vali", jira_source="https://jira.example")
    assert current["total"] == 1
    assert current["summary"]["worked_seconds"] == 7200
    assert current["tasks"][0]["sprint_ids"] == [17]
    assert repo.get_snapshot(321)["summary"]["worked_seconds"] == 14400
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
        conn.execute("DELETE FROM team_analytics_productivity_settings WHERE company_id=321")
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
        conn.execute("DELETE FROM team_analytics_productivity_settings WHERE company_id=321")
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


def test_sprint_filter_uses_current_membership_and_preserves_history():
    from utils.database import team_analytics_repository as repo
    from utils.database.runtime import connect_processing_db

    source = "https://sprint-filter.example"
    conn = connect_processing_db()
    try:
        conn.execute("DELETE FROM team_analytics_events WHERE company_id=321")
        conn.execute("DELETE FROM team_analytics_tasks WHERE company_id=321")
        conn.execute("DELETE FROM team_analytics_settings WHERE company_id=321")
        conn.execute("DELETE FROM team_analytics_productivity_settings WHERE company_id=321")
        conn.commit()
    finally:
        conn.close()
    for index in range(2):
        start = body(0, key=f"TEST-SPRINT-{index}")
        finish = body(4, "Done", key=f"TEST-SPRINT-{index}")
        # One task moved away; only the task still in Pilot belongs in its list.
        finish["issue"]["fields"]["sprint"] = ([{"id": 18, "name": "Next"}] if index == 0
                                                    else [{"id": 17, "name": "Pilot"}])
        repo.persist_events(321, source, [normalize_event(start, "sp", "sprint", BASE),
                                         normalize_event(finish, "sp", "sprint", BASE)])
    repo.save_sprints(321, source, [{"id": 17, "name": "Pilot", "state": "closed", "started_at": (BASE + timedelta(hours=1)).isoformat(),
                                   "completed_at": (BASE + timedelta(hours=3)).isoformat()}])
    page = repo.get_snapshot(321, limit=1, sprint_id=17, sprint_source=source, assignee_id="ali", jira_source=source)
    assert page["total"] == 1
    assert len(page["tasks"]) == 1
    assert page["tasks"][0]["issue_key"] == "TEST-SPRINT-1"
    assert page["summary"]["worked_seconds"] == 7200
    assert page["summary"]["task_points"] == 4
    assert page["tasks"][0]["assignee_seconds"] == 7200
    assert datetime.fromisoformat(page["tasks"][0]["intervals"][0]["started_at"]) == BASE + timedelta(hours=1)
    assert datetime.fromisoformat(page["tasks"][0]["intervals"][0]["ended_at"]) == BASE + timedelta(hours=3)
    assert not page["tasks"][0]["intervals"][0]["is_open"]
    assert repo.get_snapshot(321)["summary"]["worked_seconds"] == 28800
    assert repo.get_snapshot(321, sprint_id=17, sprint_source=source, assignee_id="ali", jira_source="https://other.example")["total"] == 0
    import pytest
    with pytest.raises(ValueError):
        repo.get_snapshot(999999, sprint_id=17, sprint_source=source)


@pytest.mark.parametrize("event_type", ["jira:issue_deleted", "jira:issue_unavailable"])
def test_jira_invisible_tasks_are_excluded_but_their_history_is_retained(event_type):
    from utils.database import team_analytics_repository as repo
    from utils.database.runtime import connect_processing_db

    source = "https://visibility.example/" + event_type.split(":")[1]
    payloads = [body(0, key="TEST-VISIBILITY"), body(2, "Done", key="TEST-VISIBILITY")]
    repo.persist_events(321, source, [normalize_event(p, "sp", "sprint", BASE) for p in payloads])
    removed = {
        "issue": {"id": "TEST-VISIBILITY", "key": "TEST-VISIBILITY"},
        "webhookEvent": event_type,
        "timestamp": int((BASE + timedelta(hours=3)).timestamp() * 1000),
    }
    repo.record_event(321, source, removed, "sp", "sprint")
    assert repo.get_snapshot(321, assignee_id="ali", jira_source=source)["total"] == 0
    conn = connect_processing_db()
    try:
        assert conn.execute("""SELECT count(*) FROM team_analytics_intervals
            WHERE company_id=321 AND jira_source=%s AND issue_id='TEST-VISIBILITY'""", [source]).fetchone()[0] == 1
    finally:
        conn.close()


def test_current_sprint_and_assignee_filters_isolate_populated_tenants_and_sources():
    from utils.auth.auth_db import create_company, get_company_by_code
    from utils.database import team_analytics_repository as repo

    other = get_company_by_code("analyticsparity") or create_company("analyticsparity", "Analytics Parity")
    source = "https://isolation.example"
    # Same Jira issue, sprint ID and account ID in two tenants and two sources.
    for company, jira, points in [(321, source, 4), (other["id"], source, 99), (321, source + "/other", 200)]:
        payload = body(0, "Done", person="same-account", key="TEST-SAME-ISSUE")
        payload["issue"]["fields"]["sp"] = points
        repo.record_event(company, jira, payload, "sp", "sprint")
        repo.save_sprints(company, jira, [{"id": 17, "name": "Pilot", "state": "active", "started_at": BASE.isoformat()}])
    selected = repo.get_snapshot(321, sprint_id=17, sprint_source=source,
                                 assignee_id="same-account", jira_source=source)
    assert selected["total"] == 1
    assert selected["summary"]["task_points"] == 4
    assert selected["tasks"][0]["jira_source"] == source
    assert repo.get_snapshot(other["id"], assignee_id="same-account", jira_source=source)["summary"]["task_points"] == 99
