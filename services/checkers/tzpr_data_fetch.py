"""TZPRService tashqi ma'lumot olish helperlari (JIRA/PR/Figma/TZ).

P2/M1 refactor: TZPRService'dan ajratilgan mixin. Metodlar tanasi o'zgarmagan —
TZPRService bularni meros oladi, `self.` chaqiruvlar MRO orqali hal bo'ladi.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from core import PRHelper, TZHelper
from core.logger import get_logger

log = get_logger("tzpr.checker")


class DataFetchMixin:
    @property
    def pr_helper(self):
        """Lazy PR Helper"""
        if self._pr_helper is None:
            self._pr_helper = PRHelper(self.github)
        return self._pr_helper

    def _get_figma_data(self, task_details: Dict, update_status) -> Optional[Dict]:
        """Figma ma'lumotlarini olish (FAIL-SAFE).

        Implementatsiya umumiy `core.module_preflight.fetch_figma_summaries` da —
        checker va testcase yagona figma fetch kodidan foydalanadi (xulq bir xil).
        """
        from core.module_preflight import fetch_figma_summaries
        return fetch_figma_summaries(self, task_details, update_status)

    def _has_usable_figma_data(self, figma_data: Optional[Dict]) -> bool:
        """Figma summary'lar ichida real frame/file ma'lumoti bormi."""
        if not figma_data or not figma_data.get('summaries'):
            return False

        unusable_markers = (
            "token topilmadi",
            "ruxsat yo'q",
            "access yo'q",
            "error:",
            "olinmadi",
            "summary error",
        )
        for item in figma_data.get('summaries', []):
            summary = str(item.get('summary') or '').strip().lower()
            if summary and not any(marker in summary for marker in unusable_markers):
                return True
        return False

    def _get_task_details(
            self,
            task_key: str,
            update_status,
            *,
            include_pr_urls: bool = True,
            include_figma_links: bool = True,
    ):
        """JIRA dan task ma'lumotlarini olish"""
        settings = self._get_settings()
        return self.jira.get_task_details(
            task_key,
            include_pr_urls=include_pr_urls,
            include_figma_links=include_figma_links,
            max_comments_to_read=int(getattr(settings, "max_comments_to_read", 0) or 0),
        )

    def _get_tz_content(self, task_details: Dict, update_status):
        """TZ kontentini olish"""
        tz_settings = self._get_settings()

        if not tz_settings.read_comments_enabled:
            # Comments o'chirilgan: bo'sh comment list ile chaqirish
            task_no_comments = dict(task_details)
            task_no_comments['comments'] = []
            tz_content, comment_analysis = TZHelper.format_tz_with_comments(
                task_no_comments,
                exclude_ai_comments=True,
            )
        else:
            max_c = tz_settings.max_comments_to_read if tz_settings.max_comments_to_read > 0 else None
            tz_content, comment_analysis = TZHelper.format_tz_with_comments(
                task_details,
                max_comments=max_c,
                exclude_ai_comments=True,
            )

        if comment_analysis['has_changes']:
            update_status("warning", comment_analysis['summary'])
        filtered_ai_comments = int(comment_analysis.get('filtered_out_ai_comments') or 0)
        if filtered_ai_comments > 0:
            update_status(
                "info",
                f"Promptdan {filtered_ai_comments} ta oldingi AI comment chiqarib tashlandi",
            )

        return tz_content, comment_analysis

    def _is_tz_too_short(self, task_details: Dict, min_chars: int) -> bool:
        """TZ description belgilangan minimal uzunlikdan qisqami aniqlash."""
        return self._get_tz_length_chars(task_details) < min_chars

    @staticmethod
    def _get_tz_length_chars(task_details: Dict[str, Any]) -> int:
        """TZ mazmunini description asosida hisoblash."""
        description = str(task_details.get("description") or "").strip()
        return len(description)

    def _get_pr_info(self, task_key: str, task_details: Dict, update_status, use_smart_patch):
        """PR ma'lumotlarini olish va cache ga saqlash"""
        pr_info = self.pr_helper.get_pr_full_info(
            task_key,
            task_details,
            update_status,
            use_smart_patch=use_smart_patch
        )

        return pr_info
