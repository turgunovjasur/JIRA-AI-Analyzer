"""
JIRA Webhook Handler - Asosiy Orchestrator
==========================================

Bu fayl webhook endpoint va singleton factory funksiyalarini o'z ichida saqlaydi.
Barcha biznes logika yangi modullarga ajratilgan:

  error_handler.py   — Xato aniqlash va comment yozish
  skip_detector.py   — AI_SKIP va re-check aniqlash
  service_runner.py  — Service1 (TZ-PR) va Service2 (Testcase) ishga tushirish
  queue_manager.py   — AI queue va rate limit boshqaruvi
  retry_scheduler.py — Blocked tasklar uchun qayta urinish scheduler

Backward-compatibility: Testlar va boshqa modullar uchun muhim funksiyalar
bu fayldan ham import qilinishi mumkin (re-export orqali).

Server startup komandasi o'zgarmaydi:
  uvicorn services.webhook.jira_webhook_handler:app --port 8000

Author: JASUR TURGUNOV
Version: 4.0 (Refactored)
"""
import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import FastAPI, BackgroundTasks, Request
from pydantic import BaseModel
import uvicorn

# Loyiha root path qo'shish (turli muhitlarda ishlashi uchun)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Windows CMD encoding muammosini tuzatish (cp1251 emoji error)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from core.logger import get_logger
from services.checkers.tz_pr_checker import TZPRService
from utils.jira.jira_comment_writer import JiraCommentWriter
from utils.jira.jira_adf_formatter import JiraADFFormatter
from config.app_settings import get_app_settings
from services.webhook.testcase_webhook_handler import is_testcase_trigger_status
from utils.database.task_db import (
    get_task, mark_progressing, mark_completed, mark_returned, mark_error,
    mark_blocked, increment_return_count, set_skip_detected,
    set_service1_done, set_service1_error, set_service1_skip, set_service1_blocked,
    set_service2_done, set_service2_error, set_service2_blocked,
    set_task_timeout_error, reset_service_statuses, get_blocked_tasks_ready_for_retry
)

# Yangi modullar (biznes logika shu fayllarda)
from services.webhook.error_handler import (
    _classify_error,
    _write_success_comment,
    _write_error_comment,
    _write_critical_error,
    _write_skip_notification,
    format_error_comment_simple,
    format_critical_error_simple,
)
from services.webhook.skip_detector import _check_skip_code, _detect_recheck
from services.webhook.service_runner import (
    check_tz_pr_and_comment,
    _run_testcase_generation,
    _handle_auto_return,
)
from services.webhook.queue_manager import (
    _get_ai_queue_lock,
    _wait_for_ai_slot,
    _run_task_group,
    _queued_check_tz_pr,
    _run_sequential_tasks,
)
from services.webhook.retry_scheduler import (
    _retry_blocked_task,
    _blocked_retry_scheduler,
)

log = get_logger("webhook.handler")

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="JIRA TZ-PR Auto Checker",
    description="Avtomatik TZ-PR moslik tekshirish + Testcase Auto-Comment + Sprint Report",
    version="4.0.0"
)

# Sprint Report API ni ulash (ixtiyoriy modul)
try:
    from services.api.sprint_report_api import router as sprint_report_router
    app.include_router(sprint_report_router)
except ImportError:
    pass


# ============================================================================
# SINGLETON FACTORY FUNKSIYALAR
# (Barcha modullar shu funksiyalar orqali servislarni oladi)
# ============================================================================

_tz_pr_service = None
_comment_writer = None
_adf_formatter = None


def get_tz_pr_service() -> TZPRService:
    """
    TZPRService singleton — birinchi chaqiruvda yaratiladi.

    Lazy loading: import paytida emas, birinchi ishlatilganda JIRA/GitHub
    clientlari inizializatsiya qilinadi. Bu server startup vaqtini kamaytiradi.

    Returns:
        TZPRService — TZ-PR tahlil servisi
    """
    global _tz_pr_service
    if _tz_pr_service is None:
        _tz_pr_service = TZPRService()
    return _tz_pr_service


