"""
Service Runner Module - Servis ishga tushirish logikasi
=======================================================

Bu modul webhook oqimining asosiy biznes logikasini o'z ichiga oladi:

Service1 (TZ-PR Checker):
  - JIRA task TZ + GitHub PR → AI tahlil → moslik bali → JIRA comment
  - Muvaffaqiyatsiz bo'lsa: xato turi bo'yicha 'blocked' | 'error' holat
  - Score past bo'lsa: avtomatik Return (auto-return) + DB 'returned' holat

Service2 (Testcase Generator):
  - Service1 done/skip bo'lgandan keyingina ishlaydi
  - TZ + PR (ixtiyoriy) → AI testcaselar → JIRA comment
  - PR topilmasa: TZ-only fallback rejim

Ikkala servis ham DB'da holat saqlaydi va xatolikda mos holat qo'yadi.
"""
from typing import Any

from config.app_settings import get_app_settings, TZPRCheckerSettings
from core.logger import get_logger
from core.constants import WARN_LOW_SCORE, WARN_AI_TIMEOUT, ERR_UNKNOWN, RECHECK_REASONS
from utils.database.task_db import (
    get_task, mark_returned, mark_returned_pr_not_merged,
    set_service1_done, set_service1_error, set_service1_blocked,
    set_service2_done, set_service2_error, set_service2_blocked,
    set_return_reason
)
from services.webhook.error_handler import _error_type_to_reason_code

log = get_logger("webhook.service_runner")


