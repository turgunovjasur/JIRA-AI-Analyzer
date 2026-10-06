import pytest

pytestmark = pytest.mark.no_db


def test_board_estimation_field_wins_over_global_field_id():
    from services.team_analytics_jira import choose_points_field

    fields = [
        {"id": "customfield_10016", "name": "Story point estimate", "schema": {"type": "number"}},
        {"id": "customfield_10038", "name": "Story Points", "schema": {"type": "number"}},
    ]
    assert choose_points_field(fields, ["customfield_10038"], {}) == "customfield_10038"


def test_ambiguous_fields_do_not_silently_choose_a_global_default():
    from services.team_analytics_jira import choose_points_field

    fields = [
        {"id": "customfield_2", "name": "Story Points", "schema": {"type": "number"}},
        {"id": "customfield_3", "name": "Story point estimate", "schema": {"type": "number"}},
    ]
    with pytest.raises(ValueError, match="ambiguous"):
        choose_points_field(fields, [], {})


def test_complete_changelog_pagination_and_search_tokens():
    from services.team_analytics_jira import JiraAnalyticsClient

    client = JiraAnalyticsClient({"jira_server": "https://jira.example", "jira_email": "e", "jira_token": "t"})
    calls = []

    def get(path, params=None):
        calls.append((path, params))
        if path.endswith("/changelog"):
            return {"values": [{"id": str(params["startAt"])}], "total": 2, "isLast": params["startAt"] == 1}
        return {
            "issues": [{"id": "2" if params.get("nextPageToken") else "1"}],
            "isLast": bool(params.get("nextPageToken")),
            "nextPageToken": "next",
        }

    client.get = get
    assert len(client.changelog("DEV-1")) == 2
    assert [issue["id"] for issue in client.search("project = DEV")] == ["1", "2"]
    assert calls[1][1]["startAt"] == 1


def test_normalized_source_and_sprint_field_schema():
    from services.team_analytics_jira import choose_sprint_field, jira_source

    assert jira_source({"jira_server": "https://JIRA.EXAMPLE/path/"}) == "https://jira.example/path"
    assert (
        choose_sprint_field(
            [{"id": "customfield_77", "name": "Спринт", "schema": {"custom": "com.pyxis.greenhopper.jira:gh-sprint"}}]
        )
        == "customfield_77"
    )


def test_webhook_credentials_override_shared_fields_independently():
    from services.team_analytics_jira import JiraAnalyticsClient

    client = JiraAnalyticsClient(
        {
            "jira_server": "https://jira.example",
            "jira_email": "shared",
            "jira_token": "shared-token",
            "webhook_jira_email": "webhook",
            "webhook_jira_token": "webhook-token",
        }
    )
    assert client.session.auth == ("webhook", "webhook-token")


def test_team_managed_simple_board_supplies_its_estimation_field():
    from services.team_analytics_jira import JiraAnalyticsClient

    client = JiraAnalyticsClient({"jira_server": "https://jira.example", "jira_email": "e", "jira_token": "t"})

    def get(path, params=None):
        if path.endswith("/field"):
            return [
                {"id": "sp1", "name": "Story Points", "schema": {"type": "number"}},
                {"id": "sp2", "name": "Story point estimate", "schema": {"type": "number"}},
                {"id": "sprint", "name": "Sprint", "schema": {"custom": "com.pyxis.greenhopper.jira:gh-sprint"}},
            ]
        if path.endswith("/board"):
            return {"values": [{"id": 10, "type": "simple"}], "isLast": True}
        return {"estimation": {"field": {"fieldId": "sp2"}}}

    client.get = get
    assert client.discover_fields("DEV", {"unrelated": True}) == ("sp2", "sprint")


def test_consistent_issue_read_retries_when_issue_changes_during_changelog():
    from services.team_analytics_jira import read_issue_history

    class Client:
        def __init__(self):
            self.calls = 0

        def issue(self, *args):
            self.calls += 1
            return {"fields": {"updated": "old" if self.calls == 1 else "new"}}

        def changelog(self, *args):
            return [{"id": self.calls}]

    client = Client()
    issue, histories = read_issue_history(client, "DEV-1", "sp", "sprint")
    assert issue["fields"]["updated"] == "new"
    assert histories == [{"id": 3}]
    assert client.calls == 4
