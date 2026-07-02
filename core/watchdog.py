"""
Self-hosted watchdog — navbat/blocked/worker holatini davriy tekshirib, muammo
bo'lsa email + WARNING log orqali ogohlantiradi (tashqi servissiz, mavjud SMTP).

Audit HIGH (Prod): "Alerting umuman yo'q — o'lik worker, bloklangan task,
barcha kalit muzlagani faqat kimdir monitoring UI'ni ochsa ko'rinadi."

Tekshiruvlar:
  - `queued >= APP_WATCHDOG_QUEUE_THRESHOLD`  → navbat to'planib qoldi
  - `blocked >= 1`                            → bloklangan tasklar (qo'lda ko'rish)
  - worker heartbeat `APP_WATCHDOG_WORKER_STALE_SECONDS` dan eski → worker o'lgan
    (faqat `queue` rejimida — inline'da worker yo'q)

Spam oldini olish: har alert turi uchun holat AKTIV bo'lganda bir marta yuboriladi;
holat tozalanmaguncha (yoki cooldown o'tmaguncha) qayta yuborilmaydi. Recovery
("hammasi normal") ham bir marta bildiriladi.

Watchdog API jarayonida ishlaydi (worker'dan ALOHIDA) — shuning uchun worker
o'limini ham aniqlay oladi. Worker esa har loop'da heartbeat yozadi.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from core.logger import get_logger
from utils.database.repository_common import execute as _execute
from utils.database.runtime import connect_processing_db

log = get_logger("watchdog")

# Alert holati (in-process — watchdog bitta API jarayonda ishlaydi).
# key -> last_sent (datetime, tz-aware). Yo'q = hozir aktiv emas.
_active_alerts: dict[str, datetime] = {}

_ALERT_SUBJECTS = {
    "queue_backlog": "Navbat to'planib qoldi",
    "blocked_tasks": "Bloklangan tasklar bor",
    "worker_dead": "Worker javob bermayapti",
    "worker_missing": "Worker ishga tushmagan",
}


def watchdog_enabled() -> bool:
    raw = (os.getenv("APP_WATCHDOG_ENABLED") or "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _env_int(name: str, default: int, minimum: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        return default


def _queue_mode() -> bool:
    return (os.getenv("APP_WEBHOOK_EXECUTION_MODE") or "inline").strip().lower() == "queue"


def ensure_watchdog_tables(conn) -> None:
    """Worker heartbeat jadvali (idempotent). Startup'da ensure qilinadi."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS worker_heartbeat (
            worker_name TEXT PRIMARY KEY,
            beat_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    conn.commit()