async def check_tz_pr_and_comment(task_key: str, new_status: str, company_id: int = None) -> None:
    """
    Service1: TZ-PR mosligini tekshirish va JIRA'ga natija comment yozish.

    Bu funksiya FastAPI BackgroundTasks orqali asinxron ishga tushiriladi.
    Webhook endpoint tomonidan to'g'ridan yoki queue_manager orqali chaqiriladi.

    Ishlash tartibi:
    1. DB'da service1_status='done' bo'lsa — allaqachon bajarilgan, skip
    2. _detect_recheck() — task qaytarilibdi, keyin yana trigger statusga tushgan aniqlash
    3. TZPRService.analyze_task() — JIRA TZ + GitHub PR → Gemini AI tahlil (7 bosqich)
    4. Muvaffaqiyatsiz → xato turi aniqlash:
       - 'ai_timeout' → service1_status='blocked', retry scheduler kutib turadi
       - 'pr_not_found' → service1_status='error', keep_service2_pending=True
         (Service2 baribir ishlashi mumkin — TZ-only rejimda)
       - 'unknown' → service1_status='error', service2 ham to'xtatiladi
    5. Muvaffaqiyatli → ADF format comment, keyin oddiy format fallback
    6. service1_status='done', compliance_score DB'ga saqlandi
    7. Score < threshold → _handle_auto_return() → task_status='returned'

    Args:
        task_key: JIRA task identifikatori (masalan: 'DEV-1234')
        new_status: JIRA'dagi yangi status (masalan: 'READY TO TEST')
                    Comment'da va error xabarlarida ko'rinadi

    Returns:
        None. Natija JIRA comment va DB holat yangilanishi orqali qaytariladi.

    Side Effects:
        - JIRA'ga comment yozadi (ADF yoki oddiy format)
        - DB'da service1_status yangilanadi: 'pending' → 'done' | 'error' | 'blocked'
        - DB'da compliance_score saqlanadi (agar muvaffaqiyatli)
        - Score past bo'lsa: JIRA task statusini return_status'ga o'zgartiradi
        - Score past bo'lsa: DB'da task_status='returned' qo'yiladi
    """
    try:
        log.service_running(task_key, "service_1")

        # DB holatini tekshirish — ikki marta ishlamaslik uchun
        task_db = get_task(task_key)
        service1_status = task_db.get('service1_status', 'pending') if task_db else 'pending'

        if service1_status == 'done':
            log.info(f"[{task_key}] SKIP -> service_1 allaqachon bajarilgan, qayta ishlanmaydi")
            return

        if company_id is None:
            log.error(f"[{task_key}] company_id yo'q — service_1 ishga tushmaydi")
            return

        from config.app_settings import get_app_settings_for_company
        app_settings = get_app_settings_for_company(company_id)
        settings = app_settings.webhook_tz_pr

        from services.webhook.jira_webhook_handler import get_adf_formatter
        from services.webhook.error_handler import (
            _classify_error, _write_success_comment,
            _write_error_comment, _write_critical_error
        )
        from services.checkers.tz_pr_checker import TZPRService
        from utils.jira.jira_comment_writer import JiraCommentWriter
        from utils.auth.auth_db import get_company_credentials

        creds = get_company_credentials(company_id)  # kalit yo'q bo'lsa RuntimeError
        tz_pr_service = TZPRService(company_id=company_id)
        comment_writer = JiraCommentWriter(
            server=creds['jira_server'],
            email=creds['jira_email'],
            token=creds['jira_token'],
        )

        adf_formatter = get_adf_formatter()

        # return_reason: oldingi qaytarilish sababi (WARN_LOW_SCORE, WARN_MIN_TZ, ...)
        return_reason = (task_db or {}).get('return_reason')
        if return_reason:
            log.info(f"[{task_key}] RE-CHECK -> return_reason={return_reason}")

        # 1. TZ-PR tahlil qilish (AI + GitHub + JIRA)
        result = tz_pr_service.analyze_task(task_key, return_reason=return_reason)

        if not result.success:
            error_msg = result.error_message
            error_type = _classify_error(error_msg)
            log.service_error(task_key, "service_1", error_msg)

            reason_code = _error_type_to_reason_code(error_type)
            if error_type == 'ai_timeout':
                # Task bloklanadi — retry scheduler keyinroq qayta urinadi
                retry_minutes = get_app_settings(force_reload=False).queue.blocked_retry_delay
                set_service1_blocked(task_key, error_msg, retry_minutes)
                set_return_reason(task_key, reason_code)
                log.info(f"[{task_key}] Service1 BLOCKED: {retry_minutes} min [{reason_code}]")
                await _write_error_comment(
                    task_key, error_msg, comment_writer, adf_formatter,
                    reason_code=reason_code
                )
            elif error_type in ('pr_not_found', 'pr_not_merged', 'tz_too_short'):
                # PR yo'q / merged emas / TZ qisqa → JIRA error, task qaytariladi, DB returned
                log.warning(f"[{task_key}] [{error_type}] → task qaytarilmoqda [{reason_code}]")
                await _write_error_comment(
                    task_key, error_msg, comment_writer, adf_formatter,
                    reason_code=reason_code
                )
                await _handle_pr_not_merged_return(task_key, settings, company_id=company_id)
                mark_returned_pr_not_merged(task_key)
                set_return_reason(task_key, reason_code)
            else:
                # Boshqa xatolik — Service2 ham to'xtatiladi
                set_service1_error(task_key, error_msg)
                set_return_reason(task_key, reason_code)
                await _write_error_comment(
                    task_key, error_msg, comment_writer, adf_formatter,
                    reason_code=reason_code
                )
            return

        # 2. Muvaffaqiyatli — ADF comment yozish (yoki oddiy format fallback)
        is_recheck = return_reason in RECHECK_REASONS
        await _write_success_comment(
            task_key, result, new_status,
            settings, comment_writer, adf_formatter,
            is_recheck=is_recheck,
            dev_objections=result.dev_objections
        )

        # 3. Service1 holatini 'done' ga o'zgartirish, score saqlash
        compliance_score = result.compliance_score
        set_service1_done(task_key, compliance_score)
        log.service_done(task_key, "service_1", score=f"{compliance_score}%")

        # 4. Score threshold tekshiruvi: past bo'lsa avtomatik Return
        if settings.auto_return_enabled and compliance_score is not None:
            threshold = settings.return_threshold
            if compliance_score < threshold:
                await _handle_auto_return(task_key, result, settings, company_id=company_id)
                mark_returned(task_key)
                set_return_reason(task_key, WARN_LOW_SCORE)

    except Exception as e:
        error_msg = str(e)
        from services.webhook.error_handler import _classify_error, _write_critical_error
        error_type = _classify_error(error_msg)
        log.service_error(task_key, "service_1", str(e))
        log.error(f"[{task_key}] Service1 error details", exc_info=True)

        exc_reason_code = _error_type_to_reason_code(error_type)
        if error_type == 'ai_timeout':
            from config.app_settings import get_app_settings_for_company
            _s = get_app_settings_for_company(company_id) if company_id else get_app_settings(force_reload=False)
            retry_minutes = _s.queue.blocked_retry_delay if _s else 5
            set_service1_blocked(task_key, error_msg, retry_minutes)
            set_return_reason(task_key, exc_reason_code)
            log.info(f"[{task_key}] Service1 BLOCKED: {retry_minutes} min [{exc_reason_code}]")
        elif error_type == 'pr_not_found':
            set_service1_error(task_key, error_msg, keep_service2_pending=True)
            set_return_reason(task_key, exc_reason_code)
        else:
            set_service1_error(task_key, error_msg)
            set_return_reason(task_key, exc_reason_code)

        # Kritik xato haqida JIRA'ga xabar berish
        try:
            from config.app_settings import get_app_settings_for_company
            if company_id is None:
                return
            app_settings = get_app_settings_for_company(company_id)
            settings = app_settings.webhook_tz_pr
            from services.webhook.jira_webhook_handler import get_adf_formatter
            from utils.jira.jira_comment_writer import JiraCommentWriter
            from utils.auth.auth_db import get_company_credentials
            _creds = get_company_credentials(company_id)
            _cw = JiraCommentWriter(server=_creds['jira_server'], email=_creds['jira_email'], token=_creds['jira_token'])
            await _write_critical_error(
                task_key, error_msg, new_status,
                settings, _cw, get_adf_formatter()
            )
        except Exception:
            pass


