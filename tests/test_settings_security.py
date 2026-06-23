import json

import pytest

from services.api.settings_api import _mask_settings_secrets

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
