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
from contextlib import asynccontextmanager, suppress
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
    set_task_timeout_error, reset_service_statuses, get_blocked_tasks_ready_for_retry,
    log_status_change, enqueue_background_job, get_background_queue_snapshot,
)

# Yangi modullar (biznes logika shu fayllarda)
from services.webhook.error_handler import (
    _classify_error,
    _write_success_comment,
    _write_error_comment,
    _write_critical_error,
    _write_skip_notification,
)
from services.webhook.skip_detector import _check_skip_code
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
)
from services.webhook.retry_scheduler import (
    _retry_blocked_task,
    _blocked_retry_scheduler,
)

log = get_logger("webhook.handler")

# ============================================================================
# SINGLETON FACTORY FUNKSIYALAR
# (Barcha modullar shu funksiyalar orqali servislarni oladi)
# ============================================================================

_tz_pr_service = None
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


def _normalize_filter_value(value: str) -> str:
    return str(value or "").strip().casefold()


def _is_allowed_issue_type(issue_type: str, allowed_types_raw: str) -> bool:
    allowed_types = [t.strip() for t in str(allowed_types_raw or "").split(",") if t.strip()]
    if not allowed_types:
        return True
    normalized_issue_type = _normalize_filter_value(issue_type)
    normalized_allowed = {_normalize_filter_value(item) for item in allowed_types}
    return normalized_issue_type in normalized_allowed


# Blocked retry scheduler uchun global task (startup'da yaratiladi)
_blocked_retry_task: Optional[asyncio.Task] = None
# Oxirgi log qilingan task — yangi task boshida separator uchun
_last_task_key: Optional[str] = None


def _webhook_execution_mode() -> str:
    raw = (os.getenv("APP_WEBHOOK_EXECUTION_MODE") or "inline").strip().lower()
    return raw if raw in {"inline", "queue"} else "inline"


def _worker_queue_enabled() -> bool:
    return _webhook_execution_mode() == "queue"