def get_comment_writer() -> JiraCommentWriter:
    """
    JiraCommentWriter singleton — JIRA'ga comment yozish uchun.

    Barcha comment yozuvchi funksiyalar (error_handler.py, service_runner.py)
    bu funksiya orqali bir xil instansiyadan foydalanadi.

    Returns:
        JiraCommentWriter — JIRA comment API wrapper
    """
    global _comment_writer
    if _comment_writer is None:
        _comment_writer = JiraCommentWriter()
    return _comment_writer


def get_adf_formatter() -> JiraADFFormatter:
    """
    JiraADFFormatter singleton — ADF format hujjatlar qurish uchun.

    ADF (Atlassian Document Format) — JIRA'ning yangi comment formati.
    Dropdown, panel, heading va boshqa boyitilgan elementlarni qo'llab-quvvatlaydi.

    Returns:
        JiraADFFormatter — ADF document builder
    """
    global _adf_formatter
    if _adf_formatter is None:
        _adf_formatter = JiraADFFormatter()
    return _adf_formatter


# Blocked retry scheduler uchun global task (startup'da yaratiladi)
_blocked_retry_task: Optional[asyncio.Task] = None


# ============================================================================
# WEBHOOK MODELS
# ============================================================================

class WebhookPayload(BaseModel):
    """
    JIRA webhook payload modeli.

    JIRA tomonidan yuborilgan JSON'ni validatsiya qilish uchun.
    Haqiqiy payload ancha katta — shu minimal maydonlar kerak.
    """
    webhookEvent: str
    issue: Dict[str, Any]
    changelog: Optional[Dict[str, Any]] = None


# ============================================================================
# ASOSIY WEBHOOK ENDPOINT
# ============================================================================

