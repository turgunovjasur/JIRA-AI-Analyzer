from datetime import timedelta

import pytest

from services.team_analytics import replay_task
from tests.test_team_analytics import BASE

pytestmark = pytest.mark.no_db


def test_import_reconstructs_old_assignee_and_complete_pause_resume():
    from services.team_analytics_history import history_events

    issue = {
        "id": "1",
        "key": "DEV-1",
        "fields": {
            "created": BASE.isoformat(),
            "updated": (BASE + timedelta(hours=4)).isoformat(),
            "status": {"id": "9", "name": "Done"},
            "assignee": {"accountId": "vali", "displayName": "Vali"},
            "sp": 4,
            "sprint": [{"id": 11}],
        },
    }
    histories = [
        {
            "id": "1",
            "created": (BASE + timedelta(hours=1)).isoformat(),
            "items": [{"fieldId": "status", "from": "1", "fromString": "To Do", "to": "3", "toString": "In Progress"}],
        },
        {
            "id": "2",
            "created": (BASE + timedelta(hours=2)).isoformat(),
            "items": [
                {"fieldId": "assignee", "from": "ali", "fromString": "Ali", "to": "vali", "toString": "Vali"},
                {"fieldId": "sprint", "field": "Sprint", "from": "10", "to": "11"},
            ],
        },
        {
            "id": "3",
            "created": (BASE + timedelta(hours=4)).isoformat(),
            "items": [{"fieldId": "status", "from": "3", "fromString": "In Progress", "to": "9", "toString": "Done"}],
        },
    ]
    events = history_events(issue, histories, "sp", "sprint", BASE + timedelta(hours=6))
    result = replay_task(events, [], BASE + timedelta(hours=6))
    assert [(i["assignee_id"], i["seconds"]) for i in result["intervals"]] == [("ali", 3600), ("vali", 7200)]
    assert result["sprint_ids"] == [11]
    assert events[0]["snapshot"]["sprint_ids"] == [10]
    assert result["total_seconds"] == 10800
    assert result["status_name"] == "Done"


def test_import_and_live_transition_have_same_event_identity():
    from services.team_analytics import normalize_event
    from services.team_analytics_history import history_events

    issue = {"id": "1", "key": "DEV-1", "fields": {"created": BASE.isoformat(), "status": {"name": "Done"}}}
    change = {
        "id": "15",
        "created": (BASE + timedelta(hours=1)).isoformat(),
        "items": [{"field": "status", "fromString": "In Progress", "toString": "Done"}],
    }
    imported = history_events(issue, [change], "sp", "sprint", BASE + timedelta(hours=2))
    live = normalize_event(
        {
            "webhookEvent": "jira:issue_updated",
            "issue": issue,
            "timestamp": int((BASE + timedelta(hours=1)).timestamp() * 1000),
            "changelog": change,
        },
        "sp",
        "sprint",
        BASE,
    )
    assert imported[1]["event_key"] == live["event_key"]


def test_import_and_delayed_created_webhook_have_same_identity_and_time():
    from services.team_analytics import normalize_event
    from services.team_analytics_history import history_events

    issue = {"id": "1", "key": "DEV-1", "fields": {"created": BASE.isoformat(), "status": {"name": "In Progress"}}}
    imported = history_events(issue, [], "sp", "sprint", BASE + timedelta(hours=2))
    live = normalize_event(
        {
            "webhookEvent": "jira:issue_created",
            "issue": issue,
            "timestamp": int((BASE + timedelta(seconds=2)).timestamp() * 1000),
        },
        "sp",
        "sprint",
        BASE + timedelta(hours=2),
    )
    assert live["event_key"] == imported[0]["event_key"]
    assert live["occurred_at"] == imported[0]["occurred_at"]


def test_snapshot_uses_source_update_time_without_rewriting_older_intervals():
    from services.team_analytics import normalize_event
    from services.team_analytics_history import history_events

    issue = {
        "id": "1",
        "key": "DEV-1",
        "fields": {
            "created": BASE.isoformat(),
            "updated": (BASE + timedelta(hours=2)).isoformat(),
            "status": {"name": "Done"},
        },
    }
    change = {
        "id": "15",
        "created": issue["fields"]["updated"],
        "items": [
            {"field": "status", "fromString": "In Progress", "toString": "Done"},
        ],
    }
    # The issue changed after a long-running sync began; observation time may lag.
    imported = history_events(issue, [change], "sp", "sprint", BASE + timedelta(hours=1))
    assert imported[-1]["occurred_at"] == BASE + timedelta(hours=2)
    later = normalize_event(
        {
            "issue": {"id": "1", "key": "DEV-1", "fields": {"status": {"name": "In Progress"}}},
            "timestamp": int((BASE + timedelta(hours=3)).timestamp() * 1000),
            "changelog": {"id": "16"},
        },
        "sp",
        "sprint",
        BASE,
    )
    result = replay_task([*imported, later], [], BASE + timedelta(hours=4))
    assert result["total_seconds"] == 10800
