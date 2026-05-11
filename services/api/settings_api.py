"""
Internal settings API endpoints.

This router is focused on the lowest-risk split step for Unified Settings:
shared API keys and webhook API keys.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from config.app_settings import get_app_settings_for_company, get_app_settings_for_user
from config.token_limits import (
    AI_MAX_INPUT_TOKENS,
    CHARS_PER_TOKEN,
    TESTCASE_MAX_OUTPUT_TOKENS,
)
from services.api.session_scope import (
    get_session_company_id,
    get_session_role,
    get_session_user_id,
    load_api_session,
)
from utils.auth.auth_db import (
    debug_company_settings_save,
    get_company_webhook_module_settings,
    get_company_settings,
    get_user_module_settings,
    get_user_credentials,
    save_company_webhook_module_settings,
    save_company_settings,
    save_user_credentials,
    save_user_module_settings,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SharedApiKeysReadRequest(BaseModel):
    user_id: int | None = None
    company_id: int | None = None
    is_company_admin: bool = False


class WebhookApiKeysReadRequest(BaseModel):
    company_id: int


class SharedApiKeysSaveRequest(BaseModel):
    user_id: int | None = None
    company_id: int | None = None
    is_company_admin: bool = False
    data: dict[str, Any] = Field(default_factory=dict)


class WebhookApiKeysSaveRequest(BaseModel):
    company_id: int
    data: dict[str, Any] = Field(default_factory=dict)


class WebhookConfigReadRequest(BaseModel):
    company_id: int | None = None


class WebhookConfigSaveRequest(BaseModel):
    company_id: int | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class SystemConfigReadRequest(BaseModel):
    company_id: int | None = None


class SystemConfigSaveRequest(BaseModel):
    company_id: int | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class ModuleSettingsReadRequest(BaseModel):
    company_id: int | None = None
    user_id: int | None = None


class ModuleSettingsSaveRequest(BaseModel):
    company_id: int | None = None
    user_id: int | None = None
    data: dict[str, Any] = Field(default_factory=dict)


_CHECKER_VISIBLE_SECTIONS_ALLOWED = ("completed", "partial", "failed", "issues", "figma")
_WEBHOOK_CHECKER_VISIBLE_SECTIONS_ALLOWED = (
    "completed",
    "partial",
    "failed",
    "issues",
    "figma",
    "contradictory_comments",
)
_CHECKER_AI_ORDER_ALLOWED = ("tz", "comments", "figma", "code")
_TESTCASE_AI_ORDER_ALLOWED = ("tz", "comments", "custom_context", "code")
_TESTCASE_TYPES_ALLOWED = ("positive", "negative", "boundary", "edge")


def _resolve_company_scope_for_webhook(session: dict, requested_company_id: int | None) -> int:
    role = get_session_role(session)
    company_id = requested_company_id
    if role == "company_admin":
        session_company_id = get_session_company_id(session)
        if company_id not in (None, session_company_id):
            raise HTTPException(status_code=403, detail="Boshqa company webhook settingsni boshqarib bo'lmaydi")
        company_id = session_company_id
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required")
    return int(company_id)


def _resolve_user_module_scope(
    session: dict,
    requested_company_id: int | None,
    requested_user_id: int | None,
) -> tuple[int, int]:
    role = get_session_role(session)
    if role not in {"company_admin", "user"}:
        raise HTTPException(status_code=403, detail="Module settings faqat company admin yoki user uchun")

    session_company_id = get_session_company_id(session)
    session_user_id = get_session_user_id(session)
    if not session_company_id or not session_user_id:
        raise HTTPException(status_code=400, detail="Sessiyada company_id yoki user_id topilmadi")

    if requested_company_id not in (None, session_company_id):
        raise HTTPException(status_code=403, detail="Boshqa company scope bilan module settings ishlatib bo'lmaydi")
    if requested_user_id not in (None, session_user_id):
        raise HTTPException(status_code=403, detail="Faqat o'z module settingsingizni boshqarishingiz mumkin")

    return int(session_company_id), int(session_user_id)


def _parse_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise HTTPException(status_code=400, detail=f"{field_name} bool bo'lishi kerak")


def _parse_non_negative_int(value: Any, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"{field_name} integer bo'lishi kerak")
    if parsed < 0:
        raise HTTPException(status_code=400, detail=f"{field_name} 0 yoki undan katta bo'lishi kerak")
    return parsed


def _parse_positive_int(value: Any, field_name: str, min_value: int = 1, max_value: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"{field_name} integer bo'lishi kerak")
    if parsed < min_value:
        raise HTTPException(status_code=400, detail=f"{field_name} {min_value} yoki undan katta bo'lishi kerak")
    if max_value is not None and parsed > max_value:
        raise HTTPException(status_code=400, detail=f"{field_name} {max_value} yoki undan kichik bo'lishi kerak")
    return parsed


def _parse_ordered_list(
    value: Any,
    field_name: str,
    allowed: tuple[str, ...],
    required_items: tuple[str, ...] = (),
) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise HTTPException(status_code=400, detail=f"{field_name} string list bo'lishi kerak")

    seen: set[str] = set()
    order: list[str] = []
    for raw_item in value:
        item = raw_item.strip()
        if not item or item in seen:
            continue
        if item not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"{field_name} noto'g'ri element: {item}. Ruxsat: {', '.join(allowed)}",
            )
        seen.add(item)
        order.append(item)

    for required in required_items:
        if required not in order:
            raise HTTPException(status_code=400, detail=f"{field_name} ichida '{required}' bo'lishi shart")

    if not order:
        raise HTTPException(status_code=400, detail=f"{field_name} bo'sh bo'lmasligi kerak")
    return order


@router.post("/api-keys/shared/read")
async def read_shared_api_keys(
    payload: SharedApiKeysReadRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin", "user"})
    role = get_session_role(session)
    session_company_id = get_session_company_id(session)
    session_user_id = get_session_user_id(session)

    if payload.is_company_admin:
        if role not in {"super_admin", "company_admin"}:
            raise HTTPException(status_code=403, detail="Company settings faqat admin uchun")
        company_id = payload.company_id
        if role == "company_admin":
            if company_id not in (None, session_company_id):
                raise HTTPException(status_code=403, detail="Boshqa company settingsni o'qib bo'lmaydi")
            company_id = session_company_id
        if not company_id:
            raise HTTPException(status_code=400, detail="company_id is required for company admin")
        return {"data": get_company_settings(company_id)}

    if role in {"company_admin", "user"}:
        if payload.user_id not in (None, session_user_id):
            raise HTTPException(status_code=403, detail="Faqat o'z user settingsingizni o'qishingiz mumkin")
        if payload.company_id not in (None, session_company_id):
            raise HTTPException(status_code=403, detail="Boshqa company scope bilan o'qib bo'lmaydi")
        if not session_user_id:
            raise HTTPException(status_code=400, detail="user_id is required for user credentials")
        return {"data": get_user_credentials(session_user_id)}

    if not payload.user_id:
        raise HTTPException(status_code=400, detail="user_id is required for user credentials")
    return {"data": get_user_credentials(payload.user_id)}


@router.post("/api-keys/webhook/read")
async def read_webhook_api_keys(
    payload: WebhookApiKeysReadRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin"})
    role = get_session_role(session)
    company_id = payload.company_id
    if role == "company_admin":
        session_company_id = get_session_company_id(session)
        if company_id not in (None, session_company_id):
            raise HTTPException(status_code=403, detail="Boshqa company webhook settingsni o'qib bo'lmaydi")
        company_id = session_company_id
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required")
    return {"data": get_company_settings(company_id)}


@router.post("/api-keys/shared/save")
async def save_shared_api_keys(
    payload: SharedApiKeysSaveRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin", "user"})
    role = get_session_role(session)
    session_company_id = get_session_company_id(session)
    session_user_id = get_session_user_id(session)

    if payload.is_company_admin:
        if role not in {"super_admin", "company_admin"}:
            raise HTTPException(status_code=403, detail="Company settings faqat admin uchun")
        company_id = payload.company_id
        if role == "company_admin":
            if company_id not in (None, session_company_id):
                raise HTTPException(status_code=403, detail="Boshqa company settingsni saqlab bo'lmaydi")
            company_id = session_company_id
        if not company_id:
            raise HTTPException(status_code=400, detail="company_id is required for company admin")
        ok = save_company_settings(company_id, payload.data)
        return {
            "success": ok,
            "reasons": [] if ok else debug_company_settings_save(company_id, payload.data),
        }

    if role in {"company_admin", "user"}:
        if payload.user_id not in (None, session_user_id):
            raise HTTPException(status_code=403, detail="Faqat o'z user settingsingizni saqlashingiz mumkin")
        if payload.company_id not in (None, session_company_id):
            raise HTTPException(status_code=403, detail="Boshqa company scope bilan saqlab bo'lmaydi")
        if not session_user_id:
            raise HTTPException(status_code=400, detail="user_id is required for user credentials")
        ok = save_user_credentials(session_user_id, payload.data)
        return {"success": ok, "reasons": [] if ok else ["User credentials save failed."]}

    if not payload.user_id:
        raise HTTPException(status_code=400, detail="user_id is required for user credentials")
    ok = save_user_credentials(payload.user_id, payload.data)
    return {"success": ok, "reasons": [] if ok else ["User credentials save failed."]}


@router.post("/api-keys/webhook/save")
async def save_webhook_api_keys(
    payload: WebhookApiKeysSaveRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin"})
    role = get_session_role(session)
    company_id = payload.company_id
    if role == "company_admin":
        session_company_id = get_session_company_id(session)
        if company_id not in (None, session_company_id):
            raise HTTPException(status_code=403, detail="Boshqa company webhook settingsni saqlab bo'lmaydi")
        company_id = session_company_id
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required")
    ok = save_company_settings(company_id, payload.data)
    return {
        "success": ok,
        "reasons": [] if ok else debug_company_settings_save(company_id, payload.data),
    }


@router.post("/webhook/config/read")
async def read_webhook_config(
    payload: WebhookConfigReadRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin"})
    company_id = _resolve_company_scope_for_webhook(session, payload.company_id)
    app_settings = get_app_settings_for_company(company_id)
    webhook_settings = app_settings.webhook_tz_pr
    webhook_testcase = app_settings.webhook_testcase
    queue_settings = app_settings.queue
    visible_sections = list(webhook_settings.visible_sections or [])
    show_contradictory = bool(webhook_settings.show_contradictory_comments)
    if show_contradictory and "contradictory_comments" not in visible_sections:
        visible_sections = [*visible_sections, "contradictory_comments"]
    if not show_contradictory:
        visible_sections = [item for item in visible_sections if item != "contradictory_comments"]

    return {
        "success": True,
        "data": {
            "trigger_status": webhook_settings.trigger_status,
            "trigger_status_aliases": webhook_settings.trigger_status_aliases,
            "return_threshold": webhook_settings.return_threshold,
            "return_status": webhook_settings.return_status,
            "use_adf_format": True,
            "tz_pr_footer_text": webhook_settings.tz_pr_footer_text,
            "recheck_comment_text": webhook_settings.recheck_comment_text,
            "show_contradictory_comments": show_contradictory,
            "visible_sections": visible_sections,
            "ai_data_section_order": list(webhook_settings.ai_data_section_order or []),
            "read_comments_enabled": bool(webhook_settings.read_comments_enabled),
            "max_comments_to_read": int(webhook_settings.max_comments_to_read),
            "min_tz_description_chars": webhook_settings.min_tz_description_chars,
            "checker_delay_seconds": queue_settings.checker_testcase_delay,
            "excluded_assignees": webhook_settings.excluded_assignees,
            "allowed_issue_types": webhook_settings.allowed_issue_types,
            "skip_code": webhook_settings.skip_code,
            "max_skip_check_comments": webhook_settings.max_skip_check_comments,
            "return_notification_text": webhook_settings.return_notification_text,
            "skip_comment_text": webhook_settings.skip_comment_text,
            "auto_return_enabled": bool(webhook_settings.auto_return_enabled),
            "trigger_statuses": webhook_settings.get_trigger_statuses(),
            "testcase_auto_comment_enabled": bool(webhook_testcase.auto_comment_enabled),
            "testcase_auto_comment_trigger_status": webhook_testcase.auto_comment_trigger_status,
            "testcase_auto_comment_trigger_aliases": webhook_testcase.auto_comment_trigger_aliases,
            "testcase_default_include_pr": bool(webhook_testcase.default_include_pr),
            "testcase_default_use_smart_patch": bool(webhook_testcase.default_use_smart_patch),
            "testcase_default_test_types": list(webhook_testcase.default_test_types or []),
            "testcase_max_test_cases": int(webhook_testcase.max_test_cases),
            "testcase_ai_data_section_order": list(webhook_testcase.ai_data_section_order or []),
            "testcase_read_comments_enabled": bool(webhook_testcase.read_comments_enabled),
            "testcase_max_comments_to_read": int(webhook_testcase.max_comments_to_read),
            "testcase_ai_max_output_tokens": TESTCASE_MAX_OUTPUT_TOKENS,
            "testcase_use_adf_format": True,
            "testcase_footer_text": webhook_testcase.testcase_footer_text,
        },
    }


@router.post("/webhook/config/save")
async def save_webhook_config(
    payload: WebhookConfigSaveRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin"})
    company_id = _resolve_company_scope_for_webhook(session, payload.company_id)

    raw = payload.data or {}
    raw_trigger = str(raw.get("trigger_status", "")).strip()
    raw_aliases = str(raw.get("trigger_status_aliases", "")).strip()
    raw_excluded = str(raw.get("excluded_assignees", "")).strip()
    raw_allowed_types = str(raw.get("allowed_issue_types", "")).strip()
    raw_skip = str(raw.get("skip_code", "")).strip()
    raw_return_status = str(raw.get("return_status", "")).strip()
    raw_return_notification_text = str(raw.get("return_notification_text", "")).strip()
    raw_tz_pr_footer_text = str(raw.get("tz_pr_footer_text", "")).strip()
    raw_skip_comment_text = str(raw.get("skip_comment_text", "")).strip()
    raw_recheck_comment_text = str(raw.get("recheck_comment_text", "")).strip()
    raw_auto_return = bool(raw.get("auto_return_enabled", False))

    try:
        raw_threshold = int(raw.get("return_threshold", 60))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="return_threshold noto'g'ri")
    try:
        raw_min_tz = int(raw.get("min_tz_description_chars", 50))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="min_tz_description_chars noto'g'ri")
    raw_checker_delay: int | None = None
    if "checker_delay_seconds" in raw:
        try:
            raw_checker_delay = int(raw.get("checker_delay_seconds", 15))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="checker_delay_seconds noto'g'ri")
    try:
        raw_max_skip_comments = int(raw.get("max_skip_check_comments", 5))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="max_skip_check_comments noto'g'ri")

    if raw_threshold < 0 or raw_threshold > 100:
        raise HTTPException(status_code=400, detail="return_threshold 0-100 oralig'ida bo'lishi kerak")
    if raw_min_tz < 0:
        raise HTTPException(status_code=400, detail="min_tz_description_chars 0 yoki undan katta bo'lishi kerak")
    if raw_checker_delay is not None and raw_checker_delay <= 0:
        raise HTTPException(status_code=400, detail="checker_delay_seconds 0 dan katta bo'lishi kerak")
    if raw_max_skip_comments <= 0:
        raise HTTPException(status_code=400, detail="max_skip_check_comments 1 yoki undan katta bo'lishi kerak")

    # trigger_statuses yuborilgan bo'lsa, trigger_status_aliases ni ulardan yig'ish
    if not raw_aliases:
        raw_statuses = raw.get("trigger_statuses")
        if isinstance(raw_statuses, list):
            statuses = []
            for item in raw_statuses:
                if not isinstance(item, str):
                    continue
                cleaned = item.strip()
                if cleaned and cleaned.lower() != raw_trigger.lower():
                    statuses.append(cleaned)
            raw_aliases = ", ".join(list(dict.fromkeys(statuses)))

    current_wh = get_company_webhook_module_settings(company_id, "webhook_tz_pr") or {}
    current_tc = get_company_webhook_module_settings(company_id, "webhook_testcase") or {}
    current_queue = get_company_webhook_module_settings(company_id, "queue") or {}

    updated_wh = dict(current_wh)
    def _wh_bool(key: str, default: bool) -> bool:
        if key in raw:
            return _parse_bool(raw.get(key), key)
        if key in current_wh:
            return bool(current_wh.get(key))
        return default

    def _wh_non_negative_int(key: str, default: int) -> int:
        if key in raw:
            return _parse_non_negative_int(raw.get(key), key)
        if key in current_wh:
            return _parse_non_negative_int(current_wh.get(key), key)
        return default

    def _wh_ordered_list(
        key: str,
        allowed: tuple[str, ...],
        required_items: tuple[str, ...],
        default: list[str],
    ) -> list[str]:
        if key in raw:
            return _parse_ordered_list(raw.get(key), key, allowed, required_items=required_items)
        if key in current_wh:
            return _parse_ordered_list(current_wh.get(key), key, allowed, required_items=required_items)
        return default

    visible_sections = _wh_ordered_list(
        "visible_sections",
        _WEBHOOK_CHECKER_VISIBLE_SECTIONS_ALLOWED,
        required_items=(),
        default=["completed", "partial", "failed", "issues", "figma"],
    )
    show_contradictory = "contradictory_comments" in visible_sections
    if "show_contradictory_comments" in raw:
        show_contradictory = _parse_bool(raw.get("show_contradictory_comments"), "show_contradictory_comments")
        if show_contradictory and "contradictory_comments" not in visible_sections:
            visible_sections = [*visible_sections, "contradictory_comments"]
        if not show_contradictory:
            visible_sections = [item for item in visible_sections if item != "contradictory_comments"]

    updated_wh.update(
        {
            "trigger_status": raw_trigger or updated_wh.get("trigger_status", "READY TO TEST"),
            "trigger_status_aliases": raw_aliases,
            "return_threshold": raw_threshold,
            "return_status": raw_return_status or updated_wh.get("return_status", "NEED CLARIFICATION/RETURN TEST"),
            "use_adf_format": True,
            "tz_pr_footer_text": raw_tz_pr_footer_text or updated_wh.get(
                "tz_pr_footer_text",
                "🤖 Bu komment AI tomonidan avtomatik yaratilgan. Savollar bo'lsa QA Team ga murojaat qiling.",
            ),
            "recheck_comment_text": raw_recheck_comment_text or updated_wh.get(
                "recheck_comment_text",
                "🔄 Re-check: Task qaytarildigan so'ng qaytadan tekshirilmoqda...",
            ),
            "show_contradictory_comments": show_contradictory,
            "visible_sections": visible_sections,
            "ai_data_section_order": _wh_ordered_list(
                "ai_data_section_order",
                _CHECKER_AI_ORDER_ALLOWED,
                required_items=("tz", "code"),
                default=["tz", "comments", "figma", "code"],
            ),
            "read_comments_enabled": _wh_bool("read_comments_enabled", True),
            "max_comments_to_read": _wh_non_negative_int("max_comments_to_read", 0),
            "min_tz_description_chars": raw_min_tz,
            "excluded_assignees": raw_excluded,
            "allowed_issue_types": raw_allowed_types,
            "skip_code": raw_skip or updated_wh.get("skip_code", "AI_SKIP"),
            "max_skip_check_comments": raw_max_skip_comments,
            "return_notification_text": raw_return_notification_text or updated_wh.get("return_notification_text", ""),
            "skip_comment_text": raw_skip_comment_text or updated_wh.get("skip_comment_text", ""),
            "auto_return_enabled": raw_auto_return,
        }
    )

    updated_queue = dict(current_queue)
    if raw_checker_delay is not None:
        updated_queue.update({"checker_testcase_delay": raw_checker_delay})

    def _tc_bool(key: str, default: bool) -> bool:
        if key in raw:
            return _parse_bool(raw.get(key), key)
        if key in current_tc:
            return bool(current_tc.get(key))
        return default

    def _tc_positive_int(key: str, default: int, min_value: int = 1, max_value: int | None = None) -> int:
        if key in raw:
            return _parse_positive_int(raw.get(key), key, min_value=min_value, max_value=max_value)
        if key in current_tc:
            return _parse_positive_int(current_tc.get(key), key, min_value=min_value, max_value=max_value)
        return default

    def _tc_non_negative_int(key: str, default: int) -> int:
        if key in raw:
            return _parse_non_negative_int(raw.get(key), key)
        if key in current_tc:
            return _parse_non_negative_int(current_tc.get(key), key)
        return default

    def _tc_string(key: str, default: str) -> str:
        if key in raw:
            return str(raw.get(key) or "").strip()
        if key in current_tc:
            return str(current_tc.get(key) or "").strip()
        return default

    def _tc_ordered_list(
        key: str,
        allowed: tuple[str, ...],
        required_items: tuple[str, ...],
        default: list[str],
    ) -> list[str]:
        if key in raw:
            return _parse_ordered_list(raw.get(key), key, allowed, required_items=required_items)
        if key in current_tc:
            return _parse_ordered_list(current_tc.get(key), key, allowed, required_items=required_items)
        return default

    updated_tc = dict(current_tc)
    updated_tc.update(
        {
            "auto_comment_enabled": _tc_bool("testcase_auto_comment_enabled", False),
            "auto_comment_trigger_status": _tc_string("testcase_auto_comment_trigger_status", "READY TO TEST") or "READY TO TEST",
            "auto_comment_trigger_aliases": _tc_string("testcase_auto_comment_trigger_aliases", "Ready To Test,READY TO TEST"),
            "default_include_pr": _tc_bool("testcase_default_include_pr", True),
            "default_use_smart_patch": _tc_bool("testcase_default_use_smart_patch", True),
            "default_test_types": _tc_ordered_list(
                "testcase_default_test_types",
                _TESTCASE_TYPES_ALLOWED,
                required_items=(),
                default=["positive", "negative"],
            ),
            "max_test_cases": _tc_positive_int("testcase_max_test_cases", 10, min_value=1, max_value=50),
            "ai_data_section_order": _tc_ordered_list(
                "testcase_ai_data_section_order",
                _TESTCASE_AI_ORDER_ALLOWED,
                required_items=("tz",),
                default=["tz", "comments", "custom_context", "code"],
            ),
            "read_comments_enabled": _tc_bool("testcase_read_comments_enabled", True),
            "max_comments_to_read": _tc_non_negative_int("testcase_max_comments_to_read", 0),
            "ai_max_output_tokens": TESTCASE_MAX_OUTPUT_TOKENS,
            "use_adf_format": True,
            "testcase_footer_text": _tc_string(
                "testcase_footer_text",
                "🤖 Test case'lar AI (Gemini) tomonidan avtomatik yaratilgan. QA Team tomonidan tekshirilishi va to'ldirilishi kerak.",
            ),
        }
    )

    current_all_modules = get_company_webhook_module_settings(company_id) or {}
    merged_all_modules = dict(current_all_modules)
    merged_all_modules["webhook_tz_pr"] = updated_wh
    merged_all_modules["webhook_testcase"] = updated_tc
    merged_all_modules["queue"] = updated_queue

    ok_company = save_company_settings(
        company_id,
        {
            "webhook_module_settings": json.dumps(merged_all_modules, ensure_ascii=True),
            "webhook_trigger_status": updated_wh.get("trigger_status", ""),
            "webhook_trigger_aliases": updated_wh.get("trigger_status_aliases", ""),
            "webhook_return_threshold": int(updated_wh.get("return_threshold", raw_threshold)),
            "webhook_return_status": updated_wh.get("return_status", ""),
            "webhook_allowed_issue_types": updated_wh.get("allowed_issue_types", ""),
            "webhook_excluded_assignees": updated_wh.get("excluded_assignees", ""),
            "webhook_auto_return_enabled": 1 if updated_wh.get("auto_return_enabled") else 0,
        },
    )

    if not ok_company:
        raise HTTPException(status_code=400, detail="Webhook konfiguratsiyasi saqlanmadi")

    return {"success": True}


@router.post("/system/config/read")
async def read_system_config(
    payload: SystemConfigReadRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin"})
    company_id = _resolve_company_scope_for_webhook(session, payload.company_id)
    app_settings = get_app_settings_for_company(company_id)
    queue_settings = app_settings.queue

    return {
        "success": True,
        "data": {
            "queue_enabled": bool(queue_settings.queue_enabled),
            "task_wait_timeout": int(queue_settings.task_wait_timeout),
            "checker_testcase_delay": int(queue_settings.checker_testcase_delay),
            "blocked_retry_delay": int(queue_settings.blocked_retry_delay),
            "gemini_min_interval": int(queue_settings.gemini_min_interval),
            "blocked_check_interval": int(queue_settings.blocked_check_interval),
            "key_freeze_duration": int(queue_settings.key_freeze_duration),
            "ai_max_retries": int(queue_settings.ai_max_retries),
            "ai_max_input_tokens": AI_MAX_INPUT_TOKENS,
            "chars_per_token": CHARS_PER_TOKEN,
            "db_busy_timeout": int(queue_settings.db_busy_timeout),
            "db_connection_timeout": int(queue_settings.db_connection_timeout),
            "http_timeout": int(queue_settings.http_timeout),
            "executor_timeout": int(queue_settings.executor_timeout),
        },
    }


@router.post("/system/config/save")
async def save_system_config(
    payload: SystemConfigSaveRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin"})
    company_id = _resolve_company_scope_for_webhook(session, payload.company_id)

    raw = payload.data or {}
    current_queue = get_company_webhook_module_settings(company_id, "queue") or {}

    def _get_current_or_default(key: str, default: int | bool) -> int | bool:
        if key in raw:
            return raw[key]
        if key in current_queue:
            return current_queue[key]
        return default

    queue_enabled = _parse_bool(
        _get_current_or_default("queue_enabled", True),
        "queue_enabled",
    )
    task_wait_timeout = _parse_positive_int(
        _get_current_or_default("task_wait_timeout", 60),
        "task_wait_timeout",
        min_value=1,
    )
    checker_testcase_delay = _parse_positive_int(
        _get_current_or_default("checker_testcase_delay", 15),
        "checker_testcase_delay",
        min_value=1,
    )
    blocked_retry_delay = _parse_positive_int(
        _get_current_or_default("blocked_retry_delay", 5),
        "blocked_retry_delay",
        min_value=1,
    )
    gemini_min_interval = _parse_positive_int(
        _get_current_or_default("gemini_min_interval", 6),
        "gemini_min_interval",
        min_value=1,
    )
    blocked_check_interval = _parse_positive_int(
        _get_current_or_default("blocked_check_interval", 30),
        "blocked_check_interval",
        min_value=1,
    )
    key_freeze_duration = _parse_positive_int(
        _get_current_or_default("key_freeze_duration", 600),
        "key_freeze_duration",
        min_value=1,
    )
    ai_max_retries = _parse_positive_int(
        _get_current_or_default("ai_max_retries", 3),
        "ai_max_retries",
        min_value=1,
    )
    ai_max_input_tokens = AI_MAX_INPUT_TOKENS
    chars_per_token = CHARS_PER_TOKEN
    db_busy_timeout = _parse_positive_int(
        _get_current_or_default("db_busy_timeout", 30000),
        "db_busy_timeout",
        min_value=1,
    )
    db_connection_timeout = _parse_positive_int(
        _get_current_or_default("db_connection_timeout", 30),
        "db_connection_timeout",
        min_value=1,
    )
    http_timeout = _parse_positive_int(
        _get_current_or_default("http_timeout", 30),
        "http_timeout",
        min_value=1,
    )
    executor_timeout = _parse_positive_int(
        _get_current_or_default("executor_timeout", 120),
        "executor_timeout",
        min_value=1,
    )

    updated_queue = dict(current_queue)
    updated_queue.update(
        {
            "queue_enabled": queue_enabled,
            "task_wait_timeout": task_wait_timeout,
            "checker_testcase_delay": checker_testcase_delay,
            "blocked_retry_delay": blocked_retry_delay,
            "gemini_min_interval": gemini_min_interval,
            "blocked_check_interval": blocked_check_interval,
            "key_freeze_duration": key_freeze_duration,
            "ai_max_retries": ai_max_retries,
            "ai_max_input_tokens": ai_max_input_tokens,
            "chars_per_token": chars_per_token,
            "db_busy_timeout": db_busy_timeout,
            "db_connection_timeout": db_connection_timeout,
            "http_timeout": http_timeout,
            "executor_timeout": executor_timeout,
        }
    )

    ok_queue = save_company_webhook_module_settings(company_id, "queue", updated_queue)
    if not ok_queue:
        raise HTTPException(status_code=400, detail="System konfiguratsiyasi saqlanmadi")

    return {"success": True}


@router.post("/modules/config/read")
async def read_module_config(
    payload: ModuleSettingsReadRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    session = load_api_session(x_session_id, allowed_roles={"company_admin", "user"})
    company_id, user_id = _resolve_user_module_scope(session, payload.company_id, payload.user_id)
    app_settings = get_app_settings_for_user(user_id, company_id)

    checker = app_settings.tz_pr_checker
    testcase = app_settings.testcase_generator

    return {
        "success": True,
        "data": {
            "checker": {
                "default_use_smart_patch": bool(checker.default_use_smart_patch),
                "visible_sections": list(checker.visible_sections or []),
                "ai_data_section_order": list(checker.ai_data_section_order or []),
                "read_comments_enabled": bool(checker.read_comments_enabled),
                "max_comments_to_read": int(checker.max_comments_to_read),
            },
            "testcase": {
                "default_include_pr": bool(testcase.default_include_pr),
                "default_use_smart_patch": bool(testcase.default_use_smart_patch),
                "default_test_types": list(testcase.default_test_types or []),
                "max_test_cases": int(testcase.max_test_cases),
                "ai_data_section_order": list(testcase.ai_data_section_order or []),
                "read_comments_enabled": bool(testcase.read_comments_enabled),
                "max_comments_to_read": int(testcase.max_comments_to_read),
            },
            "allowed": {
                "checker_visible_sections": list(_CHECKER_VISIBLE_SECTIONS_ALLOWED),
                "checker_ai_data_order": list(_CHECKER_AI_ORDER_ALLOWED),
                "testcase_ai_data_order": list(_TESTCASE_AI_ORDER_ALLOWED),
                "testcase_types": list(_TESTCASE_TYPES_ALLOWED),
            },
        },
    }


@router.post("/modules/config/save")
async def save_module_config(
    payload: ModuleSettingsSaveRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    session = load_api_session(x_session_id, allowed_roles={"company_admin", "user"})
    company_id, user_id = _resolve_user_module_scope(session, payload.company_id, payload.user_id)

    raw = payload.data or {}
    checker_raw = raw.get("checker")
    testcase_raw = raw.get("testcase")
    if not isinstance(checker_raw, dict) or not isinstance(testcase_raw, dict):
        raise HTTPException(status_code=400, detail="checker va testcase sozlamalari object bo'lishi kerak")

    checker_update = {
        "default_use_smart_patch": _parse_bool(
            checker_raw.get("default_use_smart_patch"),
            "checker.default_use_smart_patch",
        ),
        "visible_sections": _parse_ordered_list(
            checker_raw.get("visible_sections"),
            "checker.visible_sections",
            _CHECKER_VISIBLE_SECTIONS_ALLOWED,
        ),
        "ai_data_section_order": _parse_ordered_list(
            checker_raw.get("ai_data_section_order"),
            "checker.ai_data_section_order",
            _CHECKER_AI_ORDER_ALLOWED,
            required_items=("tz", "code"),
        ),
        "read_comments_enabled": _parse_bool(
            checker_raw.get("read_comments_enabled"),
            "checker.read_comments_enabled",
        ),
        "max_comments_to_read": _parse_non_negative_int(
            checker_raw.get("max_comments_to_read"),
            "checker.max_comments_to_read",
        ),
    }

    testcase_update = {
        "default_include_pr": _parse_bool(
            testcase_raw.get("default_include_pr"),
            "testcase.default_include_pr",
        ),
        "default_use_smart_patch": _parse_bool(
            testcase_raw.get("default_use_smart_patch"),
            "testcase.default_use_smart_patch",
        ),
        "default_test_types": _parse_ordered_list(
            testcase_raw.get("default_test_types"),
            "testcase.default_test_types",
            _TESTCASE_TYPES_ALLOWED,
        ),
        "max_test_cases": _parse_positive_int(
            testcase_raw.get("max_test_cases"),
            "testcase.max_test_cases",
            min_value=1,
            max_value=50,
        ),
        "ai_data_section_order": _parse_ordered_list(
            testcase_raw.get("ai_data_section_order"),
            "testcase.ai_data_section_order",
            _TESTCASE_AI_ORDER_ALLOWED,
            required_items=("tz",),
        ),
        "read_comments_enabled": _parse_bool(
            testcase_raw.get("read_comments_enabled"),
            "testcase.read_comments_enabled",
        ),
        "max_comments_to_read": _parse_non_negative_int(
            testcase_raw.get("max_comments_to_read"),
            "testcase.max_comments_to_read",
        ),
    }

    current_checker = get_user_module_settings(user_id, "tz_pr_checker")
    current_testcase = get_user_module_settings(user_id, "testcase_generator")

    merged_checker = {}
    if isinstance(current_checker, dict):
        merged_checker.update(current_checker)
    merged_checker.update(checker_update)

    merged_testcase = {}
    if isinstance(current_testcase, dict):
        merged_testcase.update(current_testcase)
    merged_testcase.update(testcase_update)

    checker_ok = save_user_module_settings(user_id, "tz_pr_checker", merged_checker)
    testcase_ok = save_user_module_settings(user_id, "testcase_generator", merged_testcase)

    if not (checker_ok and testcase_ok):
        raise HTTPException(status_code=400, detail="Module sozlamalarini saqlab bo'lmadi")

    updated = get_app_settings_for_user(user_id, company_id)
    return {
        "success": True,
        "data": {
            "checker": asdict(updated.tz_pr_checker),
            "testcase": asdict(updated.testcase_generator),
        },
    }