def _queue_job(
    *,
    job_type: str,
    task_key: str,
    company_id: int | None,
    new_status: str | None = None,
    include_testcase: bool | None = None,
    dedupe_key: str | None = None,
) -> dict[str, Any]:
    payload: Dict[str, Any] = {"task_key": task_key}
    if company_id is not None:
        payload["company_id"] = company_id
    if new_status is not None:
        payload["new_status"] = new_status
    if include_testcase is not None:
        payload["include_testcase"] = include_testcase
    return enqueue_background_job(
        job_type,
        task_key,
        company_id=company_id,
        payload=payload,
        dedupe_key=dedupe_key,
        max_attempts=5,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Server lifecycle boshqaruvi.

    Startup:
      - access log'larni pasaytirish
      - sozlamalarni log qilish
      - blocked retry scheduler ni ishga tushirish
    Shutdown:
      - scheduler taskini toza to'xtatish
    """
    global _blocked_retry_task

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    app_settings = get_app_settings(force_reload=False)
    settings = app_settings.webhook_tz_pr

    log.system_started("4.0.0", 8000)
    log.settings_loaded(
        adf=settings.use_adf_format,
        auto_return=settings.auto_return_enabled,
        threshold=settings.return_threshold
    )
    ai_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    ai_keys = 1
    i = 2
    while os.getenv(f"GOOGLE_API_KEY_{i}"):
        ai_keys += 1
        i += 1
    log.ai_ready(ai_model, ai_keys)
    log.info(f"TRIGGER       {settings.trigger_status}")
    log.info(f"RETRY-DELAY   {app_settings.queue.blocked_retry_delay} min")

    log.info(f"EXECUTION-MODE { _webhook_execution_mode() }")
    if not _worker_queue_enabled():
        _blocked_retry_task = asyncio.create_task(_blocked_retry_scheduler())

    try:
        yield
    finally:
        if _blocked_retry_task is not None:
            _blocked_retry_task.cancel()
            with suppress(asyncio.CancelledError):
                await _blocked_retry_task
            _blocked_retry_task = None


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="JIRA TZ-PR Auto Checker",
    description="Avtomatik TZ-PR moslik tekshirish + Testcase Auto-Comment + Sprint Report",
    version="4.0.0",
    lifespan=lifespan,
)


def _resolve_company_for_webhook(task_key: str, company_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Webhook uchun kompaniyani aniqlash."""
    from utils.auth.auth_db import get_company_by_code, get_company_by_project_key

    if company_code:
        company = get_company_by_code(company_code)
        if company and company.get("is_active"):
            return company
        return None

    return get_company_by_project_key(task_key.split('-')[0].upper())

# Sprint Report API ni ulash (ixtiyoriy modul)
try:
    from services.api.sprint_report_api import router as sprint_report_router
    app.include_router(sprint_report_router)
except ImportError:
    pass

# Monitoring API ni ulash (frontend/backend ajratishning birinchi slice'i)
try:
    from services.api.monitoring_api import router as monitoring_router
    app.include_router(monitoring_router)
except ImportError:
    pass

# Settings API ni ulash (Unified Settings ichidagi API keys slice'i)
try:
    from services.api.settings_api import router as settings_router
    app.include_router(settings_router)
except ImportError:
    pass

# Auth API ni ulash
try:
    from services.api.auth_api import router as auth_router
    app.include_router(auth_router)
except ImportError:
    pass

# TZ-PR API ni ulash
try:
    from services.api.tzpr_api import router as tzpr_router
    app.include_router(tzpr_router)
except ImportError:
    pass

# Testcase API ni ulash
try:
    from services.api.testcase_api import router as testcase_router
    app.include_router(testcase_router)
except ImportError:
    pass

# Internal RPC API ni ulash
try:
    from services.api.internal_rpc_api import router as internal_rpc_router
    app.include_router(internal_rpc_router)
except ImportError:
    pass


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

async def _jira_webhook_impl(
    request: Request,
    background_tasks: BackgroundTasks,
    company_code: Optional[str] = None,
):
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
    6. Background task ishga tushiriladi:
       - testcase trigger → _run_task_group() (Service1 → delay → Service2)
       - faqat checker → _queued_check_tz_pr() (faqat Service1)

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

        # Task o'zgarganda ajratuvchi — har bir yangi task (7235, 7359, ...) alohida blok
        global _last_task_key
        if _last_task_key is not None and _last_task_key != task_key:
            log.request_separator()
        _last_task_key = task_key

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

        # Tavsiya etilgan routing: company-specific endpoint.
        # Legacy endpoint faqat backward compatibility uchun qoldirilgan.
        from config.app_settings import get_app_settings_for_company
        project_key = task_key.split('-')[0].upper()
        company = _resolve_company_for_webhook(task_key, company_code)
        if company:
            company_id = company['id']
            app_settings = get_app_settings_for_company(company_id)
            log.info(f"[{task_key}] Company: {company.get('company_code')} (id={company_id})")
        else:
            if company_code:
                log.warning(f"[{task_key}] Company code '{company_code}' uchun kompaniya topilmadi — ignored")
                return {"status": "ignored", "reason": f"unknown company code '{company_code}'"}
            log.warning(f"[{task_key}] Project key '{project_key}' uchun kompaniya topilmadi yoki ambiguous — ignored")
            return {"status": "ignored", "reason": f"unknown or ambiguous project key '{project_key}'"}

        # Yangi status trigger status'lardan birimi?
        settings = app_settings.webhook_tz_pr
        target_statuses = settings.get_trigger_statuses()

        if new_status.lower() not in [s.lower() for s in target_statuses]:
            log.info(f"[{task_key}] SKIP -> {old_status} => {new_status} (trigger emas)")
            return {
                "status": "ignored",
                "reason": f"status is '{new_status}', not in {target_statuses}"
            }

        # Webhook payload'dan issue fields ni olish (qo'shimcha API kerak emas)
        issue_fields = issue.get('fields', {})

        # ━━━ FILTER 1: Issue Type ━━━
        issue_type = (issue_fields.get('issuetype') or {}).get('name', '')
        allowed_types_raw = settings.allowed_issue_types.strip()
        if allowed_types_raw:
            allowed_types = [t.strip() for t in allowed_types_raw.split(',') if t.strip()]
            if not _is_allowed_issue_type(issue_type, allowed_types_raw):
                log.info(f"[{task_key}] SKIP → type '{issue_type}' allowed list da yo'q {allowed_types}")
                return {
                    "status": "ignored",
                    "reason": f"Issue type '{issue_type}' not in allowed list",
                    "issue_type": issue_type,
                    "allowed_types": allowed_types
                }

        # ━━━ FILTER 2: Assignee ━━━
        assignee_name = (issue_fields.get('assignee') or {}).get('displayName', '')
        excluded_raw = settings.excluded_assignees.strip()
        if excluded_raw and assignee_name:
            excluded = [a.strip() for a in excluded_raw.split(',') if a.strip()]
            if assignee_name in excluded:
                log.info(f"[{task_key}] SKIP → assignee '{assignee_name}' excluded ro'yxatida")
                return {
                    "status": "ignored",
                    "reason": f"Assignee '{assignee_name}' is in excluded list",
                    "assignee": assignee_name
                }

        log.request_separator()
        log.ai_request("KEY_1", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
        log.info(f"[{task_key}] STATUS -> {old_status} => {new_status} | tahlil boshlandi")

        # Story points (JIRA customfield_10016)
        from config.settings import settings as _cfg_settings
        sp_field = getattr(_cfg_settings, 'STORY_POINTS_FIELD', 'customfield_10016')
        raw_sp = issue_fields.get(sp_field)
        try:
            story_points = float(raw_sp) if raw_sp is not None else None
        except (TypeError, ValueError):
            story_points = None

        # Status o'zgarishini tarixga yozish (sprint report uchun)
        log_status_change(
            task_id=task_key,
            from_status=old_status,
            to_status=new_status,
            changed_at=datetime.now(),
            assignee=assignee_name or None,
            story_points=story_points,
            issue_type=issue_type or None,
            company_id=company_id,
        )

        # DB holat boshqaruvi (state machine)
        task_db = get_task(task_key)

        if not task_db:
            # Yangi task — DB'ga qo'shish
            mark_progressing(task_key, new_status, datetime.now(), company_id=company_id)
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
                mark_progressing(task_key, new_status, datetime.now(), company_id=company_id)
            elif task_status in ('completed', 'error', 'blocked'):
                reset_service_statuses(task_key)
                mark_progressing(task_key, new_status, datetime.now(), company_id=company_id)
            elif task_status == 'returned':
                # Qaytarilgan task yana keldi — return_count ko'payadi
                increment_return_count(task_key)
                reset_service_statuses(task_key)
                mark_progressing(task_key, new_status, datetime.now(), company_id=company_id)
            elif task_status == 'progressing':
                log.info(f"[{task_key}] SKIP -> task hozir jarayonda, qayta ishlanmaydi")
                return {
                    "status": "ignored",
                    "reason": "Task already in progressing state",
                    "task_status": task_status
                }

        # AI_SKIP kodi tekshiruvi
        skip_code = settings.skip_code.strip() if settings.skip_code else ""
        from utils.pr_cache import set_skip_cache
        from utils.auth.auth_db import get_company_credentials
        skip_detected = False
        _skip_writer = None
        if skip_code:
            try:
                from utils.auth.auth_db import get_company_webhook_credentials
                _creds = get_company_webhook_credentials(company_id)
                _skip_writer = JiraCommentWriter(
                    server=_creds['jira_server'],
                    email=_creds['jira_email'],
                    token=_creds['jira_token'],
                )
                skip_detected = await _check_skip_code(
                    task_key,
                    skip_code,
                    _skip_writer,
                    max_comments=settings.max_skip_check_comments,
                )
            except Exception as skip_error:
                log.warning(f"[{task_key}] AI_SKIP tekshiruvi o'tkazib yuborildi: {skip_error}")
        set_skip_cache(task_key, skip_detected)
        if skip_detected:
            log.service_skip(task_key, "service_1", f"skip_code='{skip_code}'")

            # Service1 'skip' holatga — score=100 hisoblanadi (threshold o'tadi)
            set_service1_skip(task_key)

            # JIRA'ga skip notification yozish
            adf_formatter = get_adf_formatter()
            if _skip_writer is not None:
                await _write_skip_notification(task_key, settings, _skip_writer, adf_formatter)

            # Service2 faqat testcase trigger status bo'lsa ishlaydi
            testcase_should_run = is_testcase_trigger_status(new_status, app_settings)
            if testcase_should_run:
                if _worker_queue_enabled():
                    _queue_job(
                        job_type="run_testcase_generation",
                        task_key=task_key,
                        company_id=company_id,
                        new_status=new_status,
                        dedupe_key=f"testcase:{company_id}:{task_key}",
                    )
                else:
                    background_tasks.add_task(
                        _run_testcase_generation, task_key=task_key, new_status=new_status,
                        company_id=company_id
                    )
                log.service_running(task_key, "service_2")

            return {
                "status": "queued" if _worker_queue_enabled() else "skipped_service1",
                "task_key": task_key,
                "reason": f"Skip code '{skip_code}' topildi",
                "skipped_tasks": ["tz_pr_check"],
                "running_tasks": ["testcase"] if testcase_should_run else []
            }

        # Background task'lar: har doim Service1 → delay → Service2
        testcase_should_run = is_testcase_trigger_status(new_status, app_settings)

        if testcase_should_run:
            if _worker_queue_enabled():
                _queue_job(
                    job_type="run_task_group",
                    task_key=task_key,
                    company_id=company_id,
                    new_status=new_status,
                    dedupe_key=f"group:{company_id}:{task_key}",
                )
            else:
                # Service1 + Service2 bitta lock ichida (Service1 tugagach Service2)
                background_tasks.add_task(
                    _run_task_group, task_key=task_key, new_status=new_status, company_id=company_id
                )
        else:
            if _worker_queue_enabled():
                _queue_job(
                    job_type="run_checker_only",
                    task_key=task_key,
                    company_id=company_id,
                    new_status=new_status,
                    dedupe_key=f"checker:{company_id}:{task_key}",
                )
            else:
                # Faqat Service1
                background_tasks.add_task(
                    _queued_check_tz_pr, task_key=task_key, new_status=new_status, company_id=company_id
                )

        return {
            "status": "queued" if _worker_queue_enabled() else "processing",
            "task_key": task_key,
            "old_status": old_status,
            "new_status": new_status,
            "message": "TZ-PR check queued" if _worker_queue_enabled() else "TZ-PR check started",
            "testcase_triggered": testcase_should_run,
            "settings": {
                "use_adf": settings.use_adf_format,
                "auto_return": settings.auto_return_enabled,
                "threshold": settings.return_threshold
            }
        }

    except Exception as e:
        log.error(f"Webhook error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


@app.post("/webhook/jira")
async def jira_webhook(request: Request, background_tasks: BackgroundTasks):
    return await _jira_webhook_impl(request, background_tasks, company_code=None)


@app.post("/webhook/jira/{company_code}")
async def jira_webhook_company(request: Request, background_tasks: BackgroundTasks, company_code: str):
    return await _jira_webhook_impl(request, background_tasks, company_code=company_code.strip().lower())


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
    settings = app_settings.webhook_tz_pr

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
        health["services"]["jira_comment"] = "ok" if JiraCommentWriter else "error"
    except Exception as e:
        health["services"]["jira_comment"] = f"error: {str(e)}"
        health["status"] = "unhealthy"

    try:
        app_settings = get_app_settings(force_reload=False)
        settings = app_settings.webhook_tz_pr
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

    health["services"]["execution_mode"] = _webhook_execution_mode()
    if _worker_queue_enabled():
        health["queue"] = get_background_queue_snapshot()

    return health


@app.get("/settings")
async def get_settings():
    """
    Joriy sozlamalarni ko'rsatish.

    Debugging va monitoring uchun — hozirgi konfiguratsiya qiymatlarini
    JSON formatida qaytaradi.
    """
    app_settings = get_app_settings(force_reload=False)
    settings = app_settings.webhook_tz_pr

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

    app_settings = get_app_settings(force_reload=False)
    tc_settings = app_settings.webhook_testcase
    testcase_triggered = bool(tc_settings.auto_comment_enabled)

    if _worker_queue_enabled():
        _queue_job(
            job_type="manual_check",
            task_key=task_key,
            company_id=None,
            include_testcase=testcase_triggered,
            dedupe_key=f"manual:{task_key}",
        )
    else:
        background_tasks.add_task(
            check_tz_pr_and_comment,
            task_key=task_key,
            new_status="Manual Check"
        )

        if testcase_triggered:
            trigger_status = tc_settings.auto_comment_trigger_status
            background_tasks.add_task(
                _run_testcase_generation,
                task_key=task_key,
                new_status=trigger_status
            )
            log.info(f"[{task_key}] Testcase generation also triggered (status='{trigger_status}')")

    return {
        "status": "queued" if _worker_queue_enabled() else "processing",
        "task_key": task_key,
        "message": (
            f"Manual TZ-PR check + Testcase generation queued for {task_key}"
            if _worker_queue_enabled()
            else f"Manual TZ-PR check + Testcase generation started for {task_key}"
        ),
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
    tc_settings = app_settings.webhook_testcase
    trigger_status = tc_settings.auto_comment_trigger_status

    if _worker_queue_enabled():
        _queue_job(
            job_type="run_testcase_generation",
            task_key=task_key,
            company_id=None,
            new_status=trigger_status,
            dedupe_key=f"manual-testcase:{task_key}",
        )
    else:
        background_tasks.add_task(
            _run_testcase_generation,
            task_key=task_key,
            new_status=trigger_status
        )

    return {
        "status": "queued" if _worker_queue_enabled() else "processing",
        "task_key": task_key,
        "message": (
            f"Manual testcase generation queued for {task_key}"
            if _worker_queue_enabled()
            else f"Manual testcase generation started for {task_key}"
        ),
        "trigger_status": trigger_status
    }


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
