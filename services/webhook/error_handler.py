"""
Error Handler Module - Xato boshqaruvi va comment yozish
=========================================================

Bu modul webhook oqimida yuz beradigan barcha xatolarni boshqaradi:
- Xato turini aniqlash (_classify_error)
- JIRA'ga turli xil xato comment'lar yozish
- Muvaffaqiyatli tahlil uchun comment yozish
- Skip notification comment yozish

Barcha comment yozish funksiyalari shu modulda to'plangan (DRY printsipi).
"""
from typing import TYPE_CHECKING, Any
from datetime import datetime

from core.logger import get_logger
from core.constants import (
    WARN_NO_PR, WARN_PR_NOT_MERGED, WARN_MIN_TZ,
    WARN_AI_TIMEOUT, ERR_UNKNOWN
)

if TYPE_CHECKING:
    from config.app_settings import TZPRCheckerSettings
    from utils.jira.jira_comment_writer import JiraCommentWriter
    from utils.jira.jira_adf_formatter import JiraADFFormatter

log = get_logger("webhook.error_handler")


def _classify_error(error_msg: str) -> str:
    """
    Xato xabarini turiga qarab ajratish.

    Webhook oqimida uch turdagi xatolar mavjud:
    1. 'pr_not_found' — GitHub'da PR topilmadi (Service2 baribir ishlashi mumkin)
    2. 'ai_timeout'   — Google Gemini API ishlamadi (rate limit, 429, quota)
                        Bu holda task 'blocked' holatga tushadi va keyinroq qayta uriniladi
    3. 'unknown'      — Boshqa turdagi xatolar (DB, JIRA, network, kod xatolari)

    Mantiq: string matching orqali — keyword'lar bo'yicha kategoriyalash.

    Args:
        error_msg: Xato xabari (Exception string)

    Returns:
        'pr_not_found' | 'ai_timeout' | 'unknown'
    """
    if not error_msg:
        return 'unknown'
    msg_lower = error_msg.lower()

    # PR topilmadi
    pr_keywords = ['pr topilmadi', 'pr not found', 'no pr found', 'pull request not found']
    if any(kw in msg_lower for kw in pr_keywords):
        return 'pr_not_found'

    # PR merged emas (open yoki closed/cancelled)
    pr_not_merged_keywords = ['pr merged emas', 'merged emas', 'not merged', 'pr not merged']
    if any(kw in msg_lower for kw in pr_not_merged_keywords):
        return 'pr_not_merged'

    # TZ yetarli emas (description belgilangan chegaradan qisqa)
    tz_too_short_keywords = ['tz yetarli emas', 'tz kam', 'description yetarli emas', 'servis-1 to\'xtatildi', "servis-2 to'xtatildi", 'tz minimal']
    if any(kw in msg_lower for kw in tz_too_short_keywords):
        return 'tz_too_short'

    # AI timeout / rate limit / 429 (ikkala key ham ishlamadi ham kiradi)
    ai_timeout_keywords = [
        'timeout', '429', 'rate limit', 'rate_limit',
        'overloaded', 'quota', 'resource exhausted',
        'resource_exhausted', 'too many requests',
        'ikkala key ham ishlamadi', 'both keys failed',
        'gemini api xatosi', 'token limit',
        'context length', 'prompt too large',
        'full_blocked_overload', 'ai limitidan oshdi',
        'freeze holatida', 'barcha api keylar', 'all keys frozen'
    ]
    if any(kw in msg_lower for kw in ai_timeout_keywords):
        return 'ai_timeout'

    return 'unknown'


def _error_type_to_reason_code(error_type: str) -> str:
    """error_type string → DB/comment uchun reason code"""
    mapping = {
        'pr_not_found':    WARN_NO_PR,
        'pr_not_merged':   WARN_PR_NOT_MERGED,
        'tz_too_short':    WARN_MIN_TZ,
        'ai_timeout':      WARN_AI_TIMEOUT,
    }
    return mapping.get(error_type, ERR_UNKNOWN)


