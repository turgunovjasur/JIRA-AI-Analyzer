"""
Queue Manager Module - AI navbat va task boshqaruvi
====================================================

Bu modul Google Gemini AI API ga bir vaqtda ko'p so'rov ketmasligi uchun
global navbat (queue) tizimini boshqaradi.

Muammo:
  - Google Gemini API: 10 so'rov/daqiqa cheklov (free tier)
  - Bir vaqtda bir nechta JIRA task trigger bo'lishi mumkin
  - Har task uchun 2 ta AI so'rov kerak (Service1 + Service2)

Yechim:
  - Global asyncio.Lock — bir vaqtda faqat bitta task AI ishlatadi
  - _wait_for_ai_slot() — so'rovlar orasida minimal interval
  - Task-level lock: Service1 → delay → Service2 (bitta lock ichida)

Ish tartibi (har doim bir xil):
  Service1 (TZ-PR) tugaydi → checker_testcase_delay → Service2 (Testcase)
"""
import asyncio
import time
from typing import Optional

from config.app_settings import get_app_settings
from core.logger import get_logger
from utils.database.task_db import get_task, mark_blocked

log = get_logger("webhook.queue_manager")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GLOBAL AI QUEUE STATE
# Asyncio single-event-loop muhitida thread-safe (lock ichida mutatsiya)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_ai_queue_lock: Optional[asyncio.Lock] = None
_ai_last_call_time: float = 0.0


def _get_ai_queue_lock() -> asyncio.Lock:
    """
    Global AI queue lock — lazy singleton.

    Singleton pattern: birinchi chaqiruvda yaratiladi, keyingilarda bir xil obyekt.
    asyncio.Lock event loop'ga bog'liq — faqat asinxron muhitda to'g'ri ishlaydi.

    Returns:
        asyncio.Lock — global lock obyekti
    """
    global _ai_queue_lock
    if _ai_queue_lock is None:
        _ai_queue_lock = asyncio.Lock()
    return _ai_queue_lock


async def _wait_for_ai_slot(task_key: str) -> None:
    """
    AI so'rov yuborishdan oldin rate limit kutish.

    Google Gemini API: 10 so'rov/daqiqa (free tier) → har so'rov orasida
    kamida gemini_min_interval sekund bo'lishi kerak (default: 6 sekund).

    _ai_last_call_time global o'zgaruvchisi oxirgi AI chaqruv vaqtini saqlaydi.
    Bu funksiya faqat _ai_queue_lock ichida chaqiriladi — global o'zgaruvchi
    lock himoyasida (asyncio single-thread, race condition yo'q).

    Args:
        task_key: Log uchun JIRA task identifikatori
    """
    global _ai_last_call_time

    app_settings = get_app_settings(force_reload=False)
    min_interval = app_settings.queue.gemini_min_interval

    elapsed = time.time() - _ai_last_call_time
    if elapsed < min_interval:
        wait_time = min_interval - elapsed
        log.queue_waiting(task_key, "AI rate limit", int(wait_time))
        await asyncio.sleep(wait_time)

    _ai_last_call_time = time.time()


async def _write_timeout_error_comment(task_key: str, timeout_seconds: int, company_id: int = None) -> None:
    """Queue timeout bo'lganda JIRA'ga xabar yozish (error_handler ga delegate)."""
    from services.webhook.error_handler import _write_timeout_error_comment as _write
    await _write(task_key, timeout_seconds, company_id=company_id)


