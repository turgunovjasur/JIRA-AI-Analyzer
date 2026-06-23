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
    # Global (QA ASSISTANT) Gemini kvota holati — UI banner/qolgan urinish uchun.
    # {"using_global": bool, "used", "limit", "remaining", "exhausted"} yoki {"using_global": False}.
    quota: dict[str, Any] | None = None

    def to_error_payload(self) -> dict[str, Any]:
        payload = build_preflight_error_payload(
            module_key=self.module_key,
            module_label=self.module_label,
            task_key=self.task_key,
            checks=self.checks,
        )
        if self.quota is not None:
            payload["gemini_quota"] = self.quota
        return payload


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

    quota: dict[str, Any] | None = None
    if scope_check.status == "fail":
        checks.append(ModuleCheck(
            id="api_credentials",
            label="API credentials",
            status="skipped",
            message="Scope xatosi sabab API kalitlar tekshirilmadi.",
        ))
        checks.extend(_skipped_agent_model_checks(module_key, "Scope xatosi sabab agent modellari tekshirilmadi."))
    else:
        cred_check, readiness = _resolve_credentials(
            module_key=module_key, user_id=user_id, company_id=company_id, source=source,
        )
        checks.append(cred_check)
        checks.extend(_check_agent_primary_models(
            module_key=module_key,
            user_id=user_id,
            company_id=company_id,
        ))
        # Global (QA ASSISTANT) kalit kvotasi — faqat credential OK va manba "global" bo'lsa.
        if (
            cred_check.status != "fail"
            and readiness
            and readiness.get("gemini_source") == "global"
            and company_id is not None
        ):
            quota_check, quota = _check_global_quota(module_key=module_key, company_id=int(company_id))
            if quota_check is not None:
                checks.append(quota_check)
        else:
            quota = {"using_global": False}

    ok = all(check.status != "fail" for check in checks)
    return StartPreflightResult(
        ok=ok,
        module_key=module_key,
        module_label=module_label,
        task_key=normalized_task_key,
        company_id=company_id,
        user_id=user_id,
        checks=checks,
        quota=quota,
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


def _resolve_credentials(
    *, module_key: str, user_id: int | None, company_id: int | None, source: str,
) -> tuple[ModuleCheck, dict | None]:
    """Modul-bilan-bog'liq credential tekshiruvi (RAISE qilmaydi).

    - testcase_generator: JIRA majburiy (GitHub kerak EMAS).
    - tz_pr_checker: JIRA + GitHub majburiy.
    - Ikkalasi ham: Gemini kalit (o'z/company/global) bo'lishi shart.

    Qaytaradi: (ModuleCheck, readiness) — readiness'da gemini_source bor (kvota uchun).
    """
    try:
        from utils.auth.auth_db import get_credential_readiness

        readiness = get_credential_readiness(
            int(company_id) if company_id is not None else None,
            int(user_id) if user_id is not None else None,
        )
    except Exception as exc:
        return (
            ModuleCheck(
                id="api_credentials",
                label="API credentials",
                status="fail",
                code="CONFIG_API_CREDENTIALS_MISSING",
                message=str(exc) or "API credentials tekshiruvi xato berdi.",
                action="API key sozlamalarini to'ldiring.",
                blocking=True,
            ),
            None,
        )

    jira_ok = bool(readiness.get("jira_ok"))
    github_ok = bool(readiness.get("github_ok"))
    gemini_source = readiness.get("gemini_source") or "none"

    if module_key == "testcase_generator":
        if not jira_ok:
            return (
                ModuleCheck(
                    id="api_credentials", label="API credentials", status="fail",
                    code="CONFIG_API_CREDENTIALS_MISSING",
                    message="Testcase moduli ishlashi uchun Jira malumotlarini kiriting!",
                    action="Sozlamalar → API Kalitlar: JIRA Server, Email va API Token kiriting.",
                    blocking=True,
                ),
                readiness,
            )
    else:  # tz_pr_checker
        if not jira_ok or not github_ok:
            return (
                ModuleCheck(
                    id="api_credentials", label="API credentials", status="fail",
                    code="CONFIG_API_CREDENTIALS_MISSING",
                    message="Checker ishlashi uchun jira va github malumotlarini kiriting",
                    action="Sozlamalar → API Kalitlar: JIRA va GitHub ma'lumotlarini kiriting.",
                    blocking=True,
                ),
                readiness,
            )

    if gemini_source == "none":
        return (
            ModuleCheck(
                id="api_credentials", label="API credentials", status="fail",
                code="CONFIG_API_CREDENTIALS_MISSING",
                message="Gemini API kalit topilmadi. O'zingizning Gemini API kalitingizni kiriting.",
                action="Sozlamalar → API Kalitlar: Gemini API kalitini kiriting.",
                blocking=True,
            ),
            readiness,
        )

    return (
        ModuleCheck(
            id="api_credentials", label="API credentials", status="ok",
            message="Kerakli API kalitlari topildi.",
        ),
        readiness,
    )


def _check_global_quota(*, module_key: str, company_id: int) -> tuple[ModuleCheck | None, dict]:
    """Global (QA ASSISTANT) kalit kvotasini tekshirish. Tugagan bo'lsa fail ModuleCheck.

    Qaytaradi: (ModuleCheck yoki None, quota_dict). quota_dict UI'ga uzatiladi.
    """
    try:
        from utils.database.quota_db import get_global_quota_status

        status = get_global_quota_status(int(company_id), module_key)
    except Exception:
        # Kvota o'qib bo'lmasa — bloklamaymiz (fail-open), faqat banner ko'rsatilmaydi.
        return None, {"using_global": True}

    quota = {"using_global": True, **status}
    if status.get("exhausted"):
        return (
            ModuleCheck(
                id="gemini_quota", label="QA ASSISTANT bepul kvota", status="fail",
                code="QUOTA_GLOBAL_FREE_EXHAUSTED",
                message=(
                    f"Imtiyoz tugadi — QA ASSISTANT bepul kvotasi ({status.get('limit', '')} ta) ishlatildi. "
                    "O'zingizning Gemini API kalitingizni kiriting."
                ),
                action="Sozlamalar → API Kalitlar: o'z Gemini API kalitingizni kiriting.",
                blocking=True,
            ),
            quota,
        )
    return None, quota


def get_module_start_status(
    *, module_key: str, company_id: int | None, user_id: int | None = None,
) -> dict[str, Any]:
    """Modul ochilganda (run'dan oldin) credential + kvota holatini qaytaradi.

    Run gate (`run_start_preflight`) bilan AYNAN bir xil mantiq, lekin task_key
    talab qilmaydi. Frontend banner + run tugmasini bloklash uchun.

    Qaytaradi: {module_key, blocked, level, message, gemini_source, gemini_quota}.
    """
    cred_check, readiness = _resolve_credentials(
        module_key=module_key, user_id=user_id, company_id=company_id, source="manual",
    )
    quota: dict[str, Any] = {"using_global": False}
    quota_check: ModuleCheck | None = None
    if (
        cred_check.status != "fail"
        and readiness
        and readiness.get("gemini_source") == "global"
        and company_id is not None
    ):
        quota_check, quota = _check_global_quota(module_key=module_key, company_id=int(company_id))

    if cred_check.status == "fail":
        message, level, blocked = cred_check.message, "error", True
    elif quota_check is not None and quota_check.status == "fail":
        message, level, blocked = quota_check.message, "error", True
    elif quota.get("using_global"):
        remaining = quota.get("remaining", 0)
        limit = quota.get("limit", 0)
        message = (
            "O'zingizning Gemini API kalitingizni kiriting — hozir QA ASSISTANT bergan "
            f"kalitdan foydalanyapsiz. Bu modul uchun yana {remaining}/{limit} tekin urinish bor."
        )
        level, blocked = "warning", False
    else:
        message, level, blocked = "", "info", False

    return {
        "module_key": module_key,
        "blocked": blocked,
        "level": level,
        "message": message,
        "gemini_source": (readiness.get("gemini_source") if readiness else "none"),
        "gemini_quota": quota,
    }


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
