"""
Internal RPC-style API for the remaining Streamlit admin/setup/settings flows.

This is intentionally narrow and whitelisted so the frontend can stop importing
backend persistence code directly while we preserve current business logic.
"""
from __future__ import annotations

import inspect
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from config.app_settings import (
    AppSettings,
    BugAnalyzerSettings,
    ModuleVisibility,
    QueueSettings,
    StatisticsSettings,
    TZPRCheckerSettings,
    TestcaseGeneratorSettings,
    get_app_settings,
    get_app_settings_for_company,
    get_app_settings_for_user,
    save_app_settings,
)
from utils.auth.auth_db import (
    count_users_in_company,
    create_company,
    create_password_reset_token,
    create_user,
    debug_company_settings_save,
    delete_company,
    delete_user,
    delete_user_for_company,
    get_all_companies,
    get_company_by_id,
    get_company_modules,
    get_company_settings,
    get_company_subscription,
    get_company_webhook_config,
    get_company_webhook_module_settings,
    get_effective_company_modules,
    get_global_setting,
    get_global_gemini_defaults,
    get_platform_admin_by_username,
    get_recent_login_audit_logs,
    get_user_by_id_and_company,
    get_user_credentials,
    get_users_by_company,
    has_api_keys_configured,
    has_user_credentials_configured,
    save_company_modules,
    save_company_settings,
    save_company_subscription,
    save_company_webhook_module_settings,
    save_platform_admin,
    save_user_credentials,
    save_user_module_settings,
    set_global_setting,
    update_company_seat_limit,
    update_company_status,
    update_user_password,
    update_user_password_for_company,
    update_user_status,
    update_user_status_for_company,
    validate_company_subscription_data,
    write_audit_log,
)
from services.api.session_scope import get_session_company_id, get_session_role, load_api_session
from utils.auth.credential_crypto import get_credential_security_status, get_sensitive_credential_fields
from utils.database.ai_usage_db import fetch_ai_usage_dashboard

router = APIRouter(prefix="/api/internal", tags=["internal-rpc"])


class RpcRequest(BaseModel):
    op: str
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)


def _build_app_settings_from_dict(payload: dict[str, Any]) -> AppSettings:
    def _testcase_settings(key: str) -> TestcaseGeneratorSettings:
        data = dict(payload.get(key, {}) or {})
        for legacy_key in (
            "max_test_cases",
            "default_include_pr",
            "default_include_comments",
            "default_include_code",
            "default_include_figma",
        ):
            data.pop(legacy_key, None)
        return TestcaseGeneratorSettings(**data)

    return AppSettings(
        modules=ModuleVisibility(**payload.get("modules", {})),
        bug_analyzer=BugAnalyzerSettings(**payload.get("bug_analyzer", {})),
        statistics=StatisticsSettings(**payload.get("statistics", {})),
        tz_pr_checker=TZPRCheckerSettings(**payload.get("tz_pr_checker", {})),
        webhook_tz_pr=TZPRCheckerSettings(**payload.get("webhook_tz_pr", {})),
        testcase_generator=_testcase_settings("testcase_generator"),
        webhook_testcase=_testcase_settings("webhook_testcase"),
        queue=QueueSettings(**payload.get("queue", {})),
    )


def _serialize(value: Any) -> Any:
    if is_dataclass(value):
        return _serialize(asdict(value))
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


_REDACTED = "***REDACTED***"
_SENSITIVE_KEY_FRAGMENTS = ("api_key", "token", "secret", "password", "credential")


def _is_sensitive_key(key: Any) -> bool:
    key_text = str(key or "").strip().lower()
    if not key_text:
        return False
    sensitive_fields = {field.lower() for field in get_sensitive_credential_fields()}
    return key_text in sensitive_fields or any(fragment in key_text for fragment in _SENSITIVE_KEY_FRAGMENTS)


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (_REDACTED if _is_sensitive_key(key) else _redact_value(item))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_redact_value(item) for item in value]
    return _serialize(value)


