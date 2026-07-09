"""
Background worker runtime.

API process webhook triggerlarni DB navbatga yozadi, worker esa shu navbatdan
olib mavjud business logikani bajaradi.
"""
from __future__ import annotations

import asyncio
import json
import os
import signal
import socket
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any

from config.app_settings import get_app_settings, get_app_settings_for_company
from core.logger import get_logger
from services.checkers.tzpr_multi_agent import execute_multi_agent_run
from services.generators.testcase_run import execute_testcase_run
from services.webhook.queue_manager import _queued_check_tz_pr, _run_task_group, _wait_for_ai_slot
from services.webhook.retry_scheduler import _retry_blocked_task
from services.webhook.service_runner import _run_testcase_generation, check_tz_pr_and_comment
from utils.database.task_db import (
    claim_next_background_job,
    complete_background_job,
    enqueue_background_job,
    fail_background_job,
    get_background_queue_snapshot,
    get_blocked_tasks_ready_for_retry,
    init_db,
    requeue_stale_background_jobs,
    retry_background_job,
    sweep_stuck_progressing_tasks,
)

log = get_logger("worker.runtime")

JOB_RUN_TASK_GROUP = "run_task_group"
JOB_RUN_CHECKER_ONLY = "run_checker_only"
JOB_RUN_TESTCASE = "run_testcase_generation"
JOB_RETRY_BLOCKED_TASK = "retry_blocked_task"
JOB_MANUAL_CHECK = "manual_check"
JOB_TZPR_MULTI_AGENT_RUN = "tzpr_multi_agent_run"
JOB_TESTCASE_MULTI_AGENT_RUN = "testcase_multi_agent_run"


def _worker_name() -> str:
    """Worker nomi. APP_WORKER_NAME berilmasa hostname qo'shiladi —
    `docker compose --scale worker=N` da har replika (container id) unikal nom oladi."""
    explicit = (os.getenv("APP_WORKER_NAME") or "").strip()
    if explicit:
        return explicit
    return f"worker-{socket.gethostname()}"


def _heartbeat_file_path() -> Path:
    return Path(os.getenv("APP_WORKER_HEARTBEAT_FILE") or "/tmp/qa_worker_heartbeat")


def _touch_heartbeat_file() -> None:
    """Docker healthcheck uchun container-lokal liveness fayli.

    DB heartbeat (core/watchdog) monitoring uchun; bu fayl esa compose
    healthcheck `find -mmin` tekshiruvi uchun — DB'siz ham ishlaydi."""
    try:
        _heartbeat_file_path().touch()
    except Exception:
        pass


def _poll_interval_seconds() -> int:
    raw = os.getenv("APP_WORKER_POLL_INTERVAL_SECONDS") or "3"
    try:
        return max(1, int(raw))
    except ValueError:
        return 3


