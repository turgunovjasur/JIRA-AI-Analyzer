"""Read-only Jira requests and project-specific analytics field discovery."""

from __future__ import annotations

import re
import time
from urllib.parse import urlsplit

import requests


class JiraReadError(RuntimeError):
    def __init__(self, status, path):
        self.status = status
        super().__init__(f"Jira GET {path}: HTTP {status}")


def read_issue_history(client, key, points_field, sprint_field):
    """Avoid combining an old issue snapshot with a newer changelog during a sync."""
    for _ in range(3):
        issue = client.issue(key, points_field, sprint_field)
        histories = client.changelog(key)
        verified = client.issue(key, points_field, sprint_field)
        if (issue.get("fields") or {}).get("updated") == (verified.get("fields") or {}).get("updated"):
            return verified, histories
    raise RuntimeError(f"Jira issue {key} changed during history read; retry sync")


def jira_source(config: dict) -> str:
    parsed = urlsplit(str(config.get("webhook_jira_server") or config.get("jira_server") or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Analytics Jira server URL missing or invalid")
    return (
        f"{parsed.scheme.lower()}://{parsed.hostname.lower()}"
        + (f":{parsed.port}" if parsed.port else "")
        + parsed.path.rstrip("/")
    )


def choose_points_field(fields: list[dict], board_fields: list[str], sample: dict) -> str:
    candidates = {
        f["id"]
        for f in fields
        if (f.get("schema") or {}).get("type") == "number"
        and str(f.get("name", "")).casefold() in {"story points", "story point estimate", "story points estimate"}
    }
    configured = candidates.intersection(board_fields)
    if len(configured) == 1:
        return configured.pop()
    populated = {field for field in candidates if sample.get(field) is not None}
    if len(populated) == 1:
        return populated.pop()
    if len(candidates) == 1:
        return candidates.pop()
    raise ValueError("Jira story-point field missing or ambiguous; project board mapping required")


def choose_sprint_field(fields: list[dict]) -> str:
    candidates = [
        f["id"] for f in fields if (f.get("schema") or {}).get("custom") == "com.pyxis.greenhopper.jira:gh-sprint"
    ]
    if not candidates:
        candidates = [f["id"] for f in fields if str(f.get("name", "")).casefold() in {"sprint", "спринт"}]
    if len(candidates) != 1:
        raise ValueError("Jira sprint field missing or ambiguous")
    return candidates[0]


def project_keys(config: dict) -> list[str]:
    value = config.get("webhook_project_keys") or config.get("jira_project_keys") or ""
    keys = [key.upper() for key in re.split(r"[\s,;]+", value) if key]
    if not keys or any(not re.fullmatch(r"[A-Z][A-Z0-9_]*", key) for key in keys):
        raise ValueError("Analytics configured Jira project keys missing or invalid")
    return list(dict.fromkeys(keys))


class JiraAnalyticsClient:
    def __init__(self, config: dict):
        self.source = jira_source(config)
        email = config.get("webhook_jira_email") or config.get("jira_email")
        token = config.get("webhook_jira_token") or config.get("jira_token")
        if not email or not token:
            raise ValueError("Analytics Jira read credentials missing")
        self.session = requests.Session()
        self.session.auth = (email, token)
        self.session.headers.update({"Accept": "application/json"})

    def get(self, path: str, params=None):
        for attempt in range(3):
            response = self.session.get(self.source + path, params=params, timeout=(5, 20))
            if response.status_code == 200:
                return response.json()
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < 2:
                    try:
                        delay = float(response.headers.get("Retry-After", attempt + 1))
                    except ValueError:
                        delay = attempt + 1
                    time.sleep(min(max(delay, 0), 10))
                    continue
            raise JiraReadError(response.status_code, path)
        raise JiraReadError(response.status_code, path)

    def search(self, jql: str, fields="id,key"):
        token = None
        while True:
            params = {"jql": jql, "maxResults": 100, "fields": fields}
            if token:
                params["nextPageToken"] = token
            data = self.get("/rest/api/3/search/jql", params)
            yield from data.get("issues", [])
            next_token = data.get("nextPageToken")
            if data.get("isLast") or not next_token:
                break
            if next_token == token:
                raise RuntimeError("Jira search pagination did not advance")
            token = next_token

    def changelog(self, key: str) -> list[dict]:
        start, result = 0, []
        while True:
            data = self.get(f"/rest/api/3/issue/{key}/changelog", {"startAt": start, "maxResults": 100})
            batch = data.get("values", [])
            result.extend(batch)
            if data.get("isLast") or start + len(batch) >= data.get("total", 0):
                return result
            if not batch:
                raise RuntimeError("Jira changelog pagination incomplete")
            start += len(batch)

    def discover_fields(self, project: str, sample_fields=None) -> tuple[str, str]:
        fields = self.get("/rest/api/3/field")
        board_fields, start = [], 0
        try:
            while True:
                boards = self.get(
                    "/rest/agile/1.0/board", {"projectKeyOrId": project, "startAt": start, "maxResults": 50}
                )
                batch = boards.get("values", [])
                for board in batch:
                    if board.get("type") in {"scrum", "simple"}:
                        try:
                            board_config = self.get(f"/rest/agile/1.0/board/{board['id']}/configuration")
                            field = ((board_config.get("estimation") or {}).get("field") or {}).get("fieldId")
                            if field:
                                board_fields.append(field)
                        except JiraReadError as exc:
                            if exc.status not in {403, 404}:
                                raise
                start += len(batch)
                if boards.get("isLast") or not batch:
                    break
        except JiraReadError as exc:
            if exc.status not in {403, 404}:
                raise
        if not sample_fields:
            sample = next(self.search(f'project = "{project}" ORDER BY updated DESC', "*all"), None)
            sample_fields = (sample or {}).get("fields", {})
        return choose_points_field(fields, board_fields, sample_fields or {}), choose_sprint_field(fields)

    def issue(self, key: str, points_field: str, sprint_field: str) -> dict:
        fields = (
            "summary,status,assignee,project,issuetype,created,updated,resolutiondate,duedate,parent,priority,resolution,reporter,labels,components,fixVersions,"
            + points_field
            + ","
            + sprint_field
        )
        return self.get(f"/rest/api/3/issue/{key}", {"fields": fields})
