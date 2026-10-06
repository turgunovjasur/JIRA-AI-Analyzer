"""Tenant-scoped source events, per-task projections and paginated analytics reads."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone

from services.team_analytics import as_time, normalize_event, replay_task
from services.team_analytics_sprints import clip_interval, sprint_window
from utils.database.runtime import connect_processing_db


def _number(value):
    try:
        result = float(value) if value is not None else None
        return result if result is None or math.isfinite(result) and result >= 0 else None
    except (TypeError, ValueError):
        return None


def _settings(conn, company_id):
    return list(
        conn.execute(
            "SELECT id,working_status,effective_at FROM team_analytics_settings WHERE company_id=%s ORDER BY effective_at,id",
            [company_id],
        ).fetchall()
    )


def _person(conn, company_id, source, person_id, name, at):
    if person_id:
        conn.execute(
            """INSERT INTO team_analytics_people(company_id,jira_source,assignee_id,assignee_name,observed_at)
            VALUES(%s,%s,%s,%s,%s) ON CONFLICT(company_id,jira_source,assignee_id) DO UPDATE
            SET assignee_name=excluded.assignee_name,observed_at=excluded.observed_at
            WHERE excluded.observed_at>=team_analytics_people.observed_at""",
            [company_id, source, person_id, name or person_id, at],
        )


def store_sprint(conn, company_id, source, sprint, at):
    conn.execute(
        """INSERT INTO team_analytics_sprints(company_id,jira_source,sprint_id,metadata,observed_at)
        VALUES(%s,%s,%s,%s::jsonb,%s) ON CONFLICT(company_id,jira_source,sprint_id) DO UPDATE
        SET metadata=team_analytics_sprints.metadata || excluded.metadata,observed_at=excluded.observed_at
        WHERE excluded.observed_at>=team_analytics_sprints.observed_at""",
        [company_id, source, sprint["id"], json.dumps(sprint), at],
    )


def _project(conn, company_id, source, issue_id, settings, now):
    history = list(
        conn.execute(
            """SELECT * FROM team_analytics_events WHERE company_id=%s AND jira_source=%s
        AND issue_id=%s ORDER BY occurred_at,event_key""",
            [company_id, source, issue_id],
        ).fetchall()
    )
    if not history:
        return
    task = replay_task(history, settings, now)
    intervals = task.pop("intervals")
    task["story_points"] = _number(task.get("story_points"))
    latest = as_time(task["jira_updated_at"]) if task.get("jira_updated_at") else max(e["occurred_at"] for e in history)
    conn.execute(
        """INSERT INTO team_analytics_tasks(company_id,jira_source,issue_id,issue_key,assignee_id,story_points,snapshot,last_event_at)
        VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb,%s) ON CONFLICT(company_id,jira_source,issue_id) DO UPDATE
        SET issue_key=excluded.issue_key,assignee_id=excluded.assignee_id,story_points=excluded.story_points,
            snapshot=excluded.snapshot,last_event_at=excluded.last_event_at,projected_at=clock_timestamp()""",
        [
            company_id,
            source,
            issue_id,
            task["issue_key"],
            task.get("assignee_id", ""),
            task["story_points"],
            json.dumps(task),
            latest,
        ],
    )
    conn.execute(
        "DELETE FROM team_analytics_intervals WHERE company_id=%s AND jira_source=%s AND issue_id=%s",
        [company_id, source, issue_id],
    )
    for index, interval in enumerate(intervals):
        conn.execute(
            """INSERT INTO team_analytics_intervals(company_id,jira_source,issue_id,ordinal,started_at,ended_at,assignee_id,assignee_name,working_status)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            [
                company_id,
                source,
                issue_id,
                index,
                interval["started_at"],
                None if interval["is_open"] else interval["ended_at"],
                interval["assignee_id"],
                interval["assignee_name"],
                interval["working_status"],
            ],
        )
        _person(
            conn,
            company_id,
            source,
            interval["assignee_id"],
            interval["assignee_name"],
            as_time(interval["started_at"]),
        )
    _person(conn, company_id, source, task.get("assignee_id", ""), task.get("assignee_name", ""), latest)
    conn.execute(
        "DELETE FROM team_analytics_task_sprints WHERE company_id=%s AND jira_source=%s AND issue_id=%s",
        [company_id, source, issue_id],
    )
    for sprint in task.get("sprints", []):
        store_sprint(conn, company_id, source, sprint, now)
        conn.execute(
            "INSERT INTO team_analytics_task_sprints VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            [company_id, source, issue_id, sprint["id"]],
        )


