"""Public facade for the run-based multi-agent TZ-PR checker."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from services.checkers.tzpr_constants import (
    AGENT_SEQUENCE,
    EXECUTION_MODE_MULTI,
    build_agent_sequence,
)
from services.checkers.tzpr_lifecycle import is_stalled_multi_agent_snapshot
from services.checkers.tzpr_orchestrator import _TZPRMultiAgentExecutor
from utils.database.checker_run_db import (
    create_checker_run_record,
    get_checker_run_snapshot,
)

_log = logging.getLogger(__name__)
_MODULE_KEY = "tz_pr_checker"


def _global_quota_status(company_id: int | None, user_id: int | None) -> tuple[bool, dict | None]:
    """Run global (QA ASSISTANT) kalitidan foydalanadimi va kvota holati.

    Qaytaradi: (is_global, status). is_global=True bo'lsa run platforma kalitini
    ishlatadi va kvota hisobga olinishi kerak. status — {used, limit, remaining,
    exhausted} yoki None. O'qish xatosida (False, None) — legit runni bloklamaymiz.
    """
    if company_id is None:
        return False, None
    try:
        from utils.auth.auth_db import get_credential_readiness
        readiness = get_credential_readiness(
            int(company_id), int(user_id) if user_id is not None else None
        )
    except Exception:
        return False, None
    if (readiness or {}).get("gemini_source") != "global":
        return False, None
    try:
        from utils.database.quota_db import get_global_quota_status
        return True, get_global_quota_status(int(company_id), _MODULE_KEY)
    except Exception:
        return True, None


def _increment_global_quota_safe(company_id: int | None) -> None:
    if company_id is None:
        return
    try:
        from utils.database.quota_db import increment_global_quota
        q = increment_global_quota(int(company_id), _MODULE_KEY)
        _log.info("quota incremented [%s] company=%s remaining=%s", _MODULE_KEY, company_id, (q or {}).get("remaining"))
    except Exception:
        _log.warning("increment_global_quota failed silently [%s]", _MODULE_KEY)


_QUOTA_EXHAUSTED_MESSAGE = (
    "QA ASSISTANT bepul kvota tugadi — tahlil qilinmadi. "
    "Sozlamalar → API Kalitlar bo'limida o'zingizning Gemini API kalitingizni kiriting."
)


def create_multi_agent_run(
    *,
    task_key: str,
    company_id: int | None,
    user_id: int | None,
    source: str,
    output_profile: str,
    show_full_diff: bool,
    use_smart_patch: bool | None,
    max_files: int | None,
    task_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_id = f"tzpr-{uuid.uuid4().hex}"
    agents = AGENT_SEQUENCE
    try:
        from config.app_settings import get_app_settings, get_app_settings_for_company, get_app_settings_for_user

        if user_id is not None and company_id is not None:
            checker_settings = get_app_settings_for_user(user_id, company_id).tz_pr_checker
        elif company_id is not None:
            checker_settings = get_app_settings_for_company(company_id).webhook_tz_pr
        else:
            checker_settings = get_app_settings().tz_pr_checker
        agents = build_agent_sequence(checker_settings)
    except Exception:
        agents = AGENT_SEQUENCE
    request_payload = {
        "task_key": task_key,
        "output_profile": output_profile,
        "show_full_diff": show_full_diff,
        "use_smart_patch": use_smart_patch,
        "max_files": max_files,
        "execution_mode": EXECUTION_MODE_MULTI,
    }
    try:
        from core.prompt_registry import get_prompt_versions_for

        request_payload["prompt_versions"] = get_prompt_versions_for("checker")
    except Exception:
        _log.warning("prompt_versions yozilmadi (checker run)", exc_info=True)
    if isinstance(task_details, dict) and task_details:
        request_payload["task_details"] = task_details

    return create_checker_run_record(
        run_id=run_id,
        task_key=task_key,
        company_id=company_id,
        user_id=user_id,
        source=source,
        execution_mode=EXECUTION_MODE_MULTI,
        requested_output_profile=output_profile,
        request_payload=request_payload,
        agents=agents,
    )


def execute_multi_agent_run(run_id: str, *, increment_quota: bool = False) -> dict[str, Any] | None:
    """UI yo'li: snapshot dict qaytaradi.

    Kvota hisobi endi SOURCE-DRIVEN — `increment_quota` flag'iga emas, running
    haqiqiy Gemini manbasiga (global bo'lsa) qarab increment qilinadi. Shu sabab
    queue rejimidagi (worker orqali) UI runlari ham kvotani sarflaydi (ilgari
    worker flag'ni uzatmagani uchun increment yo'qolardi). Flag backward-compat
    uchun qoldirilgan, lekin qaror manbadan olinadi.
    """
    snapshot = get_checker_run_snapshot(run_id)
    if not snapshot:
        raise RuntimeError(f"Checker run topilmadi: {run_id}")
    company_id = snapshot.get("company_id")
    user_id = snapshot.get("user_id")
    is_global, quota = _global_quota_status(company_id, user_id)

    executor = _TZPRMultiAgentExecutor(snapshot)
    if is_global and (quota or {}).get("exhausted"):
        blocked = executor._build_blocked_result(_QUOTA_EXHAUSTED_MESSAGE)
        try:
            executor._mark_run_finished("blocked", blocked, _QUOTA_EXHAUSTED_MESSAGE)
        except Exception:
            pass
        return blocked

    result = executor.run()
    if is_global and (result or {}).get("run_state") == "completed":
        _increment_global_quota_safe(company_id)
    return result


def run_multi_agent_for_webhook(run_id: str):
    """Run'ni bajaradi va JONLI `TZPRAnalysisResult` obyektini qaytaradi.

    UI yo'li (`execute_multi_agent_run`) snapshot dict qaytaradi — uni brauzer
    o'qiydi. Webhook esa natijani JIRA comment formatter'iga (ichki dataclass'lar
    bilan) uzatadi, shuning uchun asdict dict emas, jonli obyekt kerak.
    Engine bir xil — faqat qaytariladigan ko'rinish farq qiladi.

    Webhook yo'lida UI preflight YO'Q — shuning uchun global (QA ASSISTANT) kvota
    tekshiruvi shu yerda: kvota tugagan bo'lsa run ishga tushmaydi (platforma
    kalitini sarflamaslik uchun), muvaffaqiyatli global run esa kvotani +1 qiladi.
    """
    snapshot = get_checker_run_snapshot(run_id)
    if not snapshot:
        raise RuntimeError(f"Checker run topilmadi: {run_id}")
    company_id = snapshot.get("company_id")
    user_id = snapshot.get("user_id")
    is_global, quota = _global_quota_status(company_id, user_id)

    executor = _TZPRMultiAgentExecutor(snapshot)
    if is_global and (quota or {}).get("exhausted"):
        blocked = executor._build_blocked_result(_QUOTA_EXHAUSTED_MESSAGE)
        try:
            executor._mark_run_finished("blocked", blocked, _QUOTA_EXHAUSTED_MESSAGE)
        except Exception:
            pass
        return executor.final_result_obj

    executor.run()
    result_obj = executor.final_result_obj
    if is_global and getattr(result_obj, "run_state", None) == "completed":
        _increment_global_quota_safe(company_id)
    return result_obj


def is_stalled_multi_agent_run(snapshot: dict[str, Any] | None) -> bool:
    return is_stalled_multi_agent_snapshot(snapshot)


def recover_stalled_multi_agent_run(run_id: str) -> dict[str, Any] | None:
    snapshot = get_checker_run_snapshot(run_id)
    if not is_stalled_multi_agent_run(snapshot):
        return snapshot
    executor = _TZPRMultiAgentExecutor(snapshot or {})
    return executor.recover_stalled_run()
