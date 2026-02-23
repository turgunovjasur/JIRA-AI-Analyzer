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
from utils.database.task_db import (
    get_task, mark_returned,
    set_service1_done, set_service1_error, set_service1_blocked,
    set_service2_done, set_service2_error, set_service2_blocked
)

log = get_logger("webhook.service_runner")


async def check_tz_pr_and_comment(task_key: str, new_status: str) -> None:
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

        app_settings = get_app_settings(force_reload=False)
        settings = app_settings.tz_pr_checker

        # Singleton servislarni import qilish (circular import oldini olish)
        from services.webhook.jira_webhook_handler import (
            get_tz_pr_service, get_comment_writer, get_adf_formatter
        )
        from services.webhook.skip_detector import _detect_recheck
        from services.webhook.error_handler import (
            _classify_error, _write_success_comment,
            _write_error_comment, _write_critical_error
        )

        tz_pr_service = get_tz_pr_service()
        comment_writer = get_comment_writer()
        adf_formatter = get_adf_formatter()

        # Re-check aniqlash: oldingi status return_status bo'lganmi?
        is_recheck = await _detect_recheck(task_key, settings, comment_writer)
        if is_recheck:
            log.info(f"[{task_key}] RE-CHECK -> task avval qaytarilgan, takroriy tahlil")

        # 1. TZ-PR tahlil qilish (AI + GitHub + JIRA)
        result = tz_pr_service.analyze_task(task_key)

        if not result.success:
            error_msg = result.error_message
            error_type = _classify_error(error_msg)
            log.service_error(task_key, "service_1", error_msg)

            if error_type == 'ai_timeout':
                # Task bloklanadi — retry scheduler keyinroq qayta urinadi
                retry_minutes = get_app_settings(force_reload=False).queue.blocked_retry_delay
                set_service1_blocked(task_key, error_msg, retry_minutes)
                log.info(f"[{task_key}] Service1 BLOCKED: {retry_minutes} min")
            elif error_type == 'pr_not_found':
                # PR topilmadi — Service2 baribir TZ-only rejimda ishlashi mumkin
                set_service1_error(task_key, error_msg, keep_service2_pending=True)
            else:
                # Boshqa xatolik — Service2 ham to'xtatiladi
                set_service1_error(task_key, error_msg)

            await _write_error_comment(
                task_key, error_msg, new_status,
                settings, comment_writer, adf_formatter
            )
            return

        # 2. Muvaffaqiyatli — ADF comment yozish (yoki oddiy format fallback)
        await _write_success_comment(
            task_key, result, new_status,
            settings, comment_writer, adf_formatter,
            is_recheck=is_recheck
        )

        # 3. Service1 holatini 'done' ga o'zgartirish, score saqlash
        compliance_score = result.compliance_score
        set_service1_done(task_key, compliance_score)
        log.service_done(task_key, "service_1", score=f"{compliance_score}%")

        # 4. Score threshold tekshiruvi: past bo'lsa avtomatik Return
        if settings.auto_return_enabled and compliance_score is not None:
            threshold = settings.return_threshold
            if compliance_score < threshold:
                await _handle_auto_return(task_key, result, settings)
                mark_returned(task_key)

    except Exception as e:
        error_msg = str(e)
        from services.webhook.error_handler import _classify_error, _write_critical_error
        error_type = _classify_error(error_msg)
        log.service_error(task_key, "service_1", str(e))
        log.error(f"[{task_key}] Service1 error details", exc_info=True)

        if error_type == 'ai_timeout':
            retry_minutes = get_app_settings(force_reload=False).queue.blocked_retry_delay
            set_service1_blocked(task_key, error_msg, retry_minutes)
            log.info(f"[{task_key}] Service1 BLOCKED: {retry_minutes} min")
        elif error_type == 'pr_not_found':
            set_service1_error(task_key, error_msg, keep_service2_pending=True)
        else:
            set_service1_error(task_key, error_msg)

        # Kritik xato haqida JIRA'ga xabar berish
        try:
            app_settings = get_app_settings(force_reload=False)
            settings = app_settings.tz_pr_checker
            from services.webhook.jira_webhook_handler import get_comment_writer, get_adf_formatter
            await _write_critical_error(
                task_key, error_msg, new_status,
                settings, get_comment_writer(), get_adf_formatter()
            )
        except Exception:
            pass


