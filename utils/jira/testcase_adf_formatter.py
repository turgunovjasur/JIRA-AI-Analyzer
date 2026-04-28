# utils/jira/testcase_adf_formatter.py
"""
Testcase ADF (Atlassian Document Format) Formatter

Test case'larni JIRA Cloud uchun ADF formatda formatlash.
Expand panel (dropdown/collapsible) ishlatiladi - har bir test case
alohida panel ichida bo'ladi.

ADF Hujjatlar: https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/

Author: JASUR TURGUNOV
Version: 1.0
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from utils.jira.base_adf_formatter import BaseADFFormatter

logger = logging.getLogger(__name__)


class TestcaseADFFormatter(BaseADFFormatter):
    """Test case'larni ADF formatda JIRA comment uchun formatlash"""

    _contradictory_action_text = "test case'lar yarating!"

    def __init__(self):
        """Initialize formatter"""
        pass

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # NUMBERED LIST (testcase specific)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _numbered_list(self, items: List[str]) -> Dict:
        """Numbered list yaratish"""
        list_items = []
        for item in items:
            list_items.append({
                "type": "listItem",
                "content": [self._paragraph([self._text_node(item)])]
            })
        return {"type": "orderedList", "content": list_items}

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PRIORITY/SEVERITY COLORS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _get_priority_color(self, priority: str) -> str:
        """Priority uchun rang"""
        colors = {
            'High': '#FF5630',
            'Critical': '#FF5630',
            'Medium': '#FFAB00',
            'Low': '#36B37E',
            'Minor': '#36B37E'
        }
        return colors.get(priority, '#8b949e')

    def _get_type_emoji(self, test_type: str) -> str:
        """Test type uchun emoji"""
        emojis = {
            'positive': '✅',
            'negative': '❌',
            'boundary': '🔲',
            'edge': '⚡',
            'performance': '🚀',
            'security': '🔒'
        }
        return emojis.get(test_type.lower(), '🧪')

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TESTCASE DOCUMENT BUILDER
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def build_testcase_document(
            self,
            task_key: str,
            test_cases: List[Any],
            comment_analysis: Optional[Dict] = None,
            footer_text: Optional[str] = None,
            pr_details: Optional[List[Dict]] = None,
            pr_count: int = 0,
            files_changed: int = 0
    ) -> Dict:
        """
        Test case'lar uchun to'liq ADF document yaratish

        Args:
            task_key: JIRA task key (masalan: DEV-1234)
            test_cases: TestCase ob'ektlari ro'yxati
            comment_analysis: TZHelper.analyze_comments() natijasi (optional)
            footer_text: Settings-dan olingan footer matn (None bo'lsa default)

        Returns:
            ADF document (dict)
        """
        content = []

        # ━━━ AI MARKER (comment ajratish uchun) ━━━
        content.append(self._paragraph([self._text_node("[AI_S2]")]))

        # ━━━ HEADER ━━━
        content.append(self._heading("🧪 Test Cases", 2))
        content.append(self._rule())

        # ━━━ META INFO ━━━
        meta_text = [
            self._bold_text("Task: "),
            self._text_node(task_key),
            self._hard_break(),
            self._bold_text("Yaratilgan: "),
            self._text_node(datetime.now().strftime('%Y-%m-%d %H:%M')),
            self._hard_break(),
            self._bold_text("Jami: "),
            self._text_node(f"{len(test_cases)} ta test case")
        ]
        content.append(self._paragraph(meta_text))

        # ━━━ ZID COMMENTLAR PANEL ━━━
        if comment_analysis:
            contradictory_panel = self._build_contradictory_comments_panel(comment_analysis)
            if contradictory_panel:
                content.append(self._rule())
                content.append(contradictory_panel)
        content.append(self._rule())

        # ━━━ STATISTIKA ━━━
        by_type = {}
        by_priority = {}
        for tc in test_cases:
            t = getattr(tc, 'test_type', 'unknown')
            by_type[t] = by_type.get(t, 0) + 1

            p = getattr(tc, 'priority', 'Medium')
            by_priority[p] = by_priority.get(p, 0) + 1

        content.append(self._heading("📊 Statistika", 3))

        stats_items = []
        for t, count in by_type.items():
            emoji = self._get_type_emoji(t)
            stats_items.append(f"{emoji} {t.capitalize()}: {count} ta")

        content.append(self._bullet_list(stats_items))

        # ━━━ PR HAVOLALAR ━━━
        if pr_details:
            content.append(self._paragraph([
                self._bold_text(f"🔗 PR'lar ({pr_count or len(pr_details)} ta | {files_changed} fayl o'zgargan):")
            ]))
            for pr in pr_details:
                pr_title = pr.get('title', 'PR')
                pr_url = pr.get('url', '')
                pr_files = pr.get('files', [])
                pr_file_count = len(pr_files)
                pr_add = sum(f.get('additions', 0) for f in pr_files)
                pr_del = sum(f.get('deletions', 0) for f in pr_files)

                nodes = [self._text_node("🔗 ")]
                if pr_url:
                    nodes.append(self._link_text(pr_title, pr_url))
                else:
                    nodes.append(self._text_node(pr_title))
                nodes += [
                    self._text_node(f" — {pr_file_count} fayl | "),
                    self._colored_text(f"+{pr_add}", "#36B37E"),
                    self._text_node(" / "),
                    self._colored_text(f"-{pr_del}", "#FF5630"),
                ]
                content.append(self._paragraph(nodes))

        content.append(self._rule())

        # ━━━ TEST CASE'LAR (EXPAND PANELS) ━━━
        content.append(self._heading("📋 Test Case'lar", 3))

        for tc in test_cases:
            tc_id = getattr(tc, 'id', 'TC-000')
            tc_title = getattr(tc, 'title', 'Nomsiz test')
            tc_priority = getattr(tc, 'priority', 'Medium')
            tc_type = getattr(tc, 'test_type', 'positive')

            type_emoji = self._get_type_emoji(tc_type)
            panel_title = f"{type_emoji} {tc_id}: {tc_title} [{tc_priority}]"

            panel_content = self._build_testcase_panel_content(tc)
            content.append(self._expand_panel(panel_title, panel_content))

        content.append(self._rule())

        # ━━━ FOOTER ━━━
        actual_footer = footer_text if footer_text else (
            "🤖 Test case'lar AI (Gemini) tomonidan avtomatik yaratilgan. "
            "QA Team tomonidan tekshirilishi va to'ldirilishi kerak."
        )
        content.append(self._paragraph([self._italic_text(actual_footer)]))

        return {"version": 1, "type": "doc", "content": content}

    def _build_testcase_panel_content(self, tc: Any) -> List[Dict]:
        """
        Bitta test case uchun panel content yaratish

        Args:
            tc: TestCase ob'ekti

        Returns:
            ADF content nodes ro'yxati
        """
        content = []

        description = getattr(tc, 'description', '')
        if description:
            content.append(self._paragraph([
                self._bold_text("📝 Tavsif: "),
                self._text_node(description)
            ]))

        preconditions = getattr(tc, 'preconditions', '')
        if preconditions:
            content.append(self._paragraph([
                self._bold_text("⚙️ Boshlang'ich shartlar: "),
                self._text_node(preconditions)
            ]))

        steps = getattr(tc, 'steps', [])
        if steps:
            content.append(self._paragraph([self._bold_text("📋 Qadamlar:")]))
            content.append(self._numbered_list(steps))

        expected_result = getattr(tc, 'expected_result', '')
        if expected_result:
            content.append(self._paragraph([
                self._bold_text("✅ Kutilgan natija: "),
                self._text_node(expected_result)
            ]))

        test_type = getattr(tc, 'test_type', 'positive')
        priority = getattr(tc, 'priority', 'Medium')
        severity = getattr(tc, 'severity', 'Normal')

        meta_line = f"Type: {test_type} | Priority: {priority} | Severity: {severity}"
        content.append(self._paragraph([self._colored_text(meta_line, "#8b949e")]))

        tags = getattr(tc, 'tags', [])
        if tags:
            tags_text = "Tags: " + ", ".join(tags)
            content.append(self._paragraph([self._colored_text(tags_text, "#58a6ff")]))

        return content

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SIMPLE TEXT FORMAT (FALLBACK)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def build_simple_comment(
            self,
            task_key: str,
            test_cases: List[Any]
    ) -> str:
        """
        Oddiy Jira Markup formatda comment (ADF ishlamasa)

        Returns:
            Jira Markup string
        """
        lines = []

        lines.append("[AI_S2]")
        lines.append("🧪 *Avtomatik Test Case'lar*")
        lines.append("----")
        lines.append(f"*Task:* {task_key}")
        lines.append(f"*Yaratilgan:* {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"*Jami:* {len(test_cases)} ta test case")
        lines.append("----")

        by_type = {}
        for tc in test_cases:
            t = getattr(tc, 'test_type', 'unknown')
            by_type[t] = by_type.get(t, 0) + 1

        lines.append("*📊 Statistika:*")
        for t, count in by_type.items():
            emoji = self._get_type_emoji(t)
            lines.append(f"• {emoji} {t.capitalize()}: {count} ta")
        lines.append("----")

        lines.append("*📋 Test Case'lar:*")
        lines.append("")

        for tc in test_cases:
            tc_id = getattr(tc, 'id', 'TC-000')
            tc_title = getattr(tc, 'title', 'Nomsiz test')
            tc_priority = getattr(tc, 'priority', 'Medium')
            tc_type = getattr(tc, 'test_type', 'positive')
            type_emoji = self._get_type_emoji(tc_type)

            lines.append(f"*{type_emoji} {tc_id}: {tc_title}* [{tc_priority}]")

            description = getattr(tc, 'description', '')
            if description:
                lines.append(f"_Tavsif:_ {description}")

            preconditions = getattr(tc, 'preconditions', '')
            if preconditions:
                lines.append(f"_Shartlar:_ {preconditions}")

            steps = getattr(tc, 'steps', [])
            if steps:
                lines.append("_Qadamlar:_")
                for i, step in enumerate(steps, 1):
                    lines.append(f"  {i}. {step}")

            expected = getattr(tc, 'expected_result', '')
            if expected:
                lines.append(f"_Kutilgan natija:_ {expected}")

            lines.append("")

        lines.append("----")
        lines.append("_🤖 Test case'lar AI tomonidan avtomatik yaratilgan._")

        return "\n".join(lines)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ERROR DOCUMENTS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def build_error_document(
            self,
            task_key: str,
            error_message: str
    ) -> Dict:
        """Xatolik uchun ADF document"""
        content = [
            self._paragraph([self._text_node("[AI_S2]")]),
            self._heading("⚠️ Test Case Yaratishda Xatolik", 2),
            self._rule(),
            self._paragraph([
                self._bold_text("Task: "),
                self._text_node(task_key),
                self._hard_break(),
                self._bold_text("Vaqt: "),
                self._text_node(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            ]),
            self._rule(),
            self._panel([
                self._paragraph([self._bold_text("Xatolik:")]),
                self._paragraph([self._text_node(error_message)])
            ], "error"),
            self._heading("Mumkin sabablar:", 4),
            self._bullet_list([
                "Task uchun TZ (Description) bo'sh",
                "PR topilmadi yoki GitHub access xatoligi",
                "AI model xatoligi"
            ]),
            self._rule(),
            self._paragraph([
                self._italic_text("Manual test case yaratish kerak bo'lishi mumkin.")
            ])
        ]

        return {"version": 1, "type": "doc", "content": content}