def _env_int(name: str, default: int, minimum: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        return default


def _stale_job_timeout_seconds() -> int:
    # Eng uzun normal run (~3-8 daqiqa) dan sezilarli katta: default 30 daqiqa.
    return _env_int("APP_STALE_JOB_TIMEOUT_SECONDS", 1800, 300)


def _stuck_task_timeout_minutes() -> int:
    # Job reaper'dan uzunroq — u crash'ni birinchi tiklaydi: default 60 daqiqa.
    return _env_int("APP_STUCK_TASK_TIMEOUT_MINUTES", 60, 10)


def _reaper_interval_seconds() -> int:
    return _env_int("APP_REAPER_INTERVAL_SECONDS", 120, 30)


def _run_recovery_sweep() -> None:
    """Stale running joblarni tiklash + qotib qolgan 'progressing' tasklarni error qilish."""
    try:
        reaped = requeue_stale_background_jobs(_stale_job_timeout_seconds())
        if reaped.get("requeued") or reaped.get("failed"):
            log.warning(
                f"WORKER -> reaper: {reaped.get('requeued', 0)} job requeued, "
                f"{reaped.get('failed', 0)} failed (stale running)"
            )
    except Exception as exc:
        log.warning(f"WORKER -> reaper error: {exc}")

    try:
        swept = sweep_stuck_progressing_tasks(_stuck_task_timeout_minutes())
        if swept:
            log.warning(f"WORKER -> sweeper: {swept} stuck 'progressing' task(s) -> error")
    except Exception as exc:
        log.warning(f"WORKER -> sweeper error: {exc}")


def _retry_delay_seconds(job: dict[str, Any]) -> int:
    attempts = int(job.get("attempts") or 1)
    return min(300, 15 * attempts)


def _retry_job_dedupe_key(task_key: str, company_id: int | None) -> str:
    return f"retry:{company_id or 'global'}:{task_key}"


def _parse_payload(job: dict[str, Any]) -> dict[str, Any]:
    raw = job.get("payload_json")
    if isinstance(raw, dict):
        return dict(raw)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


async def _run_manual_check(
    task_key: str,
    company_id: int | None,
    include_testcase: bool,
    new_status: str,
) -> None:
    await check_tz_pr_and_comment(task_key=task_key, new_status=new_status, company_id=company_id)
    if include_testcase:
        queue_settings = (
            get_app_settings_for_company(company_id).queue
            if company_id is not None
            else get_app_settings(force_reload=False).queue
        )
        await _wait_for_ai_slot(task_key, company_id=company_id, min_interval=queue_settings.gemini_min_interval)
        tc_settings = get_app_settings(force_reload=False).webhook_testcase
        trigger_status = tc_settings.auto_comment_trigger_status
        await _run_testcase_generation(task_key=task_key, new_status=trigger_status, company_id=company_id)


async def _dispatch_job(job: dict[str, Any]) -> None:
    payload = _parse_payload(job)
    task_key = str(payload.get("task_key") or job.get("task_key") or "").strip().upper()
    company_id = payload.get("company_id", job.get("company_id"))
    if company_id in ("", None):
        company_id = None
    elif not isinstance(company_id, int):
        company_id = int(company_id)
    new_status = str(payload.get("new_status") or "READY TO TEST")
    task_details = payload.get("task_details") if isinstance(payload.get("task_details"), dict) else None
    job_type = str(job.get("job_type") or "")

    if not task_key:
        raise RuntimeError("task_key bo'sh")

    if job_type == JOB_RUN_TASK_GROUP:
        await _run_task_group(
            task_key=task_key,
            new_status=new_status,
            company_id=company_id,
            task_details=task_details,
        )
        return
    if job_type == JOB_RUN_CHECKER_ONLY:
        await _queued_check_tz_pr(
            task_key=task_key,
            new_status=new_status,
            company_id=company_id,
            task_details=task_details,
        )
        return
    if job_type == JOB_RUN_TESTCASE:
        await _run_testcase_generation(task_key=task_key, new_status=new_status, company_id=company_id)
        return
    if job_type == JOB_RETRY_BLOCKED_TASK:
        await _retry_blocked_task(task_key)
        return
    if job_type == JOB_MANUAL_CHECK:
        await _run_manual_check(
            task_key=task_key,
            company_id=company_id,
            include_testcase=bool(payload.get("include_testcase")),
            new_status=new_status,
        )
        return
    if job_type == JOB_TZPR_MULTI_AGENT_RUN:
        run_id = str(payload.get("run_id") or "").strip()
        if not run_id:
            raise RuntimeError("run_id bo'sh")
        await asyncio.to_thread(execute_multi_agent_run, run_id)
        return
    if job_type == JOB_TESTCASE_MULTI_AGENT_RUN:
        run_id = str(payload.get("run_id") or "").strip()
        if not run_id:
            raise RuntimeError("run_id bo'sh")
        await asyncio.to_thread(execute_testcase_run, run_id)
        return

    raise RuntimeError(f"Noma'lum job_type: {job_type}")


def _enqueue_due_retry_jobs() -> int:
    enqueued = 0
    for task in get_blocked_tasks_ready_for_retry():
        task_key = str(task.get("task_id") or "").strip().upper()
        if not task_key:
            continue
        company_id = task.get("company_id")
        job = enqueue_background_job(
            JOB_RETRY_BLOCKED_TASK,
            task_key,
            company_id=company_id,
            payload={"task_key": task_key, "company_id": company_id},
            dedupe_key=_retry_job_dedupe_key(task_key, company_id),
            max_attempts=10,
        )
        if job:
            enqueued += 1
    return enqueued


async def run_worker(stop_event: asyncio.Event | None = None) -> None:
    worker_name = _worker_name()
    stop_event = stop_event or asyncio.Event()

    # STRICT_MODE'da master key yo'q bo'lsa boot'da loud fail (worker credential
    # deshifrlaydi — kalitsiz har job jimgina yiqilardi). Backend API lifespan'da
    # ham shu tekshiruv bor (audit F6).
    from utils.auth.credential_crypto import assert_master_key_configured
    assert_master_key_configured()

    init_db()
    log.info(f"WORKER -> started | name={worker_name}")
    # Restart'da darhol crash-recovery: oldingi worker o'lganda qolgan stale
    # 'running' joblarni va qotib qolgan 'progressing' tasklarni tiklash.
    _run_recovery_sweep()
    poll_interval = _poll_interval_seconds()
    last_retry_scan: datetime | None = None
    last_session_cleanup: datetime | None = None
    last_subscription_expire: datetime | None = None
    last_reaper_scan: datetime | None = datetime.now()
    last_retention: datetime | None = None
    last_heartbeat: datetime | None = None
    _SESSION_CLEANUP_INTERVAL = 3600
    _SUBSCRIPTION_EXPIRE_INTERVAL = 3600
    _RETENTION_INTERVAL = _env_int("APP_RETENTION_INTERVAL_SECONDS", 86400, 3600)
    _HEARTBEAT_INTERVAL = _env_int("APP_WORKER_HEARTBEAT_SECONDS", 60, 15)

    while not stop_event.is_set():
        settings = get_app_settings(force_reload=False)
        retry_scan_interval = max(5, int(settings.queue.blocked_check_interval))

        now = datetime.now()
        if last_heartbeat is None or (now - last_heartbeat).total_seconds() >= _HEARTBEAT_INTERVAL:
            try:
                from core.watchdog import record_worker_heartbeat
                record_worker_heartbeat(worker_name)
            except Exception:
                pass
            _touch_heartbeat_file()
            last_heartbeat = now

        now = datetime.now()
        if last_retry_scan is None or (now - last_retry_scan).total_seconds() >= retry_scan_interval:
            queued_retries = _enqueue_due_retry_jobs()
            if queued_retries:
                log.info(f"WORKER -> enqueued {queued_retries} retry job(s)")
            last_retry_scan = now

        now = datetime.now()
        if last_reaper_scan is None or (now - last_reaper_scan).total_seconds() >= _reaper_interval_seconds():
            _run_recovery_sweep()
            last_reaper_scan = now

        now = datetime.now()
        if last_session_cleanup is None or (now - last_session_cleanup).total_seconds() >= _SESSION_CLEANUP_INTERVAL:
            try:
                from utils.auth.auth_db import cleanup_expired_sessions
                removed = cleanup_expired_sessions()
                if removed:
                    log.info(f"WORKER -> session cleanup: {removed} ta muddati o'tgan sessiya o'chirildi")
            except Exception:
                pass
            last_session_cleanup = now

        now = datetime.now()
        if last_subscription_expire is None or (now - last_subscription_expire).total_seconds() >= _SUBSCRIPTION_EXPIRE_INTERVAL:
            try:
                from utils.auth.auth_db import expire_overdue_company_subscriptions
                expired = expire_overdue_company_subscriptions()
                if expired:
                    log.info(f"WORKER -> subscription expire: {expired} ta muddati o'tgan obuna suspended qilindi")
            except Exception:
                pass
            last_subscription_expire = now

        now = datetime.now()
        if last_retention is None or (now - last_retention).total_seconds() >= _RETENTION_INTERVAL:
            try:
                from utils.database.retention import run_retention_cleanup
                removed = await asyncio.to_thread(run_retention_cleanup)
                if removed:
                    summary = ", ".join(f"{k}={v}" for k, v in removed.items())
                    log.info(f"WORKER -> retention: eski yozuvlar o'chirildi ({summary})")
            except Exception as exc:
                log.warning(f"WORKER -> retention error: {exc}")
            last_retention = now

        job = claim_next_background_job(worker_name)
        if not job:
            await asyncio.sleep(poll_interval)
            continue

        log.info(
            f"WORKER -> claim job id={job.get('id')} type={job.get('job_type')} "
            f"task={job.get('task_key')} attempt={job.get('attempts')}/{job.get('max_attempts')}"
        )

        try:
            await _dispatch_job(job)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            error_message = str(exc)
            if int(job.get("attempts") or 0) < int(job.get("max_attempts") or 1):
                retry_background_job(job, error_message, _retry_delay_seconds(job))
                log.warning(f"WORKER -> retry scheduled for job {job.get('id')}: {error_message}")
            else:
                fail_background_job(job, error_message)
                log.error(f"WORKER -> failed job {job.get('id')}: {error_message}", exc_info=True)
        else:
            complete_background_job(job)

    log.info("WORKER -> stop signal accepted")


async def _async_main() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    try:
        await run_worker(stop_event)
    finally:
        snapshot = get_background_queue_snapshot()
        log.info(
            "WORKER -> shutdown snapshot | "
            f"queued={snapshot.get('queued', 0)} running={snapshot.get('running', 0)} "
            f"done={snapshot.get('done', 0)} failed={snapshot.get('failed', 0)}"
        )


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