async def _run_testcase_generation(task_key: str, new_status: str) -> None:
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
        log.service_running(task_key, "service_2")

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

        # Score threshold tekshiruvi
        app_settings = get_app_settings(force_reload=False)
        settings = app_settings.tz_pr_checker
        tc_settings = app_settings.testcase_generator
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

        success, message = await check_and_generate_testcases(task_key, new_status)

        if success:
            set_service2_done(task_key)
            log.service_done(task_key, "service_2", result=message)
        else:
            error_msg = f"Testcase generation failed: {message}"
            error_type = _classify_error(error_msg)
            log.service_error(task_key, "service_2", error_msg)

            if error_type == 'ai_timeout':
                # Bloklanadi — retry scheduler keyinroq urinadi
                retry_minutes = app_settings.queue.blocked_retry_delay
                set_service2_blocked(task_key, error_msg, retry_minutes)
                log.info(f"[{task_key}] Service2 BLOCKED: {retry_minutes} min")
            elif error_type == 'pr_not_found' and tc_settings.default_include_pr:
                # PR topilmadi → TZ-only rejimda qayta urinish
                success2, message2 = await check_and_generate_testcases(
                    task_key, new_status, include_pr=False
                )
                if success2:
                    set_service2_done(task_key)
                    log.service_done(task_key, "service_2", result=f"{message2} (TZ-only)")
                else:
                    error_msg2 = f"Testcase TZ-only fallback failed: {message2}"
                    error_type2 = _classify_error(error_msg2)
                    if error_type2 == 'ai_timeout':
                        retry_minutes = app_settings.queue.blocked_retry_delay
                        set_service2_blocked(task_key, error_msg2, retry_minutes)
                    else:
                        set_service2_error(task_key, error_msg2)
                    log.service_error(task_key, "service_2", error_msg2)
            else:
                set_service2_error(task_key, error_msg)

    except Exception as e:
        error_msg = f"Testcase generation error: {str(e)}"
        from services.webhook.error_handler import _classify_error
        error_type = _classify_error(error_msg)
        log.service_error(task_key, "service_2", str(e))
        log.error(f"[{task_key}] Service2 error details", exc_info=True)

        if error_type == 'ai_timeout':
            retry_minutes = get_app_settings(force_reload=False).queue.blocked_retry_delay
            set_service2_blocked(task_key, error_msg, retry_minutes)
        else:
            set_service2_error(task_key, error_msg)


async def _handle_auto_return(
        task_key: str,
        result: Any,
        settings: "TZPRCheckerSettings"
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
            from utils.jira.jira_status_manager import get_status_manager
            status_manager = get_status_manager()
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
                # Return haqida JIRA'ga notification comment yozish
                try:
                    from services.webhook.jira_webhook_handler import get_comment_writer, get_adf_formatter
                    comment_writer = get_comment_writer()
                    adf_formatter = get_adf_formatter()
                    return_doc = adf_formatter.build_return_notification_document(
                        task_key=task_key,
                        compliance_score=score,
                        threshold=threshold,
                        return_status=settings.return_status,
                        notification_text=settings.return_notification_text,
                        ai_analysis=result.ai_analysis
                    )
                    notif_success = comment_writer.add_comment_adf(task_key, return_doc)

                    if not notif_success:
                        # Fallback — oddiy text format
                        comment_writer.add_comment(
                            task_key,
                            f"Task Qaytarildi\n\n"
                            f"Moslik bali: *{score}%* (chegarasi: {threshold}%)\n\n"
                            f"Task *{settings.return_status}* statusga qaytarildi.\n\n"
                            f"TZ talablarini tekshiring va qaytadan PR bering."
                        )
                        log.jira_comment_added(task_key, "simple")
                    else:
                        log.jira_comment_added(task_key, "ADF")

                except Exception as notif_e:
                    log.error(f"[{task_key}] Return notification xato: {notif_e}")
            else:
                log.warning(f"[{task_key}] Auto-return FAILED: {msg}")

    except Exception as e:
        log.error(f"[{task_key}] Auto-return xato: {e}")
