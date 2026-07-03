"""
Markaziy task holat mashinasi — `task_processing` status ustunlari uchun.

DB schemadagi REAL qiymatlar (database/postgresql/001_initial_schema.sql):
    task_status:            none / progressing / completed / returned / error / blocked
    service1_status:        pending / done / error / skip / blocked
    service2_status:        pending / done / error / blocked  (skip faqat service1 da)

Tranzitsiya grafigi task_db.py mutatorlari, jira_webhook_handler.py (duplicate/
reset oqimi), retry_scheduler.py va service_runner.py oqimlaridan olingan.

Guard rejimi — APP_STATE_GUARD_MODE env:
    warn    (default) — noqonuniy o'tish WARNING log qilinadi, yozuv davom etadi
    enforce           — InvalidTransition raise qilinadi (yozuv bajarilmaydi)
"""
from __future__ import annotations

import logging
import os
import traceback
from enum import Enum
from typing import Optional

log = logging.getLogger("task_state")

GUARD_MODE_ENV = "APP_STATE_GUARD_MODE"
MODE_WARN = "warn"
MODE_ENFORCE = "enforce"


class InvalidTransition(ValueError):
    """Ruxsat etilmagan holat o'tishi (faqat enforce rejimida raise bo'ladi)."""


class TaskStatus(str, Enum):
    NONE = "none"
    PROGRESSING = "progressing"
    COMPLETED = "completed"
    RETURNED = "returned"
    ERROR = "error"
    BLOCKED = "blocked"


class ServiceStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    ERROR = "error"
    SKIP = "skip"  # faqat service1 (AI_SKIP kodi topilganda)
    BLOCKED = "blocked"


# task_status o'tishlari (self-loop har doim ruxsat — validate_transition ichida):
#   none -> progressing:        webhook yangi sikl (mark_progressing)
#   progressing -> completed:   set_service2_done / mark_completed / _finalize_terminal_state
#   progressing -> returned:    mark_returned / mark_returned_pr_not_merged
#   progressing -> error:       mark_error / set_service*_error / sweep_stuck_progressing_tasks
#   progressing -> blocked:     mark_blocked (queue timeout) / set_service*_blocked
#   completed/returned -> progressing: re-trigger (reset_service_statuses + mark_progressing)
#   error -> progressing:       re-trigger
#   blocked -> progressing:     retry_scheduler / re-trigger
#   completed/returned/blocked -> error: umumiy exception handler'lar (mark_error catch-all)
ALLOWED_TASK_TRANSITIONS: dict[str, frozenset[str]] = {
    TaskStatus.NONE.value: frozenset({"progressing"}),
    TaskStatus.PROGRESSING.value: frozenset({"completed", "returned", "error", "blocked"}),
    TaskStatus.COMPLETED.value: frozenset({"progressing", "error"}),
    TaskStatus.RETURNED.value: frozenset({"progressing", "error"}),
    TaskStatus.ERROR.value: frozenset({"progressing"}),
    TaskStatus.BLOCKED.value: frozenset({"progressing", "error"}),
}

# service1_status o'tishlari:
#   pending -> done/error/blocked/skip: oddiy run natijalari + AI_SKIP
#   done -> pending:    reset_service_statuses / mark_returned_pr_not_merged (S2 oqimida)
#   done -> error/blocked: done'dan KEYINGI exception (comment yozish, auto-return xatosi)
#   error/blocked/skip -> pending: reset / retry_scheduler
#   blocked -> error:   umumiy error catch-all (set_task_timeout_error)
ALLOWED_SERVICE1_TRANSITIONS: dict[str, frozenset[str]] = {
    ServiceStatus.PENDING.value: frozenset({"done", "error", "blocked", "skip"}),
    ServiceStatus.DONE.value: frozenset({"pending", "error", "blocked"}),
    ServiceStatus.ERROR.value: frozenset({"pending"}),
    ServiceStatus.BLOCKED.value: frozenset({"pending", "error"}),
    ServiceStatus.SKIP.value: frozenset({"pending"}),
}

# service2_status o'tishlari (skip yo'q):
#   pending -> done/error/blocked: oddiy run natijalari
#   done -> pending:    reset_service_statuses / mark_returned
#   done -> error/blocked: done'dan keyingi exception
#   error -> pending:   reset / set_service1_error(keep_service2_pending=True)
#   blocked -> pending: retry_scheduler
#   blocked -> error:   set_service1_error(default) service2 ni ham error qiladi
ALLOWED_SERVICE2_TRANSITIONS: dict[str, frozenset[str]] = {
    ServiceStatus.PENDING.value: frozenset({"done", "error", "blocked"}),
    ServiceStatus.DONE.value: frozenset({"pending", "error", "blocked"}),
    ServiceStatus.ERROR.value: frozenset({"pending"}),
    ServiceStatus.BLOCKED.value: frozenset({"pending", "error"}),
}

_TRANSITIONS: dict[str, dict[str, frozenset[str]]] = {
    "task_status": ALLOWED_TASK_TRANSITIONS,
    "service1_status": ALLOWED_SERVICE1_TRANSITIONS,
    "service2_status": ALLOWED_SERVICE2_TRANSITIONS,
}

# upsert yozuvida tekshiriladigan status ustunlari
STATUS_FIELDS: tuple[str, ...] = tuple(_TRANSITIONS)

_INTERNAL_FILES = ("task_state.py", "task_repository.py", "task_db.py")


def get_guard_mode() -> str:
    mode = (os.getenv(GUARD_MODE_ENV) or MODE_WARN).strip().lower()
    return MODE_ENFORCE if mode == MODE_ENFORCE else MODE_WARN


def _coerce(value) -> Optional[str]:
    if value is None:
        return None
    return getattr(value, "value", value)


def _caller_info() -> str:
    """Guard'ni trigger qilgan tashqi chaqiruvchini topish (log uchun)."""
    for frame in reversed(traceback.extract_stack()):
        if os.path.basename(frame.filename) in _INTERNAL_FILES:
            continue
        return f"{os.path.basename(frame.filename)}:{frame.lineno} {frame.name}"
    return "unknown"


def validate_transition(
    kind: str,
    old,
    new,
    *,
    task_id: Optional[str] = None,
) -> None:
    """Holat o'tishini tekshirish.

    - old == new (self-loop) va old=None (yangi qator) — har doim ruxsat.
    - Noqonuniy o'tish: warn rejimda WARNING log, enforce rejimda InvalidTransition.
    """
    old_value = _coerce(old)
    new_value = _coerce(new)
    if new_value is None or old_value is None or old_value == new_value:
        return

    allowed = _TRANSITIONS.get(kind)
    if allowed is None:
        return

    if new_value in allowed.get(old_value, frozenset()):
        return

    label = f"[{task_id}] " if task_id else ""
    msg = (
        f"{label}Noqonuniy {kind} o'tishi: {old_value!r} -> {new_value!r} "
        f"(caller: {_caller_info()})"
    )
    if get_guard_mode() == MODE_ENFORCE:
        raise InvalidTransition(msg)
    log.warning(msg)
