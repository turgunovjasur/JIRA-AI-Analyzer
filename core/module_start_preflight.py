"""Run-start preflight for manual and webhook-backed modules.

This layer runs before a persisted run is created. It intentionally avoids JIRA
and GitHub fetching; expensive input collection starts only after required local
configuration is present.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from core.module_errors import ModuleCheck, build_preflight_error_payload

TASK_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")

MODULE_LABELS = {
    "tz_pr_checker": "TZ-PR Checker",
    "testcase_generator": "Test Case Generator",
}

MODULE_SETTINGS_ATTR = {
    "tz_pr_checker": ("tz_pr_checker", "webhook_tz_pr"),
    "testcase_generator": ("testcase_generator", "webhook_testcase"),
}

MODULE_AGENT_FIELDS = {
    "tz_pr_checker": [
        ("agent1_primary_model", "Agent1 Scope Builder primary model"),
        ("agent2_primary_model", "Agent2 Verifier primary model"),
        ("agent3_primary_model", "Agent3 Arbiter primary model"),
    ],
    "testcase_generator": [
        ("agent1_primary_model", "Agent1 Talablar primary model"),
        ("agent2_primary_model", "Agent2 Testcase primary model"),
        ("agent3_primary_model", "Agent3 Audit primary model"),
    ],
}


@dataclass
class StartPreflightResult:
    ok: bool
    module_key: str
    module_label: str
    task_key: str
    company_id: int | None
    user_id: int | None
    checks: list[ModuleCheck]

    def to_error_payload(self) -> dict[str, Any]:
        return build_preflight_error_payload(
            module_key=self.module_key,
            module_label=self.module_label,
            task_key=self.task_key,
            checks=self.checks,
        )


def run_start_preflight(
    *,
    module_key: str,
    task_key: str,
    company_id: int | None,
    user_id: int | None,
    source: str = "manual",
) -> StartPreflightResult:
    normalized_task_key = str(task_key or "").strip().upper()
    module_label = MODULE_LABELS.get(module_key, module_key)
    checks: list[ModuleCheck] = []

    checks.append(_check_task_key(normalized_task_key))

    user_id, company_id, scope_check = _resolve_scope(user_id=user_id, company_id=company_id)
    checks.append(scope_check)

    if company_id is not None:
        checks.append(_check_module_access(company_id, module_key, module_label))
    else:
        checks.append(ModuleCheck(
            id="module_access",
            label="Company module access",
            status="skipped",
            message="Company scope topilmagani uchun modul ruxsati tekshirilmadi.",
        ))

    if scope_check.status == "fail":
        checks.append(ModuleCheck(
            id="api_credentials",
            label="API credentials",
            status="skipped",
            message="Scope xatosi sabab API kalitlar tekshirilmadi.",
        ))
        checks.extend(_skipped_agent_model_checks(module_key, "Scope xatosi sabab agent modellari tekshirilmadi."))
    else:
        checks.append(_check_credentials(user_id=user_id, company_id=company_id, source=source))
        checks.extend(_check_agent_primary_models(
            module_key=module_key,
            user_id=user_id,
            company_id=company_id,
        ))

    ok = all(check.status != "fail" for check in checks)
    return StartPreflightResult(
        ok=ok,
        module_key=module_key,
        module_label=module_label,
        task_key=normalized_task_key,
        company_id=company_id,
        user_id=user_id,
        checks=checks,
    )


def _check_task_key(task_key: str) -> ModuleCheck:
    if TASK_KEY_RE.match(task_key):
        return ModuleCheck(
            id="task_key_format",
            label="JIRA task key format",
            status="ok",
            message=f"{task_key} formati to'g'ri.",
        )
    return ModuleCheck(
        id="task_key_format",
        label="JIRA task key format",
        status="fail",
        code="INPUT_TASK_KEY_INVALID",
        message="Task key formati noto'g'ri. Masalan: DEV-1234.",
        action="Task key formatini tekshiring.",
        blocking=True,
    )


def _resolve_scope(*, user_id: int | None, company_id: int | None) -> tuple[int | None, int | None, ModuleCheck]:
    if user_id is not None and company_id is None:
        try:
            from utils.auth.auth_db import get_user_by_id

            user_row = get_user_by_id(int(user_id)) or {}
            raw_company_id = user_row.get("company_id")
            company_id = int(raw_company_id) if raw_company_id not in (None, "") else None
        except Exception:
            company_id = None

        if company_id is None:
            return user_id, company_id, ModuleCheck(
                id="customer_scope",
                label="Customer scope",
                status="fail",
                code="CUSTOMER_SCOPE_MISSING",
                message="User uchun company scope topilmadi.",
                action="Runni aniq company scope bilan boshlang.",
                blocking=True,
            )

    if user_id is not None or company_id is not None:
        return user_id, company_id, ModuleCheck(
            id="customer_scope",
            label="Customer scope",
            status="ok",
            message=(
                f"company_id={company_id or 'none'}, "
                f"user_id={user_id or 'none'}"
            ),
        )

    return user_id, company_id, ModuleCheck(
        id="customer_scope",
        label="Customer scope",
        status="fail",
        code="CUSTOMER_SCOPE_MISSING",
        message="Run uchun company yoki user scope topilmadi.",
        action="Runni customer/company scope bilan boshlang.",
        blocking=True,
    )


def _check_module_access(company_id: int, module_key: str, module_label: str) -> ModuleCheck:
    try:
        from utils.auth.auth_db import get_effective_company_modules

        modules = get_effective_company_modules(int(company_id)) or {}
        if modules.get(module_key, False):
            return ModuleCheck(
                id="module_access",
                label="Company module access",
                status="ok",
                message=f"{module_label} company uchun yoqilgan.",
            )
        return ModuleCheck(
            id="module_access",
            label="Company module access",
            status="fail",
            code="MODULE_ACCESS_DISABLED",
            message=f"{module_label} bu company uchun yoqilmagan.",
            action="Company module access yoki subscription holatini tekshiring.",
            blocking=True,
        )
    except Exception as exc:
        return ModuleCheck(
            id="module_access",
            label="Company module access",
            status="fail",
            code="MODULE_ACCESS_CHECK_FAILED",
            message=f"Company module access tekshiruvi xato berdi: {exc}",
            action="Company module/subscription sozlamalarini tekshiring.",
            blocking=True,
        )


def _check_credentials(*, user_id: int | None, company_id: int | None, source: str) -> ModuleCheck:
    try:
        if user_id is not None:
            from utils.auth.auth_db import get_user_credentials_for_service

            get_user_credentials_for_service(int(user_id))
        elif company_id is not None:
            from utils.auth.auth_db import get_company_webhook_credentials

            get_company_webhook_credentials(int(company_id))
        else:
            raise RuntimeError("company_id yoki user_id ko'rsatilmagan")
        return ModuleCheck(
            id="api_credentials",
            label="API credentials",
            status="ok",
            message="JIRA, GitHub va Gemini API kalitlari topildi.",
        )
    except Exception as exc:
        scope_label = "manual" if str(source or "").lower() == "manual" else "webhook"
        return ModuleCheck(
            id="api_credentials",
            label="API credentials",
            status="fail",
            code="CONFIG_API_CREDENTIALS_MISSING",
            message=str(exc) or "API credentials tekshiruvi xato berdi.",
            action=f"{scope_label} API key sozlamalarini to'ldiring.",
            blocking=True,
        )


def _check_agent_primary_models(
    *,
    module_key: str,
    user_id: int | None,
    company_id: int | None,
) -> list[ModuleCheck]:
    settings = _load_module_settings(module_key=module_key, user_id=user_id, company_id=company_id)
    checks: list[ModuleCheck] = []
    for field_name, label in MODULE_AGENT_FIELDS.get(module_key, []):
        value = str(getattr(settings, field_name, "") or "").strip() if settings is not None else ""
        if value:
            checks.append(ModuleCheck(
                id=field_name,
                label=label,
                status="ok",
                message=value,
            ))
        else:
            checks.append(ModuleCheck(
                id=field_name,
                label=label,
                status="fail",
                code="CONFIG_AI_MODEL_MISSING",
                message=f"{label} sozlanmagan.",
                action="Modul Agent modellari yoki Super Admin global AI defaultlarini sozlang.",
                blocking=True,
            ))
    return checks


def _skipped_agent_model_checks(module_key: str, message: str) -> list[ModuleCheck]:
    return [
        ModuleCheck(
            id=field_name,
            label=label,
            status="skipped",
            message=message,
        )
        for field_name, label in MODULE_AGENT_FIELDS.get(module_key, [])
    ]


def _load_module_settings(
    *,
    module_key: str,
    user_id: int | None,
    company_id: int | None,
) -> Any:
    standalone_attr, webhook_attr = MODULE_SETTINGS_ATTR.get(module_key, (module_key, module_key))
    try:
        if user_id is not None and company_id is not None:
            from config.app_settings import get_app_settings_for_user

            return getattr(get_app_settings_for_user(int(user_id), int(company_id)), standalone_attr)
        if company_id is not None:
            from config.app_settings import get_app_settings_for_company

            return getattr(get_app_settings_for_company(int(company_id)), webhook_attr)
        from config.app_settings import get_app_settings

        return getattr(get_app_settings(), standalone_attr)
    except Exception:
        return None
