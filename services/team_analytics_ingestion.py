"""Webhook analytics capture; shares field discovery and persistence with sync."""

from services.team_analytics import normalize_sprints
from services.team_analytics_jira import JiraAnalyticsClient, jira_source
from utils.database.team_analytics_repository import field_mapping, record_event, save_field_mapping, save_sprints


def capture_issue(company_id: int, config: dict, body: dict):
    source = jira_source(config)
    issue = body.get("issue") or {}
    project = str(
        (issue.get("fields", {}).get("project") or {}).get("key") or issue.get("key", "").split("-")[0]
    ).upper()
    mapping = field_mapping(company_id, source, project)
    if not mapping:
        points, sprint = JiraAnalyticsClient(config).discover_fields(project, (issue.get("fields") or {}))
        save_field_mapping(company_id, source, project, points, sprint)
        mapping = {"points_field": points, "sprint_field": sprint}
    return record_event(company_id, source, body, mapping["points_field"], mapping["sprint_field"])


def capture_sprint(company_id: int, config: dict, body: dict):
    sprints = normalize_sprints([body.get("sprint") or {}])
    if body.get("webhookEvent") == "sprint_deleted":
        for sprint in sprints:
            sprint["state"] = "deleted"
    save_sprints(company_id, jira_source(config), sprints)
