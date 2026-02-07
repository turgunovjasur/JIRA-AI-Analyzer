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

logger = logging.getLogger(__name__)


@dataclass
class AnalysisSection:
    """AI tahlil bo'limi"""
    title: str
    emoji: str
    items: List[str]
    section_type: str  # 'completed', 'partial', 'failed', 'issues'


class JiraADFFormatter:
    """Jira ADF formatda comment yaratish"""

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
    # ADF NODE BUILDERS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _text_node(self, text: str, marks: Optional[List[Dict]] = None) -> Dict:
        """Text node yaratish"""
        node = {"type": "text", "text": text}
        if marks:
            node["marks"] = marks
        return node

    def _bold_text(self, text: str) -> Dict:
        """Bold text node"""
        return self._text_node(text, [{"type": "strong"}])

    def _italic_text(self, text: str) -> Dict:
        """Italic text node"""
        return self._text_node(text, [{"type": "em"}])

    def _colored_text(self, text: str, color: str) -> Dict:
        """Rangli text node"""
        return self._text_node(text, [{"type": "textColor", "attrs": {"color": color}}])

    def _paragraph(self, content: List[Dict]) -> Dict:
        """Paragraph node"""
        return {"type": "paragraph", "content": content}

    def _hard_break(self) -> Dict:
        """Line break"""
        return {"type": "hardBreak"}

    def _rule(self) -> Dict:
        """Horizontal rule (chiziq)"""
        return {"type": "rule"}

    def _bullet_list(self, items: List[str]) -> Dict:
        """Bullet list yaratish"""
        list_items = []
        for item in items:
            list_items.append({
                "type": "listItem",
                "content": [
                    self._paragraph([self._text_node(item)])
                ]
            })
        return {"type": "bulletList", "content": list_items}

    def _expand_panel(self, title: str, content: List[Dict]) -> Dict:
        """
        Expand panel (dropdown/collapsible) yaratish

        Bu ADF ning eng muhim qismi - foydalanuvchi ko'rmoqchi bo'lgan
        bo'limni ochib ko'radi, qolganlari yopiq turadi.
        """
        return {
            "type": "expand",
            "attrs": {"title": title},
            "content": content
        }

    def _heading(self, text: str, level: int = 3) -> Dict:
        """Heading node"""
        return {
            "type": "heading",
            "attrs": {"level": level},
            "content": [self._text_node(text)]
        }

    def _code_block(self, text: str, language: str = "") -> Dict:
        """Code block"""
        return {
            "type": "codeBlock",
            "attrs": {"language": language},
            "content": [self._text_node(text)]
        }

    def _panel(self, content: List[Dict], panel_type: str = "info") -> Dict:
        """
        Panel node

        panel_type: info, note, warning, error, success
        """
        return {
            "type": "panel",
            "attrs": {"panelType": panel_type},
            "content": content
        }

    def _emoji(self, short_name: str) -> Dict:
        """Emoji node"""
        return {
            "type": "emoji",
            "attrs": {"shortName": f":{short_name}:"}
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

        # Bo'sh bo'lsa
        if not content or content.strip() in ['yo\'q', 'yoq', '-', 'none', 'n/a']:
            return items

        # Har bir qatorni tekshirish
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Marker'larni olib tashlash: -, *, •, 1., 2., etc.
            cleaned = re.sub(r'^[-*•]\s*', '', line)
            cleaned = re.sub(r'^\d+\.\s*', '', cleaned)
            cleaned = cleaned.strip()

            if cleaned and len(cleaned) > 2:
                items.append(cleaned)

        return items

    def extract_compliance_score(self, ai_analysis: str) -> Optional[int]:
        """Moslik balini ajratib olish"""
        # Pattern 1: COMPLIANCE_SCORE: XX%
        match = re.search(r'COMPLIANCE_SCORE:\s*(\d+)%', ai_analysis, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # Pattern 2: **XX%** yoki XX%
        match = re.search(r'\*?\*?(\d+)%\*?\*?', ai_analysis)
        if match:
            return int(match.group(1))

        return None

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CONTRADICTORY COMMENTS PANEL BUILDER
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_contradictory_comments_panel(self, comment_analysis: Dict) -> Optional[Dict]:
        """
        Zid commentlar uchun expand panel yaratish

        Args:
            comment_analysis: TZHelper.analyze_comments() natijasi

        Returns:
            ADF expand panel node yoki None (agar zid comment yo'q bo'lsa)
        """
        if not comment_analysis or not comment_analysis.get('has_changes'):
            return None

        change_count = comment_analysis['change_count']
        panel_title = f"🚨 ZID COMMENTLAR ({change_count} ta)"

        panel_content = []

        # Warning text
        warning_para = [
            self._colored_text("⚠️ DIQQAT: ", "#FF5630"),
            self._text_node("Quyidagi comment'larda TZ'ni o'zgartiruvchi yoki bekor qiluvchi kalit so'zlar topildi. "),
            self._text_node("Eng so'nggi talablar asosida ishlov bering!")
        ]
        panel_content.append(self._paragraph(warning_para))

        # Comment'larni ko'rsatish
        for idx, comment in enumerate(comment_analysis.get('important_comments', []), 1):
            # Comment header
            comment_header = [
                self._bold_text(f"Comment #{idx}:"),
                self._text_node(f" {comment['author']} - {comment['created']}")
            ]
            panel_content.append(self._paragraph(comment_header))

            # Comment text
            comment_text = comment['full_text']
            # Code block for better readability
            panel_content.append(self._code_block(comment_text))

        return self._expand_panel(panel_title, panel_content)

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
        content.append(self._heading("🎯 Avtomatik TZ-PR Moslik Tekshiruvi", 2))
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

        # ━━━ RE-CHECK PANEL (task qaytarildigan so'ng yana tekshirilayotgan) ━━━
        if is_recheck and recheck_text:
            content.append(self._panel([
                self._paragraph([self._text_node(recheck_text)])
            ], "note"))
            content.append(self._rule())

        # ━━━ ZID COMMENTLAR PANEL (agar mavjud bo'lsa) ━━━
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
        content.append(self._rule())

        # ━━━ AI TAHLIL BO'LIMLARI (EXPAND PANELS) ━━━
        sections = self.parse_ai_analysis(result.ai_analysis)

        # Faqat yoqilgan bo'limlarni ko'rsatish (token tejash sozlamasi)
        _visible = visible_sections if visible_sections else [
            'completed', 'partial', 'failed', 'issues', 'figma'
        ]

        for section_key in ['completed', 'partial', 'failed', 'issues', 'figma']:
            if section_key not in _visible:
                continue
            if section_key in sections:
                section = sections[section_key]
                if section.items:
                    # Expand panel title with count
                    panel_title = f"{section.title} ({len(section.items)} ta)"

                    # Panel ichidagi content
                    panel_content = [self._bullet_list(section.items)]

                    content.append(self._expand_panel(panel_title, panel_content))

        content.append(self._rule())

        # ━━━ FOOTER ━━━
        # footer_text parametr berilgan bo'lsa settings-dan, yo'q bo'lsa default
        actual_footer = footer_text if footer_text else (
            "🤖 Bu komment AI tomonidan avtomatik yaratilgan. "
            "Savollar bo'lsa QA Team ga murojaat qiling."
        )
        content.append(self._paragraph([
            self._italic_text(actual_footer)
        ]))

        # ━━━ TO'LIQ DOCUMENT ━━━
        return {
            "version": 1,
            "type": "doc",
            "content": content
        }

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

        Moslik bali past bo'lsa task qaytarilgani xaqida
        alohida warning panel comment sifatida JIRA ga yoziladi.

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

        return {
            "version": 1,
            "type": "doc",
            "content": content
        }

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

        # Emoji va status
        status_emoji = "🎯" if "Ready" in new_status else "🧪"

        comment = f"""
{status_emoji} *Avtomatik TZ-PR Moslik Tekshiruvi*

----

*Task:* {result.task_key}
*Vaqt:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
*Status:* {new_status}

----
"""

        # Moslik bali
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

        return {
            "version": 1,
            "type": "doc",
            "content": content
        }

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

        return {
            "version": 1,
            "type": "doc",
            "content": content
        }
