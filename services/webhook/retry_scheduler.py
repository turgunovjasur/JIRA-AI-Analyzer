"""
Retry Scheduler Module - Blocked tasklar uchun qayta urinish tizimi
====================================================================

Bu modul AI API xatosi sababli 'blocked' holatga tushgan tasklar uchun
avtomatik qayta urinish (retry) mexanizmini ta'minlaydi.

Qachon task 'blocked' bo'ladi:
  - Google Gemini API 429 (rate limit) yoki timeout xatosi
  - Ikkala API key ham ishlamay qolsa
  → Task 'blocked' holatga tushadi va blocked_retry_at vaqti belgilanadi

Qanday qayta uriniladi:
  1. _blocked_retry_scheduler() har N sekundda DB'ni tekshiradi
  2. blocked_retry_at <= hozirgi vaqt bo'lgan tasklar topiladi
  3. Har task uchun _retry_blocked_task() chaqiriladi
  4. Xato ko'rinishiga qarab Service1 va/yoki Service2 qayta ishlatiladi

Sozlamalar (config/app_settings.py QueueSettings):
  - blocked_check_interval: qancha sekundda bir tekshirish (default: 60s)
  - blocked_retry_delay: qancha minutdan keyin qayta urinish (default: 5 min)
  - task_wait_timeout: AI queue uchun maksimal kutish (default: 60s)
"""
import asyncio
from datetime import datetime
from typing import Optional

from config.app_settings import get_app_settings
from core.logger import get_logger
from utils.database.task_db import (
    get_task, mark_progressing, mark_error,
    get_blocked_tasks_ready_for_retry, upsert_task
)

log = get_logger("webhook.retry_scheduler")

# Global background task — startup'da yaratiladi, shutdown'da bekor qilinadi
_blocked_retry_task: Optional[asyncio.Task] = None


async def _retry_blocked_task(task_id: str) -> None:
    """
    Bitta blocked taskni qayta ishlashga urinish.

    Qayta ishlash strategiyasi:
    - service1='blocked' → service1 'pending' ga qaytariladi va qayta ishga tushiriladi
    - service1='done'|'skip' → service1 o'tkazib yuboriladi
    - service2='blocked'|'pending' → service1 tugagandan keyin service2 ishga tushiriladi
    - service2='done' → o'tkazib yuboriladi

    Xato holati: agar service1 yana xato bersa (blocked/error) — service2 ishlamaydi.
    Bu funksiya _blocked_retry_scheduler() tomonidan queue lock ichida chaqiriladi.

    Args:
        task_id: Qayta urinish kerak bo'lgan JIRA task identifikatori

    Side Effects:
        - DB'da task_status='progressing' qo'yiladi
        - service1/service2 holatlar yangilanadi
        - JIRA'ga natija comment yoziladi (service_runner orqali)
        - Xato bo'lsa: DB'da task_status='error' qo'yiladi
    """
    try:
        task_data = get_task(task_id)
        if not task_data:
            log.warning(f"[{task_id}] SKIP -> task DB da topilmadi, retry o'tkazib yuborildi")
            return

        service1_status = task_data.get('service1_status', 'pending')
        service2_status = task_data.get('service2_status', 'pending')
        last_jira_status = task_data.get('last_jira_status', 'READY TO TEST')

        log.info(f"[{task_id}] RETRY -> s1={service1_status} s2={service2_status} last_status={last_jira_status}")

        # Progressing holatiga o'tkazish
        mark_progressing(task_id, last_jira_status, datetime.now())

        # Qaysi servislar qayta ishlashi kerak?
        need_service1 = (service1_status == 'blocked')
        need_service2 = (service2_status in ('blocked', 'pending'))

        if need_service1:
            # Service1 'blocked' → 'pending' ga qaytarish va qayta ishga tushirish
            upsert_task(task_id, {
                'service1_status': 'pending',
                'service1_error': None,
                'blocked_at': None,
                'blocked_retry_at': None,
                'block_reason': None
            })

            # Circular import oldini olish uchun funksiya ichida import
            from services.webhook.queue_manager import _wait_for_ai_slot
            from services.webhook.service_runner import check_tz_pr_and_comment

            log.service_running(task_id, "service_1")
            await _wait_for_ai_slot(task_id)
            await check_tz_pr_and_comment(task_key=task_id, new_status=last_jira_status)

            # Service1 natijasini qayta o'qish
            task_data = get_task(task_id)
            if not task_data:
                return

            service1_status = task_data.get('service1_status', 'pending')
            task_status = task_data.get('task_status', 'none')

            # Agar service1 yana muvaffaqiyatsiz — service2 ham to'xtatiladi
            if service1_status not in ('done', 'skip'):
                log.info(f"[{task_id}] SKIP -> service_1 retry muvaffaqiyatsiz (s1={service1_status}), service_2 ishlamaydi")
                return
            if task_status in ('returned', 'blocked'):
                log.info(f"[{task_id}] SKIP -> task {task_status} holatida, service_2 ishlamaydi")
                return

        if need_service2:
            # Service2 'blocked'|'pending' → 'pending' ga qaytarish va qayta ishga tushirish
            task_data = get_task(task_id)
            if task_data and task_data.get('service2_status') != 'done':
                upsert_task(task_id, {
                    'service2_status': 'pending',
                    'service2_error': None,
                    'blocked_at': None,
                    'blocked_retry_at': None,
                    'block_reason': None
                })

                # Service1 va Service2 orasida delay
                if need_service1:
                    app_settings = get_app_settings(force_reload=False)
                    delay = app_settings.queue.checker_testcase_delay
                    if delay > 0:
                        await asyncio.sleep(delay)

                from services.webhook.queue_manager import _wait_for_ai_slot
                from services.webhook.service_runner import _run_testcase_generation

                log.service_running(task_id, "service_2")
                await _wait_for_ai_slot(task_id)
                await _run_testcase_generation(task_key=task_id, new_status=last_jira_status)

        # Ikkala servis ham done bo'lsa — retry kerak emas
        if not need_service1 and not need_service2:
            log.info(f"[{task_id}] SKIP -> all services done, retry not needed")

    except Exception as e:
        log.error(f"[{task_id}] Blocked task retry error: {e}", exc_info=True)
        mark_error(task_id, f"Retry error: {str(e)}")


