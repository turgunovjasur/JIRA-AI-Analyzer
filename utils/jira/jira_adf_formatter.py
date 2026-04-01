# utils/jira/jira_adf_formatter.py
"""
Jira ADF (Atlassian Document Format) Formatter

Jira Cloud REST API v3 uchun ADF formatda comment yaratish.
Expand panel (dropdown/collapsible) qo'llab-quvvatlanadi.

ADF Hujjatlar: https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/

Author: JASUR TURGUNOV
Version: 1.0
"""
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from utils.jira.base_adf_formatter import BaseADFFormatter

logger = logging.getLogger(__name__)


@dataclass
class AnalysisSection:
    """AI tahlil bo'limi"""
    title: str
    emoji: str
    items: List[str]
    section_type: str  # 'completed', 'partial', 'failed', 'issues'


class JiraADFFormatter(BaseADFFormatter):
    """Jira ADF formatda comment yaratish"""

    _contradictory_action_text = "ishlov bering!"

    def __init__(self):
        """Initialize formatter"""
        self.section_patterns = {
            'completed': r'##\s*✅\s*BAJARILGAN\s*TALABLAR?\s*(.*?)(?=##\s*[⚠❌🐛🎨📊]|$)',
            'partial': r'##\s*⚠️?\s*QISMAN\s*BAJARILGAN\s*(.*?)(?=##\s*[✅❌🐛🎨📊]|$)',
            'failed': r'##\s*❌\s*BAJARILMAGAN\s*TALABLAR?\s*(.*?)(?=##\s*[✅⚠🐛🎨📊]|$)',
            'issues': r'##\s*🐛\s*POTENSIAL\s*MUAMMOLAR?\s*(.*?)(?=##\s*[✅⚠❌🎨📊]|$)',
            'figma': r'##\s*🎨\s*FIGMA\s*DIZAYN\s*MOSLIGI?\s*(.*?)(?=##\s*[✅⚠❌🐛📊]|$)',
            'score': r'##\s*📊\s*MOSLIK\s*BALI?\s*(.*?)(?=##|$)'
        }

        self.section_titles = {
            'completed': ('✅ Bajarilgan talablar', 'completed'),
            'partial': ('⚠️ Qisman bajarilgan', 'partial'),
            'failed': ('❌ Bajarilmagan talablar', 'failed'),
            'issues': ('🐛 Potensial muammolar', 'issues'),
            'figma': ('🎨 Figma dizayn mosligi', 'figma')
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # AI ANALYSIS PARSER
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def parse_ai_analysis(self, ai_analysis: str) -> Dict[str, AnalysisSection]:
        """
        AI tahlil natijasini bo'limlarga ajratish

        Returns:
            {
                'completed': AnalysisSection(...),
                'partial': AnalysisSection(...),
                'failed': AnalysisSection(...),
                'issues': AnalysisSection(...)
            }
        """
        sections = {}

        for section_key, pattern in self.section_patterns.items():
            if section_key == 'score':
                continue  # Score alohida ishlanadi

            match = re.search(pattern, ai_analysis, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                items = self._extract_items(content)

                if section_key in self.section_titles:
                    title, emoji = self.section_titles[section_key]
                    sections[section_key] = AnalysisSection(
                        title=title,
                        emoji=emoji,
                        items=items,
                        section_type=section_key
                    )

        return sections

    def _extract_items(self, content: str) -> List[str]:
        """Matndan item'larni ajratib olish"""
        items = []

        if not content or content.strip() in ['yo\'q', 'yoq', '-', 'none', 'n/a']:
            return items

        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            cleaned = re.sub(r'^[-*•]\s*', '', line)
            cleaned = re.sub(r'^\d+\.\s*', '', cleaned)
            cleaned = cleaned.strip()

            if cleaned and len(cleaned) > 2:
                items.append(cleaned)

        return items

    def extract_compliance_score(self, ai_analysis: str) -> Optional[int]:
        """Moslik balini ajratib olish"""
        match = re.search(r'COMPLIANCE_SCORE:\s*(\d+)%', ai_analysis, re.IGNORECASE)
        if match:
            return int(match.group(1))

        match = re.search(r'\*?\*?(\d+)%\*?\*?', ai_analysis)
        if match:
            return int(match.group(1))

        return None

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # COMMENT DOCUMENT BUILDER
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def build_comment_document(
            self,
            result: Any,
            new_status: str = "Ready to Test",
            comment_analysis: Optional[Dict] = None,
            footer_text: Optional[str] = None,
            is_recheck: bool = False,
            recheck_text: Optional[str] = None,
            visible_sections: Optional[List[str]] = None
    ) -> Dict:
        """
        To'liq ADF comment document yaratish

        Args:
            result: TZPRAnalysisResult object
            new_status: Yangi status nomi
            comment_analysis: TZHelper.analyze_comments() natijasi (optional)
            footer_text: Settings-dan olingan footer matn (None bo'lsa default)
            is_recheck: Bu re-check (qaytarildigan so'ng) tekshirish ekanmi
            recheck_text: Re-check paneli uchun matn (settings-dan)

        Returns:
            ADF document (dict)
        """
        from datetime import datetime

        content = []

        # ━━━ HEADER ━━━
        content.append(self._heading("🎯 TZ-PR Checker", 2))
        content.append(self._rule())

        # ━━━ META INFO ━━━
        meta_text = [
            self._bold_text("Task: "),
            self._text_node(f"{result.task_key}"),
            self._hard_break(),
            self._bold_text("Vaqt: "),
            self._text_node(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            self._hard_break(),
            self._bold_text("Status: "),
            self._text_node(new_status)
        ]
        content.append(self._paragraph(meta_text))

        # ━━━ MOSLIK BALI ━━━
        if result.compliance_score is not None:
            score = result.compliance_score
            score_color = self._get_score_color(score)

            score_content = [
                self._bold_text("📊 Moslik Bali: "),
                self._colored_text(f"{score}%", score_color)
            ]
            content.append(self._paragraph(score_content))
        content.append(self._rule())

        # ━━━ RE-CHECK PANEL ━━━
        if is_recheck and recheck_text:
            content.append(self._panel([
                self._paragraph([self._text_node(recheck_text)])
            ], "note"))
            content.append(self._rule())

        # ━━━ ZID COMMENTLAR PANEL ━━━
        if comment_analysis:
            contradictory_panel = self._build_contradictory_comments_panel(comment_analysis)
            if contradictory_panel:
                content.append(contradictory_panel)
                content.append(self._rule())

        # ━━━ STATISTIKA ━━━
        stats_items = [
            f"Pull Requests: {result.pr_count} ta",
            f"O'zgargan fayllar: {result.files_changed} ta",
            f"Qo'shilgan: +{result.total_additions}",
            f"O'chirilgan: -{result.total_deletions}"
        ]
        content.append(self._heading("📈 Statistika", 3))
        content.append(self._bullet_list(stats_items))

        # ━━━ PR HAVOLALAR ━━━
        pr_details = getattr(result, 'pr_details', [])
        if pr_details:
            pr_links_content = []
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
                pr_links_content.append(self._paragraph(nodes))
            content.extend(pr_links_content)

        content.append(self._rule())

        # ━━━ AI TAHLIL BO'LIMLARI (EXPAND PANELS) ━━━
        sections = self.parse_ai_analysis(result.ai_analysis)

        _visible = visible_sections if visible_sections else [
            'completed', 'partial', 'failed', 'issues', 'figma'
        ]

        for section_key in ['completed', 'partial', 'failed', 'issues', 'figma']:
            if section_key not in _visible:
                continue
            if section_key in sections:
                section = sections[section_key]
                if section.items:
                    panel_title = f"{section.title} ({len(section.items)} ta)"
                    panel_content = [self._bullet_list(section.items)]
                    content.append(self._expand_panel(panel_title, panel_content))

        content.append(self._rule())

        # ━━━ FOOTER ━━━
        actual_footer = footer_text if footer_text else (
            "🤖 Bu komment AI tomonidan avtomatik yaratilgan. "
            "Savollar bo'lsa QA Team ga murojaat qiling."
        )
        content.append(self._paragraph([self._italic_text(actual_footer)]))

        return {"version": 1, "type": "doc", "content": content}

    def build_return_notification_document(
            self,
            task_key: str,
            compliance_score: int,
            threshold: int,
            return_status: str,
            notification_text: Optional[str] = None,
            ai_analysis: Optional[str] = None
    ) -> Dict:
        """
        Auto-return notification uchun ADF document yaratish.

        Args:
            task_key: JIRA task key (DEV-1234)
            compliance_score: Hisoblangan moslik foizi (0-100)
            threshold: Qaytarish chegarasi (e.g. 60)
            return_status: Qaytarish statusi nomi
            notification_text: Settings-dan olingan panel matn (None bo'lsa default)

        Returns:
            ADF document (dict)
        """
        from datetime import datetime

        content = []

        # ━━━ HEADER ━━━
        content.append(self._heading("🔄 Task Qaytarildi", 2))
        content.append(self._rule())

        # ━━━ META INFO ━━━
        meta_text = [
            self._bold_text("Task: "),
            self._text_node(task_key),
            self._hard_break(),
            self._bold_text("Vaqt: "),
            self._text_node(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            self._hard_break(),
            self._bold_text("Qaytarish statusi: "),
            self._text_node(return_status)
        ]
        content.append(self._paragraph(meta_text))
        content.append(self._rule())

        # ━━━ WARNING PANEL ━━━
        score_color = self._get_score_color(compliance_score)
        panel_content = [
            self._paragraph([
                self._bold_text("Moslik bali: "),
                self._colored_text(f"{compliance_score}%", score_color),
                self._text_node(f" (chegarasi: {threshold}%)")
            ]),
            self._paragraph([
                self._text_node(
                    notification_text if notification_text else (
                        "TZ-PR tekshiruvi past natija ko'rsatdi. "
                        "Iltimos, TZ talablarini to'liq bajarilganligini tekshiring "
                        "va qaytadan PR bering."
                    )
                )
            ])
        ]
        content.append(self._panel(panel_content, "warning"))
        content.append(self._rule())

        # ━━━ AI TAHLIL BO'LIMLARI (EXPAND PANELS) ━━━
        if ai_analysis:
            sections = self.parse_ai_analysis(ai_analysis)

            for section_key in ['completed', 'partial', 'failed']:
                if section_key in sections:
                    section = sections[section_key]
                    if section.items:
                        panel_title = f"{section.title} ({len(section.items)} ta)"
                        panel_content_section = [self._bullet_list(section.items)]
                        content.append(self._expand_panel(panel_title, panel_content_section))

            content.append(self._rule())

        # ━━━ FOOTER ━━━
        content.append(self._paragraph([
            self._italic_text("🤖 Bu notification AI tomonidan avtomatik yaratilgan.")
        ]))

        return {"version": 1, "type": "doc", "content": content}

    def _get_score_color(self, score: int) -> str:
        """Moslik bali uchun rang"""
        if score >= 80:
            return "#36B37E"  # Green
        elif score >= 60:
            return "#FFAB00"  # Yellow/Orange
        else:
            return "#FF5630"  # Red

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SIMPLE TEXT FORMAT (FALLBACK)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def build_simple_comment(
            self,
            result: Any,
            new_status: str = "Ready to Test"
    ) -> str:
        """
        Oddiy Jira Markup formatda comment (ADF ishlamasa)

        Returns:
            Jira Markup string
        """
        from datetime import datetime

        status_emoji = "🎯" if "Ready" in new_status else "🧪"

        comment = f"""
{status_emoji} *TZ-PR Checker*

----

*Task:* {result.task_key}
*Vaqt:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
*Status:* {new_status}

----
"""

        if result.compliance_score is not None:
            comment += f"\n*📊 Moslik Bali:* *{result.compliance_score}%*\n"

        comment += f"""
----

*📈 Statistika:*
• Pull Requests: {result.pr_count} ta
• O'zgargan fayllar: {result.files_changed} ta
• Qo'shilgan qatorlar: {{color:green}}+{result.total_additions}{{color}}
• O'chirilgan qatorlar: {{color:red}}-{result.total_deletions}{{color}}

----

*AI Tahlili (Gemini 2.5 Flash):*

{result.ai_analysis}

----

_Bu komment AI tomonidan avtomatik yaratilgan. Savollar bo'lsa QA Team ga murojaat qiling._
"""
        return comment

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ERROR COMMENTS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def build_error_document(
            self,
            task_key: str,
            error_message: str,
            new_status: str
    ) -> Dict:
        """Xatolik uchun ADF document"""
        from datetime import datetime

        content = [
            self._heading("⚠️ Avtomatik TZ-PR Tekshiruvi - Xatolik", 2),
            self._rule(),
            self._paragraph([
                self._bold_text("Task: "),
                self._text_node(task_key),
                self._hard_break(),
                self._bold_text("Vaqt: "),
                self._text_node(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                self._hard_break(),
                self._bold_text("Status: "),
                self._text_node(new_status)
            ]),
            self._rule(),
            self._panel([
                self._paragraph([self._bold_text("Xatolik:")]),
                self._paragraph([self._text_node(error_message)])
            ], "error"),
            self._heading("Mumkin sabablar:", 4),
            self._bullet_list([
                "Task uchun PR topilmadi",
                "GitHub access xatoligi",
                "TZ (Description) bo'sh"
            ]),
            self._rule(),
            self._paragraph([
                self._italic_text("Manual tekshirish kerak. QA Team'ga xabar bering.")
            ])
        ]

        return {"version": 1, "type": "doc", "content": content}

    def build_critical_error_document(
            self,
            task_key: str,
            error: str,
            new_status: str
    ) -> Dict:
        """Kritik xatolik uchun ADF document"""
        from datetime import datetime

        content = [
            self._heading("🚨 Avtomatik TZ-PR Tekshiruvi - Kritik Xatolik", 2),
            self._rule(),
            self._paragraph([
                self._bold_text("Task: "),
                self._text_node(task_key),
                self._hard_break(),
                self._bold_text("Vaqt: "),
                self._text_node(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                self._hard_break(),
                self._bold_text("Status: "),
                self._text_node(new_status)
            ]),
            self._rule(),
            self._panel([
                self._paragraph([self._bold_text("Kritik Xatolik:")]),
                self._code_block(error)
            ], "error"),
            self._rule(),
            self._paragraph([
                self._italic_text("System administrator'ga xabar berildi.")
            ])
        ]

        return {"version": 1, "type": "doc", "content": content}
