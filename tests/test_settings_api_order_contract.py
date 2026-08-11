import asyncio
import json

import pytest
from fastapi import HTTPException

from config.app_settings import TestcaseGeneratorSettings as TestcaseSettings
from config.app_settings import TZPRCheckerSettings
from services.api.settings_api import (
    _CHECKER_AI_ORDER_ALLOWED,
    _TESTCASE_AI_ORDER_ALLOWED,
    WebhookConfigSaveRequest,
    _parse_ordered_list,
)

pytestmark = pytest.mark.no_db

JIRA_COMMENT_SECTIONS = [
    "statistics",
    "ai_pipeline",
    "summary",
    "completed",
    "failed",
    "skipped",
    "issues",
]


def test_checker_api_allowlist_matches_app_settings():
    assert set(_CHECKER_AI_ORDER_ALLOWED) == set(TZPRCheckerSettings._AI_DATA_ORDER_ALLOWED)


def test_testcase_api_allowlist_matches_app_settings():
    assert set(_TESTCASE_AI_ORDER_ALLOWED) == set(TestcaseSettings._AI_DATA_ORDER_ALLOWED)


@pytest.mark.parametrize(
    "settings_cls,allowed",
    [
        (TZPRCheckerSettings, _CHECKER_AI_ORDER_ALLOWED),
        (TestcaseSettings, _TESTCASE_AI_ORDER_ALLOWED),
    ],
)
def test_default_order_survives_api_validation(settings_cls, allowed):
    """Read → forma → save aylanishi: default qiymat save validatsiyasidan o'tishi shart."""
    default_order = settings_cls().ai_data_section_order

    parsed = _parse_ordered_list(default_order, "ai_data_section_order", allowed)

    assert parsed == default_order


def test_testcase_order_accepts_figma_flag():
    """'figma' — testcase_generator uchun Figma'ni yoqish flagi, rad etilmasligi kerak."""
    parsed = _parse_ordered_list(
        ["tz", "comments", "custom_context", "figma", "code"],
        "testcase_ai_data_section_order",
        _TESTCASE_AI_ORDER_ALLOWED,
        required_items=("tz",),
    )

    assert "figma" in parsed


def test_unknown_order_item_is_still_rejected():
    with pytest.raises(HTTPException) as exc:
        _parse_ordered_list(["tz", "nonexistent"], "testcase_ai_data_section_order", _TESTCASE_AI_ORDER_ALLOWED)

    assert exc.value.status_code == 400


def test_jira_comment_sections_default_all_enabled():
    assert TZPRCheckerSettings().jira_comment_sections == JIRA_COMMENT_SECTIONS


def test_jira_comment_sections_preserves_selected_order():
    settings = TZPRCheckerSettings(
        jira_comment_sections=["summary", "failed"],
    )

    assert settings.jira_comment_sections == ["summary", "failed"]


def test_jira_comment_sections_allows_empty_selection():
    settings = TZPRCheckerSettings(jira_comment_sections=[])

    assert settings.jira_comment_sections == []


def test_parse_ordered_list_allows_empty_only_when_requested():
    assert _parse_ordered_list(
        [],
        "jira_comment_sections",
        tuple(JIRA_COMMENT_SECTIONS),
        allow_empty=True,
    ) == []

    with pytest.raises(HTTPException):
        _parse_ordered_list([], "visible_sections", ("failed",))


def test_webhook_config_save_persists_jira_comment_sections(monkeypatch):
    from services.api import settings_api

    saved_payload: dict = {}

    monkeypatch.setattr(settings_api, "load_api_session", lambda *args, **kwargs: {})
    monkeypatch.setattr(settings_api, "_resolve_company_scope_for_webhook", lambda session, company_id: 7)
    monkeypatch.setattr(
        settings_api,
        "get_company_webhook_module_settings",
        lambda company_id, module_name=None: {},
    )

    def save_company_settings(company_id: int, payload: dict) -> bool:
        saved_payload.update(payload)
        return True

    monkeypatch.setattr(settings_api, "save_company_settings", save_company_settings)

    result = asyncio.run(
        settings_api.save_webhook_config(
            WebhookConfigSaveRequest(
                company_id=7,
                data={"jira_comment_sections": ["summary", "failed"]},
            ),
            x_session_id="session",
        )
    )

    saved_modules = json.loads(saved_payload["webhook_module_settings"])
    assert result == {"success": True}
    assert saved_modules["webhook_tz_pr"]["jira_comment_sections"] == ["summary", "failed"]
