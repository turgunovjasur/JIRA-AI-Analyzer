"""Pure Jira event normalization and calendar-time replay (no DB side effects)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone


def as_time(value) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, (int, float)):
        result = datetime.fromtimestamp(value / 1000, timezone.utc)
    else:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Analytics timestamps must include a timezone")
    return result.astimezone(timezone.utc)


def normalize_event(body: dict, points_field: str, sprint_field: str, received_at: datetime) -> dict:
    issue = body.get("issue") or {}
    fields = issue.get("fields") or {}
    issue_id = str(issue.get("id") or "")
    if not issue_id or not issue.get("key"):
        raise ValueError("Jira issue ID/key missing")
    occurred_at = received_at
    time_source = "received_at"
    for name, value in (("webhook_timestamp", body.get("timestamp")), ("issue_updated", fields.get("updated"))):
        if value is None:
            continue
        try:
            occurred_at, time_source = as_time(value), name
            break
        except (ValueError, TypeError, OverflowError):
            continue
    snapshot = {}
    for field, prefix in (
        ("status", "status"),
        ("assignee", "assignee"),
        ("project", "project"),
        ("issuetype", "issue_type"),
    ):
        if field in fields:
            entity = fields[field] or {}
            snapshot[f"{prefix}_id"] = str(entity.get("accountId") or entity.get("key") or entity.get("id") or "")
            snapshot[f"{prefix}_name"] = entity.get("displayName") or entity.get("name") or ""
    if "summary" in fields:
        snapshot["summary"] = fields["summary"]
    for field, key in (
        ("created", "created_at"),
        ("updated", "jira_updated_at"),
        ("resolutiondate", "resolved_at"),
        ("duedate", "due_date"),
        ("labels", "labels"),
        ("components", "components"),
        ("fixVersions", "fix_versions"),
    ):
        if field in fields:
            value = fields[field]
            snapshot[key] = (
                [{k: item.get(k) for k in ("id", "name")} for item in value]
                if field in {"components", "fixVersions"} and isinstance(value, list)
                else value
            )
    if "project" in fields:
        snapshot["project_id"] = str((fields["project"] or {}).get("id") or "")
        snapshot["project_key"] = (fields["project"] or {}).get("key") or ""
    for field in ("parent", "priority", "resolution", "reporter"):
        if field in fields:
            entity = fields[field] or {}
            snapshot[field + "_id"] = str(entity.get("accountId") or entity.get("id") or "")
            snapshot[field + "_name"] = entity.get("displayName") or entity.get("name") or entity.get("key") or ""
    if "status" in fields:
        snapshot["status_category"] = ((fields["status"] or {}).get("statusCategory") or {}).get("key")
    if points_field in fields:
        snapshot["story_points"] = fields[points_field]
        snapshot["points_field"] = points_field
    if sprint_field in fields:
        snapshot["sprints"] = normalize_sprints(fields[sprint_field])
        snapshot["sprint_ids"] = [s["id"] for s in snapshot["sprints"]]
        snapshot["sprint_field"] = sprint_field
    changelog = body.get("changelog") or {}
    changes = []
    for item in changelog.get("items") or []:
        if item.get("fieldId") in {
            points_field,
            sprint_field,
            "status",
            "assignee",
            "priority",
            "resolution",
            "parent",
            "project",
        } or str(item.get("field", "")).casefold() in {
            "status",
            "assignee",
            "story points",
            "story point estimate",
            "sprint",
            "summary",
            "priority",
            "resolution",
            "parent",
            "project",
        }:
            changes.append({key: item.get(key) for key in ("field", "fieldId", "from", "fromString", "to", "toString")})
    event_type = body.get("webhookEvent", "jira:issue_updated")
    if event_type == "jira:issue_created" and fields.get("created"):
        occurred_at, time_source = as_time(fields["created"]), "jira_created"
    identity = {
        "event_type": event_type,
        "timestamp": body.get("timestamp") or fields.get("updated"),
        "snapshot": snapshot,
        "changes": changes,
    }
    event_key = (
        "created:" + issue_id
        if event_type == "jira:issue_created"
        else f"{event_type}:{changelog['id']}"
        if changelog.get("id")
        else hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    )
    return {
        "issue_id": issue_id,
        "issue_key": issue["key"],
        "event_key": event_key,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "time_source": time_source,
        "actor_id": str((body.get("user") or {}).get("accountId") or (body.get("user") or {}).get("key") or ""),
        "actor_name": (body.get("user") or {}).get("displayName") or "",
        "origin": body.get("analytics_origin", "webhook"),
        "snapshot": snapshot,
        "changes": changes,
    }


def normalize_sprints(value) -> list[dict]:
    """Cloud objects and legacy Data Center sprint strings, with stable numeric IDs."""
    result = []
    for item in value if isinstance(value, list) else [value] if value else []:
        if isinstance(item, str):
            item = dict(re.findall(r"(?:\[|,)(\w+)=([^,\]]*)", item))
        if not isinstance(item, dict):
            continue
        try:
            sprint_id = int(item["id"])
        except (KeyError, ValueError, TypeError):
            continue
        sprint = {"id": sprint_id}
        for source, target in (
            ("name", "name"),
            ("state", "state"),
            ("goal", "goal"),
            ("boardId", "board_id"),
            ("rapidViewId", "board_id"),
            ("originBoardId", "board_id"),
            ("startDate", "started_at"),
            ("endDate", "ends_at"),
            ("completeDate", "completed_at"),
        ):
            if item.get(source) not in (None, "", "<null>"):
                sprint[target] = item[source]
        result.append(sprint)
    return list({s["id"]: s for s in result}.values())


def change_snapshot(items: list[dict], points_field: str = "", sprint_field: str = "", *, reverse=False) -> dict:
    """Translate changelog deltas; missing fields and explicit clears are distinct."""
    result = {}
    value_key, name_key = ("from", "fromString") if reverse else ("to", "toString")
    for item in reversed(items) if reverse else items:
        field = str(item.get("fieldId") or item.get("field") or "").casefold()
        name = str(item.get("field") or "").casefold()
        value, label = item.get(value_key), item.get(name_key)
        if field in {"status", "assignee", "priority", "resolution", "parent", "project"}:
            result[field + "_id"] = str(value or "")
            result[field + "_name"] = label or ""
        elif field == "summary":
            result["summary"] = label if label is not None else value
        elif (points_field and field == points_field.casefold()) or name in {"story points", "story point estimate"}:
            result["story_points"] = value if value not in (None, "") else None
        elif (sprint_field and field == sprint_field.casefold()) or name == "sprint":
            ids = [int(n) for n in re.findall(r"\d+", str(value or ""))]
            result["sprint_ids"] = ids
            result["sprints"] = [{"id": n} for n in ids]
    return result


def event_order(event: dict) -> tuple:
    kind = event["event_type"]
    phase = (
        0
        if kind == "jira:issue_created"
        else 2
        if kind == "jira:issue_snapshot"
        else 3
        if kind in {"jira:issue_deleted", "jira:issue_unavailable"}
        else 1
    )
    key = str(event.get("event_key", ""))
    suffix = key.rsplit(":", 1)[-1]
    return phase, int(suffix) if suffix.isdecimal() else 0, key


def replay_task(events: list[dict], settings: list[dict], now: datetime) -> dict:
    """Derive intervals from immutable events; config changes never rewrite history."""
    now = as_time(now)
    timeline = [(as_time(e["occurred_at"]), 1, event_order(e), "event", e) for e in events]
    timeline += [(as_time(s["effective_at"]), 0, (0, int(s.get("id", 0)), ""), "setting", s) for s in settings]
    timeline.sort(key=lambda entry: entry[:3])
    state, intervals = {}, []
    working_status, cursor, observed, deleted, unavailable = "In Progress", None, False, False, False
    issue_key = events[0]["issue_key"] if events else ""

    def active():
        return (
            observed
            and not deleted
            and not unavailable
            and bool(working_status)
            and str(state.get("status_name", "")).strip().casefold() == working_status.casefold()
        )

    def append_interval(end):
        if cursor is not None and end > cursor and active():
            interval = {
                "started_at": cursor.isoformat(),
                "ended_at": end.isoformat(),
                "seconds": (end - cursor).total_seconds(),
                "assignee_id": state.get("assignee_id", ""),
                "assignee_name": state.get("assignee_name", ""),
                "working_status": working_status,
                "is_open": False,
            }
            # Unrelated Jira updates must not split a continuous working interval.
            previous = intervals[-1] if intervals else None
            if (
                previous
                and previous["ended_at"] == interval["started_at"]
                and previous["assignee_id"] == interval["assignee_id"]
                and previous["working_status"] == interval["working_status"]
            ):
                previous["ended_at"] = interval["ended_at"]
                previous["seconds"] += interval["seconds"]
                previous["assignee_name"] = interval["assignee_name"]
            else:
                intervals.append(interval)

    for at, _, _, kind, entry in timeline:
        if at > now:
            break
        append_interval(at)
        if kind == "setting":
            working_status = entry["working_status"].strip()
        else:
            state.update(
                change_snapshot(entry.get("changes", []), state.get("points_field", ""), state.get("sprint_field", ""))
            )
            state.update(entry["snapshot"])
            issue_key = entry["issue_key"]
            observed = True
            deleted = deleted or entry["event_type"] == "jira:issue_deleted"
            unavailable = entry["event_type"] == "jira:issue_unavailable"
        cursor = at
    append_interval(now)
    if (
        intervals
        and active()
        and intervals[-1]["ended_at"] == now.isoformat()
        and intervals[-1]["assignee_id"] == state.get("assignee_id", "")
        and intervals[-1]["working_status"] == working_status
    ):
        intervals[-1]["is_open"] = True
    return {
        **state,
        "issue_key": issue_key,
        "is_working": active(),
        "deleted": deleted,
        "unavailable": unavailable,
        "total_seconds": sum(i["seconds"] for i in intervals),
        "intervals": intervals,
    }
