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


async def _write_success_comment(
        task_key: str,
        result: Any,
        new_status: str,
        settings: "TZPRCheckerSettings",
        comment_writer: "JiraCommentWriter",
        adf_formatter: "JiraADFFormatter",
        is_recheck: bool = False
) -> None:
    """
    Muvaffaqiyatli TZ-PR tahlili uchun JIRA'ga ADF comment yozish.

    Ishlash tartibi:
    1. ADF format bilan dropdown/panel formatli comment yaratadi
    2. Agar ADF muvaffaqiyatsiz bo'lsa — oddiy text formatga fallback qiladi

    Qo'shimcha imkoniyatlar:
    - is_recheck=True bo'lsa — "Re-check" belgisi bilan comment
    - show_contradictory_comments=False bo'lsa — zid commentlar paneli yashiriladi
    - visible_sections — AI javobining qaysi bo'limlari ko'rinishini boshqaradi

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
            # Fallback — oddiy format
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
        settings: "TZPRCheckerSettings",
        comment_writer: "JiraCommentWriter",
        adf_formatter: "JiraADFFormatter"
) -> None:
    """
    Xatolik uchun JIRA'ga error comment yozish.

    ADF format mavjud bo'lsa — panel bilan chiroyli xato hujjati,
    aks holda oddiy text format ishlatiladi.

    Foydalanish holatlari:
    - PR topilmaganda
    - AI tahlil muvaffaqiyatsiz bo'lganda (unknown xato)
    - Service1 yoki Service2 general xatosi

    Args:
        task_key: JIRA task identifikatori
        error_message: Foydalanuvchiga ko'rsatiladigan xato xabari
        new_status: Xato yuz bergandagi JIRA status
        settings: TZPRCheckerSettings
        comment_writer: JIRA API
        adf_formatter: ADF document builder
    """
    try:
        if settings.use_adf_format:
            adf_doc = adf_formatter.build_error_document(task_key, error_message, new_status)
            success = comment_writer.add_comment_adf(task_key, adf_doc)

            if not success:
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
        settings: "TZPRCheckerSettings",
        comment_writer: "JiraCommentWriter",
        adf_formatter: "JiraADFFormatter"
) -> None:
    """
    Kutilmagan kritik xatolik uchun JIRA'ga critical error comment yozish.

    Bu funksiya faqat Service1 ning try/except blokida except bo'lganda,
    ya'ni kod xatosi (AttributeError, ImportError, va h.k.) yuz berganda chaqiriladi.
    Oddiy API xatolari uchun _write_error_comment() ishlatiladi.

    Args:
        task_key: JIRA task identifikatori
        error: Xato xabari (traceback yoki exception string)
        new_status: JIRA status
        settings: TZPRCheckerSettings
        comment_writer: JIRA API
        adf_formatter: ADF document builder
    """
    try:
        if settings.use_adf_format:
            adf_doc = adf_formatter.build_critical_error_document(task_key, error, new_status)
            comment_writer.add_comment_adf(task_key, adf_doc)
        else:
            simple_comment = format_critical_error_simple(task_key, error, new_status)
            comment_writer.add_comment(task_key, simple_comment)

    except Exception as e:
        log.error(f"[{task_key}] Critical error comment yozishda xato: {e}")


async def _write_timeout_error_comment(task_key: str, timeout_seconds: int) -> None:
    """
    AI queue timeout bo'lganda JIRA'ga xabar beruvchi comment yozish.

    Bu holat: boshqa task AI queue'ni ushlab turibdi,
    yangi task belgilangan vaqt (task_wait_timeout) ichida lock ololmadi.
    Comment foydalanuvchiga manual tekshirish kerakligini bildiradi.

    Args:
        task_key: Timeout bo'lgan JIRA task identifikatori
        timeout_seconds: Nechtа soniya kutildi (queue.task_wait_timeout dan)
    """
    try:
        from services.webhook.jira_webhook_handler import get_adf_formatter, get_comment_writer
        adf_formatter = get_adf_formatter()
        comment_writer = get_comment_writer()

        error_doc = adf_formatter.build_error_document(
            task_key=task_key,
            error_message=(
                f"AI tekshirish timeout: {timeout_seconds} sekunda kutildi, "
                f"boshqa task ishlanmoqda edi. "
                f"Manual tekshirish kerak."
            ),
            new_status="Ready to Test"
        )
        comment_writer.add_comment_adf(task_key, error_doc)
        log.jira_comment_added(task_key, "ADF")
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
            "AI tekshirish o'chirilgan. "
            "Dev tomanidan skip ko'rsatma berilgan. "
            "Manual tekshirish tavsiya etiladi."
        )

        content = [
            adf_formatter._heading("AI Tekshirish O'chirilgan", 2),
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
                adf_formatter._italic_text("Bu notification AI tomonidan avtomatik yaratilgan.")
            ])
        ]

        skip_doc = {
            "version": 1,
            "type": "doc",
            "content": content
        }

        success = comment_writer.add_comment_adf(task_key, skip_doc)

        if not success:
            log.warning(f"[{task_key}] Skip ADF failed, simple fallback")
            comment_writer.add_comment(task_key, f"*{skip_text}*")
            log.jira_comment_added(task_key, "simple")
        else:
            log.jira_comment_added(task_key, "ADF")

    except Exception as e:
        log.error(f"[{task_key}] Skip notification xato: {e}")


def format_error_comment_simple(task_key: str, error_message: str, new_status: str) -> str:
    """
    Xatolik uchun oddiy text format comment matni qaytarish.

    ADF format ishlamagan holatlarda fallback sifatida ishlatiladi.
    JIRA Wiki markup formatida yozilgan (bold, rule).

    Args:
        task_key: JIRA task identifikatori
        error_message: Foydalanuvchiga ko'rsatiladigan xato tavsifi
        new_status: Xato yuz bergandagi JIRA status

    Returns:
        JIRA Wiki Markup formatidagi comment matni
    """
    return f"""
*Avtomatik TZ-PR Tekshiruvi - Xatolik*

----

*Task:* {task_key}
*Vaqt:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
*Status:* {new_status}

----

*Xatolik:*

{error_message}

----

*Mumkin sabablar:*
* Task uchun PR topilmadi
* GitHub access xatoligi
* TZ (Description) bo'sh

----

_Manual tekshirish kerak. QA Team'ga xabar bering._
"""


def format_critical_error_simple(task_key: str, error: str, new_status: str) -> str:
    """
    Kritik xatolik uchun oddiy text format comment matni qaytarish.

    Kod darajasidagi kutilmagan xatolar uchun (AttributeError, ImportError va h.k.).
    ADF format ishlamagan yoki mavjud bo'lmagan holatlarda fallback sifatida.

    Args:
        task_key: JIRA task identifikatori
        error: Xato xabari yoki traceback
        new_status: JIRA status

    Returns:
        JIRA Wiki Markup formatidagi comment matni
    """
    return f"""
*Avtomatik TZ-PR Tekshiruvi - Kritik Xatolik*

----

*Task:* {task_key}
*Vaqt:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
*Status:* {new_status}

----

*Kritik Xatolik:*

{{code}}
{error}
{{code}}

----

_System administrator'ga xabar berildi._
"""