async def _write_success_comment(
        task_key: str,
        result: Any,
        new_status: str,
        settings: "TZPRCheckerSettings",
        comment_writer: "JiraCommentWriter",
        adf_formatter: "JiraADFFormatter",
        is_recheck: bool = False,
        dev_objections: list = None
) -> None:
    """
    Muvaffaqiyatli TZ-PR tahlili uchun JIRA'ga ADF comment yozish.

    Ishlash tartibi:
    1. ADF format bilan dropdown/panel formatli comment yaratadi
    2. Agar ADF muvaffaqiyatsiz bo'lsa — oddiy text formatga fallback qiladi

    Qo'shimcha imkoniyatlar:
    - is_recheck=True bo'lsa — "Re-check" belgisi bilan comment
    - comment bo'limlari UI checker final report contracti bilan bir xil render qilinadi

    Args:
        task_key: JIRA task identifikatori (masalan: 'DEV-1234')
        result: TZPRAnalysisResult — AI tahlil natijasi (score, analysis, figma)
        new_status: JIRA'dagi yangi status nomi
        settings: TZPRCheckerSettings — sozlamalar
        comment_writer: JIRA comment yozish uchun
        adf_formatter: ADF document qurish uchun
        is_recheck: Agar True bo'lsa, comment'da re-check belgisi ko'rinadi
    """
    try:
        extra_scan_enabled = bool(getattr(settings, "agent2_extra_scan_enabled", True))
        adf_doc = adf_formatter.build_comment_document(
            result,
            new_status,
            footer_text=settings.tz_pr_footer_text,
            is_recheck=is_recheck,
            recheck_text=settings.recheck_comment_text,
            dev_objections=dev_objections or [],
            extra_scan_enabled=extra_scan_enabled
        )
        success = comment_writer.add_comment_adf(task_key, adf_doc)

        if not success:
            # Fallback — oddiy format
            log.warning(f"[{task_key}] ADF failed, falling back to simple format")
            simple_comment = adf_formatter.build_simple_comment(
                result,
                new_status,
                extra_scan_enabled=extra_scan_enabled,
            )
            comment_writer.add_comment(task_key, simple_comment)

    except Exception as e:
        log.error(f"[{task_key}] Comment yozishda xato: {e}")


def _build_warning_adf(
        adf_formatter: "JiraADFFormatter",
        service: str,
        reason: str,
        task_key: str,
        panel_type: str = "warning",
        reason_code: str = ""
) -> dict:
    """
    Qisqa Warning ADF panel document qurish.

    panel_type: 'warning' (sariq) — kutilgan xatoliklar uchun
                'error'   (qizil) — kutilmagan kritik xatoliklar uchun
    reason_code: WARN_MIN_TZ, WARN_NO_PR kabi kod (bo'sh bo'lsa yozilmaydi)
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    marker = f"[AI_S1][{reason_code}]" if reason_code else "[AI_S1]"
    return {
        "version": 1,
        "type": "doc",
        "content": [
            adf_formatter._panel([
                adf_formatter._paragraph([
                    adf_formatter._bold_text(f"⚠️ {service} | Warning"),
                    adf_formatter._hard_break(),
                    adf_formatter._text_node(reason),
                    adf_formatter._hard_break(),
                    adf_formatter._italic_text(
                        f"{task_key} | {timestamp} | Manual tekshirish tavsiya etiladi"
                    )
                ])
            ], panel_type),
            adf_formatter._paragraph([adf_formatter._text_node(marker)])
        ]
    }


def format_warning_simple(service: str, reason: str, task_key: str, reason_code: str = "") -> str:
    """Qisqa Warning oddiy text fallback (ADF ishlamagan holatda)."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    marker = f"[AI_S1][{reason_code}]" if reason_code else "[AI_S1]"
    return (
        f"{marker}\n"
        f"⚠️ *{service} | Warning*\n\n"
        f"{reason}\n\n"
        f"_{task_key} | {timestamp} | Manual tekshirish tavsiya etiladi_"
    )


async def _write_error_comment(
        task_key: str,
        error_message: str,
        comment_writer: "JiraCommentWriter",
        adf_formatter: "JiraADFFormatter",
        service: str = "Servis-1",
        reason_code: str = "",
        panel_type: str = "warning"
) -> None:
    """
    Xatolik uchun JIRA'ga qisqa Warning/Error panel comment yozish.

    Foydalanish holatlari:
    - PR topilmaganda
    - AI tahlil muvaffaqiyatsiz bo'lganda
    - Service1 yoki Service2 general xatosi
    """
    try:
        warning_doc = _build_warning_adf(adf_formatter, service, error_message, task_key, panel_type=panel_type, reason_code=reason_code)
        success = comment_writer.add_comment_adf(task_key, warning_doc)
        if not success:
            comment_writer.add_comment(task_key, format_warning_simple(service, error_message, task_key, reason_code=reason_code))
    except Exception as e:
        log.error(f"[{task_key}] Error comment yozishda xato: {e}")


