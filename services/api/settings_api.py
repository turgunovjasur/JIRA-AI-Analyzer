"""
Internal settings API endpoints.

This router is focused on the lowest-risk split step for Unified Settings:
shared API keys and webhook API keys.
"""
from __future__ import annotations

import json
import os
import secrets
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
    get_company_by_id,
    get_company_settings,
    get_company_webhook_module_settings,
    get_user_credentials,
    get_user_module_settings,
    save_company_settings,
    save_company_webhook_module_settings,
    save_user_credentials,
    save_user_module_settings,
)
from utils.auth.credential_crypto import get_sensitive_credential_fields, mask_secret_value

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _mask_token_rows(value: Any) -> str:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return mask_secret_value(value)
    else:
        parsed = value
    if not isinstance(parsed, list):
        return ""
    masked = []
    for row in parsed:
        item = dict(row or {}) if isinstance(row, dict) else {}
        if "token" in item:
            item["token"] = mask_secret_value(item.get("token"))
        masked.append(item)
    return json.dumps(masked, ensure_ascii=True)


def _mask_settings_secrets(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload or {})
    for field in get_sensitive_credential_fields():
        if field not in result:
            continue
        if field in {"figma_tokens", "webhook_figma_tokens"}:
            result[field] = _mask_token_rows(result.get(field))
        else:
            result[field] = mask_secret_value(result.get(field))
    return result


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


_CHECKER_VISIBLE_SECTIONS_ALLOWED = ("completed", "failed", "skipped", "issues", "figma")
_CHECKER_AI_ORDER_ALLOWED = ("tz", "comments", "figma", "code")
_TESTCASE_AI_ORDER_ALLOWED = ("tz", "comments", "custom_context", "figma", "code")
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
        if item in {"partial", "contradictory_comments"}:
            continue
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
        return {"data": _mask_settings_secrets(get_company_settings(company_id))}

    if role in {"company_admin", "user"}:
        if payload.user_id not in (None, session_user_id):
            raise HTTPException(status_code=403, detail="Faqat o'z user settingsingizni o'qishingiz mumkin")
        if payload.company_id not in (None, session_company_id):
            raise HTTPException(status_code=403, detail="Boshqa company scope bilan o'qib bo'lmaydi")
        if not session_user_id:
            raise HTTPException(status_code=400, detail="user_id is required for user credentials")
        return {"data": _mask_settings_secrets(get_user_credentials(session_user_id))}

    if not payload.user_id:
        raise HTTPException(status_code=400, detail="user_id is required for user credentials")
    return {"data": _mask_settings_secrets(get_user_credentials(payload.user_id))}


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
    return {"data": _mask_settings_secrets(get_company_settings(company_id))}


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


def _build_company_webhook_url(company_id: int) -> str:
    """
    Kompaniya uchun JIRA'ga qo'yiladigan tayyor webhook URL.

    Secret ?token= query orqali — JIRA'ning oddiy system webhook'i custom
    header yubora olmaydi. Base: APP_BASE_URL (Caddy /webhook/* ni backendga
    proxy qiladi, shuning uchun domen frontend bilan bir xil).
    """
    company = get_company_by_id(company_id) or {}
    company_code = str(company.get("company_code") or "").strip()
    if not company_code:
        return ""
    base_url = (os.getenv("APP_BASE_URL") or "").strip().rstrip("/")
    secret = str(get_company_settings(company_id).get("webhook_secret") or "").strip()
    url = f"{base_url}/webhook/jira/{company_code}"
    return f"{url}?token={secret}" if secret else url


class WebhookSecretGenerateRequest(BaseModel):
    company_id: int | None = None


