"""
Auth configuration helper functions.

`auth_db.py` ichidagi credential composition va webhook config shaping
logikalarini ajratish uchun yordamchi modul.
"""
from __future__ import annotations

import json
from typing import Callable, Dict, List


def build_company_gemini_keys(company_settings: Dict) -> list:
    keys = []
    k1 = (company_settings.get("gemini_api_key_1") or "").strip()
    k2 = (company_settings.get("gemini_api_key_2") or "").strip()
    if k1:
        keys.append(k1)
    if k2:
        keys.append(k2)
    return keys


def build_company_credentials(
    company_id: int,
    company_settings: Dict,
    parse_figma_tokens: Callable[[object], list],
    get_global_gemini_defaults: Callable[[], dict],
) -> dict:
    missing = []

    jira_server = (company_settings.get("jira_server") or "").strip()
    jira_email = (company_settings.get("jira_email") or "").strip()
    jira_token = (company_settings.get("jira_token") or "").strip()
    github_token = (company_settings.get("github_token") or "").strip()
    github_org = (company_settings.get("github_org") or "").strip()
    figma_token = (company_settings.get("figma_token") or "").strip()
    figma_tokens = parse_figma_tokens(company_settings.get("figma_tokens"))
    if not figma_tokens and figma_token:
        figma_tokens = [{"name": "", "token": figma_token}]
    gemini_model = (company_settings.get("gemini_model") or "").strip()
    gemini_keys = build_company_gemini_keys(company_settings)
    if not gemini_keys:
        global_defaults = get_global_gemini_defaults() or {}
        g1 = (global_defaults.get("api_key_1") or "").strip()
        g2 = (global_defaults.get("api_key_2") or "").strip()
        gemini_keys = [key for key in [g1, g2] if key]
        if not gemini_model:
            gemini_model = (global_defaults.get("model") or "").strip()
    # SaaS qoidasi: Gemini faqat company -> super admin default tartibi bilan olinadi.
    # Env fallback ishlatilmaydi.
    if not jira_email:
        missing.append("JIRA Email")
    if not jira_server:
        missing.append("JIRA Server")
    if not jira_token:
        missing.append("JIRA API Token")
    if not github_token:
        missing.append("GitHub Token")
    if not github_org:
        missing.append("GitHub Organization")
    if not gemini_keys:
        missing.append("Gemini API Key (company yoki super admin default)")

    if missing:
        raise RuntimeError(
            f"Kompaniya (id={company_id}) API kalitlari to'liq emas: "
            f"{', '.join(missing)}. Sozlamalar -> API Kalitlar bo'limini to'ldiring."
        )

    return {
        "jira_server": jira_server,
        "jira_email": jira_email,
        "jira_token": jira_token,
        "github_token": github_token,
        "github_org": github_org,
        "figma_token": figma_token,
        "figma_tokens": figma_tokens,
        "gemini_keys": gemini_keys,
        "gemini_model": gemini_model or None,
    }


def build_company_webhook_credentials(
    company_id: int,
    company_settings: Dict,
    parse_figma_tokens: Callable[[object], list],
    get_global_gemini_defaults: Callable[[], dict],
) -> dict:
    missing = []

    jira_server = (company_settings.get("webhook_jira_server") or company_settings.get("jira_server") or "").strip()
    jira_email = (company_settings.get("webhook_jira_email") or company_settings.get("jira_email") or "").strip()
    jira_token = (company_settings.get("webhook_jira_token") or company_settings.get("jira_token") or "").strip()
    github_token = (company_settings.get("webhook_github_token") or company_settings.get("github_token") or "").strip()
    github_org = (company_settings.get("webhook_github_org") or company_settings.get("github_org") or "").strip()
    figma_token = (company_settings.get("webhook_figma_token") or company_settings.get("figma_token") or "").strip()
    figma_tokens = parse_figma_tokens(company_settings.get("webhook_figma_tokens"))
    if not figma_tokens:
        figma_tokens = parse_figma_tokens(company_settings.get("figma_tokens"))
    if not figma_tokens and figma_token:
        figma_tokens = [{"name": "", "token": figma_token}]
    gemini_model = (company_settings.get("webhook_gemini_model") or company_settings.get("gemini_model") or "").strip()
    gemini_k1 = (company_settings.get("webhook_gemini_api_key_1") or company_settings.get("gemini_api_key_1") or "").strip()
    gemini_k2 = (company_settings.get("webhook_gemini_api_key_2") or company_settings.get("gemini_api_key_2") or "").strip()
    gemini_keys = [k for k in [gemini_k1, gemini_k2] if k]
    if not gemini_keys:
        global_defaults = get_global_gemini_defaults() or {}
        g1 = (global_defaults.get("api_key_1") or "").strip()
        g2 = (global_defaults.get("api_key_2") or "").strip()
        gemini_keys = [key for key in [g1, g2] if key]
        if not gemini_model:
            gemini_model = (global_defaults.get("model") or "").strip()
    # SaaS qoidasi: Gemini faqat company/webhook -> super admin default tartibi bilan olinadi.
    # Env fallback ishlatilmaydi.
    if not jira_email:
        missing.append("JIRA Email")
    if not jira_server:
        missing.append("JIRA Server")
    if not jira_token:
        missing.append("JIRA API Token")
    if not github_token:
        missing.append("GitHub Token")
    if not github_org:
        missing.append("GitHub Organization")
    if not gemini_keys:
        missing.append("Gemini API Key (company/webhook yoki super admin default)")

    if missing:
        raise RuntimeError(
            f"Kompaniya (id={company_id}) webhook API kalitlari to'liq emas: "
            f"{', '.join(missing)}. Sozlamalar -> JIRA Webhook -> API Kalitlar bo'limini to'ldiring."
        )

    return {
        "jira_server": jira_server,
        "jira_email": jira_email,
        "jira_token": jira_token,
        "github_token": github_token,
        "github_org": github_org,
        "figma_token": figma_token,
        "figma_tokens": figma_tokens,
        "gemini_keys": gemini_keys,
        "gemini_model": gemini_model or None,
    }