async def _write_critical_error(
        task_key: str,
        error: str,
        new_status: str,
        settings: "TZPRCheckerSettings",
        comment_writer: "JiraCommentWriter",
        adf_formatter: "JiraADFFormatter"
) -> None:
    """
    Kutilmagan kritik xatolik uchun JIRA'ga qisqa Error panel comment yozish.

    Bu funksiya faqat Service1 ning try/except blokida except bo'lganda,
    ya'ni kod xatosi (AttributeError, ImportError, va h.k.) yuz berganda chaqiriladi.
    Oddiy API xatolari uchun _write_error_comment() ishlatiladi.
    """
    try:
        # Traceback juda uzun bo'lishi mumkin — qisqartirib yozamiz
        reason = f"Kutilmagan tizim xatosi: {error[:200]}"
        warning_doc = _build_warning_adf(adf_formatter, "Servis-1", reason, task_key, "error")
        success = comment_writer.add_comment_adf(task_key, warning_doc)
        if not success:
            comment_writer.add_comment(task_key, format_warning_simple("Servis-1", reason, task_key))
    except Exception as e:
        log.error(f"[{task_key}] Critical error comment yozishda xato: {e}")


async def _write_timeout_error_comment(task_key: str, timeout_seconds: int, company_id: int = None) -> None:
    """
    AI queue timeout bo'lganda JIRA'ga qisqa Warning panel comment yozish.

    Bu holat: boshqa task AI queue'ni ushlab turibdi,
    yangi task belgilangan vaqt (task_wait_timeout) ichida lock ololmadi.
    """
    try:
        from services.webhook.jira_webhook_handler import get_adf_formatter
        from utils.jira.jira_comment_writer import JiraCommentWriter
        from utils.auth.auth_db import get_company_credentials
        adf_formatter = get_adf_formatter()
        from utils.auth.auth_db import get_company_webhook_credentials
        creds = get_company_webhook_credentials(company_id)
        comment_writer = JiraCommentWriter(
            server=creds['jira_server'],
            email=creds['jira_email'],
            token=creds['jira_token'],
        )

        reason = f"AI queue timeout ({timeout_seconds}s). Boshqa task ishlanmoqda edi."
        warning_doc = _build_warning_adf(adf_formatter, "Sistem", reason, task_key)
        success = comment_writer.add_comment_adf(task_key, warning_doc)
        if not success:
            comment_writer.add_comment(task_key, format_warning_simple("Sistem", reason, task_key))
        log.jira_comment_added(task_key, "Warning ADF")
    except Exception as e:
        log.error(f"[{task_key}] Timeout error comment yozishda xato: {e}")


async def _write_skip_notification(
        task_key: str,
        settings: "TZPRCheckerSettings",
        comment_writer: "JiraCommentWriter",
        adf_formatter: "JiraADFFormatter"
) -> None:
    """
    Skip code topilganda JIRA'ga "AI tekshirish o'chirilgan" notification yozish.

    Dev "AI_SKIP" (yoki settings dagi skip_code) commentini yozganida,
    Service1 o'chiriladi va bu notification JIRA'ga yoziladi.
    Foydalanuvchiga manual tekshirish kerakligini eslatadi.

    ADF format: heading + rule + task info paragraph + warning panel + footer.
    Agar ADF muvaffaqiyatsiz → oddiy text fallback.

    Args:
        task_key: JIRA task identifikatori
        settings: TZPRCheckerSettings (skip_code, skip_comment_text olish uchun)
        comment_writer: JIRA API
        adf_formatter: ADF document builder
    """
    try:
        skip_text = settings.skip_comment_text or (
            "⏭️ AI tekshirish o'chirilgan. "
            "Dev tomanidan skip ko'rsatma berilgan. "
            "Manual tekshirish tavsiya etiladi."
        )

        skip_doc = _build_warning_adf(adf_formatter, "AI Skip", skip_text, task_key, "note")

        success = comment_writer.add_comment_adf(task_key, skip_doc)

        if not success:
            log.warning(f"[{task_key}] Skip ADF failed, simple fallback")
            comment_writer.add_comment(task_key, skip_text)
            log.jira_comment_added(task_key, "simple")
        else:
            log.jira_comment_added(task_key, "ADF")

    except Exception as e:
        log.error(f"[{task_key}] Skip notification xato: {e}")
