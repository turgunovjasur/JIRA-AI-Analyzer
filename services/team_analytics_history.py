"""Reconstruct historical states from complete Jira changelog pages, without I/O."""

from copy import deepcopy
from datetime import datetime

from services.team_analytics import as_time, change_snapshot, normalize_event


def history_events(
    issue: dict, histories: list[dict], points_field: str, sprint_field: str, observed_at: datetime
) -> list[dict]:
    current = normalize_event(
        {"issue": issue, "timestamp": int(observed_at.timestamp() * 1000), "analytics_origin": "jira_rest"},
        points_field,
        sprint_field,
        observed_at,
    )
    ordered = sorted(histories, key=lambda h: (as_time(h["created"]), int(h.get("id", 0))))
    initial = deepcopy(current["snapshot"])
    for history in reversed(ordered):
        initial.update(change_snapshot(history.get("items", []), points_field, sprint_field, reverse=True))
    created = as_time((issue.get("fields") or {}).get("created") or observed_at)
    initial["jira_updated_at"] = created.isoformat()
    initial["resolved_at"] = None
    result = [
        {
            **current,
            "event_type": "jira:issue_created",
            "event_key": "created:" + current["issue_id"],
            "occurred_at": created,
            "time_source": "jira_created",
            "snapshot": initial,
            "changes": [],
        }
    ]
    for history in ordered:
        changes = normalize_event(
            {
                "issue": {"id": issue["id"], "key": issue["key"]},
                "webhookEvent": "jira:issue_updated",
                "changelog": history,
                "user": history.get("author", {}),
                "analytics_origin": "jira_changelog",
                "timestamp": int(as_time(history["created"]).timestamp() * 1000),
            },
            points_field,
            sprint_field,
            observed_at,
        )
        changes["snapshot"] = change_snapshot(history.get("items", []), points_field, sprint_field)
        # Retain exact Jira changelog time rather than rounding it through milliseconds.
        changes["occurred_at"] = as_time(history["created"])
        changes["time_source"] = "jira_changelog"
        result.append(changes)
    result.append(
        {
            **current,
            "event_type": "jira:issue_snapshot",
            "event_key": "snapshot:" + str((issue.get("fields") or {}).get("updated") or observed_at.isoformat()),
            "occurred_at": as_time((issue.get("fields") or {}).get("updated") or observed_at),
            "time_source": "issue_updated" if (issue.get("fields") or {}).get("updated") else "jira_observed",
            "changes": [],
        }
    )
    return result
