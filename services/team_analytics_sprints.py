"""Sprint calendar boundaries shared by analytics reads (no I/O)."""

from datetime import datetime

from services.team_analytics import as_time


def sprint_window(sprint: dict, now: datetime) -> tuple[datetime, datetime]:
    """Active sprints run to now; closed sprints end at actual completion."""
    if sprint.get("state") in {"future", "deleted"}:
        raise ValueError("Bu sprint hali boshlanmagan yoki o'chirilgan")
    end = (sprint.get("completed_at") or sprint.get("ends_at")) if sprint.get("state") == "closed" else None
    try:
        start = as_time(sprint["started_at"])
        finish = min(as_time(end), now) if end else now
    except (KeyError, TypeError, ValueError, OverflowError):
        raise ValueError("Sprintning boshlanish yoki tugash sanasi Jira'dan olinmagan") from None
    if sprint.get("state") == "closed" and not end:
        raise ValueError("Sprintning tugash sanasi Jira'dan olinmagan")
    if finish <= start:
        raise ValueError("Sprintning hisoblanadigan vaqt oralig'i mavjud emas")
    return start, finish


def clip_interval(start: datetime, end: datetime, window: tuple[datetime, datetime] | None):
    if window:
        start, end = max(start, window[0]), min(end, window[1])
    return (start, end) if end > start else None
