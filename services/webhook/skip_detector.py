"""
Skip Detector Module - Skip aniqlash
=====================================

Bu modul webhook oqimida AI_SKIP holatni aniqlaydi:
Developer JIRA comment'da skip code yozsa → Service1 o'chiriladi, Service2 ishlaydi.

Stateless — faqat JIRA'dan ma'lumot o'qiydi, hech narsa yozmaydi.
"""
from typing import TYPE_CHECKING

import requests

from core.logger import get_logger

if TYPE_CHECKING:
    from config.app_settings import TZPRCheckerSettings
    from utils.jira.jira_comment_writer import JiraCommentWriter

log = get_logger("webhook.skip_detector")


def _comment_body(comment) -> str:
    if isinstance(comment, dict):
        return str(comment.get("body") or "")
    return str(getattr(comment, "body", "") or "")


def _comment_author(comment) -> str:
    if isinstance(comment, dict):
        return str(comment.get("author") or "Unknown")
    author = getattr(comment, "author", None)
    return str(getattr(author, "displayName", None) or getattr(author, "name", None) or "Unknown")


def _comment_created(comment) -> str:
    if isinstance(comment, dict):
        return str(comment.get("created") or "")
    return str(getattr(comment, "created", "") or "")


def check_skip_code_in_comments(
        task_key: str,
        skip_code: str,
        comments,
        *,
        max_comments: int,
) -> bool:
    """Oldindan olingan commentlar ichidan skip code'ni qidirish."""
    code = str(skip_code or "").strip()
    if not code:
        return False

    try:
        comments_to_check = int(max_comments)
    except (TypeError, ValueError):
        comments_to_check = 5
    if comments_to_check <= 0:
        comments_to_check = 5

    recent_comments = list(comments or [])[-comments_to_check:]
    for comment in reversed(recent_comments):
        comment_body = _comment_body(comment)
        if code.upper() in comment_body.upper():
            log.info(
                f"[{task_key}] Skip code '{code}' topildi: "
                f"author={_comment_author(comment)}, created={_comment_created(comment)}"
            )
            return True
    return False


async def _check_skip_code(
        task_key: str,
        skip_code: str,
        comment_writer: "JiraCommentWriter",
        max_comments: int | None = None,
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
        comments = list(issue.fields.comment.comments or [])

        # Webhook checker scope'dan berilgan qiymat ustuvor.
        # Berilmasa settings.max_skip_check_comments, oxirgi fallback 5.
        if isinstance(max_comments, int) and max_comments > 0:
            comments_to_check = max_comments
        else:
            try:
                from config.app_settings import get_app_settings

                comments_to_check = int(get_app_settings().webhook_tz_pr.max_skip_check_comments)
            except Exception:
                comments_to_check = 5
            if comments_to_check <= 0:
                comments_to_check = 5

        return check_skip_code_in_comments(
            task_key,
            skip_code,
            comments,
            max_comments=comments_to_check,
        )

    except Exception as e:
        log.error(f"[{task_key}] Skip code check xato: {e}")
        return False  # Xato bo'lsa AI davom etadi


async def _detect_recheck(
        task_key: str,
        settings: "TZPRCheckerSettings",
        comment_writer: "JiraCommentWriter",
) -> bool:
    """
    JIRA changelog'da task return statusdan trigger statusga qaytganini aniqlash.

    Bu yordamchi eski webhook testlari va re-check oqimi uchun saqlangan:
    changelog ichida ``field=status`` va ``fromString=settings.return_status``
    bo'lsa, task qayta tekshiruvga qaytgan hisoblanadi.
    """
    try:
        if not comment_writer.jira:
            log.warning(f"[{task_key}] JIRA client yo'q, re-check aniqlanmadi")
            return False

        server = ""
        try:
            server = str(comment_writer.jira._options.get("server") or "").rstrip("/")
        except Exception:
            server = ""

        url = f"{server}/rest/api/2/issue/{task_key}?expand=changelog" if server else task_key
        response = requests.get(url)
        if response.status_code != 200:
            log.warning(f"[{task_key}] Re-check changelog API status={response.status_code}")
            return False

        return_status = str(getattr(settings, "return_status", "") or "").strip().lower()
        if not return_status:
            return False

        data = response.json() or {}
        histories = data.get("changelog", {}).get("histories", []) or []
        for history in histories:
            for item in history.get("items", []) or []:
                if str(item.get("field", "")).lower() != "status":
                    continue
                from_status = str(item.get("fromString", "") or "").strip().lower()
                if from_status == return_status:
                    return True
        return False
    except Exception as e:
        log.error(f"[{task_key}] Re-check detection xato: {e}")
        return False