def build_user_credentials_for_service(
    user_id: int,
    user_credentials: Dict,
    parse_figma_tokens: Callable[[object], list],
    get_global_gemini_defaults: Callable[[], dict],
    get_user_by_id: Callable[[int], Dict | None],
    get_company_settings: Callable[[int], Dict],
) -> dict:
    user_row = get_user_by_id(user_id)
    company_settings = get_company_settings(user_row["company_id"]) if user_row else {}

    # SaaS qoidasi: userlar JIRA/GitHub/Figma credentiallarini company (admin) sozlamasidan oladi.
    jira_server = (company_settings.get("jira_server") or "").strip()
    jira_email = (company_settings.get("jira_email") or "").strip()
    jira_token = (company_settings.get("jira_token") or "").strip()
    github_token = (company_settings.get("github_token") or "").strip()
    github_org = (company_settings.get("github_org") or "").strip()
    figma_token = (company_settings.get("figma_token") or "").strip()
    figma_tokens = parse_figma_tokens(company_settings.get("figma_tokens"))
    if not figma_tokens and figma_token:
        figma_tokens = [{"name": "", "token": figma_token}]
    gemini_k1 = (user_credentials.get("gemini_api_key_1") or "").strip()
    gemini_k2 = (user_credentials.get("gemini_api_key_2") or "").strip()
    gemini_model = (user_credentials.get("gemini_model") or "").strip()

    if not gemini_k1 and not gemini_k2:
        gemini_k1 = (company_settings.get("gemini_api_key_1") or "").strip()
        gemini_k2 = (company_settings.get("gemini_api_key_2") or "").strip()
        if not gemini_model:
            gemini_model = (company_settings.get("gemini_model") or "").strip()

    if not gemini_k1 and not gemini_k2:
        glb = get_global_gemini_defaults() or {}
        gemini_k1 = (glb.get("api_key_1") or "").strip()
        gemini_k2 = (glb.get("api_key_2") or "").strip()
        if not gemini_model:
            gemini_model = (glb.get("model") or "").strip()

    missing = []
    if not jira_server:
        missing.append("JIRA Server")
    if not jira_email:
        missing.append("JIRA Email")
    if not jira_token:
        missing.append("JIRA API Token")
    if not github_token:
        missing.append("GitHub Token")
    if not github_org:
        missing.append("GitHub Organization")

    if missing:
        raise RuntimeError(
            f"API kalitlar to'liq emas: {', '.join(missing)}. "
            f"Sozlamalar -> API Kalitlar bo'limini to'ldiring."
        )

    if not gemini_k1 and not gemini_k2:
        raise RuntimeError(
            "Gemini API Key topilmadi. Profilingizga kiriting yoki company admin/super admin defaultini sozlang."
        )

    return {
        "jira_server": jira_server,
        "jira_email": jira_email,
        "jira_token": jira_token,
        "github_token": github_token,
        "github_org": github_org,
        "figma_token": figma_token,
        "figma_tokens": figma_tokens,
        "gemini_keys": [k for k in [gemini_k1, gemini_k2] if k],
        "gemini_model": gemini_model or None,
    }


def build_company_webhook_config(company_settings: Dict) -> Dict:
    return {
        "webhook_project_keys": company_settings.get("webhook_project_keys", ""),
        "webhook_trigger_status": company_settings.get("webhook_trigger_status", ""),
        "webhook_trigger_aliases": company_settings.get("webhook_trigger_aliases", ""),
        "webhook_return_status": company_settings.get("webhook_return_status", ""),
        "webhook_allowed_issue_types": company_settings.get("webhook_allowed_issue_types", ""),
        "webhook_excluded_assignees": company_settings.get("webhook_excluded_assignees", ""),
        "webhook_auto_return_enabled": bool(company_settings.get("webhook_auto_return_enabled", 0)),
        "webhook_return_threshold": int(company_settings.get("webhook_return_threshold") or 60),
    }


def validate_company_webhook_config_shape(config: Dict) -> List[str]:
    errors = []
    if not config.get("webhook_project_keys", "").strip():
        errors.append("JIRA Project Key(lar) kiritilishi shart (masalan: DEV, QA)")
    if not config.get("webhook_trigger_status", "").strip():
        errors.append("Trigger Status kiritilishi shart (masalan: Ready to Test)")
    return errors


def parse_webhook_module_settings(raw: str, module_key: str | None = None) -> Dict:
    try:
        all_settings = json.loads(raw) if raw else {}
    except (json.JSONDecodeError, TypeError):
        all_settings = {}
    if module_key:
        return all_settings.get(module_key, {})
    return all_settings