async def _run_task_group(task_key: str, new_status: str, company_id: int = None) -> None:
    """
    Service1 va Service2 ni bitta lock ichida ketma-ket ishga tushirish.

    Har doim Service1 birinchi, so'ng Service2 (agar shartlar bajarilsa).
    Bitta lock ichida ishlaydi — boshqa task shu vaqtda AI ishlatmaydi.

    Oqim:
    1. Lock olish (timeout: task_wait_timeout sekund)
    2. _wait_for_ai_slot() → Service1 chaqruvi
    3. checker_testcase_delay sekund kutish
    4. DB'dan Service1 natijasini o'qish (score, status)
    5. Score OK va task returned emas → _wait_for_ai_slot() → Service2 chaqruvi
    6. Lock release (finally blokida)

    Service2 ishlamaydigan hollar:
    - service1_status 'done' | 'skip' emas (xato yuz bergan)
    - compliance_score < threshold (score past — task qaytarildi)
    - task_status 'returned' | 'blocked'
    - service1='error' va service2='pending' → ishlaydi (TZ-only rejim uchun)

    Args:
        task_key: JIRA task identifikatori
        new_status: JIRA yangi status (comment'larga yoziladi)
    """
    from services.webhook.service_runner import check_tz_pr_and_comment, _run_testcase_generation
    from config.app_settings import get_app_settings_for_company

    if company_id is not None:
        app_settings = get_app_settings_for_company(company_id)
    else:
        app_settings = get_app_settings(force_reload=False)
    queue_settings = app_settings.queue

    if not queue_settings.queue_enabled:
        # Queue o'chirilgan: lock siz ketma-ket chaqruv
        await check_tz_pr_and_comment(task_key=task_key, new_status=new_status, company_id=company_id)

        task_db = get_task(task_key)
        if task_db and _can_run_service2(task_db, app_settings):
            delay = queue_settings.checker_testcase_delay
            if delay > 0:
                await asyncio.sleep(delay)
            await _run_testcase_generation(task_key=task_key, new_status=new_status, company_id=company_id)
        return

    lock = _get_ai_queue_lock()
    timeout = queue_settings.task_wait_timeout
    delay = queue_settings.checker_testcase_delay

    try:
        await asyncio.wait_for(lock.acquire(), timeout=timeout)
    except asyncio.TimeoutError:
        log.queue_timeout(task_key, timeout)
        mark_blocked(task_key, f"Queue timeout: {timeout}s", retry_minutes=5)
        await _write_timeout_error_comment(task_key, timeout, company_id=company_id)
        return

    try:
        # Service1
        await _wait_for_ai_slot(task_key)
        await check_tz_pr_and_comment(task_key=task_key, new_status=new_status, company_id=company_id)

        # Service1 → Service2 orasidagi kutish
        if delay > 0:
            await asyncio.sleep(delay)

        # Service2 — faqat shartlar bajarilsa
        task_db = get_task(task_key)
        if task_db and _can_run_service2(task_db, app_settings):
            await _wait_for_ai_slot(task_key)
            await _run_testcase_generation(task_key=task_key, new_status=new_status, company_id=company_id)
        elif task_db:
            s1 = task_db.get('service1_status', 'pending')
            score = task_db.get('compliance_score')
            threshold = app_settings.webhook_tz_pr.return_threshold
            if s1 in ('done', 'skip') and score is not None and score < threshold:
                log.info(f"[{task_key}] Score past ({score}% < {threshold}%), Service2 skip")
    finally:
        lock.release()


async def _queued_check_tz_pr(task_key: str, new_status: str, company_id: int = None) -> None:
    """
    Queue wrapper: faqat Service1 (testcase ishlamaydigan holatlar uchun).

    Testcase trigger status emas yoki testcase o'chirilgan bo'lsa
    jira_webhook() bu funksiyani chaqiradi (_run_task_group o'rniga).

    Oqim:
    1. Lock olish (timeout: task_wait_timeout)
    2. _wait_for_ai_slot() → Service1

    Args:
        task_key: JIRA task identifikatori
        new_status: JIRA yangi status
    """
    from services.webhook.service_runner import check_tz_pr_and_comment
    from config.app_settings import get_app_settings_for_company

    if company_id is not None:
        app_settings = get_app_settings_for_company(company_id)
    else:
        app_settings = get_app_settings(force_reload=False)
    queue_settings = app_settings.queue

    if not queue_settings.queue_enabled:
        await check_tz_pr_and_comment(task_key=task_key, new_status=new_status, company_id=company_id)
        return

    lock = _get_ai_queue_lock()
    timeout = queue_settings.task_wait_timeout

    try:
        await asyncio.wait_for(lock.acquire(), timeout=timeout)
    except asyncio.TimeoutError:
        log.queue_timeout(task_key, timeout)
        mark_blocked(task_key, f"Queue timeout: {timeout}s", retry_minutes=5)
        await _write_timeout_error_comment(task_key, timeout, company_id=company_id)
        return

    try:
        await _wait_for_ai_slot(task_key)
        await check_tz_pr_and_comment(task_key=task_key, new_status=new_status, company_id=company_id)
    finally:
        lock.release()


def _can_run_service2(task_db: dict, app_settings) -> bool:
    """
    Service2 ishlay oladimi tekshirish (DB ma'lumotlari asosida).

    Shartlar:
    - service1_status 'done' | 'skip': score tekshirish kerak
    - service1_status 'error': service2_status='pending' bo'lsa ishlaydi (TZ-only)
    - Boshqa holatlarda: False

    Args:
        task_db: DB'dan olingan task ma'lumotlari (dict)
        app_settings: AppSettings — threshold olish uchun

    Returns:
        True — Service2 ishlay oladi
        False — Service2 ishlamamaydi
    """
    service1_status = task_db.get('service1_status', 'pending')
    compliance_score = task_db.get('compliance_score')
    task_status = task_db.get('task_status', 'none')
    threshold = app_settings.webhook_tz_pr.return_threshold

    if service1_status in ('done', 'skip'):
        if compliance_score is None or compliance_score >= threshold:
            if task_status not in ('returned', 'blocked'):
                return True
    elif service1_status == 'error':
        s2_status = task_db.get('service2_status', 'pending')
        if s2_status == 'pending':
            return True

    return False


