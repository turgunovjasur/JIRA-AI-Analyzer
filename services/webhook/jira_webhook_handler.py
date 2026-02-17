"""
JIRA Webhook Service - VERSION 3.0 WITH TESTCASE AUTO-COMMENT
==============================================================

Yangiliklar v3.0:
- Testcase auto-comment (Ready to Test statusda)
- Yagona sozlamalar tizimi (app_settings)

Yangiliklar v2.0:
- ADF format (dropdown/expand panel) qo'llab-quvvatlash
- Dinamik status nomlari (Admin panel orqali)
- Avtomatik Return (moslik past bo'lganda)
- Dinamik threshold sozlamalari

Author: JASUR TURGUNOV
Date: 2026-02-03
Version: 3.0
"""
from fastapi import FastAPI, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
from datetime import datetime
import logging
import sys
import os
import asyncio
import requests
from dotenv import load_dotenv

# Loyiha root path qo'shish
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# New structured logger
from core.logger import get_logger

# Core imports
from services.checkers.tz_pr_checker import TZPRService
from utils.jira.jira_comment_writer import JiraCommentWriter

# Yangi imports - ADF va Settings
from utils.jira.jira_adf_formatter import JiraADFFormatter
from utils.jira.jira_status_manager import get_status_manager

# Yagona sozlamalar (v4.0) - tz_pr_settings.py olib tashlandi
from config.app_settings import get_app_settings, TZPRCheckerSettings

# Testcase auto-comment (v3.0)
from services.webhook.testcase_webhook_handler import (
    is_testcase_trigger_status,
    generate_testcases_sync,
    check_and_generate_testcases
)

# DB helper (v4.0 - DB bilan boshqarish)
from utils.database.task_db import (
    get_task,
    mark_progressing,
    mark_completed,
    mark_returned,
    mark_error,
    mark_blocked,
    increment_return_count,
    set_skip_detected,
    set_service1_done,
    set_service1_error,
    set_service1_skip,
    set_service1_blocked,
    set_service2_done,
    set_service2_error,
    set_service2_blocked,
    set_task_timeout_error,
    reset_service_statuses,
    get_blocked_tasks_ready_for_retry
)

# ============================================================================
# WINDOWS ENCODING FIX (cp1251 emoji error)
# ============================================================================
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ============================================================================
# LOGGING SETUP
# ============================================================================
# New structured logger
log = get_logger("webhook.handler")

# ============================================================================
# FASTAPI APP
# ============================================================================
app = FastAPI(
    title="JIRA TZ-PR Auto Checker",
    description="Avtomatik TZ-PR moslik tekshirish + Testcase Auto-Comment + Sprint Report",
    version="3.1.0"
)

# Mount Sprint Report API
try:
    from services.api.sprint_report_api import router as sprint_report_router
    app.include_router(sprint_report_router)
    log.info("Sprint Report API mounted at /api/sprint-report")
except ImportError as e:
    log.warning(f"Sprint Report API not available: {e}")

# Services (lazy loading)
_tz_pr_service = None
_comment_writer = None
_adf_formatter = None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GLOBAL AI QUEUE (Rate Limit Himoya)
# Task-level ordering: bitta task'ning barcha AI chaqrishlari
# birma-bir ketadi, boshqa task kutadi.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_ai_queue_lock: Optional[asyncio.Lock] = None
_ai_last_call_time: float = 0.0


def _get_ai_queue_lock() -> asyncio.Lock:
    """AI queue lock — lazy singleton"""
    global _ai_queue_lock
    if _ai_queue_lock is None:
        _ai_queue_lock = asyncio.Lock()
    return _ai_queue_lock


def get_tz_pr_service():
    """TZ-PR service - singleton"""
    global _tz_pr_service
    if _tz_pr_service is None:
        _tz_pr_service = TZPRService()
    return _tz_pr_service


def get_comment_writer():
    """Comment writer - singleton"""
    global _comment_writer
    if _comment_writer is None:
        _comment_writer = JiraCommentWriter()
    return _comment_writer


def get_adf_formatter():
    """ADF Formatter - singleton"""
    global _adf_formatter
    if _adf_formatter is None:
        _adf_formatter = JiraADFFormatter()
    return _adf_formatter


# ============================================================================
# ERROR CLASSIFICATION (v6.0)
# ============================================================================

def _classify_error(error_msg: str) -> str:
    """
    Xato xabarini turlariga ajratish

    Returns:
        'pr_not_found' — PR topilmadi
        'ai_timeout' — AI timeout yoki 429 rate limit (ikkala key ham ishlamadi)
        'ai_rate_limit' — 429 rate limit (alohida kategoriya)
        'unknown' — boshqa xatoliklar
    """
    if not error_msg:
        return 'unknown'
    msg_lower = error_msg.lower()

    # PR topilmadi
    pr_keywords = ['pr topilmadi', 'pr not found', 'no pr found', 'pull request not found']
    if any(kw in msg_lower for kw in pr_keywords):
        return 'pr_not_found'

    # AI timeout / rate limit / 429 (ikkala key ham ishlamadi ham kiradi)
    ai_timeout_keywords = [
        'timeout', '429', 'rate limit', 'rate_limit',
        'overloaded', 'quota', 'resource exhausted',
        'resource_exhausted', 'too many requests',
        'ikkala key ham ishlamadi', 'both keys failed',
        'gemini api xatosi'
    ]
    if any(kw in msg_lower for kw in ai_timeout_keywords):
        return 'ai_timeout'

    return 'unknown'


# Blocked retry scheduler o'zgaruvchisi
_blocked_retry_task: Optional[asyncio.Task] = None


# ============================================================================
# WEBHOOK MODELS
# ============================================================================

class WebhookPayload(BaseModel):
    """JIRA webhook payload (simplified)"""
    webhookEvent: str
    issue: Dict[str, Any]
    changelog: Optional[Dict[str, Any]] = None


# ============================================================================
# MAIN WEBHOOK ENDPOINT
# ============================================================================