def persist_events(company_id: int, jira_source: str, events: list[dict]) -> int:
    conn = connect_processing_db(row_factory=True)
    try:
        conn.execute("SELECT pg_advisory_xact_lock(%s,%s)", [51005, company_id])
        settings = _settings(conn, company_id)
        affected, count = set(), 0
        for event in events:
            inserted = conn.execute(
                """INSERT INTO team_analytics_events
                (company_id,jira_source,issue_id,issue_key,event_key,event_type,occurred_at,time_source,snapshot,changes,actor_id,actor_name,origin)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s)
                ON CONFLICT(company_id,jira_source,issue_id,event_key) DO NOTHING RETURNING id""",
                [
                    company_id,
                    jira_source,
                    event["issue_id"],
                    event["issue_key"],
                    event["event_key"],
                    event["event_type"],
                    event["occurred_at"],
                    event["time_source"],
                    json.dumps(event["snapshot"]),
                    json.dumps(event.get("changes", [])),
                    event.get("actor_id", ""),
                    event.get("actor_name", ""),
                    event.get("origin", "webhook"),
                ],
            ).fetchone()
            if inserted:
                affected.add(event["issue_id"])
                count += 1
                for sprint in event["snapshot"].get("sprints", []):
                    store_sprint(conn, company_id, jira_source, sprint, event["occurred_at"])
        now = datetime.now(timezone.utc)
        for issue_id in affected:
            _project(conn, company_id, jira_source, issue_id, settings, now)
        conn.commit()
        return count
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def record_event(company_id, jira_source, body, points_field, sprint_field):
    return persist_events(
        company_id, jira_source, [normalize_event(body, points_field, sprint_field, datetime.now(timezone.utc))]
    )


def field_mapping(company_id, source, project):
    conn = connect_processing_db(row_factory=True)
    try:
        return conn.execute(
            "SELECT points_field,sprint_field,discovered_at FROM team_analytics_jira_fields WHERE company_id=%s AND jira_source=%s AND project_key=%s",
            [company_id, source, project],
        ).fetchone()
    finally:
        conn.close()


def save_field_mapping(company_id, source, project, points_field, sprint_field):
    conn = connect_processing_db()
    try:
        conn.execute(
            """INSERT INTO team_analytics_jira_fields(company_id,jira_source,project_key,points_field,sprint_field)
            VALUES(%s,%s,%s,%s,%s) ON CONFLICT(company_id,jira_source,project_key) DO UPDATE
            SET points_field=excluded.points_field,sprint_field=excluded.sprint_field,discovered_at=clock_timestamp()""",
            [company_id, source, project, points_field, sprint_field],
        )
        conn.commit()
    finally:
        conn.close()


def save_sprints(company_id, source, sprints):
    conn = connect_processing_db()
    try:
        for sprint in sprints:
            store_sprint(conn, company_id, source, sprint, datetime.now(timezone.utc))
        conn.commit()
    finally:
        conn.close()


