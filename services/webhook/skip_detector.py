"""
Skip Detector Module - Skip va Re-check aniqlash
=================================================

Bu modul webhook oqimida ikki muhim holatni aniqlaydi:

1. AI_SKIP — developer JIRA comment'da skip code yozgan
   → Service1 (TZ-PR check) o'chiriladi, Service2 baribir ishlashi mumkin

2. Re-check — task avval "Return" statusga qaytarilgan,
   so'ng yana trigger statusga o'tkazilgan
   → Comment'da "Re-check" belgisi ko'rinadi

Ikkala funksiya ham stateless — faqat JIRA'dan ma'lumot o'qiydi, hech narsa yozmaydi.
"""
import os
from typing import TYPE_CHECKING

import requests
from dotenv import load_dotenv

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


async def _detect_recheck(
        task_key: str,
        settings: "TZPRCheckerSettings",
        comment_writer: "JiraCommentWriter"
) -> bool:
    """
    Task avval "Return" statusga qaytarilibdi-yu, yana trigger statusga tushganini aniqlash.

    Mantiq: JIRA REST API orqali task changelog'ini o'qib,
    oxirgi status o'zgarishida "fromString" settings.return_status ga teng
    ekanligini tekshirish. Agar shunday bo'lsa — bu re-check.

    Misollar:
    - "In Progress" → "Ready to Test" — oddiy tahlil (False)
    - "Return to Dev" → "Ready to Test" — re-check (True)
    - "Ready to Test" → "Ready to Test" — changelog orqali topilmaydi (False)

    JIRA REST API v2 ishlatiladi chunki python-jira changelog'ni to'g'ridan
    qo'llab-quvvatlamaydi.

    Xatolik holati: API xato → False qaytariladi (re-check belgisi qo'yilmaydi,
    tahlil davom etadi)

    Args:
        task_key: JIRA task identifikatori
        settings: TZPRCheckerSettings (return_status olish uchun)
        comment_writer: JIRA client (connection ma'lumotlari uchun)

    Returns:
        True — re-check aniqlandi (task avval qaytarilgan edi)
        False — oddiy birinchi tahlil yoki API xatosi
    """
    try:
        if not comment_writer.jira:
            return False

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

        # Eng so'nggi status o'zgarishni tekshirish (reversed = eng yaqindan)
        return_status_lower = settings.return_status.lower()

        for history in reversed(changelog):
            for item in history.get('items', []):
                if item.get('field', '').lower() == 'status':
                    from_status = item.get('fromString', '')
                    # Oldingi status return_status bo'lgan bo'lsa — re-check
                    if from_status.lower() == return_status_lower:
                        log.info(f"[{task_key}] Re-check: {from_status} → {item.get('toString')}")
                        return True
                    # Birinchi (eng yaqin) status o'zgarishi ko'rib chiqildi
                    return False

        return False

    except Exception as e:
        log.error(f"[{task_key}] Re-check detect xato: {e}")
        return False