def _redact_rpc_payload(op: str, args: list[Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    redacted_args = _redact_value(args)
    redacted_kwargs = _redact_value(kwargs)

    # set_global_setting("gemini_default_api_key_1", value) carries the sensitive
    # setting value positionally, so dict-key redaction alone cannot see it.
    if op == "set_global_setting" and len(redacted_args) >= 2 and _is_sensitive_key(args[0]):
        redacted_args[1] = _REDACTED

    return {"args": redacted_args, "kwargs": redacted_kwargs}


def _op_save_app_settings(payload: dict[str, Any]) -> bool:
    return save_app_settings(_build_app_settings_from_dict(payload))


def _op_get_app_settings_for_user(user_id: int, company_id: int):
    return get_app_settings_for_user(user_id, company_id)


_OPERATIONS: dict[str, Callable[..., Any]] = {
    "get_company_settings": get_company_settings,
    "save_company_settings": save_company_settings,
    "get_user_credentials": get_user_credentials,
    "save_user_credentials": save_user_credentials,
    "has_user_credentials_configured": has_user_credentials_configured,
    "count_users_in_company": count_users_in_company,
    "create_user": create_user,
    "create_password_reset_token": create_password_reset_token,
    "get_company_by_id": get_company_by_id,
    "get_users_by_company": get_users_by_company,
    "update_user_password_for_company": update_user_password_for_company,
    "update_user_status_for_company": update_user_status_for_company,
    "delete_user_for_company": delete_user_for_company,
    "get_all_companies": get_all_companies,
    "create_company": create_company,
    "update_company_status": update_company_status,
    "update_company_seat_limit": update_company_seat_limit,
    "get_company_subscription": get_company_subscription,
    "validate_company_subscription_data": validate_company_subscription_data,
    "save_company_subscription": save_company_subscription,
    "delete_company": delete_company,
    "has_api_keys_configured": has_api_keys_configured,
    "get_company_modules": get_company_modules,
    "save_company_modules": save_company_modules,
    "update_user_password": update_user_password,
    "update_user_status": update_user_status,
    "delete_user": delete_user,
    "get_global_gemini_defaults": get_global_gemini_defaults,
    "get_global_setting": get_global_setting,
    "set_global_setting": set_global_setting,
    "save_platform_admin": save_platform_admin,
    "get_platform_admin_by_username": get_platform_admin_by_username,
    "get_recent_login_audit_logs": get_recent_login_audit_logs,
    "get_credential_security_status": get_credential_security_status,
    "get_company_webhook_config": get_company_webhook_config,
    "save_user_module_settings": save_user_module_settings,
    "save_company_webhook_module_settings": save_company_webhook_module_settings,
    "debug_company_settings_save": debug_company_settings_save,
    "get_company_webhook_module_settings": get_company_webhook_module_settings,
    "get_effective_company_modules": get_effective_company_modules,
    "get_app_settings": get_app_settings,
    "save_app_settings": _op_save_app_settings,
    "get_app_settings_for_company": get_app_settings_for_company,
    "get_app_settings_for_user": _op_get_app_settings_for_user,
    "get_ai_usage_dashboard": fetch_ai_usage_dashboard,
}

_COMPANY_ADMIN_COMPANY_ARG0_OPS = {
    "count_users_in_company",
    "get_company_by_id",
    "get_company_modules",
    "save_company_settings",
    "save_company_webhook_module_settings",
    "get_company_subscription",
    "get_company_webhook_config",
    "get_company_webhook_module_settings",
    "get_effective_company_modules",
    "get_users_by_company",
    "has_api_keys_configured",
    "get_app_settings_for_company",
}


def _arg_as_positive_int(args: list[Any], index: int) -> int:
    try:
        value = int(args[index])
    except (IndexError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="RPC argument noto'g'ri yoki yetishmaydi")
    if value <= 0:
        raise HTTPException(status_code=400, detail="RPC argument musbat integer bo'lishi kerak")
    return value


def _effective_positional_args(op: str, args: list[Any], kwargs: dict[str, Any]) -> list[Any]:
    """args + kwargs'ni operation funksiyasi imzosiga bog'lab, pozitsion tartibdagi
    effektiv argumentlar ro'yxatini qaytaradi.

    Nima uchun kerak: authz tekshiruvi security-muhim argumentlarni (company_id,
    role) pozitsion INDEKS bo'yicha o'qiydi. Agar chaqiruvchi ularni kwargs orqali
    yuborsa (masalan create_user(..., role="company_admin")), positional-only
    tekshiruv ularni ko'rmay qolib, keyin fn(*args, **kwargs) haqiqiy qiymatni
    qo'llab, authz'ni CHETLAB o'tardi. Bind qilib effektiv qiymatlarni olamiz.
    Kutilmagan/mos kelmaydigan argument → TypeError → 400.
    """
    fn = _OPERATIONS.get(op)
    if fn is None:
        return list(args or [])
    try:
        sig = inspect.signature(fn)
        bound = sig.bind_partial(*(args or []), **(kwargs or {}))
    except TypeError:
        raise HTTPException(status_code=400, detail="RPC argumentlari funksiya imzosiga mos emas")
    bound.apply_defaults()
    eff: list[Any] = []
    for p in sig.parameters.values():
        if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        eff.append(bound.arguments.get(p.name))
    return eff


def _authorize_internal_rpc(session: dict, payload: RpcRequest) -> None:
    role = get_session_role(session)
    if role == "super_admin":
        return

    if role != "company_admin":
        raise HTTPException(status_code=403, detail="Internal RPC faqat admin rollari uchun")

    session_company_id = get_session_company_id(session)
    if not session_company_id:
        raise HTTPException(status_code=403, detail="Company admin sessiyasida company_id topilmadi")

    # Kwargs bypass'ining oldini olish uchun effektiv (bind qilingan) argumentlar.
    eff = _effective_positional_args(payload.op, payload.args, payload.kwargs)

    if payload.op in _COMPANY_ADMIN_COMPANY_ARG0_OPS:
        company_id = _arg_as_positive_int(eff, 0)
        if company_id != session_company_id:
            raise HTTPException(status_code=403, detail="Boshqa company scope bilan RPC chaqirib bo'lmaydi")
        return

    if payload.op == "create_user":
        company_id = _arg_as_positive_int(eff, 0)
        target_role = str(eff[3] if len(eff) > 3 and eff[3] is not None else "user").strip().lower()
        if company_id != session_company_id:
            raise HTTPException(status_code=403, detail="Boshqa companyga user yaratib bo'lmaydi")
        if target_role != "user":
            raise HTTPException(status_code=403, detail="Company admin faqat oddiy user yarata oladi")
        return

    if payload.op in {"update_user_password_for_company", "update_user_status_for_company", "delete_user_for_company"}:
        company_id = _arg_as_positive_int(eff, 1)
        if company_id != session_company_id:
            raise HTTPException(status_code=403, detail="Boshqa company useriga ta'sir qilib bo'lmaydi")
        return

    if payload.op == "create_password_reset_token":
        user_id = _arg_as_positive_int(eff, 0)
        if not get_user_by_id_and_company(user_id, session_company_id):
            raise HTTPException(status_code=403, detail="Faqat o'z company useri uchun reset token yaratish mumkin")
        return

    raise HTTPException(status_code=403, detail=f"{payload.op} operation company admin uchun ruxsat etilmagan")


@router.post("/rpc")
async def call_rpc(
    payload: RpcRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin"})
    _authorize_internal_rpc(session, payload)
    fn = _OPERATIONS.get(payload.op)
    if fn is None:
        raise HTTPException(status_code=404, detail=f"Unknown internal RPC op: {payload.op}")

    auth = session.get("auth") or {}
    actor_user_id = auth.get("user_id")
    actor_role = auth.get("role") or get_session_role(session)
    company_id = get_session_company_id(session)
    audit_payload = _redact_rpc_payload(payload.op, payload.args, payload.kwargs)

    try:
        result = fn(*payload.args, **payload.kwargs)
        write_audit_log(
            event_type=f"rpc.{payload.op}",
            entity_type="rpc",
            entity_id=payload.op,
            company_id=company_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            event_payload={**audit_payload, "success": True},
        )
        return {"result": _serialize(result)}
    except Exception as exc:
        write_audit_log(
            event_type=f"rpc.{payload.op}.error",
            entity_type="rpc",
            entity_id=payload.op,
            company_id=company_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            event_payload={**audit_payload, "error": str(exc)},
        )
        raise HTTPException(status_code=500, detail=f"Internal RPC error in {payload.op}: {exc}") from exc