def save_settings(company_id, working_status, user_id, daily_hours=8):
    conn = connect_processing_db(row_factory=True)
    try:
        conn.execute("SELECT pg_advisory_xact_lock(%s,%s)", [51005, company_id])
        settings = _settings(conn, company_id)
        previous = settings[-1]["working_status"] if settings else "In Progress"
        if previous != working_status:
            conn.execute(
                "INSERT INTO team_analytics_settings(company_id,working_status,updated_by) VALUES(%s,%s,%s)",
                [company_id, working_status, user_id],
            )
            settings = _settings(conn, company_id)
            now = datetime.now(timezone.utc)
            for row in conn.execute(
                "SELECT jira_source,issue_id FROM team_analytics_tasks WHERE company_id=%s", [company_id]
            ).fetchall():
                _project(conn, company_id, row["jira_source"], row["issue_id"], settings, now)
        conn.execute(
            """INSERT INTO team_analytics_productivity_settings(company_id,daily_hours,updated_by) VALUES(%s,%s,%s)
            ON CONFLICT(company_id) DO UPDATE SET daily_hours=excluded.daily_hours,updated_by=excluded.updated_by""",
            [company_id, daily_hours, user_id],
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


_SPRINT_MEMBERSHIP = """(EXISTS (
    SELECT 1 FROM team_analytics_task_sprints m WHERE m.company_id=t.company_id
      AND m.jira_source=t.jira_source AND m.issue_id=t.issue_id AND m.sprint_id=%(sprint)s)
    OR EXISTS (SELECT 1 FROM team_analytics_events e WHERE e.company_id=t.company_id
      AND e.jira_source=t.jira_source AND e.issue_id=t.issue_id
      AND e.snapshot @> %(sprint_snapshot)s::jsonb))"""

_SELECTED = """WITH scoped_intervals AS (
    SELECT jira_source,issue_id,
      greatest(started_at,coalesce(%(window_start)s::timestamptz,started_at)) AS starts,
      least(coalesce(ended_at,%(now)s),%(now)s,coalesce(%(window_end)s::timestamptz,%(now)s)) AS ends
    FROM team_analytics_intervals WHERE company_id=%(company)s AND started_at<=%(now)s
      AND (%(person)s::text IS NULL OR (assignee_id=%(person)s AND (%(person)s='' OR jira_source=%(source)s)))
      AND (%(sprint)s::bigint IS NULL OR jira_source=%(sprint_source)s)), durations AS (
    SELECT jira_source,issue_id,sum(extract(epoch FROM (ends-starts)))::double precision AS seconds
    FROM scoped_intervals WHERE ends>starts GROUP BY jira_source,issue_id), selected AS (
    SELECT t.*,coalesce(d.seconds,0) AS seconds FROM team_analytics_tasks t LEFT JOIN durations d USING(jira_source,issue_id)
    WHERE t.company_id=%(company)s AND (%(sprint)s::bigint IS NULL OR
      (t.jira_source=%(sprint_source)s AND """ + _SPRINT_MEMBERSHIP + """))
      AND (%(person)s::text IS NULL OR
      (t.assignee_id=%(person)s AND (%(person)s='' OR t.jira_source=%(source)s)) OR coalesce(d.seconds,0)>0)) """


def get_snapshot(company_id, limit=100, offset=0, assignee_id=None, jira_source=None, sprint_id=None, sprint_source=None):
    conn = connect_processing_db(row_factory=True)
    try:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        now = datetime.now(timezone.utc)
        sprints = [
            {"jira_source": r["jira_source"], **r["metadata"], "id": r["sprint_id"]}
            for r in conn.execute(
                """WITH known_sprints AS (
                  SELECT jira_source,sprint_id FROM team_analytics_task_sprints WHERE company_id=%s
                  UNION SELECT e.jira_source,ids.value::bigint FROM team_analytics_events e
                    CROSS JOIN LATERAL jsonb_array_elements_text(e.snapshot->'sprint_ids') ids(value)
                    WHERE e.company_id=%s)
                SELECT s.jira_source,s.sprint_id,s.metadata FROM team_analytics_sprints s
                JOIN known_sprints k USING(jira_source,sprint_id)
                WHERE s.company_id=%s AND coalesce(s.metadata->>'state','')!='deleted'
                ORDER BY CASE s.metadata->>'state' WHEN 'active' THEN 0 WHEN 'future' THEN 1 ELSE 2 END,
                  s.metadata->>'started_at' DESC NULLS LAST,s.sprint_id DESC,s.jira_source""",
                [company_id, company_id, company_id],
            ).fetchall()
        ]
        selected_sprint, window = None, None
        if sprint_id is not None:
            selected_sprint = next((s for s in sprints if s["id"] == sprint_id and s["jira_source"] == sprint_source), None)
            if selected_sprint is None:
                raise ValueError("Sprint topilmadi yoki kompaniyaga tegishli emas")
            window = sprint_window(selected_sprint, now)
        params = {
            "company": company_id,
            "now": now,
            "person": assignee_id,
            "source": jira_source,
            "limit": limit,
            "offset": offset,
            "sprint": sprint_id,
            "sprint_source": sprint_source,
            "sprint_snapshot": json.dumps({"sprint_ids": [sprint_id]}),
            "window_start": window[0] if window else None,
            "window_end": window[1] if window else None,
        }
        settings = _settings(conn, company_id)
        productivity = conn.execute(
            "SELECT daily_hours FROM team_analytics_productivity_settings WHERE company_id=%s", [company_id]
        ).fetchone()
        hours = float(productivity["daily_hours"]) if productivity else 8
        summary = dict(
            conn.execute(
                _SELECTED
                + """SELECT count(*) AS total,coalesce(sum(seconds),0) AS worked_seconds,
            coalesce(sum(story_points),0) AS task_points,count(*) FILTER(WHERE story_points IS NULL) AS missing_points,
            count(DISTINCT (jira_source,assignee_id)) AS assignee_count,
            coalesce(jsonb_agg(jsonb_build_object('worked_seconds',seconds,'story_points',story_points)),'[]'::jsonb) AS task_estimates FROM selected""",
                params,
            ).fetchone()
        )
        tasks = []
        page = conn.execute(
            _SELECTED
            + "SELECT * FROM selected ORDER BY last_event_at DESC,jira_source,issue_id LIMIT %(limit)s OFFSET %(offset)s",
            params,
        ).fetchall()
        by_issue = {}
        if page:
            identities = [value for row in page for value in (row["jira_source"], row["issue_id"])]
            placeholders = ",".join(["(%s,%s)"] * len(page))
            for interval in conn.execute(
                "SELECT * FROM team_analytics_intervals WHERE company_id=%s AND (jira_source,issue_id) IN ("
                + placeholders
                + ") ORDER BY jira_source,issue_id,ordinal",
                [company_id, *identities],
            ).fetchall():
                by_issue.setdefault((interval["jira_source"], interval["issue_id"]), []).append(interval)
        for row in page:
            task = {
                **row["snapshot"],
                "jira_source": row["jira_source"],
                "issue_id": row["issue_id"],
                "assignee_seconds": float(row["seconds"]),
                "work_days": float(row["seconds"]) / (hours * 3600),
                "intervals": [],
            }
            intervals = by_issue.get((row["jira_source"], row["issue_id"]), [])
            for i in intervals:
                bounds = clip_interval(i["started_at"], min(i["ended_at"] or now, now), window)
                if bounds is None:
                    continue
                start, end = bounds
                task["intervals"].append(
                    {
                        "started_at": start.isoformat(),
                        "ended_at": end.isoformat(),
                        "seconds": (end - start).total_seconds(),
                        "assignee_id": i["assignee_id"],
                        "assignee_name": i["assignee_name"],
                        "working_status": i["working_status"],
                        "is_open": i["ended_at"] is None and end == now,
                    }
                )
            task["total_seconds"] = sum(i["seconds"] for i in task["intervals"])
            if window:
                task["is_working"] = any(i["is_open"] for i in task["intervals"])
            tasks.append(task)
        total = summary.pop("total")
        summary["work_days"] = summary["worked_seconds"] / (hours * 3600)
        people = [
            dict(r)
            for r in conn.execute(
                "SELECT jira_source,assignee_id,assignee_name FROM team_analytics_people WHERE company_id=%s ORDER BY assignee_name,jira_source,assignee_id",
                [company_id],
            ).fetchall()
        ]
        sync = [
            dict(r)
            for r in conn.execute(
                "SELECT jira_source,last_success_at,last_error FROM team_analytics_sync_state WHERE company_id=%s",
                [company_id],
            ).fetchall()
        ]
        return {
            "working_status": settings[-1]["working_status"] if settings else "In Progress",
            "daily_hours": hours,
            "timezone": "Asia/Tashkent",
            "tasks": tasks,
            "assignees": people,
            "sprints": sprints,
            "selected_sprint": selected_sprint,
            "sprint_window": {"started_at": window[0].isoformat(), "ended_at": window[1].isoformat()} if window else None,
            "summary": summary,
            "total": total,
            "limit": limit,
            "offset": offset,
            "generated_at": now.isoformat(),
            "sync": sync,
        }
    finally:
        conn.close()
