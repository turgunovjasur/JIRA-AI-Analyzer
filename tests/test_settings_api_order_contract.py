import pytest
from fastapi import HTTPException

from config.app_settings import TZPRCheckerSettings
from config.app_settings import TestcaseGeneratorSettings as TestcaseSettings
from services.api.settings_api import (
    _CHECKER_AI_ORDER_ALLOWED,
    _TESTCASE_AI_ORDER_ALLOWED,
    _parse_ordered_list,
)

pytestmark = pytest.mark.no_db


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