@app.post("/webhook/jira")
async def jira_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    JIRA webhook endpoint — barcha JIRA event'larini qabul qiluvchi asosiy nuqta.

    JIRA har safar issue yangilanganda bu endpoint'ga POST so'rov yuboradi.
    Sozlamalar (trigger status, threshold, skip_code) Admin panel orqali dinamik
    o'zgartiriladi va har webhook'da qayta o'qiladi.

    Ishlash mantiqi:
    1. Faqat 'jira:issue_updated' event'larini qabul qiladi, boshqalari ignored
    2. Changelog'dan status o'zgarishini topadi (field='status')
    3. Yangi status settings'dagi trigger status'lardan birimi? → davom etadi
    4. DB'da task holatini tekshiradi:
       - Yangi task → mark_progressing()
       - completed/error/returned/blocked → reset + mark_progressing()
       - progressing → ignored (dublikat oldini olish)
       - Dublikat event (bir xil status, progressing/completed) → ignored
    5. AI_SKIP kodi borligini tekshiradi:
       - Bor → Service1 o'chiriladi, skip notification yoziladi, faqat Service2 ishlaydi
    6. comment_order sozlamasiga qarab background task ishga tushiriladi:
       - 'parallel' + testcase → _run_task_group() (lock ichida ikkalasi)
       - faqat checker → _queued_check_tz_pr() (faqat Service1)
       - 'checker_first'/'testcase_first' → _run_sequential_tasks()

    Returns:
        JSON response:
        - {"status": "processing"} — task ishlanmoqda
        - {"status": "ignored"} — dublikat, noto'g'ri status, noto'g'ri event
        - {"status": "skipped_service1"} — AI_SKIP topildi
        - {"status": "error"} — kutilmagan xato
    """
    try:
        body = await request.json()
        event = body.get('webhookEvent', 'unknown')

        # Faqat issue update event'larni qabul qilamiz
        if event != "jira:issue_updated":
            return {"status": "ignored", "reason": f"event is '{event}'"}

        issue = body.get('issue', {})
        task_key = issue.get('key')

        if not task_key:
            log.warning("No task key found")
            return {"status": "error", "reason": "no task key"}

        # Changelog'dan status o'zgarishini topish (case-insensitive)
        changelog = body.get('changelog', {})
        items = changelog.get('items', [])

        status_changed = False
        new_status = None
        old_status = None

        for item in items:
            if item.get('field', '').lower() == 'status':
                old_status = item.get('fromString')
                new_status = item.get('toString')
                status_changed = True
                break

        if not status_changed:
            return {"status": "ignored", "reason": "status not changed", "debug_items": items}

        # Yangi status trigger status'lardan birimi?
        app_settings = get_app_settings(force_reload=False)
        settings = app_settings.tz_pr_checker
        target_statuses = settings.get_trigger_statuses()

        if new_status not in target_statuses:
            log.info(f"[{task_key}] SKIP -> {old_status} => {new_status} (trigger emas)")
            return {
                "status": "ignored",
                "reason": f"status is '{new_status}', not in {target_statuses}"
            }

        log.info("-" * 60)
        log.info(f"[{task_key}] STATUS -> {old_status} => {new_status} | tahlil boshlandi")

        # DB holat boshqaruvi (state machine)
        task_db = get_task(task_key)

        if not task_db:
            # Yangi task — DB'ga qo'shish
            mark_progressing(task_key, new_status, datetime.now())
        else:
            task_status = task_db.get('task_status', 'none')
            last_jira_status = task_db.get('last_jira_status')

            # Dublikat event: bir xil status, allaqachon ishlanmoqda yoki tugagan
            if last_jira_status == new_status and task_status in ('progressing', 'completed'):
                if task_status == 'progressing':
                    log.info(f"[{task_key}] SKIP -> task hozir jarayonda, qayta ishlanmaydi")
                else:
                    log.info(f"[{task_key}] SKIP -> task allaqachon bajarilgan (status={new_status}), o'tkazib yuborildi")
                return {
                    "status": "ignored",
                    "reason": f"Duplicate event: {new_status} already processing or completed",
                    "task_status": task_status
                }

            # Har holat uchun alohida tranzitsiya
            if task_status == 'none':
                mark_progressing(task_key, new_status, datetime.now())
            elif task_status in ('completed', 'error', 'blocked'):
                reset_service_statuses(task_key)
                mark_progressing(task_key, new_status, datetime.now())
            elif task_status == 'returned':
                # Qaytarilgan task yana keldi — return_count ko'payadi
                increment_return_count(task_key)
                reset_service_statuses(task_key)
                mark_progressing(task_key, new_status, datetime.now())
            elif task_status == 'progressing':
                log.info(f"[{task_key}] SKIP -> task hozir jarayonda, qayta ishlanmaydi")
                return {
                    "status": "ignored",
                    "reason": "Task already in progressing state",
                    "task_status": task_status
                }

        # AI_SKIP kodi tekshiruvi
        skip_code = settings.skip_code.strip() if settings.skip_code else ""
        if skip_code:
            comment_writer = get_comment_writer()
            skip_detected = await _check_skip_code(task_key, skip_code, comment_writer)
            if skip_detected:
                log.service_skip(task_key, "service_1", f"skip_code='{skip_code}'")

                # Service1 'skip' holatga — score=100 hisoblanadi (threshold o'tadi)
                set_service1_skip(task_key)

                # JIRA'ga skip notification yozish
                adf_formatter = get_adf_formatter()
                await _write_skip_notification(task_key, settings, comment_writer, adf_formatter)

                # Service2 faqat testcase trigger status bo'lsa ishlaydi
                testcase_should_run = is_testcase_trigger_status(new_status)
                if testcase_should_run:
                    background_tasks.add_task(
                        _run_testcase_generation, task_key=task_key, new_status=new_status
                    )
                    log.service_running(task_key, "service_2")

                return {
                    "status": "skipped_service1",
                    "task_key": task_key,
                    "reason": f"Skip code '{skip_code}' topildi",
                    "skipped_tasks": ["tz_pr_check"],
                    "running_tasks": ["testcase"] if testcase_should_run else []
                }

        # Background task'lar (comment_order sozlamasiga qarab)
        testcase_should_run = is_testcase_trigger_status(new_status)
        comment_order = settings.comment_order

        if comment_order == "parallel" or not testcase_should_run:
            if testcase_should_run:
                # Parallel mode: Service1 + Service2 bitta lock ichida
                log.info(f"[{task_key}] Starting task group (parallel mode)")
                background_tasks.add_task(
                    _run_task_group, task_key=task_key, new_status=new_status
                )
            else:
                # Faqat Service1
                background_tasks.add_task(
                    _queued_check_tz_pr, task_key=task_key, new_status=new_status
                )
        else:
            # Sequential mode: checker_first yoki testcase_first
            background_tasks.add_task(
                _run_sequential_tasks,
                task_key=task_key,
                new_status=new_status,
                first="checker" if comment_order == "checker_first" else "testcase",
                run_testcase=testcase_should_run
            )

        return {
            "status": "processing",
            "task_key": task_key,
            "old_status": old_status,
            "new_status": new_status,
            "message": "TZ-PR check started",
            "testcase_triggered": testcase_should_run,
            "comment_order": comment_order,
            "settings": {
                "use_adf": settings.use_adf_format,
                "auto_return": settings.auto_return_enabled,
                "threshold": settings.return_threshold
            }
        }

    except Exception as e:
        log.error(f"Webhook error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


# ============================================================================
# HTTP ENDPOINT'LAR
# ============================================================================

@app.get("/")
async def root():
    """
    Root endpoint — service holati va mavjud endpoint'lar ro'yxati.

    Monitoring va to'g'ri ishlayotganini tekshirish uchun.
    """
    app_settings = get_app_settings(force_reload=False)
    settings = app_settings.tz_pr_checker

    return {
        "service": "JIRA TZ-PR Auto Checker",
        "status": "running",
        "version": "4.0.0",
        "features": {
            "adf_format": settings.use_adf_format,
            "auto_return": settings.auto_return_enabled,
            "return_threshold": settings.return_threshold
        },
        "endpoints": {
            "webhook": "/webhook/jira",
            "manual_check": "/manual/check/{task_key}",
            "health": "/health",
            "settings": "/settings"
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint — monitoring tizimlari uchun.

    Tekshiradigan komponentlar:
    - tz_pr service: TZPRService instansiyasi yaratilganmi
    - jira_comment: JIRA client ulangan va ishlaydimi
    - settings: Konfiguratsiya yuklanganmi
    - database: DB fayl o'qilishi mumkinmi

    Returns:
        {"status": "healthy"|"unhealthy", "services": {...}}
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }

    try:
        tz_pr = get_tz_pr_service()
        health["services"]["tz_pr"] = "ok" if tz_pr else "error"
    except Exception as e:
        health["services"]["tz_pr"] = f"error: {str(e)}"
        health["status"] = "unhealthy"

    try:
        writer = get_comment_writer()
        health["services"]["jira_comment"] = "ok" if writer.jira else "error"
    except Exception as e:
        health["services"]["jira_comment"] = f"error: {str(e)}"
        health["status"] = "unhealthy"

    try:
        app_settings = get_app_settings(force_reload=False)
        settings = app_settings.tz_pr_checker
        health["services"]["settings"] = "ok"
        health["settings"] = {
            "use_adf": settings.use_adf_format,
            "auto_return": settings.auto_return_enabled,
            "threshold": settings.return_threshold,
            "trigger_status": settings.trigger_status
        }
    except Exception as e:
        health["services"]["settings"] = f"error: {str(e)}"

    # DB ulanishini tekshirish
    try:
        get_task("HEALTH_CHECK_PROBE")
        health["services"]["database"] = "ok"
    except Exception as e:
        health["services"]["database"] = f"error: {str(e)}"
        health["status"] = "unhealthy"

    return health


@app.get("/settings")
async def get_settings():
    """
    Joriy sozlamalarni ko'rsatish.

    Debugging va monitoring uchun — hozirgi konfiguratsiya qiymatlarini
    JSON formatida qaytaradi.
    """
    app_settings = get_app_settings(force_reload=False)
    settings = app_settings.tz_pr_checker

    return {
        "return_threshold": settings.return_threshold,
        "auto_return_enabled": settings.auto_return_enabled,
        "trigger_status": settings.trigger_status,
        "trigger_status_aliases": settings.trigger_status_aliases,
        "return_status": settings.return_status,
        "use_adf_format": settings.use_adf_format,
        "show_statistics": settings.show_statistics,
        "show_compliance_score": settings.show_compliance_score,
        "all_trigger_statuses": settings.get_trigger_statuses()
    }


@app.post("/manual/check/{task_key}")
async def manual_check(task_key: str, background_tasks: BackgroundTasks):
    """
    Manual TZ-PR check trigger — test va debugging uchun.

    JIRA webhook kelib chiqmasligi mumkin bo'lgan holatlarda yoki
    qayta tekshirish kerak bo'lganda qo'l bilan ishga tushirish.

    Trigger qiladi: Service1 (TZ-PR check) + agar auto_comment yoqilgan bo'lsa Service2

    Usage:
        curl -X POST http://localhost:8000/manual/check/DEV-1234
    """
    log.info(f"Manual check triggered for {task_key}")

    background_tasks.add_task(
        check_tz_pr_and_comment,
        task_key=task_key,
        new_status="Manual Check"
    )

    app_settings = get_app_settings(force_reload=False)
    tc_settings = app_settings.testcase_generator
    testcase_triggered = False

    if tc_settings.auto_comment_enabled:
        trigger_status = tc_settings.auto_comment_trigger_status
        background_tasks.add_task(
            _run_testcase_generation,
            task_key=task_key,
            new_status=trigger_status
        )
        testcase_triggered = True
        log.info(f"[{task_key}] Testcase generation also triggered (status='{trigger_status}')")

    return {
        "status": "processing",
        "task_key": task_key,
        "message": f"Manual TZ-PR check + Testcase generation started for {task_key}",
        "testcase_triggered": testcase_triggered
    }


@app.post("/manual/testcase/{task_key}")
async def manual_testcase(task_key: str, background_tasks: BackgroundTasks):
    """
    Manual testcase generation — faqat testcase yaratish (TZ-PR check emas).

    Service1 (TZ-PR) tugagan, lekin Service2 (Testcase) ishlamagan holatlarda
    qo'l bilan ishga tushirish uchun.

    Usage:
        curl -X POST http://localhost:8000/manual/testcase/DEV-1234
    """
    log.info(f"Manual testcase generation triggered for {task_key}")

    app_settings = get_app_settings(force_reload=False)
    tc_settings = app_settings.testcase_generator
    trigger_status = tc_settings.auto_comment_trigger_status

    background_tasks.add_task(
        _run_testcase_generation,
        task_key=task_key,
        new_status=trigger_status
    )

    return {
        "status": "processing",
        "task_key": task_key,
        "message": f"Manual testcase generation started for {task_key}",
        "trigger_status": trigger_status
    }


# ============================================================================
# STARTUP EVENT
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Server startup'da avtomatik ishga tushadigan vazifalar.

    Bajaradigan amallar:
    1. Uvicorn access log'larini o'chirish (har request uchun chiqadigan POST loglar spam)
    2. Tizim sozlamalarini log qilish
    3. Blocked retry scheduler'ni background task sifatida ishga tushirish
    """
    global _blocked_retry_task

    # Uvicorn access loglarini o'chirish
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    app_settings = get_app_settings(force_reload=False)
    settings = app_settings.tz_pr_checker

    log.system_started("4.0.0", 8000)
    log.settings_loaded(
        adf=settings.use_adf_format,
        auto_return=settings.auto_return_enabled,
        threshold=settings.return_threshold
    )
    log.info(f"TRIGGER       {settings.trigger_status}")
    log.info(f"RETRY-DELAY   {app_settings.queue.blocked_retry_delay} min")

    # Blocked retry scheduler ni background'da ishga tushirish
    _blocked_retry_task = asyncio.create_task(_blocked_retry_scheduler())


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "services.webhook.jira_webhook_handler:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