async def _blocked_retry_scheduler() -> None:
    """
    Background scheduler: blocked tasklarni avtomatik qayta ishlash.

    Bu funksiya startup_event() tomonidan asyncio.create_task() bilan
    background'da ishga tushiriladi va server ishlagan vaqt davomida
    har blocked_check_interval sekundda DB'ni tekshirib turadi.

    Ishlash mantiqi:
    1. blocked_check_interval sekund uxlash
    2. get_blocked_tasks_ready_for_retry() — vaqti kelgan tasklar olish
    3. Har task uchun AI queue lock olib _retry_blocked_task() chaqirish
    4. Yana 1-ga qaytish

    Xato holati:
    - asyncio.CancelledError: server to'xtaganda scheduler tozalanadi
    - Boshqa xatolar: log yozib davom etish (scheduler to'xtamaydi)

    Sozlamalar (dinamik, har tsiklda qayta o'qiladi):
    - queue.blocked_check_interval: tekshirish intervali (sekund)
    - queue.task_wait_timeout: AI queue kutish vaqti (sekund)

    Note: Settings force_reload=False — settings cache ishlatiladi.
    UI'dan o'zgarishlar keyingi tekshirishda ko'rinadi.
    """
    log.info("RETRY-SCHEDULER -> started, blocked tasks monitoring active")

    app_settings = get_app_settings(force_reload=False)
    check_interval = app_settings.queue.blocked_check_interval

    while True:
        try:
            await asyncio.sleep(check_interval)

            # Settings yangilash (UI'dan o'zgarishlarni ko'rish uchun)
            app_settings = get_app_settings(force_reload=False)
            check_interval = app_settings.queue.blocked_check_interval

            # blocked_retry_at <= now bo'lgan tasklar
            blocked_tasks = get_blocked_tasks_ready_for_retry()
            if not blocked_tasks:
                continue

            log.info(f"RETRY-SCHEDULER -> {len(blocked_tasks)} blocked task(s) ready for retry")

            for task_data in blocked_tasks:
                task_id = task_data['task_id']

                # AI queue lock olib retry qilish
                from services.webhook.queue_manager import _get_ai_queue_lock
                lock = _get_ai_queue_lock()

                app_settings = get_app_settings(force_reload=False)
                timeout = app_settings.queue.task_wait_timeout

                try:
                    await asyncio.wait_for(lock.acquire(), timeout=timeout)
                except asyncio.TimeoutError:
                    log.warning(f"[{task_id}] Retry: queue timeout, keyingi tsiklda urinadi")
                    continue

                try:
                    await _retry_blocked_task(task_id)
                finally:
                    lock.release()

        except asyncio.CancelledError:
            log.info("RETRY-SCHEDULER -> stopped")
            break
        except Exception as e:
            log.error(f"Blocked retry scheduler error: {e}", exc_info=True)
            # Xato bo'lganda ham interval yangilanadi
            app_settings = get_app_settings(force_reload=False)
            check_interval = app_settings.queue.blocked_check_interval
            await asyncio.sleep(check_interval)