async def _run_testcase_generation(task_key: str, new_status: str, company_id: int = None) -> None:
    """
    Service2: Test case'lar yaratish va JIRA'ga yozish.

    Bu funksiya Service1 tugagandan so'ng (yoki Service1 skip bo'lganda)
    avtomatik ishga tushiriladi. Queue manager tomonidan boshqariladi.

    Ishlamay qoladigan holatlar (skip):
    - Task DB'da topilmadi
    - service1_status 'done' | 'skip' | 'error' emas (hali tayor emas)
    - service1='error' va service2='pending' emas (avvalroq xato bo'lgan)
    - service2_status allaqachon 'done'
    - compliance_score < threshold (score past — task qaytariladi)
    - task_status='returned' (task qaytarilgan)

    Xato holatlari:
    - 'ai_timeout' → service2_status='blocked', retry scheduler kutib turadi
    - 'pr_not_found' va default_include_pr=True → TZ-only fallback urinish
    - Boshqa xatolik → service2_status='error'

    Args:
        task_key: JIRA task identifikatori
        new_status: JIRA'dagi yangi status (testcase trigger status)
    """
    try:
        log.info(f"[{task_key}] service_2 running | status={new_status}")

        task_db = get_task(task_key)
        if not task_db:
            log.warning(f"[{task_key}] Task DB'da topilmadi, Service2 skip")
            return

        service1_status = task_db.get('service1_status', 'pending')
        service2_status = task_db.get('service2_status', 'pending')
        compliance_score = task_db.get('compliance_score')
        task_status = task_db.get('task_status', 'none')

        # Service1 tayyor bo'lishi kerak
        if service1_status not in ('done', 'skip', 'error'):
            log.info(f"[{task_key}] SKIP -> service_2 kutmoqda, service_1 hali tugamagan (s1={service1_status})")
            return

        # service1=error holatida faqat service2=pending bo'lsa ishlaydi (TZ-only)
        if service1_status == 'error' and service2_status != 'pending':
            log.info(f"[{task_key}] SKIP -> service_1 xato bilan tugagan, service_2 ishlamaydi")
            return

        # Service2 allaqachon bajarilgan
        if service2_status == 'done':
            log.info(f"[{task_key}] SKIP -> service_2 allaqachon bajarilgan, qayta ishlanmaydi")
            return

        if company_id is None:
            log.error(f"[{task_key}] company_id yo'q — service_2 ishga tushmaydi")
            return

        from config.app_settings import get_app_settings_for_company
        app_settings = get_app_settings_for_company(company_id)
        settings = app_settings.webhook_tz_pr
        tc_settings = app_settings.webhook_testcase
        threshold = settings.return_threshold

        if compliance_score is not None and compliance_score < threshold:
            log.info(f"[{task_key}] SKIP -> score past ({compliance_score}% < {threshold}%), testcase yaratilmaydi")
            return

        # Task qaytarilgan bo'lsa Service2 ishlamaydi
        if task_status == 'returned':
            log.info(f"[{task_key}] SKIP -> task qaytarilgan holatda, testcase yaratilmaydi")
            return

        # Testcase generation ishga tushirish
        from services.webhook.testcase_webhook_handler import check_and_generate_testcases
        from services.webhook.error_handler import _classify_error

        log.info(f"[{task_key}] Service2 ▶ check_and_generate_testcases() chaqirilmoqda...")
        success, message = await check_and_generate_testcases(task_key, new_status, company_id=company_id)

        # Barcha cache yozuvlarini tozalash (task tugadi)
        try:
            from utils.pr_cache import clear_task_cache
            clear_task_cache(task_key)
        except Exception:
            pass

        if success:
            set_service2_done(task_key)
            log.service_done(task_key, "service_2", result=message)
        else:
            error_msg = message
            error_type = _classify_error(error_msg)
            log.service_error(task_key, "service_2", error_msg)

            reason_code_s2 = _error_type_to_reason_code(error_type)
            if error_type == 'ai_timeout':
                # Bloklanadi — retry scheduler keyinroq urinadi
                retry_minutes = app_settings.queue.blocked_retry_delay
                set_service2_blocked(task_key, error_msg, retry_minutes)
                set_return_reason(task_key, reason_code_s2)
                log.info(f"[{task_key}] Service2 BLOCKED: {retry_minutes} min [{reason_code_s2}]")
            elif error_type in ('pr_not_found', 'pr_not_merged', 'tz_too_short'):
                # PR yo'q / merged emas / TZ qisqa → task qaytariladi (comment testcase_webhook_handler da yoziladi)
                log.warning(f"[{task_key}] Servis-2 [{error_type}] → task qaytarilmoqda [{reason_code_s2}]")
                await _handle_pr_not_merged_return(task_key, app_settings.webhook_tz_pr, company_id=company_id)
                mark_returned_pr_not_merged(task_key)
                set_return_reason(task_key, reason_code_s2)
            else:
                set_service2_error(task_key, error_msg)
                set_return_reason(task_key, reason_code_s2)

    except Exception as e:
        error_msg = f"Testcase generation error: {str(e)}"
        from services.webhook.error_handler import _classify_error
        error_type = _classify_error(error_msg)
        log.service_error(task_key, "service_2", str(e))
        log.error(f"[{task_key}] Service2 error details", exc_info=True)

        if error_type == 'ai_timeout':
            from config.app_settings import get_app_settings_for_company
            _s = get_app_settings_for_company(company_id) if company_id else get_app_settings(force_reload=False)
            retry_minutes = _s.queue.blocked_retry_delay
            set_service2_blocked(task_key, error_msg, retry_minutes)
            set_return_reason(task_key, WARN_AI_TIMEOUT)
        else:
            set_service2_error(task_key, error_msg)
            set_return_reason(task_key, ERR_UNKNOWN)


