import hashlib
import hmac
import json

from fastapi.testclient import TestClient


def test_analytics_captures_all_issue_updates_without_ai_addon(monkeypatch):
    from services.team_analytics_ingestion import capture_issue
    from services.webhook.jira_webhook_handler import app
    from utils.auth import auth_db

    captured = []
    monkeypatch.setattr(
        auth_db, "get_effective_company_modules", lambda company: {"team_analytics": True, "webhook": False}
    )
    monkeypatch.setattr(
        "services.team_analytics_ingestion.capture_issue", lambda company, config, body: captured.append(body)
    )
    client = TestClient(app)
    body = {
        "webhookEvent": "jira:issue_updated",
        "issue": {"id": "42", "key": "TEST-42", "fields": {"status": {"name": "Done"}}},
        "changelog": {"items": []},
    }
    response = client.post("/webhook/jira/pytestco", json=body, headers={"X-Webhook-Secret": "pytest-webhook-secret"})
    assert response.status_code == 200
    assert response.json()["status"] == "recorded"
    assert captured == [body]
    assert callable(capture_issue)


def test_sprint_event_is_authenticated_and_stored_without_an_issue(monkeypatch):
    from services.webhook.jira_webhook_handler import app
    from utils.auth import auth_db

    captured = []
    monkeypatch.setattr(auth_db, "get_effective_company_modules", lambda company: {"team_analytics": True})
    monkeypatch.setattr(
        "services.team_analytics_ingestion.capture_sprint",
        lambda company, config, body: captured.append(body["sprint"]["id"]),
    )
    client = TestClient(app)
    body = {"webhookEvent": "sprint_closed", "sprint": {"id": 17, "name": "Pilot", "state": "closed"}}
    denied = client.post("/webhook/jira/pytestco", json=body, headers={"X-Webhook-Secret": "wrong"})
    assert denied.status_code == 401
    assert captured == []
    response = client.post("/webhook/jira/pytestco", json=body, headers={"X-Webhook-Secret": "pytest-webhook-secret"})
    assert response.status_code == 200
    assert response.json()["status"] == "recorded"
    assert captured == [17]


def test_native_jira_signed_webhook_verifies_exact_body_and_rejects_tampering(monkeypatch):
    from services.webhook.jira_webhook_handler import app
    from utils.auth import auth_db

    captured = []
    monkeypatch.setattr(
        auth_db, "get_effective_company_modules", lambda company: {"team_analytics": True, "webhook": False}
    )
    monkeypatch.setattr(
        "services.team_analytics_ingestion.capture_issue", lambda company, config, body: captured.append(body)
    )
    raw = json.dumps(
        {
            "webhookEvent": "jira:issue_updated",
            "issue": {"id": "42", "key": "TEST-42", "fields": {"summary": "O‘zgarish"}},
            "changelog": {"items": []},
        },
        ensure_ascii=False,
    ).encode()
    signature = "sha256=" + hmac.new(b"pytest-webhook-secret", raw, hashlib.sha256).hexdigest()
    client = TestClient(app)
    response = client.post(
        "/webhook/jira/pytestco",
        content=raw,
        headers={"X-Hub-Signature": signature, "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert len(captured) == 1
    denied = client.post("/webhook/jira/pytestco", content=raw + b" ", headers={"X-Hub-Signature": signature})
    assert denied.status_code == 401
    assert len(captured) == 1