@router.post("/webhook/secret/generate")
async def generate_webhook_secret(
    payload: WebhookSecretGenerateRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    """
    Bo'sh webhook_secret uchun parol yaratish (avto-generatsiya kodidan OLDIN
    yaratilgan kompaniyalar uchun). Mavjud parolni QAYTA yozmaydi — aks holda
    JIRA'dagi eski URL indamay 401 ola boshlaydi.
    """
    session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin"})
    company_id = _resolve_company_scope_for_webhook(session, payload.company_id)
    current = str(get_company_settings(company_id).get("webhook_secret") or "").strip()
    if current:
        return {"success": True, "generated": False, "webhook_url": _build_company_webhook_url(company_id)}
    if not save_company_settings(company_id, {"webhook_secret": secrets.token_urlsafe(32)}):
        raise HTTPException(status_code=500, detail="Webhook secret saqlanmadi")
    return {"success": True, "generated": True, "webhook_url": _build_company_webhook_url(company_id)}


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
    visible_sections = [
        item
        for item in list(webhook_settings.visible_sections or [])
        if item in _CHECKER_VISIBLE_SECTIONS_ALLOWED
    ] or ["completed", "failed", "skipped", "issues", "figma"]
    show_contradictory = bool(webhook_settings.show_contradictory_comments)

    return {
        "success": True,
        "data": {
            "webhook_url": _build_company_webhook_url(company_id),
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
            "dev_comment_source": str(getattr(webhook_settings, "dev_comment_source", "assignee_reporter") or "assignee_reporter"),
            "min_tz_description_chars": webhook_settings.min_tz_description_chars,
            "excluded_assignees": webhook_settings.excluded_assignees,
            "allowed_issue_types": webhook_settings.allowed_issue_types,
            "skip_code": webhook_settings.skip_code,
            "max_skip_check_comments": webhook_settings.max_skip_check_comments,
            "return_notification_text": webhook_settings.return_notification_text,
            "skip_comment_text": webhook_settings.skip_comment_text,
            "auto_return_enabled": bool(webhook_settings.auto_return_enabled),
            "agent2_batch_size": int(getattr(webhook_settings, "agent2_batch_size", 6) or 6),
            "agent1_primary_model": str(getattr(webhook_settings, "agent1_primary_model", "") or ""),
            "agent1_fallback_model": str(getattr(webhook_settings, "agent1_fallback_model", "") or ""),
            "agent2_primary_model": str(getattr(webhook_settings, "agent2_primary_model", "") or ""),
            "agent2_fallback_model": str(getattr(webhook_settings, "agent2_fallback_model", "") or ""),
            "agent3_primary_model": str(getattr(webhook_settings, "agent3_primary_model", "") or ""),
            "agent3_fallback_model": str(getattr(webhook_settings, "agent3_fallback_model", "") or ""),
            "trigger_statuses": webhook_settings.get_trigger_statuses(),
            "testcase_auto_comment_enabled": bool(webhook_testcase.auto_comment_enabled),
            "testcase_auto_comment_trigger_status": webhook_testcase.auto_comment_trigger_status,
            "testcase_auto_comment_trigger_aliases": webhook_testcase.auto_comment_trigger_aliases,
            "testcase_default_test_types": list(webhook_testcase.default_test_types or []),
            "testcase_testcases_per_requirement": int(getattr(webhook_testcase, "testcases_per_requirement", 3) or 3),
            "testcase_ai_data_section_order": list(webhook_testcase.ai_data_section_order or []),
            "testcase_read_comments_enabled": bool(webhook_testcase.read_comments_enabled),
            "testcase_max_comments_to_read": int(webhook_testcase.max_comments_to_read),
            "testcase_agent1_primary_model": str(getattr(webhook_testcase, "agent1_primary_model", "") or ""),
            "testcase_agent1_fallback_model": str(getattr(webhook_testcase, "agent1_fallback_model", "") or ""),
            "testcase_agent2_primary_model": str(getattr(webhook_testcase, "agent2_primary_model", "") or ""),
            "testcase_agent2_fallback_model": str(getattr(webhook_testcase, "agent2_fallback_model", "") or ""),
            "testcase_agent3_primary_model": str(getattr(webhook_testcase, "agent3_primary_model", "") or ""),
            "testcase_agent3_fallback_model": str(getattr(webhook_testcase, "agent3_fallback_model", "") or ""),
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
    raw_skip_present = "skip_code" in raw
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
    try:
        raw_max_skip_comments = int(raw.get("max_skip_check_comments", 5))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="max_skip_check_comments noto'g'ri")

    if raw_threshold < 0 or raw_threshold > 100:
        raise HTTPException(status_code=400, detail="return_threshold 0-100 oralig'ida bo'lishi kerak")
    if raw_min_tz < 0:
        raise HTTPException(status_code=400, detail="min_tz_description_chars 0 yoki undan katta bo'lishi kerak")
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
        _CHECKER_VISIBLE_SECTIONS_ALLOWED,
        required_items=(),
        default=["completed", "failed", "skipped", "issues", "figma"],
    )
    effective_skip_code = raw_skip if raw_skip_present else str(updated_wh.get("skip_code", "AI_SKIP") or "").strip()
    effective_max_comments_to_read = _wh_non_negative_int("max_comments_to_read", 0)
    if not effective_skip_code and raw_max_skip_comments <= 0:
        raw_max_skip_comments = 1
    if effective_skip_code and raw_max_skip_comments <= 0:
        raise HTTPException(status_code=400, detail="max_skip_check_comments 1 yoki undan katta bo'lishi kerak")
    if (
        effective_skip_code
        and effective_max_comments_to_read > 0
        and raw_max_skip_comments >= effective_max_comments_to_read
    ):
        raise HTTPException(
            status_code=400,
            detail="max_comments_to_read skip tekshirish comment sonidan katta bo'lishi kerak",
        )
    show_contradictory = bool(updated_wh.get("show_contradictory_comments", True))
    if "show_contradictory_comments" in raw:
        show_contradictory = _parse_bool(raw.get("show_contradictory_comments"), "show_contradictory_comments")

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
            "max_comments_to_read": effective_max_comments_to_read,
            "dev_comment_source": (
                "all"
                if str(raw.get("dev_comment_source", current_wh.get("dev_comment_source", "")) or "").strip().lower() == "all"
                else "assignee_reporter"
            ),
            "min_tz_description_chars": raw_min_tz,
            "excluded_assignees": raw_excluded,
            "allowed_issue_types": raw_allowed_types,
            "skip_code": effective_skip_code,
            "max_skip_check_comments": raw_max_skip_comments,
            "return_notification_text": raw_return_notification_text or updated_wh.get("return_notification_text", ""),
            "skip_comment_text": raw_skip_comment_text or updated_wh.get("skip_comment_text", ""),
            "auto_return_enabled": raw_auto_return,
            "agent2_batch_size": _parse_positive_int(
                raw.get("agent2_batch_size", updated_wh.get("agent2_batch_size", 6)),
                "agent2_batch_size",
                min_value=1,
                max_value=20,
            ),
            "agent1_primary_model": str(raw.get("agent1_primary_model", updated_wh.get("agent1_primary_model", "")) or "").strip(),
            "agent1_fallback_model": str(raw.get("agent1_fallback_model", updated_wh.get("agent1_fallback_model", "")) or "").strip(),
            "agent2_primary_model": str(raw.get("agent2_primary_model", updated_wh.get("agent2_primary_model", "")) or "").strip(),
            "agent2_fallback_model": str(raw.get("agent2_fallback_model", updated_wh.get("agent2_fallback_model", "")) or "").strip(),
            "agent3_primary_model": str(raw.get("agent3_primary_model", updated_wh.get("agent3_primary_model", "")) or "").strip(),
            "agent3_fallback_model": str(raw.get("agent3_fallback_model", updated_wh.get("agent3_fallback_model", "")) or "").strip(),
        }
    )

    updated_queue = dict(current_queue)
    updated_queue.pop("checker_testcase_delay", None)

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
            "default_test_types": _tc_ordered_list(
                "testcase_default_test_types",
                _TESTCASE_TYPES_ALLOWED,
                required_items=(),
                default=["positive", "negative"],
            ),
            "testcases_per_requirement": _tc_positive_int(
                "testcase_testcases_per_requirement",
                3,
                min_value=1,
                max_value=3,
            ),
            "ai_data_section_order": _tc_ordered_list(
                "testcase_ai_data_section_order",
                _TESTCASE_AI_ORDER_ALLOWED,
                required_items=("tz",),
                default=["tz", "comments", "custom_context", "figma", "code"],
            ),
            "read_comments_enabled": _tc_bool("testcase_read_comments_enabled", True),
            "max_comments_to_read": _tc_non_negative_int("testcase_max_comments_to_read", 0),
            "agent1_primary_model": str(raw.get("testcase_agent1_primary_model", current_tc.get("agent1_primary_model", "")) or "").strip(),
            "agent1_fallback_model": str(raw.get("testcase_agent1_fallback_model", current_tc.get("agent1_fallback_model", "")) or "").strip(),
            "agent2_primary_model": str(raw.get("testcase_agent2_primary_model", current_tc.get("agent2_primary_model", "")) or "").strip(),
            "agent2_fallback_model": str(raw.get("testcase_agent2_fallback_model", current_tc.get("agent2_fallback_model", "")) or "").strip(),
            "agent3_primary_model": str(raw.get("testcase_agent3_primary_model", current_tc.get("agent3_primary_model", "")) or "").strip(),
            "agent3_fallback_model": str(raw.get("testcase_agent3_fallback_model", current_tc.get("agent3_fallback_model", "")) or "").strip(),
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

    company_payload = {
        "webhook_module_settings": json.dumps(merged_all_modules, ensure_ascii=True),
        "webhook_trigger_status": updated_wh.get("trigger_status", ""),
        "webhook_trigger_aliases": updated_wh.get("trigger_status_aliases", ""),
        "webhook_return_threshold": int(updated_wh.get("return_threshold", raw_threshold)),
        "webhook_return_status": updated_wh.get("return_status", ""),
        "webhook_allowed_issue_types": updated_wh.get("allowed_issue_types", ""),
        "webhook_excluded_assignees": updated_wh.get("excluded_assignees", ""),
        "webhook_auto_return_enabled": bool(updated_wh.get("auto_return_enabled")),
    }
    ok_company = save_company_settings(company_id, company_payload)

    if not ok_company:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "Webhook konfiguratsiyasi saqlanmadi",
                "reasons": debug_company_settings_save(company_id, company_payload),
            },
        )

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
            "queue_enabled": True,
            "task_wait_timeout": int(queue_settings.task_wait_timeout),
            "blocked_retry_delay": int(queue_settings.blocked_retry_delay),
            "gemini_min_interval": int(queue_settings.gemini_min_interval),
            "blocked_check_interval": int(queue_settings.blocked_check_interval),
            "key_freeze_duration": int(queue_settings.key_freeze_duration),
            "gemini_max_retries": int(queue_settings.gemini_max_retries),
            "ai_max_input_tokens": AI_MAX_INPUT_TOKENS,
            "chars_per_token": CHARS_PER_TOKEN,
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

    current_queue = get_company_webhook_module_settings(company_id, "queue") or {}

    queue_enabled = True

    updated_queue = dict(current_queue)
    updated_queue.update(
        {
            "queue_enabled": queue_enabled,
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
                "agent2_parallelism": int(getattr(checker, "agent2_parallelism", 5) or 5),
                "agent2_batch_size": int(getattr(checker, "agent2_batch_size", 6) or 6),
                "visible_sections": [
                    item
                    for item in list(checker.visible_sections or [])
                    if item in _CHECKER_VISIBLE_SECTIONS_ALLOWED
                ] or ["completed", "failed", "skipped", "issues", "figma"],
                "ai_data_section_order": list(checker.ai_data_section_order or []),
                "read_comments_enabled": bool(checker.read_comments_enabled),
                "max_comments_to_read": int(checker.max_comments_to_read),
                "trusted_scope_comment_authors": str(checker.trusted_scope_comment_authors or ""),
                "dev_comment_source": str(getattr(checker, "dev_comment_source", "assignee_reporter") or "assignee_reporter"),
                "agent1_primary_model": str(getattr(checker, "agent1_primary_model", "") or ""),
                "agent1_fallback_model": str(getattr(checker, "agent1_fallback_model", "") or ""),
                "agent2_primary_model": str(getattr(checker, "agent2_primary_model", "") or ""),
                "agent2_fallback_model": str(getattr(checker, "agent2_fallback_model", "") or ""),
                "agent3_primary_model": str(getattr(checker, "agent3_primary_model", "") or ""),
                "agent3_fallback_model": str(getattr(checker, "agent3_fallback_model", "") or ""),
            },
            "testcase": {
                "default_test_types": list(testcase.default_test_types or []),
                "testcases_per_requirement": int(getattr(testcase, "testcases_per_requirement", 3) or 3),
                "ai_data_section_order": list(testcase.ai_data_section_order or []),
                "read_comments_enabled": bool(testcase.read_comments_enabled),
                "max_comments_to_read": int(testcase.max_comments_to_read),
                "agent1_primary_model": str(getattr(testcase, "agent1_primary_model", "") or ""),
                "agent1_fallback_model": str(getattr(testcase, "agent1_fallback_model", "") or ""),
                "agent2_primary_model": str(getattr(testcase, "agent2_primary_model", "") or ""),
                "agent2_fallback_model": str(getattr(testcase, "agent2_fallback_model", "") or ""),
                "agent3_primary_model": str(getattr(testcase, "agent3_primary_model", "") or ""),
                "agent3_fallback_model": str(getattr(testcase, "agent3_fallback_model", "") or ""),
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
        "trusted_scope_comment_authors": str(
            checker_raw.get("trusted_scope_comment_authors") or ""
        ).strip(),
        "dev_comment_source": (
            "all"
            if str(checker_raw.get("dev_comment_source") or "").strip().lower() == "all"
            else "assignee_reporter"
        ),
        "agent2_batch_size": _parse_positive_int(
            checker_raw.get("agent2_batch_size", 6),
            "checker.agent2_batch_size",
            min_value=1,
            max_value=20,
        ),
        "agent1_primary_model": str(checker_raw.get("agent1_primary_model") or "").strip(),
        "agent1_fallback_model": str(checker_raw.get("agent1_fallback_model") or "").strip(),
        "agent2_primary_model": str(checker_raw.get("agent2_primary_model") or "").strip(),
        "agent2_fallback_model": str(checker_raw.get("agent2_fallback_model") or "").strip(),
        "agent3_primary_model": str(checker_raw.get("agent3_primary_model") or "").strip(),
        "agent3_fallback_model": str(checker_raw.get("agent3_fallback_model") or "").strip(),
    }

    testcase_update = {
        "default_test_types": _parse_ordered_list(
            testcase_raw.get("default_test_types"),
            "testcase.default_test_types",
            _TESTCASE_TYPES_ALLOWED,
        ),
        "testcases_per_requirement": _parse_positive_int(
            testcase_raw.get("testcases_per_requirement", 3),
            "testcase.testcases_per_requirement",
            min_value=1,
            max_value=3,
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
        "agent1_primary_model": str(testcase_raw.get("agent1_primary_model") or "").strip(),
        "agent1_fallback_model": str(testcase_raw.get("agent1_fallback_model") or "").strip(),
        "agent2_primary_model": str(testcase_raw.get("agent2_primary_model") or "").strip(),
        "agent2_fallback_model": str(testcase_raw.get("agent2_fallback_model") or "").strip(),
        "agent3_primary_model": str(testcase_raw.get("agent3_primary_model") or "").strip(),
        "agent3_fallback_model": str(testcase_raw.get("agent3_fallback_model") or "").strip(),
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
