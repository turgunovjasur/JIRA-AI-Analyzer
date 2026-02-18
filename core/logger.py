"""
JIRA-AI-Analyzer: Unified Logging System
Windows CMD-friendly, strukturali, o'qish oson
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """CMD-friendly formatter (ranglar ixtiyoriy)"""

    # Windows CMD uchun ANSI rang kodlari (ixtiyoriy)
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'RESET': '\033[0m'
    }

    def __init__(self, use_colors: bool = False):
        super().__init__(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.use_colors = use_colors

    def format(self, record):
        if self.use_colors and record.levelname in self.COLORS:
            levelname_color = self.COLORS[record.levelname]
            reset = self.COLORS['RESET']
            record.levelname = f"{levelname_color}{record.levelname}{reset}"

        return super().format(record)


class StructuredLogger:
    """
    Windows CMD-friendly structured logger

    Asosiy xususiyatlar:
    - Oddiy, tushunarli format
    - Emoji o'rniga text prefix'lar
    - Bir satrda maksimal ma'lumot
    - Task key-based filtering
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_handlers()

    def _setup_handlers(self):
        """Logger handler'larni sozlash"""
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)

            # Console handler (rang bilan, ixtiyoriy)
            console = logging.StreamHandler(sys.stdout)
            console.setFormatter(ColoredFormatter(use_colors=False))  # Windows uchun False

            # File handler (rang yo'q)
            log_file = Path("data/webhook.log")
            log_file.parent.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(ColoredFormatter(use_colors=False))

            self.logger.addHandler(console)
            self.logger.addHandler(file_handler)

    # === WEBHOOK LIFECYCLE ===

    def webhook_received(self, task_key: str, event_type: str):
        """Webhook qabul qilindi"""
        self.logger.info(f"[{task_key}] WEBHOOK -> {event_type}")

    def status_changed(self, task_key: str, from_status: str, to_status: str):
        """Status o'zgarishi"""
        self.logger.info(f"[{task_key}] STATUS -> {from_status} => {to_status}")

    def status_ignored(self, task_key: str, status: str, reason: str):
        """Status ignore qilindi"""
        self.logger.info(f"[{task_key}] SKIP -> {status} ({reason})")

    def target_status_matched(self, task_key: str, status: str):
        """Target statusga mos keldi"""
        self.logger.info(f"[{task_key}] TARGET-MATCH -> {status} | Starting analysis...")

    # === DATABASE OPERATIONS ===

    def db_state_checked(self, task_key: str, status: str, return_count: int,
                        last_status: Optional[str] = None):
        """DB holat tekshirildi"""
        info = f"status={status} | returns={return_count}"
        if last_status:
            info += f" | last_jira_status={last_status}"
        self.logger.info(f"[{task_key}] DB-STATE -> {info}")

    def db_state_updated(self, task_key: str, old: str, new: str):
        """DB holat yangilandi"""
        self.logger.info(f"[{task_key}] DB-UPDATE -> {old} => {new}")

    def db_reset(self, task_key: str, reason: str):
        """DB reset qilindi"""
        self.logger.warning(f"[{task_key}] DB-RESET -> {reason}")

    # === SERVICE LIFECYCLE ===

    def service_started(self, task_key: str, service: str):
        """Service boshlandi"""
        self.logger.info(f"[{task_key}] SERVICE-START -> {service}")

    def service_completed(self, task_key: str, service: str, result: str):
        """Service tugadi"""
        self.logger.info(f"[{task_key}] SERVICE-DONE -> {service} | {result}")

    def service_failed(self, task_key: str, service: str, error: str):
        """Service xato berdi"""
        self.logger.error(f"[{task_key}] SERVICE-ERROR -> {service} | {error}")

    def service_skipped(self, task_key: str, service: str, reason: str):
        """Service skip qilindi"""
        self.logger.info(f"[{task_key}] SERVICE-SKIP -> {service} ({reason})")

    # === COMPACT SERVICE LOGGING (Minimal) ===

    def service_running(self, task_key: str, service: str):
        """Service running (compact)"""
        self.logger.info(f"[{task_key}] {service} running")

    def service_done(self, task_key: str, service: str, **kwargs):
        """Service done (compact)"""
        details = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        self.logger.info(f"[{task_key}] {service} DONE | {details}")

    def service_error(self, task_key: str, service: str, error: str):
        """Service error (compact)"""
        self.logger.error(f"[{task_key}] {service} ERROR | {error}")

    def service_skip(self, task_key: str, service: str, reason: str):
        """Service skip (compact)"""
        self.logger.info(f"[{task_key}] {service} SKIP | {reason}")

    # === AI OPERATIONS ===

    def ai_analyzing(self, task_key: str, model: str):
        """AI tahlil qilmoqda"""
        self.logger.info(f"[{task_key}] AI-ANALYZE -> model={model}")

    def ai_ready(self, model: str, key_count: int):
        """AI tayyor"""
        self.logger.info(f"AI-READY -> model={model} | keys={key_count}")

    def ai_rate_limit(self, key_name: str, retry_after: int):
        """AI rate limit"""
        self.logger.warning(f"AI-RATE-LIMIT -> {key_name} | retry={retry_after}s")

    def ai_key_fallback(self, from_key: str, to_key: str):
        """API key fallback"""
        self.logger.warning(f"AI-FALLBACK -> {from_key} => {to_key}")

    # === SCORING & THRESHOLD ===

    def score_evaluated(self, task_key: str, score: int, threshold: int, passed: bool):
        """Score baholandi"""
        status = "PASS" if passed else "FAIL"
        self.logger.info(f"[{task_key}] SCORE -> {score}% vs {threshold}% | {status}")

    def task_returning(self, task_key: str, target_status: str, score: int):
        """Task qaytarilmoqda"""
        self.logger.warning(f"[{task_key}] AUTO-RETURN -> {target_status} | score={score}%")

    def task_returned(self, task_key: str, status: str):
        """Task qaytarildi"""
        self.logger.info(f"[{task_key}] RETURNED -> {status}")

    # === JIRA OPERATIONS ===

    def jira_connected(self, purpose: str = "operations"):
        """JIRA connected"""
        self.logger.info(f"JIRA-CONNECTED -> {purpose}")

    def jira_comment_added(self, task_key: str, format_type: str = "ADF"):
        """JIRA komment qo'shildi"""
        self.logger.info(f"[{task_key}] JIRA-COMMENT -> {format_type} added")

    def jira_comment_failed(self, task_key: str, error: str):
        """JIRA komment xatosi"""
        self.logger.error(f"[{task_key}] JIRA-ERROR -> {error}")

    def jira_transitions_available(self, task_key: str, count: int):
        """JIRA transition'lar mavjud"""
        self.logger.info(f"[{task_key}] JIRA-TRANSITIONS -> {count} available")

    def jira_transitioned(self, task_key: str, target_status: str):
        """JIRA status o'zgartirildi"""
        self.logger.info(f"[{task_key}] JIRA-TRANSITIONED -> {target_status}")

    # === QUEUE & DELAYS ===

    def queue_waiting(self, task_key: str, reason: str, seconds: float):
        """Queue kutish"""
        self.logger.info(f"[{task_key}] QUEUE-WAIT -> {reason} | {seconds}s")

    def queue_timeout(self, task_key: str, seconds: int):
        """Queue timeout"""
        self.logger.warning(f"[{task_key}] QUEUE-TIMEOUT -> {seconds}s exceeded")

    def delay_waiting(self, task_key: str, reason: str, seconds: int):
        """Delay kutish"""
        self.logger.info(f"[{task_key}] DELAY -> {reason} | waiting {seconds}s")

    # === ERRORS ===

    def error(self, task_key: str, context: str, error: str):
        """Umumiy xato"""
        self.logger.error(f"[{task_key}] ERROR -> {context} | {error}")

    def pr_not_found(self, task_key: str):
        """PR topilmadi"""
        self.logger.error(f"[{task_key}] PR-NOT-FOUND -> checked JIRA & GitHub")

    def json_parse_error(self, task_key: str, details: str):
        """JSON parse xatosi"""
        self.logger.warning(f"[{task_key}] JSON-PARSE-ERROR -> {details}")

    def json_repair_attempt(self, task_key: str):
        """JSON repair urinish"""
        self.logger.warning(f"[{task_key}] JSON-REPAIR -> attempting fix...")

    def json_repair_success(self, task_key: str, result: str):
        """JSON repair muvaffaqiyatli"""
        self.logger.info(f"[{task_key}] JSON-REPAIR -> success | {result}")

    # === SYSTEM LIFECYCLE ===

    def system_started(self, version: str, port: int):
        """Tizim boshlandi"""
        separator = "=" * 80
        self.logger.info(separator)
        self.logger.info(f"SYSTEM-START -> JIRA TZ-PR Auto Checker v{version}")
        self.logger.info(f"LISTENING -> http://0.0.0.0:{port}/webhook/jira")
        self.logger.info(f"TIME -> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(separator)

    def settings_loaded(self, **kwargs):
        """Sozlamalar yuklandi"""
        settings_str = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        self.logger.info(f"SETTINGS -> {settings_str}")

    def request_separator(self):
        """So'rov ajratuvchi"""
        self.logger.info("=" * 80)

    # === GENERIC LOGGING ===

    def info(self, message: str):
        """Generic info log"""
        self.logger.info(message)

    def warning(self, message: str):
        """Generic warning log"""
        self.logger.warning(message)

    def debug(self, message: str):
        """Generic debug log"""
        self.logger.debug(message)


# Global logger factory
def get_logger(name: str) -> StructuredLogger:
    """Logger factory function"""
    return StructuredLogger(name)