def _get_status_manager(company_id):
    """JiraStatusManager yaratish — company_id bo'lsa multi-tenant, aks holda global."""
    from utils.jira.jira_status_manager import JiraStatusManager
    if company_id is not None:
        from utils.auth.auth_db import get_company_credentials
        _creds = get_company_credentials(company_id)
        return JiraStatusManager(server=_creds['jira_server'], email=_creds['jira_email'], token=_creds['jira_token'])
    from utils.jira.jira_status_manager import get_status_manager
    return get_status_manager()


async def _handle_auto_return(
        task_key: str,
        result: Any,
        settings: "TZPRCheckerSettings",
        company_id: int = None,
) -> None:
    """
    Compliance score threshold'dan past bo'lganda JIRA task'ni avtomatik qaytarish.

    Bu funksiya Service1 muvaffaqiyatli tugaganidan keyin compliance_score < threshold
    bo'lsa chaqiriladi. Amallar ketma-ketligi:
    1. JiraStatusManager.auto_return_if_needed() — JIRA statusini return_status'ga o'zgartirish
    2. Muvaffaqiyatli bo'lsa — ADF return notification comment yozish (yoki oddiy format fallback)
    3. mark_returned() — DB'da task_status='returned' qo'yiladi (caller tomonidan)

    Nima uchun alohida funksiya:
    - Return logikasi murakkab (ADF + fallback + log)
    - check_tz_pr_and_comment() juda uzayib ketmasligi uchun

    Args:
        task_key: JIRA task identifikatori
        result: TZPRAnalysisResult — compliance_score va ai_analysis olish uchun
        settings: TZPRCheckerSettings — threshold, return_status, notification_text

    Side Effects:
        - JIRA task statusini return_status'ga o'zgartiradi
        - JIRA'ga return notification comment yozadi
        - mark_returned() bu funksiyadan TASHQARIDA chaqiriladi (caller tomonidan)
    """
    try:
        score = result.compliance_score
        threshold = settings.return_threshold

        if score < threshold:
            status_manager = _get_status_manager(company_id)

            success, msg = status_manager.auto_return_if_needed(
                task_key=task_key,
                compliance_score=score,
                threshold=threshold,
                return_status=settings.return_status,
                enabled=settings.auto_return_enabled
            )

            if success:
                log.warning(
                    f"[{task_key}] RETURNED -> {settings.return_status} | score={score}% < {threshold}%"
                )
                # Return haqida JIRA'ga qisqa Warning comment yozish
                try:
                    from services.webhook.jira_webhook_handler import get_adf_formatter
                    from services.webhook.error_handler import _build_warning_adf, format_warning_simple
                    from utils.jira.jira_comment_writer import JiraCommentWriter
                    from utils.auth.auth_db import get_company_credentials
                    _creds = get_company_credentials(company_id)
                    comment_writer = JiraCommentWriter(server=_creds['jira_server'], email=_creds['jira_email'], token=_creds['jira_token'])
                    adf_formatter = get_adf_formatter()
                    reason = (
                        f"Task qaytarildi. Moslik bali: {score}% (chegarasi: {threshold}%). "
                        f"Status: {settings.return_status}. "
                        f"TZ talablarini tekshiring va qaytadan PR bering."
                    )
                    return_doc = _build_warning_adf(adf_formatter, "Servis-1", reason, task_key, "warning", reason_code=WARN_LOW_SCORE)
                    notif_success = comment_writer.add_comment_adf(task_key, return_doc)

                    if not notif_success:
                        comment_writer.add_comment(task_key, format_warning_simple("Servis-1", reason, task_key))
                        log.jira_comment_added(task_key, "simple")
                    else:
                        log.jira_comment_added(task_key, "Warning ADF")

                except Exception as notif_e:
                    log.error(f"[{task_key}] Return notification xato: {notif_e}")
            else:
                log.warning(f"[{task_key}] Auto-return FAILED: {msg}")

    except Exception as e:
        log.error(f"[{task_key}] Auto-return xato: {e}")


async def _handle_pr_not_merged_return(
        task_key: str,
        settings: "TZPRCheckerSettings",
        company_id: int = None,
) -> None:
    """
    PR merged emas bo'lganda JIRA task statusini return_status ga o'zgartirish.

    check_tz_pr_and_comment() tomonidan chaqiriladi — error comment yozilgandan
    keyin, mark_returned_pr_not_merged() dan oldin.

    Ishlash tartibi:
        1. JiraStatusManager.change_status() orqali return_status ga o'tkazish
        2. Muvaffaqiyatli bo'lsa — warning log
        3. Muvaffaqiyatsiz bo'lsa — log (DB yangilanishi caller tomonidan baribir bo'ladi)

    Args:
        task_key: JIRA task identifikatori
        settings: TZPRCheckerSettings — return_status olish uchun
    """
    try:
        status_manager = _get_status_manager(company_id)
        return_status = settings.return_status

        success, msg = status_manager.change_status(task_key, return_status)
        if success:
            log.warning(
                f"[{task_key}] RETURNED (PR not merged) → {return_status}"
            )
        else:
            log.warning(f"[{task_key}] PR not merged return FAILED: {msg}")

    except Exception as e:
        log.error(f"[{task_key}] PR not merged return xato: {e}")
