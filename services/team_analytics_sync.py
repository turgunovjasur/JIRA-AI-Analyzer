"""Idempotent Jira history import and queued reconciliation of missed webhooks."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from services.team_analytics import normalize_sprints
from services.team_analytics_history import history_events
from services.team_analytics_jira import JiraAnalyticsClient, JiraReadError, project_keys, read_issue_history
from utils.auth.auth_db import get_company_settings, get_effective_company_modules, is_company_subscription_active
from utils.database.runtime import connect_processing_db
from utils.database.team_analytics_repository import field_mapping, persist_events, save_field_mapping, save_sprints

JOB_TYPE = "team_analytics_sync"


def sync_company(company_id: int, *, initial=False) -> dict:
    if not initial and (
        not get_effective_company_modules(company_id).get("team_analytics")
        or not is_company_subscription_active(company_id)[0]
    ):
        return {"skipped": "module_disabled_or_subscription_inactive"}
    config = get_company_settings(company_id)
    client = JiraAnalyticsClient(config)
    projects = project_keys(config)
    started = datetime.now(timezone.utc)
    conn = connect_processing_db(row_factory=True)
    locked = False
    try:
        locked = conn.execute("SELECT pg_try_advisory_lock(%s,%s) AS locked", [51006, company_id]).fetchone()["locked"]
        conn.commit()
        if not locked:
            return {"skipped": "sync_already_running"}
        checkpoint = conn.execute(
            "SELECT last_success_at FROM team_analytics_sync_state WHERE company_id=%s AND jira_source=%s",
            [company_id, client.source],
        ).fetchone()
        selected_projects = ",".join('"' + p + '"' for p in projects)
        since = checkpoint["last_success_at"] if checkpoint else None
        if initial:
            jql = f"project in ({selected_projects}) AND statusCategory != Done"
        else:
            minutes = max(30, math.ceil((started - since).total_seconds() / 60) + 15) if since else 1440
            jql = f"project in ({selected_projects}) AND updated >= -{minutes}m"
        keys = {issue["key"] for issue in client.search(jql)}
        if initial:
            keys.update(
                row["task_id"]
                for row in conn.execute(
                    "SELECT DISTINCT task_id FROM task_status_history WHERE company_id=%s", [company_id]
                ).fetchall()
            )
        else:
            keys.update(
                row["issue_key"]
                for row in conn.execute(
                    "SELECT issue_key FROM team_analytics_tasks WHERE company_id=%s AND jira_source=%s AND (snapshot->>'is_working'='true' OR snapshot->>'unavailable'='true')",
                    [company_id, client.source],
                ).fetchall()
            )
        conn.commit()
        mappings, inserted, seen_sprints, unavailable = {}, 0, set(), 0

        def mapping_for(project):
            if project not in mappings:
                mapping = field_mapping(company_id, client.source, project)
                if initial or not mapping or (started - mapping["discovered_at"]).total_seconds() > 86400:
                    points, sprint = client.discover_fields(project)
                    save_field_mapping(company_id, client.source, project, points, sprint)
                    mapping = {"points_field": points, "sprint_field": sprint}
                mappings[project] = mapping
            return mappings[project]

        for key in sorted(keys):
            project = key.split("-")[0].upper()
            if initial and project not in projects:
                continue
            mapping = mapping_for(project)
            try:
                issue, histories = read_issue_history(client, key, mapping["points_field"], mapping["sprint_field"])
                actual_project = issue["key"].split("-")[0].upper()
                if actual_project != project:
                    mapping = mapping_for(actual_project)
                    issue, histories = read_issue_history(
                        client, issue["key"], mapping["points_field"], mapping["sprint_field"]
                    )
            except JiraReadError as exc:
                if exc.status not in {403, 404}:
                    raise
                row = conn.execute(
                    "SELECT issue_id,snapshot FROM team_analytics_tasks WHERE company_id=%s AND jira_source=%s AND issue_key=%s",
                    [company_id, client.source, key],
                ).fetchone()
                if row and not row["snapshot"].get("unavailable"):
                    inserted += persist_events(
                        company_id,
                        client.source,
                        [
                            {
                                "issue_id": row["issue_id"],
                                "issue_key": key,
                                "event_key": "unavailable:" + started.isoformat(),
                                "event_type": "jira:issue_unavailable",
                                "occurred_at": started,
                                "time_source": "jira_observed",
                                "origin": "jira_rest",
                                "snapshot": {},
                                "changes": [],
                            }
                        ],
                    )
                unavailable += 1
                conn.commit()
                continue
            events = history_events(issue, histories, mapping["points_field"], mapping["sprint_field"], started)
            row = conn.execute(
                "SELECT snapshot FROM team_analytics_tasks WHERE company_id=%s AND jira_source=%s AND issue_id=%s",
                [company_id, client.source, str(issue["id"])],
            ).fetchone()
            conn.commit()
            if row and row["snapshot"].get("unavailable"):
                events.append(
                    {
                        **events[-1],
                        "event_key": "available:" + started.isoformat(),
                        "event_type": "jira:issue_available",
                        "occurred_at": datetime.now(timezone.utc),
                        "time_source": "jira_observed",
                        "snapshot": {},
                        "changes": [],
                    }
                )
            inserted += persist_events(company_id, client.source, events)
            for event in events:
                seen_sprints.update(event["snapshot"].get("sprint_ids", []))
        seen_sprints.update(
            row["sprint_id"]
            for row in conn.execute(
                "SELECT sprint_id FROM team_analytics_sprints WHERE company_id=%s AND jira_source=%s AND coalesce(metadata->>'state','') NOT IN ('closed','deleted')",
                [company_id, client.source],
            ).fetchall()
        )
        conn.commit()
        sprint_count = 0
        for sprint_id in sorted(seen_sprints):
            try:
                sprint = client.get(f"/rest/agile/1.0/sprint/{sprint_id}")
                normalized = normalize_sprints([sprint])
                if normalized:
                    save_sprints(company_id, client.source, normalized)
                    sprint_count += 1
            except JiraReadError as exc:
                if exc.status not in {403, 404}:
                    raise
        conn.execute(
            """INSERT INTO team_analytics_sync_state(company_id,jira_source,last_success_at,last_attempt_at,last_error)
            VALUES(%s,%s,%s,%s,NULL) ON CONFLICT(company_id,jira_source) DO UPDATE
            SET last_success_at=excluded.last_success_at,last_attempt_at=excluded.last_attempt_at,last_error=NULL""",
            [company_id, client.source, started, started],
        )
        conn.commit()
        return {
            "tasks": len(keys),
            "inserted_events": inserted,
            "sprints": sprint_count,
            "unavailable_tasks": unavailable,
        }
    except Exception as exc:
        conn.rollback()
        conn.execute(
            """INSERT INTO team_analytics_sync_state(company_id,jira_source,last_attempt_at,last_error)
            VALUES(%s,%s,%s,%s) ON CONFLICT(company_id,jira_source) DO UPDATE
            SET last_attempt_at=excluded.last_attempt_at,last_error=excluded.last_error""",
            [company_id, client.source, started, str(exc)[:1000]],
        )
        conn.commit()
        raise
    finally:
        if locked:
            conn.execute("SELECT pg_advisory_unlock(%s,%s)", [51006, company_id])
            conn.commit()
        conn.close()


def enqueue_due_syncs() -> int:
    from utils.database.task_db import enqueue_background_job

    conn = connect_processing_db(row_factory=True)
    try:
        companies = [row["id"] for row in conn.execute("SELECT id FROM companies WHERE is_active=TRUE").fetchall()]
        running = {
            row["company_id"]
            for row in conn.execute(
                "SELECT DISTINCT company_id FROM job_queue WHERE job_type=%s AND status IN ('queued','running')",
                [JOB_TYPE],
            ).fetchall()
        }
    finally:
        conn.close()
    count = 0
    bucket = int(datetime.now(timezone.utc).timestamp()) // 300
    for company in companies:
        if (
            company in running
            or not get_effective_company_modules(company).get("team_analytics")
            or not is_company_subscription_active(company)[0]
        ):
            continue
        job = enqueue_background_job(
            JOB_TYPE,
            f"ANALYTICS-{company}",
            company_id=company,
            payload={"company_id": company},
            dedupe_key=f"analytics-sync:{company}:{bucket}",
            max_attempts=3,
        )
        count += bool(job)
    return count