def record_worker_heartbeat(worker_name: str) -> None:
    """Worker tirikligini belgilaydi (upsert). Worker loop'da davriy chaqiriladi."""
    try:
        conn = connect_processing_db()
        try:
            _execute(
                conn,
                """
                INSERT INTO worker_heartbeat (worker_name, beat_at)
                VALUES (?, NOW())
                ON CONFLICT (worker_name) DO UPDATE SET beat_at = NOW()
                """,
                [worker_name],
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        # Heartbeat yozilmasa alert xato bo'lishi mumkin, lekin worker ishini to'xtatmaydi.
        log.warning("worker heartbeat yozilmadi", exc_info=True)


def _collect_state() -> dict:
    conn = connect_processing_db(row_factory=True)
    try:
        row = _execute(
            conn,
            """
            SELECT
                (SELECT COUNT(*) FROM job_queue WHERE status = 'queued')   AS queued,
                (SELECT COUNT(*) FROM job_queue WHERE status = 'running')  AS running,
                (SELECT COUNT(*) FROM task_processing WHERE task_status = 'blocked') AS blocked,
                (SELECT EXTRACT(EPOCH FROM (NOW() - MAX(beat_at)))::bigint FROM worker_heartbeat) AS worker_stale_seconds
            """,
        ).fetchone()
        data = dict(row) if row else {}
        return {
            "queued": int(data.get("queued") or 0),
            "running": int(data.get("running") or 0),
            "blocked": int(data.get("blocked") or 0),
            "worker_stale_seconds": (
                int(data["worker_stale_seconds"])
                if data.get("worker_stale_seconds") is not None
                else None
            ),
        }
    finally:
        conn.close()


def evaluate_alerts(state: dict) -> list[tuple[str, str]]:
    """Aktiv muammolar ro'yxati: [(key, human_message), ...]."""
    alerts: list[tuple[str, str]] = []

    queue_threshold = _env_int("APP_WATCHDOG_QUEUE_THRESHOLD", 20, 1)
    if state["queued"] >= queue_threshold:
        alerts.append((
            "queue_backlog",
            f"Navbatda {state['queued']} ta job to'planib qoldi "
            f"(chegara {queue_threshold}, running={state['running']}). "
            f"Worker yetishmayapti yoki sekinlashgan."
        ))

    if state["blocked"] >= 1:
        alerts.append((
            "blocked_tasks",
            f"{state['blocked']} ta task 'blocked' holatda (AI timeout / kvota / kalit muzlashi). "
            f"Retry scheduler tiklamasa qo'lda ko'rish kerak."
        ))

    # Worker o'limi — faqat queue rejimida (inline'da worker yo'q).
    if _queue_mode():
        stale = state["worker_stale_seconds"]
        # Chegara eng uzun normal job'dan (multi-agent ~3-8 daq) xavfsiz balandroq:
        # worker job ustida band bo'lsa heartbeat joblar orasida yangilanadi.
        stale_limit = _env_int("APP_WATCHDOG_WORKER_STALE_SECONDS", 900, 120)
        if stale is None:
            # Heartbeat umuman yo'q, lekin navbatда ish bor — worker ko'tarilmagan.
            if state["queued"] > 0 or state["running"] > 0:
                alerts.append((
                    "worker_missing",
                    "Worker heartbeat topilmadi, lekin navbatда ish bor. "
                    "Worker jarayoni ishga tushmagan bo'lishi mumkin."
                ))
        elif stale > stale_limit:
            alerts.append((
                "worker_dead",
                f"Worker heartbeat {stale}s oldin yozilgan (chegara {stale_limit}s). "
                f"Worker o'lgan yoki qotgan bo'lishi mumkin."
            ))

    return alerts


def _send_alert(subject: str, body: str) -> None:
    """WARNING log + (sozlangan bo'lsa) email."""
    log.warning(f"WATCHDOG ALERT -> {subject}: {body}")
    recipient = (os.getenv("APP_WATCHDOG_ALERT_EMAIL") or "").strip()
    if not recipient:
        return
    try:
        from utils.email.email_sender import send_email, is_email_configured
        if not is_email_configured():
            return
        html = (
            f"<div style='font-family:Arial,sans-serif'>"
            f"<h3 style='color:#b91c1c;margin:0 0 8px'>⚠️ QA-Assistant Watchdog</h3>"
            f"<p style='margin:0 0 6px;font-weight:600'>{subject}</p>"
            f"<p style='margin:0;color:#444;line-height:1.6'>{body}</p></div>"
        )
        send_email(recipient, f"[QA-Assistant] {subject}", html, text_body=f"{subject}\n\n{body}")
    except Exception:
        log.warning("watchdog email yuborilmadi", exc_info=True)


def run_watchdog_and_notify() -> list[str]:
    """Bir marta tekshiradi, yangi (yoki cooldown o'tgan) alertlarni yuboradi.

    Qaytaradi: shu sikldа yuborilgan alert key'lari.
    """
    if not watchdog_enabled():
        return []

    try:
        state = _collect_state()
    except Exception:
        log.warning("watchdog holatni o'qiy olmadi", exc_info=True)
        return []

    cooldown = _env_int("APP_WATCHDOG_COOLDOWN_SECONDS", 3600, 60)
    now = datetime.now(timezone.utc)
    triggered = {key: msg for key, msg in evaluate_alerts(state)}
    sent: list[str] = []

    # Yangi (yoki cooldown o'tgan) alertlarni yuborish.
    for key, msg in triggered.items():
        last = _active_alerts.get(key)
        if last is None or (now - last).total_seconds() >= cooldown:
            _send_alert(_ALERT_SUBJECTS.get(key, key), msg)
            _active_alerts[key] = now
            sent.append(key)

    # Tozalangan alertlar uchun recovery bildirishnomasi (bir marta).
    for key in list(_active_alerts.keys()):
        if key not in triggered:
            _send_alert("Holat normallashdi", f"Avvalgi muammo bartaraf bo'ldi: {_ALERT_SUBJECTS.get(key, key)}")
            _active_alerts.pop(key, None)

    return sent
