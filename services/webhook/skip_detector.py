"""
Skip Detector Module - Skip aniqlash
=====================================

Bu modul webhook oqimida AI_SKIP holatni aniqlaydi:
Developer JIRA comment'da skip code yozsa → Service1 o'chiriladi, Service2 ishlaydi.

Stateless — faqat JIRA'dan ma'lumot o'qiydi, hech narsa yozmaydi.
"""
from typing import TYPE_CHECKING

from core.logger import get_logger

if TYPE_CHECKING:
    from config.app_settings import TZPRCheckerSettings
    from utils.jira.jira_comment_writer import JiraCommentWriter

log = get_logger("webhook.skip_detector")


async def _check_skip_code(
        task_key: str,
        skip_code: str,
        comment_writer: "JiraCommentWriter"
) -> bool:
    """
    JIRA task comment'larida skip_code borligini tekshirish.

    Developer "AI_SKIP" (yoki settings.skip_code) deb comment yozsa,
    Service1 (TZ-PR tahlil) o'chiriladi. Birinchi urinishda ham ishlaydi —
    return_count sharti yo'q.

    Tekshirish qoidalari:
    - Faqat so'nggi N ta comment tekshiriladi (settings.max_skip_check_comments, default=5)
    - Case-insensitive: "ai_skip", "AI_SKIP", "Ai_Skip" — barchasi ishlaydi
    - Birinchi moslik topilsa True qaytariladi

    Xatolik holati: JIRA client yo'q yoki API xato → False qaytariladi
    (xato bo'lsa AI tekshirish davom etadi, skip o'chirilmaydi)

    Args:
        task_key: JIRA task identifikatori (masalan: 'DEV-1234')
        skip_code: Qidiriladigan skip kalit so'zi (masalan: 'AI_SKIP')
        comment_writer: JIRA comment writer (jira client orqali issue o'qish uchun)

    Returns:
        True — skip code topildi, Service1 o'chirilsin
        False — skip code topilmadi yoki JIRA API xatosi
    """
    try:
        if not comment_writer.jira:
            log.warning(f"[{task_key}] JIRA client yo'q, skip check o'chgan")
            return False

        issue = comment_writer.jira.issue(task_key)
        comments = sorted(issue.fields.comment.comments, key=lambda c: c.created, reverse=True)

        # Settings'dan nechta comment tekshirish kerakligini olish
        from config.app_settings import get_app_settings
        app_settings = get_app_settings(force_reload=False)
        max_comments = app_settings.tz_pr_checker.max_skip_check_comments

        # Faqat so'nggi N ta comment tekshiriladi (performance uchun)
        for comment in comments[:max_comments]:
            comment_body = comment.body if comment.body else ""
            if skip_code.upper() in comment_body.upper():
                log.info(
                    f"[{task_key}] Skip code '{skip_code}' topildi: "
                    f"author={comment.author.displayName}, created={comment.created}"
                )
                return True

        return False

    except Exception as e:
        log.error(f"[{task_key}] Skip code check xato: {e}")
        return False  # Xato bo'lsa AI davom etadi
