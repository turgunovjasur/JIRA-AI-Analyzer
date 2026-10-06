"""Behavior regressions; not executed without the user's explicit request."""

from datetime import datetime, timedelta, timezone

import pytest

from services.team_analytics import normalize_event, replay_task

BASE = datetime(2026, 10, 5, 8, tzinfo=timezone.utc)
pytestmark = pytest.mark.no_db


def event(hour, status="In Progress", person="ali", kind="jira:issue_updated"):
    return {
        "occurred_at": BASE + timedelta(hours=hour),
        "event_key": str(hour),
        "event_type": kind,
        "issue_key": "DEV-1",
        "snapshot": {"status_name": status, "assignee_id": person, "assignee_name": person},
    }


def config(hour=0, status="In Progress"):
    return {"effective_at": BASE + timedelta(hours=hour), "working_status": status}


def test_pause_resume_preserves_accumulated_time():
    result = replay_task(
        [event(0), event(3, "Timeout"), event(7), event(9, "Done")], [config()], BASE + timedelta(hours=12)
    )
    assert result["total_seconds"] == 5 * 3600
    assert not result["is_working"]


def test_every_nonworking_status_stops_time():
    for status in ("To Do", "Review", "Testing", "Rejected", "Done", "Timeout"):
        result = replay_task([event(0), event(2, status)], [config()], BASE + timedelta(hours=8))
        assert result["total_seconds"] == 7200
        assert not result["is_working"]


def test_late_delivery_replays_in_event_order():
    result = replay_task(
        [event(5, "Done"), event(0), event(3, "Timeout"), event(4)], [config()], BASE + timedelta(hours=6)
    )
    assert result["total_seconds"] == 4 * 3600


def test_assignee_change_splits_time_between_people():
    result = replay_task(
        [event(0), event(2, person="vali"), event(5, "Done", "vali")], [config()], BASE + timedelta(hours=6)
    )
    assert [(i["assignee_id"], i["seconds"]) for i in result["intervals"]] == [("ali", 7200), ("vali", 10800)]


def test_settings_change_does_not_reinterpret_prior_time():
    result = replay_task(
        [event(0), event(4, "Coding"), event(7, "Done")], [config(), config(3, "Coding")], BASE + timedelta(hours=8)
    )
    assert result["total_seconds"] == 6 * 3600
    assert {i["working_status"] for i in result["intervals"]} == {"In Progress", "Coding"}


def test_first_observation_does_not_invent_earlier_work():
    result = replay_task([event(5)], [config()], BASE + timedelta(hours=6))
    assert result["total_seconds"] == 3600


def test_delete_stops_active_task():
    result = replay_task([event(0), event(2, kind="jira:issue_deleted")], [config()], BASE + timedelta(hours=9))
    assert result["total_seconds"] == 7200
    assert result["deleted"] and not result["is_working"]


def test_normalization_uses_jira_time_and_stable_retry_identity():
    body = {
        "webhookEvent": "jira:issue_updated",
        "timestamp": int(BASE.timestamp() * 1000),
        "issue": {
            "id": "100",
            "key": "DEV-1",
            "fields": {
                "assignee": {"accountId": "ali", "displayName": "Ali"},
                "customfield_points": 4,
                "customfield_sprint": [{"id": 3}],
            },
        },
        "changelog": {"id": "20", "items": [{"field": "assignee", "from": "vali", "to": "ali"}]},
    }
    first = normalize_event(body, "customfield_points", "customfield_sprint", BASE)
    retry = normalize_event(body, "customfield_points", "customfield_sprint", BASE + timedelta(hours=3))
    assert first["occurred_at"] == BASE
    assert first["event_key"] == retry["event_key"]
    assert first["snapshot"]["assignee_id"] == "ali"
    assert first["snapshot"]["story_points"] == 4
    assert first["changes"][0]["from"] == "vali"


def test_retry_without_changelog_id_has_same_content_identity():
    body = {"issue": {"id": "1", "key": "DEV-1", "fields": {"status": {"id": "3", "name": "Done"}}}}
    assert (
        normalize_event(body, "sp", "sprint", BASE)["event_key"]
        == normalize_event(body, "sp", "sprint", BASE + timedelta(hours=1))["event_key"]
    )


def test_default_status_before_first_delivered_setting_keeps_late_work():
    result = replay_task([event(1, "Done"), event(0)], [config(1)], BASE + timedelta(hours=2))
    assert result["total_seconds"] == 3600


def test_same_time_changelog_ids_use_numeric_order():
    start = event(0)
    start["event_key"] = "jira:issue_updated:2"
    stop = event(0, "Done")
    stop["event_key"] = "jira:issue_updated:10"
    result = replay_task([stop, start], [config()], BASE + timedelta(hours=1))
    assert not result["is_working"]
    assert result["total_seconds"] == 0


def test_changelog_can_stop_timer_when_snapshot_is_sparse():
    stop = event(2, "Done")
    stop["snapshot"] = {}
    stop["changes"] = [{"fieldId": "status", "field": "status", "to": "9", "toString": "Done"}]
    result = replay_task([event(0), stop], [config()], BASE + timedelta(hours=5))
    assert result["total_seconds"] == 7200


def test_normalization_preserves_future_analytics_metadata_and_sprint_ids():
    body = {
        "timestamp": int(BASE.timestamp() * 1000),
        "user": {"accountId": "actor", "displayName": "Actor"},
        "issue": {
            "id": "1",
            "key": "DEV-1",
            "fields": {
                "created": BASE.isoformat(),
                "updated": BASE.isoformat(),
                "resolutiondate": None,
                "project": {"id": "12", "key": "DEV", "name": "Dev"},
                "status": {"id": "3", "name": "IN PROGRESS", "statusCategory": {"id": 4, "key": "indeterminate"}},
                "parent": {"id": "2", "key": "DEV-2"},
                "labels": ["release"],
                "customfield_sprint": [
                    {"id": 17, "name": "Sprint 17", "state": "active", "boardId": 5, "startDate": BASE.isoformat()}
                ],
                "customfield_points": 4,
            },
        },
    }
    normalized = normalize_event(body, "customfield_points", "customfield_sprint", BASE)
    snapshot = normalized["snapshot"]
    assert snapshot["sprint_ids"] == [17]
    assert snapshot["sprints"][0]["board_id"] == 5
    assert snapshot["project_id"] == "12"
    assert snapshot["project_key"] == "DEV"
    assert snapshot["status_category"] == "indeterminate"
    assert snapshot["created_at"] == BASE.isoformat()
    assert snapshot["parent_id"] == "2"
    assert normalized["actor_id"] == "actor"
    assert snapshot["points_field"] == "customfield_points"
