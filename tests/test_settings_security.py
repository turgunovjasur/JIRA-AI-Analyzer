import json

import pytest

from services.api.settings_api import _build_company_webhook_url, _mask_settings_secrets

pytestmark = pytest.mark.no_db


def test_settings_api_masks_plain_secret_fields():
    masked = _mask_settings_secrets(
        {
            "jira_token": "jira-token-secret",
            "github_token": "github-token-secret",
            "jira_email": "qa@example.com",
        }
    )

    assert masked["jira_token"] != "jira-token-secret"
    assert masked["github_token"] != "github-token-secret"
    assert masked["jira_email"] == "qa@example.com"
    assert masked["jira_token"].endswith("cret")


def test_settings_api_masks_figma_token_rows_without_breaking_json_shape():
    raw_rows = json.dumps(
        [
            {"name": "design", "token": "figma-secret-token"},
            {"name": "qa", "token": ""},
        ]
    )

    masked = _mask_settings_secrets({"figma_tokens": raw_rows})
    rows = json.loads(masked["figma_tokens"])

    assert rows[0]["name"] == "design"
    assert rows[0]["token"] != "figma-secret-token"
    assert rows[0]["token"].endswith("oken")
    assert rows[1]["name"] == "qa"


def test_build_company_webhook_url_with_secret(monkeypatch):
    monkeypatch.setenv("APP_BASE_URL", "https://qa.example.uz/")
    monkeypatch.setattr(
        "services.api.settings_api.get_company_by_id",
        lambda company_id: {"id": company_id, "company_code": "uzum"},
    )
    monkeypatch.setattr(
        "services.api.settings_api.get_company_settings",
        lambda company_id: {"webhook_secret": "s3cr3t-token"},
    )

    assert _build_company_webhook_url(331) == "https://qa.example.uz/webhook/jira/uzum?token=s3cr3t-token"


def test_build_company_webhook_url_without_secret(monkeypatch):
    monkeypatch.setenv("APP_BASE_URL", "https://qa.example.uz")
    monkeypatch.setattr(
        "services.api.settings_api.get_company_by_id",
        lambda company_id: {"id": company_id, "company_code": "uzum"},
    )
    monkeypatch.setattr(
        "services.api.settings_api.get_company_settings",
        lambda company_id: {"webhook_secret": ""},
    )

    assert _build_company_webhook_url(331) == "https://qa.example.uz/webhook/jira/uzum"


def test_build_company_webhook_url_missing_company(monkeypatch):
    monkeypatch.setenv("APP_BASE_URL", "https://qa.example.uz")
    monkeypatch.setattr("services.api.settings_api.get_company_by_id", lambda company_id: None)

    assert _build_company_webhook_url(999) == ""


def test_generate_webhook_secret_creates_once(monkeypatch):
    import asyncio

    from services.api import settings_api

    saved: dict = {}
    monkeypatch.setenv("APP_BASE_URL", "https://qa.example.uz")
    monkeypatch.setattr(
        settings_api, "load_api_session",
        lambda sid, allowed_roles=None: {"role": "company_admin", "company_id": 331},
    )
    monkeypatch.setattr(settings_api, "_resolve_company_scope_for_webhook", lambda session, cid: 331)
    monkeypatch.setattr(
        settings_api, "get_company_settings",
        lambda cid: {"webhook_secret": saved.get("webhook_secret", "")},
    )
    monkeypatch.setattr(settings_api, "get_company_by_id", lambda cid: {"id": cid, "company_code": "uzum"})

    def fake_save(cid, settings):
        saved.update(settings)
        return True

    monkeypatch.setattr(settings_api, "save_company_settings", fake_save)

    result = asyncio.run(
        settings_api.generate_webhook_secret(settings_api.WebhookSecretGenerateRequest(), x_session_id="sid")
    )
    assert result["generated"] is True
    assert saved["webhook_secret"]
    assert result["webhook_url"] == f"https://qa.example.uz/webhook/jira/uzum?token={saved['webhook_secret']}"

    first_secret = saved["webhook_secret"]
    result2 = asyncio.run(
        settings_api.generate_webhook_secret(settings_api.WebhookSecretGenerateRequest(), x_session_id="sid")
    )
    assert result2["generated"] is False
    assert saved["webhook_secret"] == first_secret