@app.post("/webhook/jira")
async def jira_webhook(
        request: Request,
        background_tasks: BackgroundTasks
):
    """
    JIRA webhook endpoint

    JIRA bu endpoint'ga har safar issue update bo'lganda request yuboradi.
    Sozlamalar Admin panel orqali dinamik o'zgartiriladi.
    """
    try:
        # Raw data olish
        body = await request.json()

        log.request_separator()
        event = body.get('webhookEvent', 'unknown')
        log.info(f"Webhook event: {event}")

        # Faqat issue update'larni qabul qilamiz
        if event != "jira:issue_updated":
            log.info(f"Event '{event}' ignored (not issue update)")
            return {"status": "ignored", "reason": f"event is '{event}'"}

        # Issue data
        issue = body.get('issue', {})
        task_key = issue.get('key')

        if not task_key:
            log.warning("No task key found")
            return {"status": "error", "reason": "no task key"}

        log.webhook_received(task_key, event)

        # Changelog tekshirish
        changelog = body.get('changelog', {})
        items = changelog.get('items', [])

        # Status o'zgarishini topish
        status_changed = False
        new_status = None
        old_status = None

        for item in items:
            # Case-insensitive check: "status", "Status", "STATUS" ham tushadi
            if item.get('field', '').lower() == 'status':
                old_status = item.get('fromString')
                new_status = item.get('toString')
                status_changed = True
                break

        if not status_changed:
            # Debug: changelog nima o'z ichiga olib — server logda ko'rish mumkin
            log.info(f"[{task_key}] Status o'zgarishi yo'q. Changelog items: {items}")
            return {"status": "ignored", "reason": "status not changed", "debug_items": items}

        log.status_changed(task_key, old_status, new_status)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # DINAMIK STATUS TEKSHIRISH (Admin sozlamalaridan)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # force_reload=True - har safar fayldan o'qish (UI'da o'zgartirilgan sozlamalar uchun)
        app_settings = get_app_settings(force_reload=True)
        settings = app_settings.tz_pr_checker
        target_statuses = settings.get_trigger_statuses()

        log.info(f"[{task_key}] Target statuses: {target_statuses}")

        if new_status not in target_statuses:
            log.status_ignored(task_key, new_status, "not in target list")
            return {
                "status": "ignored",
                "reason": f"status is '{new_status}', not in {target_statuses}"
            }

        # BINGO! Target statusga o'tdi
        log.target_status_matched(task_key, new_status)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # DB HOLAT TEKSHIRISH (v4.0)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        task_db = get_task(task_key)

        # Task DB da yo'q bo'lsa - yangi task (yoki o'chirilgan task), to'g'ridan-to'g'ri ishlash
        if not task_db:
            log.info(f"[{task_key}] Task DB da yo'q - yangi task (yoki manual delete qilingan), to'g'ridan-to'g'ri ishlash")
            mark_progressing(task_key, new_status, datetime.now())
            log.db_state_updated(task_key, "none", "progressing")
        else:
            task_status = task_db.get('task_status', 'none')
            return_count = task_db.get('return_count', 0)
            last_jira_status = task_db.get('last_jira_status')
            last_processed_at = task_db.get('last_processed_at')

            log.db_state_checked(task_key, task_status, return_count, last_jira_status)

            # Dublikat event tekshirish - faqat task DB da bo'lsa va progressing bo'lsa
            # COMPLETED holatida emas - chunki task ishlanib bo'lgan bo'lsa qayta ishlanmasligi kerak
            if last_jira_status == new_status and task_status in ('progressing', 'completed'):
                log.info(f"[{task_key}] Dublikat event: {new_status} allaqachon ishlanmoqda/ishlanib bo'lgan (task_status={task_status})")
                return {
                    "status": "ignored",
                    "reason": f"Duplicate event: {new_status} already processing or completed",
                    "task_status": task_status
                }

            # Task holatini yangilash
            if task_status == 'none':
                mark_progressing(task_key, new_status, datetime.now())
                log.db_state_updated(task_key, task_status, "progressing")
            elif task_status == 'completed':
                # Completed taskni qayta ishlash uchun reset qilish
                log.db_reset(task_key, "completed task reprocessing")
                reset_service_statuses(task_key)
                mark_progressing(task_key, new_status, datetime.now())
            elif task_status == 'error':
                # Error holatida service statuslarni reset qilish kerak (oldingi ishlashda error bo'lgan bo'lishi mumkin)
                reset_service_statuses(task_key)
                mark_progressing(task_key, new_status, datetime.now())
                log.db_state_updated(task_key, "error", "progressing")
            elif task_status == 'returned':
                increment_return_count(task_key)
                reset_service_statuses(task_key)  # Service statuslarni qayta boshlash
                mark_progressing(task_key, new_status, datetime.now())
                new_return_count = get_task(task_key).get('return_count', 0) if get_task(task_key) else 0
                log.db_state_updated(task_key, "returned", "progressing")
                log.info(f"[{task_key}] return_count: {return_count} → {new_return_count}")
            elif task_status == 'blocked':
                # Blocked task qayta kelsa — reset va progressing
                reset_service_statuses(task_key)
                mark_progressing(task_key, new_status, datetime.now())
                log.db_state_updated(task_key, "blocked", "progressing")
            elif task_status == 'progressing':
                log.info(f"[{task_key}] Task allaqachon progressing, skip")
                return {
                    "status": "ignored",
                    "reason": "Task already in progressing state",
                    "task_status": task_status
                }

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # AI_SKIP SHARTI (v5.0 - birinchi urinishda ham ishlaydi)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        skip_code = settings.skip_code.strip() if settings.skip_code else ""
        if skip_code:
            # return_count sharti olib tashlandi - birinchi urinishda ham ishlaydi
            comment_writer = get_comment_writer()
            skip_detected = await _check_skip_code(task_key, skip_code, comment_writer)
            if skip_detected:
                log.info(f"[{task_key}] Skip code '{skip_code}' topildi, Service1 skip, Service2 run")

                # Mark Service1 as skip (score=100 threshold check o'tishi uchun)
                set_service1_skip(task_key)

                # Write skip notification
                adf_formatter = get_adf_formatter()
                await _write_skip_notification(task_key, settings, comment_writer, adf_formatter)

                # Run Service2 ONLY if testcase trigger matches
                testcase_should_run = is_testcase_trigger_status(new_status)
                if testcase_should_run:
                    background_tasks.add_task(_run_testcase_generation, task_key=task_key, new_status=new_status)
                    log.service_started(task_key, "Testcase-Generator")

                return {
                    "status": "skipped_service1",
                    "task_key": task_key,
                    "reason": f"Skip code '{skip_code}' topildi",
                    "skipped_tasks": ["tz_pr_check"],
                    "running_tasks": ["testcase"] if testcase_should_run else []
                }

        # Queue sozlamalari
        queue_settings = app_settings.queue
        log.info(f"[{task_key}] Queue sozlamalari: enabled={queue_settings.queue_enabled}, timeout={queue_settings.task_wait_timeout}s, delay={queue_settings.checker_testcase_delay}s")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # BACKGROUND TASKS (checker + testcase)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        testcase_should_run = is_testcase_trigger_status(new_status)
        comment_order = settings.comment_order

        if comment_order == "parallel" or not testcase_should_run:
            if testcase_should_run:
                # Parallel mode + testcase: task group ile (task-level lock)
                log.info(f"[{task_key}] Starting task group (parallel mode)")
                background_tasks.add_task(
                    _run_task_group,
                    task_key=task_key,
                    new_status=new_status
                )
            else:
                # Faqat checker
                background_tasks.add_task(
                    _queued_check_tz_pr,
                    task_key=task_key,
                    new_status=new_status
                )
        else:
            # Sequential mode: bitta background task, ichida order
            log.info(f"[{task_key}] Sequential mode: {comment_order}")
            background_tasks.add_task(
                _run_sequential_tasks,
                task_key=task_key,
                new_status=new_status,
                first="checker" if comment_order == "checker_first" else "testcase",
                run_testcase=testcase_should_run
            )

        testcase_triggered = testcase_should_run

        return {
            "status": "processing",
            "task_key": task_key,
            "old_status": old_status,
            "new_status": new_status,
            "message": "TZ-PR check started",
            "testcase_triggered": testcase_triggered,
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
# BACKGROUND TASK - TZ-PR CHECK (YANGILANGAN)
# ============================================================================

async def check_tz_pr_and_comment(task_key: str, new_status: str):
    """
    Background task: TZ-PR mosligini tekshirish va comment yozish (Service1)

    Yangi funksionalliklar (v4.0):
    - DB orqali Service1 holatini boshqarish
    - Score threshold tekshiruvi va testcase bloklash
    - Xatolarda DB holatini yangilash
    """
    try:
        log.service_started(task_key, "TZ-PR-Checker")

        # DB holatini tekshirish
        task_db = get_task(task_key)
        service1_status = task_db.get('service1_status', 'pending') if task_db else 'pending'

        if service1_status == 'done':
            log.info(f"[{task_key}] Service1 allaqachon done, skip")
            return

        # Settings yuklash (force_reload=True - har safar fayldan o'qish)
        app_settings = get_app_settings(force_reload=True)
        settings = app_settings.tz_pr_checker
        log.settings_loaded(
            adf=settings.use_adf_format,
            auto_return=settings.auto_return_enabled,
            threshold=settings.return_threshold
        )

        # Services
        tz_pr_service = get_tz_pr_service()
        comment_writer = get_comment_writer()
        adf_formatter = get_adf_formatter()

        # RE-CHECK DETECT
        # Oldingi status return_status bo'lsa bu re-check
        is_recheck = await _detect_recheck(task_key, settings, comment_writer)
        if is_recheck:
            log.info(f"[{task_key}] Re-check detected (task qaytarildigan so'ng)")

        # 1. TZ-PR tahlil qilish
        log.ai_analyzing(task_key, "gemini-2.5-flash")
        result = tz_pr_service.analyze_task(task_key)

        if not result.success:
            error_msg = result.error_message
            error_type = _classify_error(error_msg)
            log.service_failed(task_key, "TZ-PR-Checker", f"{error_msg} (type: {error_type})")

            if error_type == 'ai_timeout':
                # AI timeout/429 → blocked status
                app_settings_reload = get_app_settings(force_reload=True)
                retry_minutes = app_settings_reload.queue.blocked_retry_delay
                set_service1_blocked(task_key, error_msg, retry_minutes)
                log.info(f"[{task_key}] Service1 BLOCKED: {retry_minutes} daqiqadan keyin qayta urinadi")
            elif error_type == 'pr_not_found':
                # PR topilmadi → error, lekin service2 pending qoladi
                set_service1_error(task_key, error_msg, keep_service2_pending=True)
                log.info(f"[{task_key}] PR topilmadi: service2 pending qoladi")
            else:
                # Boshqa xatolar → oddiy error
                set_service1_error(task_key, error_msg)

            await _write_error_comment(
                task_key, error_msg, new_status,
                settings, comment_writer, adf_formatter
            )
            return

        # 2. Comment yozish (ADF yoki oddiy format)
        log.info(f"[{task_key}] Writing comment to JIRA...")
        await _write_success_comment(
            task_key, result, new_status,
            settings, comment_writer, adf_formatter,
            is_recheck=is_recheck
        )

        # 3. Service1 holatini 'done' ga o'zgartirish
        compliance_score = result.compliance_score
        set_service1_done(task_key, compliance_score)
        log.service_completed(task_key, "TZ-PR-Checker", f"score={compliance_score}%")

        # 4. Score threshold tekshiruvi va avtomatik Return
        if settings.auto_return_enabled and compliance_score is not None:
            threshold = settings.return_threshold
            passed = compliance_score >= threshold
            log.score_evaluated(task_key, compliance_score, threshold, passed)

            if not passed:
                log.task_returning(task_key, settings.return_status, compliance_score)
                await _handle_auto_return(task_key, result, settings)
                # Task qaytarilgan, testcase ishlamaydi
                mark_returned(task_key)
                log.info(f"[{task_key}] Task returned, Service2 (testcase) bloklangan")
            else:
                log.info(f"[{task_key}] Score OK: Service2 ishlaydi")

    except Exception as e:
        error_msg = str(e)
        error_type = _classify_error(error_msg)
        log.service_failed(task_key, "TZ-PR-Checker", f"{e} (type: {error_type})")
        log.error(f"[{task_key}] Service1 Background task error details", exc_info=True)

        if error_type == 'ai_timeout':
            app_settings_reload = get_app_settings(force_reload=True)
            retry_minutes = app_settings_reload.queue.blocked_retry_delay
            set_service1_blocked(task_key, error_msg, retry_minutes)
            log.info(f"[{task_key}] Service1 BLOCKED (exception): {retry_minutes} daqiqadan keyin")
        elif error_type == 'pr_not_found':
            set_service1_error(task_key, error_msg, keep_service2_pending=True)
        else:
            set_service1_error(task_key, error_msg)

        # Critical error ham yoziladi
        try:
            app_settings = get_app_settings(force_reload=True)
            settings = app_settings.tz_pr_checker
            await _write_critical_error(
                task_key, error_msg, new_status,
                settings, get_comment_writer(), get_adf_formatter()
            )
        except:
            pass


async def _write_success_comment(
        task_key: str,
        result: Any,
        new_status: str,
        settings: TZPRCheckerSettings,
        comment_writer: JiraCommentWriter,
        adf_formatter: JiraADFFormatter,
        is_recheck: bool = False
):
    """Muvaffaqiyatli tahlil uchun comment yozish"""
    try:
        # Settings always has ADF enabled (hardcoded in config), but keeping check for safety
        # ADF format (dropdown'li) with contradictory comments panel
        comment_analysis = getattr(result, 'comment_analysis', None)

        # Zid commentlar panelini ko'rsatish/yashirish sozlamasi
        if not settings.show_contradictory_comments:
            comment_analysis = None
        adf_doc = adf_formatter.build_comment_document(
            result,
            new_status,
            comment_analysis=comment_analysis,
            footer_text=settings.tz_pr_footer_text,
            is_recheck=is_recheck,
            recheck_text=settings.recheck_comment_text,
            visible_sections=settings.visible_sections
        )
        success = comment_writer.add_comment_adf(task_key, adf_doc)

        if not success:
            # Fallback - oddiy format
            log.warning(f"[{task_key}] ADF failed, falling back to simple format")
            simple_comment = adf_formatter.build_simple_comment(result, new_status)
            comment_writer.add_comment(task_key, simple_comment)
            log.jira_comment_added(task_key, "simple")
        else:
            log.jira_comment_added(task_key, "ADF")

    except Exception as e:
        log.error(f"[{task_key}] Comment yozishda xato: {e}")


async def _write_error_comment(
        task_key: str,
        error_message: str,
        new_status: str,
        settings: TZPRCheckerSettings,
        comment_writer: JiraCommentWriter,
        adf_formatter: JiraADFFormatter
):
    """Xatolik uchun comment yozish"""
    try:
        if settings.use_adf_format:
            adf_doc = adf_formatter.build_error_document(task_key, error_message, new_status)
            success = comment_writer.add_comment_adf(task_key, adf_doc)

            if not success:
                # Fallback
                simple_comment = format_error_comment_simple(task_key, error_message, new_status)
                comment_writer.add_comment(task_key, simple_comment)
        else:
            simple_comment = format_error_comment_simple(task_key, error_message, new_status)
            comment_writer.add_comment(task_key, simple_comment)

    except Exception as e:
        log.error(f"[{task_key}] Error comment yozishda xato: {e}")


async def _write_critical_error(
        task_key: str,
        error: str,
        new_status: str,
        settings: TZPRCheckerSettings,
        comment_writer: JiraCommentWriter,
        adf_formatter: JiraADFFormatter
):
    """Kritik xatolik uchun comment yozish"""
    try:
        if settings.use_adf_format:
            adf_doc = adf_formatter.build_critical_error_document(task_key, error, new_status)
            comment_writer.add_comment_adf(task_key, adf_doc)
        else:
            simple_comment = format_critical_error_simple(task_key, error, new_status)
            comment_writer.add_comment(task_key, simple_comment)

    except Exception as e:
        log.error(f"[{task_key}] Critical error comment yozishda xato: {e}")


async def _handle_auto_return(task_key: str, result: Any, settings: TZPRCheckerSettings):
    """Avtomatik Return logikasi (v4.0)"""
    try:
        score = result.compliance_score
        threshold = settings.return_threshold

        if score < threshold:
            log.task_returning(task_key, settings.return_status, score)

            status_manager = get_status_manager()
            success, msg = status_manager.auto_return_if_needed(
                task_key=task_key,
                compliance_score=score,
                threshold=threshold,
                return_status=settings.return_status,
                enabled=settings.auto_return_enabled
            )

            if success:
                log.jira_transitioned(task_key, settings.return_status)

                # DB holatini 'returned' ga o'zgartirish
                mark_returned(task_key)
                log.db_state_updated(task_key, "progressing", "returned")

                # Qaytarilgan xaqida ADF notification comment yozish
                try:
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
                        log.warning(f"[{task_key}] Return notification ADF failed, fallback")
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
                log.warning(f"[{task_key}] Auto-return failed: {msg}")
        else:
            log.info(f"[{task_key}] Score OK: {score}% >= {threshold}%")

    except Exception as e:
        log.error(f"[{task_key}] Auto-return xato: {e}")


# ============================================================================
# SKIP CODE + RE-CHECK HELPER FUNCTIONS
# ============================================================================

async def _check_skip_code(
        task_key: str,
        skip_code: str,
        comment_writer: JiraCommentWriter
) -> bool:
    """
    JIRA task comment'larida skip_code borligini tekshirish.

    DEV "AI_SKIP" (yoki settings-dan berilgan kod) yozgan bo'lsa True qaytaradi.
    Faqat so'nggi 5 comment tekshiriladi.

    Returns:
        True agar skip code topildi, False aks hol
    """
    try:
        if not comment_writer.jira:
            log.warning(f"[{task_key}] JIRA client yo'q, skip check o'chilgan")
            return False

        issue = comment_writer.jira.issue(task_key)
        comments = sorted(issue.fields.comment.comments, key=lambda c: c.created, reverse=True)

        # Settings dan nechta comment tekshirish
        app_settings = get_app_settings(force_reload=True)
        max_comments = app_settings.tz_pr_checker.max_skip_check_comments

        # Faqat so'nggi N comment tekshirish (performance)
        for comment in comments[:max_comments]:
            comment_body = comment.body if comment.body else ""
            # Case-insensitive tekshirish
            if skip_code.upper() in comment_body.upper():
                log.info(f"[{task_key}] Skip code '{skip_code}' topildi: "
                            f"author={comment.author.displayName}, created={comment.created}")
                return True

        return False

    except Exception as e:
        log.error(f"[{task_key}] Skip code check xato: {e}")
        return False  # Xato bo'lsa tekshirish o'chadi, AI davom etadi


async def _detect_recheck(
        task_key: str,
        settings: TZPRCheckerSettings,
        comment_writer: JiraCommentWriter
) -> bool:
    """
    Task qaytarildigan so'ng yana "Ready to Test" statusga tushgan ekanligini detect.

    Mantiq: task'ning changelog'ini o'qib oldingi statusi return_status'ga
    teng ekanligini tekshirish. Agar "Return" → "Ready to Test" transition
    bo'lgan bo'lsa bu re-check.

    Returns:
        True agar re-check detected
    """
    try:
        if not comment_writer.jira:
            return False

        issue = comment_writer.jira.issue(task_key, fields=['status'])

        # JIRA REST API v2 changelog'dan tekshirish
        # python-jira changelog to'g'ridan support etmaydi, REST API ishlash
        load_dotenv()

        server = os.getenv('JIRA_SERVER', 'https://smartupx.atlassian.net')
        email = os.getenv('JIRA_EMAIL')
        token = os.getenv('JIRA_API_TOKEN')

        url = f"{server}/rest/api/2/issue/{task_key}?expand=changelog&fields=status"
        response = requests.get(url, auth=(email, token))

        if response.status_code != 200:
            log.warning(f"[{task_key}] Changelog API failed: {response.status_code}")
            return False

        data = response.json()
        changelog = data.get('changelog', {}).get('histories', [])

        # So'nggi history'larni qaytadan tekshirish (eng yaqin bir tarixdan)
        return_status_lower = settings.return_status.lower()

        for history in reversed(changelog):
            for item in history.get('items', []):
                if item.get('field', '').lower() == 'status':
                    from_status = item.get('fromString', '')
                    # Agar oldingi status return_status bo'lgan bo'lsa → re-check
                    if from_status.lower() == return_status_lower:
                        log.info(f"[{task_key}] Re-check: {from_status} → {item.get('toString')}")
                        return True
                    # Birinchi status o'zgarishini ko'rib chiqamiz (eng yaqin)
                    return False

        return False

    except Exception as e:
        log.error(f"[{task_key}] Re-check detect xato: {e}")
        return False


async def _write_skip_notification(
        task_key: str,
        settings: TZPRCheckerSettings,
        comment_writer: JiraCommentWriter,
        adf_formatter: JiraADFFormatter
):
    """
    Skip code topilganda ADF notification comment yozish.

    ⏭️ "AI tekshirish o'chirilgan" warning panel comment.
    """
    try:
        skip_text = settings.skip_comment_text or (
            "⏭️ AI tekshirish o'chirilgan. "
            "Dev tomanidan skip ko'rsatma berilgan. "
            "Manual tekshirish tavsiya etiladi."
        )

        # ADF document: heading + warning panel + footer
        from datetime import datetime
        content = [
            adf_formatter._heading("⏭️ AI Tekshirish O'chirilgan", 2),
            adf_formatter._rule(),
            adf_formatter._paragraph([
                adf_formatter._bold_text("Task: "),
                adf_formatter._text_node(task_key),
                adf_formatter._hard_break(),
                adf_formatter._bold_text("Vaqt: "),
                adf_formatter._text_node(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                adf_formatter._hard_break(),
                adf_formatter._bold_text("Skip kodi: "),
                adf_formatter._text_node(settings.skip_code)
            ]),
            adf_formatter._rule(),
            adf_formatter._panel([
                adf_formatter._paragraph([
                    adf_formatter._text_node(skip_text)
                ])
            ], "warning"),
            adf_formatter._rule(),
            adf_formatter._paragraph([
                adf_formatter._italic_text("🤖 Bu notification AI tomonidan avtomatik yaratilgan.")
            ])
        ]

        skip_doc = {
            "version": 1,
            "type": "doc",
            "content": content
        }

        success = comment_writer.add_comment_adf(task_key, skip_doc)

        if not success:
            # Fallback
            log.warning(f"[{task_key}] Skip ADF failed, simple fallback")
            comment_writer.add_comment(task_key, f"*{skip_text}*")
            log.jira_comment_added(task_key, "simple")
        else:
            log.jira_comment_added(task_key, "ADF")

    except Exception as e:
        log.error(f"[{task_key}] Skip notification xato: {e}")


async def _run_testcase_generation(task_key: str, new_status: str):
    """
    Background task: Testcase yaratish va JIRA ga yozish (Service2) (v6.0)

    Funksionalliklar:
    - DB orqali Service2 holatini boshqarish
    - Service1 done/skip va score threshold tekshiruvi
    - Xato turlariga qarab blocked/error
    - PR topilmasa TZ-only fallback
    """
    try:
        log.service_started(task_key, "Testcase-Generator")

        # DB holatini tekshirish
        task_db = get_task(task_key)
        if not task_db:
            log.warning(f"[{task_key}] Task DB'da topilmadi, Service2 skip")
            return

        service1_status = task_db.get('service1_status', 'pending')
        service2_status = task_db.get('service2_status', 'pending')
        compliance_score = task_db.get('compliance_score')
        task_status = task_db.get('task_status', 'none')

        log.info(f"[{task_key}] DB holat: service1={service1_status}, service2={service2_status}, "
                   f"score={compliance_score}, task_status={task_status}")

        # Service1 done/skip yoki error (PR topilmadi) bo'lishi kerak
        # Service1=error bo'lsa Service2 TZ-only bilan ishlaydi
        if service1_status not in ('done', 'skip', 'error'):
            log.warning(f"[{task_key}] Service1 hali done/skip/error emas ({service1_status}), Service2 skip")
            return

        # Service1=error bo'lsa faqat service2=pending bo'lsa ishlaydi (TZ-only)
        if service1_status == 'error':
            if service2_status != 'pending':
                log.warning(f"[{task_key}] Service1=error, service2={service2_status} (pending emas), Service2 skip")
                return
            log.info(f"[{task_key}] Service1=error, service2=pending → TZ-only Service2")

        # Service2 allaqachon done bo'lsa skip
        if service2_status == 'done':
            log.info(f"[{task_key}] Service2 allaqachon done, skip")
            return

        # Score threshold tekshiruvi
        app_settings = get_app_settings(force_reload=True)
        settings = app_settings.tz_pr_checker
        tc_settings = app_settings.testcase_generator
        threshold = settings.return_threshold

        if compliance_score is not None and compliance_score < threshold:
            log.warning(f"[{task_key}] Score past: {compliance_score}% < {threshold}%, Service2 bloklangan")
            return

        # Task returned bo'lsa Service2 ishlamaydi
        if task_status == 'returned':
            log.warning(f"[{task_key}] Task returned, Service2 bloklangan")
            return

        # Testcase generation
        log.info(f"[{task_key}] Generating testcases...")
        success, message = await check_and_generate_testcases(task_key, new_status)

        if success:
            set_service2_done(task_key)
            log.service_completed(task_key, "Testcase-Generator", message)
        else:
            error_msg = f"Testcase generation failed: {message}"
            error_type = _classify_error(error_msg)
            log.service_failed(task_key, "Testcase-Generator", f"{error_msg} (type: {error_type})")

            if error_type == 'ai_timeout':
                # AI timeout/429 → Service2 blocked
                retry_minutes = app_settings.queue.blocked_retry_delay
                set_service2_blocked(task_key, error_msg, retry_minutes)
                log.info(f"[{task_key}] Service2 BLOCKED: {retry_minutes} daqiqadan keyin qayta urinadi")
            elif error_type == 'pr_not_found' and tc_settings.default_include_pr:
                # PR topilmadi + PR hisobga olish yoqiq → TZ-only fallback
                log.info(f"[{task_key}] PR topilmadi, TZ-only fallback bilan qayta urinish...")
                success2, message2 = await check_and_generate_testcases(
                    task_key, new_status, include_pr=False
                )
                if success2:
                    set_service2_done(task_key)
                    log.service_completed(task_key, "Testcase-Generator", f"{message2} (TZ-only)")
                else:
                    error_msg2 = f"Testcase TZ-only fallback failed: {message2}"
                    error_type2 = _classify_error(error_msg2)
                    if error_type2 == 'ai_timeout':
                        retry_minutes = app_settings.queue.blocked_retry_delay
                        set_service2_blocked(task_key, error_msg2, retry_minutes)
                    else:
                        set_service2_error(task_key, error_msg2)
                    log.service_failed(task_key, "Testcase-Generator", f"{error_msg2} (TZ-only fallback)")
            else:
                set_service2_error(task_key, error_msg)

    except Exception as e:
        error_msg = f"Testcase generation error: {str(e)}"
        error_type = _classify_error(error_msg)
        log.service_failed(task_key, "Testcase-Generator", f"{e} (type: {error_type})")
        log.error(f"[{task_key}] Service2 error details", exc_info=True)

        if error_type == 'ai_timeout':
            app_settings_reload = get_app_settings(force_reload=True)
            retry_minutes = app_settings_reload.queue.blocked_retry_delay
            set_service2_blocked(task_key, error_msg, retry_minutes)
        else:
            set_service2_error(task_key, error_msg)


# ============================================================================
# AI QUEUE WRAPPER VA TASK GROUP FUNKSIYALAR
# ============================================================================

async def _wait_for_ai_slot(task_key: str):
    """
    Global AI interval kutish (settings dan — Google rate limit: 10 req/min).
    Foydalanuvchi sozlamasiz ichki himoya.
    """
    global _ai_last_call_time
    import time
    
    app_settings = get_app_settings(force_reload=True)
    min_interval = app_settings.queue.gemini_min_interval

    elapsed = time.time() - _ai_last_call_time
    if elapsed < min_interval:
        wait_time = min_interval - elapsed
        log.queue_waiting(task_key, "AI rate limit", int(wait_time))
        await asyncio.sleep(wait_time)

    _ai_last_call_time = time.time()


async def _write_timeout_error_comment(task_key: str, timeout_seconds: int):
    """
    Queue timeout etganda JIRA'ga error comment yozish.
    """
    try:
        adf_formatter = get_adf_formatter()
        comment_writer = get_comment_writer()

        error_doc = adf_formatter.build_error_document(
            task_key=task_key,
            error_message=(
                f"⏳ AI tekshirish timeout: {timeout_seconds} sekunda kutildi, "
                f"boshqa task ishlanmoqda bo'lgan. "
                f"Manual tekshirish kerak."
            ),
            new_status="Ready to Test"
        )
        comment_writer.add_comment_adf(task_key, error_doc)
        log.jira_comment_added(task_key, "ADF")
    except Exception as e:
        log.error(f"[{task_key}] Timeout error comment yozishda xato: {e}")


async def _run_task_group(task_key: str, new_status: str):
    """
    Task-level queue wrapper (parallel mode) (v4.0).

    Bitta task'ning checker + testcase AI chaqrishlari lock ichida
    birma-bir yashlanadi. Boshqa task lock olgunga qadar kutadi.
    Ichidagi order: Service1 (checker) → (checker_testcase_delay) → Service2 (testcase).
    
    Yangi funksionalliklar:
    - Service1 done bo'lgandan keyin Service2 ishlaydi
    - Score threshold tekshiruvi Service2 ni bloklaydi
    """
    app_settings = get_app_settings(force_reload=True)
    queue_settings = app_settings.queue

    if not queue_settings.queue_enabled:
        # Queue o'chirilgan: ikkalasi birma-bir lekin lock siz
        await check_tz_pr_and_comment(task_key=task_key, new_status=new_status)

        # Service1 natijasini tekshirish
        task_db = get_task(task_key)
        if task_db:
            service1_status = task_db.get('service1_status', 'pending')
            task_status = task_db.get('task_status', 'none')
            compliance_score = task_db.get('compliance_score')
            settings = app_settings.tz_pr_checker
            threshold = settings.return_threshold

            can_run_service2 = False
            if service1_status in ('done', 'skip'):
                if compliance_score is None or compliance_score >= threshold:
                    if task_status not in ('returned', 'blocked'):
                        can_run_service2 = True
            elif service1_status == 'error':
                # PR topilmadi holati — Service2 TZ-only bilan ishlashi mumkin
                s2_status = task_db.get('service2_status', 'pending')
                if s2_status == 'pending':
                    can_run_service2 = True
                    log.info(f"[{task_key}] Service1=error, service2=pending → TZ-only Service2")

            if can_run_service2:
                delay = queue_settings.checker_testcase_delay
                if delay > 0:
                    log.delay_waiting(task_key, "Service1→Service2", delay)
                    await asyncio.sleep(delay)
                await _run_testcase_generation(task_key=task_key, new_status=new_status)
            else:
                log.info(f"[{task_key}] Service2 skip (s1={service1_status}, task={task_status})")
        return

    lock = _get_ai_queue_lock()
    timeout = queue_settings.task_wait_timeout
    delay = queue_settings.checker_testcase_delay

    try:
        await asyncio.wait_for(lock.acquire(), timeout=timeout)
    except asyncio.TimeoutError:
        log.queue_timeout(task_key, timeout)
        set_task_timeout_error(task_key, f"Queue timeout: {timeout}s")
        await _write_timeout_error_comment(task_key, timeout)
        return

    try:
        # Service1 (Checker)
        log.service_started(task_key, "TZ-PR-Checker (queue lock)")
        await _wait_for_ai_slot(task_key)
        await check_tz_pr_and_comment(task_key=task_key, new_status=new_status)

        # Service1 → Service2 delay
        if delay > 0:
            log.delay_waiting(task_key, "Service1→Service2", delay)
            await asyncio.sleep(delay)

        # Service2 (Testcase) - faqat Service1 done/skip bo'lsa va score OK bo'lsa
        task_db = get_task(task_key)
        if task_db:
            service1_status = task_db.get('service1_status', 'pending')
            compliance_score = task_db.get('compliance_score')
            task_status = task_db.get('task_status', 'none')
            settings = app_settings.tz_pr_checker
            threshold = settings.return_threshold

            if service1_status in ('done', 'skip'):
                if compliance_score is None or compliance_score >= threshold:
                    if task_status not in ('returned', 'blocked'):
                        log.service_started(task_key, "Testcase-Generator (queue lock)")
                        await _wait_for_ai_slot(task_key)
                        await _run_testcase_generation(task_key=task_key, new_status=new_status)
                    else:
                        log.info(f"[{task_key}] Task {task_status}, Service2 skip")
                else:
                    log.info(f"[{task_key}] Score past ({compliance_score}% < {threshold}%), Service2 skip")
            elif service1_status == 'error':
                # Service1 error — service2 pending bo'lsa TZ-only bilan ishlashi mumkin
                s2_status = task_db.get('service2_status', 'pending')
                if s2_status == 'pending':
                    log.service_started(task_key, "Testcase-Generator (TZ-only, queue lock)")
                    await _wait_for_ai_slot(task_key)
                    await _run_testcase_generation(task_key=task_key, new_status=new_status)
                else:
                    log.info(f"[{task_key}] Service1=error, service2={s2_status} → Service2 skip")
            else:
                log.warning(f"[{task_key}] Service1 hali done/skip emas ({service1_status}), Service2 skip")
    finally:
        lock.release()


async def _queued_check_tz_pr(task_key: str, new_status: str):
    """Queue wrapper: faqat checker (testcase_should_run = False bo'lgan holat)"""
    app_settings = get_app_settings(force_reload=True)
    queue_settings = app_settings.queue

    if not queue_settings.queue_enabled:
        await check_tz_pr_and_comment(task_key=task_key, new_status=new_status)
        return

    lock = _get_ai_queue_lock()
    timeout = queue_settings.task_wait_timeout

    try:
        await asyncio.wait_for(lock.acquire(), timeout=timeout)
    except asyncio.TimeoutError:
        log.queue_timeout(task_key, timeout)
        set_task_timeout_error(task_key, f"Queue timeout: {timeout}s")
        await _write_timeout_error_comment(task_key, timeout)
        return

    try:
        await _wait_for_ai_slot(task_key)
        await check_tz_pr_and_comment(task_key=task_key, new_status=new_status)
    finally:
        lock.release()


async def _run_sequential_tasks(
        task_key: str,
        new_status: str,
        first: str,
        run_testcase: bool = True
):
    """
    Sequential task execution (v4.0): birinchi task tugangandan so'ng ikkinchisi yashlanadi.
    Task-level queue: lock bitta oliladi, ichida birma-bir ketadi.
    Service1 → Service2 o'rtasida checker_testcase_delay sozlamasi ile kutish.
    
    Yangi funksionalliklar:
    - Service1 done bo'lgandan keyin Service2 ishlaydi
    - Score threshold tekshiruvi Service2 ni bloklaydi

    Args:
        first: "checker" yoki "testcase"
        run_testcase: testcase yashlanishi kerak ekanmi
    """
    app_settings = get_app_settings(force_reload=True)
    queue_settings = app_settings.queue
    delay = queue_settings.checker_testcase_delay

    if not queue_settings.queue_enabled:
        # Queue o'chirilgan: sequential lekin lock siz
        if first == "checker":
            try:
                await check_tz_pr_and_comment(task_key=task_key, new_status=new_status)
            except Exception as e:
                log.error(f"[{task_key}] Sequential Service1 error: {e}", exc_info=True)
                set_service1_error(task_key, str(e))
            if run_testcase:
                # Service1 natijasini tekshirish
                task_db_seq = get_task(task_key)
                can_run = False
                if task_db_seq:
                    s1 = task_db_seq.get('service1_status', 'pending')
                    ts = task_db_seq.get('task_status', 'none')
                    score = task_db_seq.get('compliance_score')
                    th = app_settings.tz_pr_checker.return_threshold

                    if s1 in ('done', 'skip'):
                        if score is None or score >= th:
                            if ts not in ('returned', 'blocked'):
                                can_run = True
                    elif s1 == 'error':
                        s2 = task_db_seq.get('service2_status', 'pending')
                        if s2 == 'pending':
                            can_run = True
                            log.info(f"[{task_key}] Service1=error, service2=pending → TZ-only Service2")

                if can_run:
                    if delay > 0:
                        log.delay_waiting(task_key, "Service1→Service2", delay)
                        await asyncio.sleep(delay)
                    try:
                        await _run_testcase_generation(task_key=task_key, new_status=new_status)
                    except Exception as e:
                        log.error(f"[{task_key}] Sequential Service2 error: {e}", exc_info=True)
                        set_service2_error(task_key, str(e))
                else:
                    if task_db_seq:
                        s1 = task_db_seq.get('service1_status', 'pending')
                        ts = task_db_seq.get('task_status', 'none')
                        log.info(f"[{task_key}] Service2 skip (s1={s1}, task={ts})")
        else:  # testcase_first (kam ishlatiladi)
            if run_testcase:
                try:
                    await _run_testcase_generation(task_key=task_key, new_status=new_status)
                except Exception as e:
                    log.error(f"[{task_key}] Sequential Service2 error: {e}", exc_info=True)
                    set_service2_error(task_key, str(e))
                    return
            # Service2 → Service1 delay (aksi tartib)
            if delay > 0:
                log.delay_waiting(task_key, "Service2→Service1", delay)
                await asyncio.sleep(delay)
            try:
                await check_tz_pr_and_comment(task_key=task_key, new_status=new_status)
            except Exception as e:
                log.error(f"[{task_key}] Sequential Service1 error: {e}", exc_info=True)
                set_service1_error(task_key, str(e))
        return

    lock = _get_ai_queue_lock()
    timeout = queue_settings.task_wait_timeout

    try:
        await asyncio.wait_for(lock.acquire(), timeout=timeout)
    except asyncio.TimeoutError:
        log.queue_timeout(task_key, timeout)
        set_task_timeout_error(task_key, f"Queue timeout: {timeout}s")
        await _write_timeout_error_comment(task_key, timeout)
        return

    try:
        if first == "checker":
            # 1) Service1 (Checker)
            await _wait_for_ai_slot(task_key)
            try:
                await check_tz_pr_and_comment(task_key=task_key, new_status=new_status)
            except Exception as e:
                log.error(f"[{task_key}] Sequential Service1 error: {e}", exc_info=True)

            # 2) Service1 → Service2 delay
            if run_testcase:
                if delay > 0:
                    log.delay_waiting(task_key, "Service1→Service2", delay)
                    await asyncio.sleep(delay)

                # Service1 done/skip va score OK tekshiruvi
                task_db = get_task(task_key)
                if task_db:
                    service1_status = task_db.get('service1_status', 'pending')
                    compliance_score = task_db.get('compliance_score')
                    task_status = task_db.get('task_status', 'none')
                    settings = app_settings.tz_pr_checker
                    threshold = settings.return_threshold

                    if service1_status in ('done', 'skip'):
                        if compliance_score is None or compliance_score >= threshold:
                            if task_status not in ('returned', 'blocked'):
                                await _wait_for_ai_slot(task_key)
                                try:
                                    await _run_testcase_generation(task_key=task_key, new_status=new_status)
                                except Exception as e:
                                    log.error(f"[{task_key}] Sequential Service2 error: {e}", exc_info=True)
                            else:
                                log.info(f"[{task_key}] Task {task_status}, Service2 skip")
                        else:
                            log.info(f"[{task_key}] Score past ({compliance_score}% < {threshold}%), Service2 skip")
                    elif service1_status == 'error':
                        # Service1 error — service2 pending bo'lsa TZ-only bilan ishlashi mumkin
                        s2_status = task_db.get('service2_status', 'pending')
                        if s2_status == 'pending':
                            log.service_started(task_key, "Testcase-Generator (TZ-only)")
                            await _wait_for_ai_slot(task_key)
                            try:
                                await _run_testcase_generation(task_key=task_key, new_status=new_status)
                            except Exception as e:
                                log.error(f"[{task_key}] Sequential Service2 TZ-only error: {e}", exc_info=True)
                        else:
                            log.info(f"[{task_key}] Service1=error, service2={s2_status} → Service2 skip")
                    else:
                        log.warning(f"[{task_key}] Service1 hali done/skip emas ({service1_status}), Service2 skip")
        else:  # testcase_first (kam ishlatiladi)
            # 1) Service2 (Testcase)
            if run_testcase:
                await _wait_for_ai_slot(task_key)
                try:
                    await _run_testcase_generation(task_key=task_key, new_status=new_status)
                except Exception as e:
                    log.error(f"[{task_key}] Sequential Service2 error: {e}", exc_info=True)

            # 2) Service2 → Service1 delay (aksi tartib)
            if delay > 0:
                log.delay_waiting(task_key, "Service2→Service1", delay)
                await asyncio.sleep(delay)
            await _wait_for_ai_slot(task_key)
            try:
                await check_tz_pr_and_comment(task_key=task_key, new_status=new_status)
            except Exception as e:
                log.error(f"[{task_key}] Sequential Service1 error: {e}", exc_info=True)
    finally:
        lock.release()


# ============================================================================
# SIMPLE FORMAT FALLBACKS
# ============================================================================

def format_error_comment_simple(task_key: str, error_message: str, new_status: str) -> str:
    """Oddiy format - xatolik"""
    return f"""
⚠️ *Avtomatik TZ-PR Tekshiruvi - Xatolik*

----

*Task:* {task_key}
*Vaqt:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
*Status:* {new_status}

----

*Xatolik:*

{error_message}

----

*Mumkin sabablar:*
• Task uchun PR topilmadi
• GitHub access xatoligi
• TZ (Description) bo'sh

----

_Manual tekshirish kerak. QA Team'ga xabar bering._
"""


def format_critical_error_simple(task_key: str, error: str, new_status: str) -> str:
    """Oddiy format - kritik xatolik"""
    return f"""
🚨 *Avtomatik TZ-PR Tekshiruvi - Kritik Xatolik*

----

*Task:* {task_key}
*Vaqt:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
*Status:* {new_status}

----

*Kritik Xatolik:*

```
{error}
```

----

_System administrator'ga xabar berildi._
"""


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - service holatini ko'rsatish"""
    app_settings = get_app_settings(force_reload=True)
    settings = app_settings.tz_pr_checker

    return {
        "service": "JIRA TZ-PR Auto Checker",
        "status": "running",
        "version": "2.0.0",
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
    """Health check - monitoring uchun"""

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
        app_settings = get_app_settings(force_reload=True)
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

    return health


@app.get("/settings")
async def get_settings():
    """Joriy sozlamalarni ko'rsatish"""
    app_settings = get_app_settings(force_reload=True)
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
    Manual trigger - TZ-PR check + Testcase generation (ikkalasi)

    Usage:
        curl -X POST http://localhost:8000/manual/check/DEV-1234
    """
    log.info(f"Manual check triggered for {task_key}")

    # TZ-PR Check background task
    background_tasks.add_task(
        check_tz_pr_and_comment,
        task_key=task_key,
        new_status="Manual Check"
    )

    # Testcase generation (settings-dan trigger statusini olish)
    app_settings = get_app_settings(force_reload=True)
    tc_settings = app_settings.testcase_generator
    testcase_triggered = False

    if tc_settings.auto_comment_enabled:
        # Trigger statusini settings-dan olish ("READY TO TEST")
        # manual_check'dan "Manual Check" o'tkaza olmaymiz - check_and_generate status tekshiradi
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
    Manual testcase generation - faqat testcase yaratish (TZ-PR check emas)

    Usage:
        curl -X POST http://localhost:8000/manual/testcase/DEV-1234
    """
    log.info(f"Manual testcase generation triggered for {task_key}")

    app_settings = get_app_settings(force_reload=True)
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
# BLOCKED RETRY SCHEDULER (v6.0)
# ============================================================================

async def _retry_blocked_task(task_id: str):
    """
    Blocked taskni qayta ishlash.
    - service1=done/skip → o'tkazib yuborish
    - service1=blocked → qayta run
    - service2=done → o'tkazib yuborish
    - service2=blocked/pending → service1 tugagandan keyin run
    """
    try:
        task_data = get_task(task_id)
        if not task_data:
            log.warning(f"[{task_id}] Retry: task DB da topilmadi")
            return

        service1_status = task_data.get('service1_status', 'pending')
        service2_status = task_data.get('service2_status', 'pending')
        last_jira_status = task_data.get('last_jira_status', 'READY TO TEST')

        log.info(f"[{task_id}] Blocked task retry: s1={service1_status}, s2={service2_status}")

        # Progressing ga o'tkazish
        mark_progressing(task_id, last_jira_status, datetime.now())

        # Service1 ni qayta run qilish kerakmi?
        need_service1 = service1_status == 'blocked'
        need_service2 = service2_status in ('blocked', 'pending')

        if need_service1:
            # Service1 blocked → pending + run
            from utils.database.task_db import upsert_task
            upsert_task(task_id, {
                'service1_status': 'pending',
                'service1_error': None,
                'blocked_at': None,
                'blocked_retry_at': None,
                'block_reason': None
            })

            log.service_started(task_id, "TZ-PR-Checker (retry)")
            await _wait_for_ai_slot(task_id)
            await check_tz_pr_and_comment(task_key=task_id, new_status=last_jira_status)

            # Service1 natijasini tekshirish
            task_data = get_task(task_id)
            if not task_data:
                return
            service1_status = task_data.get('service1_status', 'pending')
            task_status = task_data.get('task_status', 'none')

            # Agar service1 yana blocked/error bo'lsa — to'xtash
            if service1_status not in ('done', 'skip'):
                log.info(f"[{task_id}] Service1 retry natijasi: {service1_status}, to'xtash")
                return
            if task_status in ('returned', 'blocked'):
                log.info(f"[{task_id}] Task {task_status} holati, Service2 skip")
                return

        if need_service2:
            # Service2 blocked/pending → run
            task_data = get_task(task_id)
            if task_data and task_data.get('service2_status') != 'done':
                from utils.database.task_db import upsert_task
                upsert_task(task_id, {
                    'service2_status': 'pending',
                    'service2_error': None,
                    'blocked_at': None,
                    'blocked_retry_at': None,
                    'block_reason': None
                })

                # Delay between services
                app_settings = get_app_settings(force_reload=True)
                delay = app_settings.queue.checker_testcase_delay
                if delay > 0 and need_service1:
                    log.delay_waiting(task_id, "Service1→Service2", delay)
                    await asyncio.sleep(delay)

                log.service_started(task_id, "Testcase-Generator (retry)")
                await _wait_for_ai_slot(task_id)
                await _run_testcase_generation(task_key=task_id, new_status=last_jira_status)

        # Done servislar tashlab ketildi (o'tkazib yuborildi)
        if not need_service1 and not need_service2:
            log.info(f"[{task_id}] Barcha servislar done, retry kerak emas")

    except Exception as e:
        log.error(f"[{task_id}] Blocked task retry error: {e}", exc_info=True)
        mark_error(task_id, f"Retry error: {str(e)}")


async def _blocked_retry_scheduler():
    """
    Background scheduler: har N sekundda blocked tasklarni tekshiradi.
    Retry vaqti kelgan tasklarni navbatga qo'yadi.

    Note: Settings har safar reload qilinadi (force_reload=True) - UI'dan o'zgarishlarni
    darhol ko'rish uchun. Log'lar DEBUG level'da yoziladi (log spam'ni oldini olish uchun).
    """
    log.info("Blocked retry scheduler boshlandi")

    # Birinchi marta sozlamalarni yuklash
    app_settings = get_app_settings(force_reload=True)
    check_interval = app_settings.queue.blocked_check_interval

    while True:
        try:
            await asyncio.sleep(check_interval)

            # Settings har safar reload qilinadi (UI'dan o'zgarishlarni ko'rish uchun)
            # Log DEBUG level'da yoziladi (log spam'ni oldini olish uchun)
            app_settings = get_app_settings(force_reload=True)
            check_interval = app_settings.queue.blocked_check_interval

            blocked_tasks = get_blocked_tasks_ready_for_retry()
            if not blocked_tasks:
                continue

            log.info(f"{len(blocked_tasks)} ta blocked task retry uchun tayyor")

            for task_data in blocked_tasks:
                task_id = task_data['task_id']

                # Boshqa task progressing bo'lsa — kutish (lock bilan)
                lock = _get_ai_queue_lock()
                # Settings reload qilinadi (yangilangan qiymatlarni olish uchun)
                app_settings = get_app_settings(force_reload=True)
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
            log.info("Blocked retry scheduler to'xtatildi")
            break
        except Exception as e:
            log.error(f"Blocked retry scheduler error: {e}", exc_info=True)
            # Xato bo'lganda ham reload qilish
            app_settings = get_app_settings(force_reload=True)
            check_interval = app_settings.queue.blocked_check_interval
            await asyncio.sleep(check_interval)


# ============================================================================
# STARTUP EVENT
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Service boshlanganda"""
    global _blocked_retry_task

    app_settings = get_app_settings(force_reload=True)
    settings = app_settings.tz_pr_checker

    log.system_started("3.1.0", 8000)
    log.settings_loaded(
        adf=settings.use_adf_format,
        auto_return=settings.auto_return_enabled,
        threshold=settings.return_threshold
    )
    log.info(f"Trigger Status: {settings.trigger_status}")
    log.info(f"Blocked Retry Delay: {app_settings.queue.blocked_retry_delay} min")

    # Blocked retry scheduler ni ishga tushirish
    _blocked_retry_task = asyncio.create_task(_blocked_retry_scheduler())


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "webhook_service_minimal:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
