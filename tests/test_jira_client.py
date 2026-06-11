from types import SimpleNamespace

from utils.jira.jira_client import JiraClient
from utils.jira.task_details_cache import clear_task_details_cache


def test_resolve_user_name_uses_secondary_fields_when_display_name_missing():
    user = SimpleNamespace(displayName=None, name="Ali Valiyev", emailAddress="ali@example.com")

    result = JiraClient._resolve_user_name(user, "Unassigned")

    assert result == "Ali Valiyev"


def test_resolve_user_name_uses_dict_email_when_name_missing():
    user = {"displayName": "", "emailAddress": "qa@example.com"}

    result = JiraClient._resolve_user_name(user, "Unknown")

    assert result == "qa@example.com"


def test_resolve_user_name_reads_raw_payload_when_direct_attrs_missing():
    user = SimpleNamespace(raw={"displayName": "Raw Assignee"})

    result = JiraClient._resolve_user_name(user, "Unassigned")

    assert result == "Raw Assignee"


def test_resolve_user_name_reads_nested_user_payload():
    user = {"user": {"displayName": "Nested Assignee"}}

    result = JiraClient._resolve_user_name(user, "Unassigned")

    assert result == "Nested Assignee"


def test_resolve_user_name_ignores_python_object_repr():
    class DummyUser:
        pass

    result = JiraClient._resolve_user_name(DummyUser(), "Unassigned")

    assert result == "Unassigned"


def test_resolve_user_name_returns_fallback_for_empty_value():
    result = JiraClient._resolve_user_name(None, "Unassigned")

    assert result == "Unassigned"


def _make_test_client() -> JiraClient:
    client = JiraClient.__new__(JiraClient)
    client.server = "https://jira.example.test"
    client.email = "qa@example.test"
    client.token = "token"
    client.story_points_field = "customfield_10016"
    client.sprint_field = "customfield_10020"
    client.pr_field = "customfield_12345"
    client._client = None
    return client


def _make_issue(issue_id: str = "10001"):
    fields = SimpleNamespace(
        summary="Task summary",
        description="Task description",
        issuetype=SimpleNamespace(name="DEV TASK"),
        status=SimpleNamespace(name="Ready"),
        assignee=SimpleNamespace(displayName="Dev User"),
        reporter=SimpleNamespace(displayName="PO User"),
        priority=SimpleNamespace(name="High"),
        comment=SimpleNamespace(comments=[]),
        created="2026-05-18T10:00:00.000+0500",
        resolutiondate=None,
        labels=["Patch"],
        components=[SimpleNamespace(name="Mobile")],
    )
    setattr(fields, "customfield_10016", 3)
    return SimpleNamespace(id=issue_id, key="DEV-1", fields=fields)


def test_get_task_details_reuses_short_lived_cache(monkeypatch):
    clear_task_details_cache()
    client = _make_test_client()
    issue = _make_issue()
    calls = {"issue": 0, "dev_status": 0}

    def fake_get_issue(issue_key):
        calls["issue"] += 1
        return issue

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "detail": [
                    {
                        "pullRequests": [
                            {
                                "url": "https://github.com/acme/repo/pull/1",
                                "name": "PR title",
                                "status": "MERGED",
                            }
                        ]
                    }
                ]
            }

    def fake_get(*args, **kwargs):
        calls["dev_status"] += 1
        return FakeResponse()

    monkeypatch.setattr(client, "get_issue", fake_get_issue)
    monkeypatch.setattr("utils.jira.jira_client.requests.get", fake_get)

    first = client.get_task_details("DEV-1")
    second = client.get_task_details("DEV-1")

    assert first == second
    assert first["issue_id"] == "10001"
    assert first["pr_urls"] == [
        {
            "url": "https://github.com/acme/repo/pull/1",
            "title": "PR title",
            "status": "MERGED",
            "source": "dev_status_api",
        }
    ]
    assert calls == {"issue": 1, "dev_status": 1}


def test_get_task_details_can_skip_pr_lookup(monkeypatch):
    clear_task_details_cache()
    client = _make_test_client()
    issue = _make_issue()
    calls = {"issue": 0, "dev_status": 0}

    def fake_get_issue(issue_key):
        calls["issue"] += 1
        return issue

    def fake_get(*args, **kwargs):
        calls["dev_status"] += 1
        raise AssertionError("dev-status should not be called when include_pr_urls=False")

    monkeypatch.setattr(client, "get_issue", fake_get_issue)
    monkeypatch.setattr("utils.jira.jira_client.requests.get", fake_get)

    details = client.get_task_details("DEV-1", include_pr_urls=False)

    assert details["pr_urls"] == []
    assert calls == {"issue": 1, "dev_status": 0}
