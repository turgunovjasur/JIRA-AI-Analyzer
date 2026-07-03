# utils/jira/jira_adf_formatter.py
"""
Jira ADF (Atlassian Document Format) Formatter

Jira Cloud REST API v3 uchun ADF formatda comment yaratish.
Expand panel (dropdown/collapsible) qo'llab-quvvatlanadi.

ADF Hujjatlar: https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/

Author: JASUR TURGUNOV
Version: 1.0
"""
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from utils.jira.base_adf_formatter import BaseADFFormatter

logger = logging.getLogger(__name__)


@dataclass
class AnalysisSection:
    """AI tahlil bo'limi"""
    title: str
    emoji: str
    items: List[str]
    section_type: str  # 'completed', 'failed', 'skipped', 'issues', 'figma'


class JiraADFFormatter(BaseADFFormatter):
    """Jira ADF formatda comment yaratish"""

    # Figma comment'da alohida bo'lim sifatida ko'rsatilmaydi — moslik har talab
    # ichidagi "Figma:" qatorida bo'ladi; figma xom ma'lumoti faqat AI kontekstida.
    _default_visible_sections = ['completed', 'failed', 'skipped', 'issues']

    # Har talab panelida va scoreboardda ishlatiladigan status belgisi
    _section_status_emoji = {
        'completed': '✅',
        'failed': '❌',
        'skipped': '⏭️',
        'issues': '🔍',
    }

    def __init__(self):
        """Initialize formatter"""
        self.section_patterns = {
            'completed': r'##\s*✅\s*BAJARILGAN\s*TALABLAR?\s*(.*?)(?=##\s*[⚠⏭❌🐛🎨📊]|$)',
            'partial': r'##\s*⚠️?\s*QISMAN\s*BAJARILGAN\s*(.*?)(?=##\s*[✅⏭❌🐛🎨📊]|$)',
            'failed': r'##\s*❌\s*BAJARILMAGAN\s*TALABLAR?\s*(.*?)(?=##\s*[✅⚠⏭🐛🎨📊]|$)',
            'skipped': r'##\s*⏭️?\s*SKIP\s*QILINGAN[^\n]*\n?(.*?)(?=##\s*[✅⚠❌🐛🎨📊]|$)',
            'issues': r'##\s*🐛\s*POTENSIAL\s*MUAMMOLAR?\s*(.*?)(?=##\s*[✅⚠⏭❌🎨📊]|$)',
            'figma': r'##\s*🎨\s*FIGMA\s*DIZAYN\s*MOSLIGI?\s*(.*?)(?=##\s*[✅⚠⏭❌🐛📊]|$)',
            'score': r'##\s*📊\s*MOSLIK\s*BALI?\s*(.*?)(?=##|$)'
        }

        self.section_titles = {
            'completed': ('✅ Bajarilgan talablar', 'completed'),
            'failed': ('❌ Bajarilmagan talablar', 'failed'),
            'skipped': ('⏭️ Skip qilingan talablar', 'skipped'),
            'issues': ('🔍 Extra Scan', 'issues'),
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
                'failed': AnalysisSection(...),
                'skipped': AnalysisSection(...),
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

    def _normalize_visible_sections(self, visible_sections: Optional[List[str]]) -> List[str]:
        allowed = set(self._default_visible_sections)
        values = [section for section in (visible_sections or self._default_visible_sections) if section in allowed]
        return values or list(self._default_visible_sections)

    def _coerce_section_items(self, section: Any) -> List[str]:
        items = getattr(section, "items", None)
        if isinstance(section, dict):
            items = section.get("items")
        if items:
            return [str(item).strip() for item in items if str(item).strip()]

        lines = getattr(section, "lines", None)
        if isinstance(section, dict):
            lines = section.get("lines")
        if lines:
            return [str(line).strip() for line in lines if str(line).strip()]
        return []

    def _sections_from_result(self, result: Any) -> Dict[str, AnalysisSection]:
        sections: Dict[str, AnalysisSection] = {}
        structured_sections = getattr(result, "analysis_sections", None) or []

        for raw_section in structured_sections:
            key = getattr(raw_section, "key", None)
            if isinstance(raw_section, dict):
                key = raw_section.get("key")
            if key not in self.section_titles:
                continue

            items = self._coerce_section_items(raw_section)
            if not items:
                continue

            title = getattr(raw_section, "title", None)
            if isinstance(raw_section, dict):
                title = raw_section.get("title")
            fallback_title, emoji = self.section_titles[key]
            sections[key] = AnalysisSection(
                title=title or fallback_title,
                emoji=emoji,
                items=items,
                section_type=key,
            )

        if sections:
            return sections

        ai_analysis = getattr(result, "ai_analysis", None)
        return self.parse_ai_analysis(ai_analysis or "")

    def _summary_lines_from_result(self, result: Any) -> List[str]:
        overview = getattr(result, "analysis_overview", None)
        if isinstance(overview, dict):
            lines = overview.get("summary_lines")
        else:
            lines = getattr(overview, "summary_lines", None)
        if lines:
            # Moslik bali commentning yuqorisida alohida ko'rsatiladi —
            # Xulosa ichida takrorlamaymiz.
            return [
                str(line).strip()
                for line in lines
                if str(line).strip()
                and not str(line).strip().lower().startswith("compliance score")
            ]
        return []

    def _split_requirement_item(self, item: str, index: int) -> tuple[str, str]:
        """Talab item'ini panel sarlavhasi (REQ-id + matn) va body (evidence/file)ga ajratish.

        Sarlavha ochmasdan tushunarli bo'lishi uchun talab matnini ham o'z ichiga oladi;
        body'da to'liq matn + evidence/file bo'ladi.
        """
        text = str(item or "").strip()
        if not text:
            return f"REQ-{index}", ""

        segments = [p.strip() for p in re.split(r'\s+\|\s+', text) if p.strip()]
        head = segments[0] if segments else text
        tail = segments[1:]

        req_match = re.search(r'(\[REQ-[^\]]+\]|REQ-[A-Za-z0-9_.-]+)', head, re.IGNORECASE)
        if req_match:
            req_id = req_match.group(1).strip()
            if not req_id.startswith("["):
                req_id = f"[{req_id}]"
            desc = (head[:req_match.start()] + head[req_match.end():]).strip(" :-–—|")
        else:
            req_id = ""
            desc = head

        title_core = f"{req_id} {desc}".strip() if req_id else desc
        title = title_core if len(title_core) <= 96 else title_core[:95].rstrip() + "…"
        if not title:
            title = f"REQ-{index}"

        body_parts = ([desc] if desc else []) + tail
        body = " | ".join(body_parts)
        return title, body

    def _requirement_panel_content(self, body: str) -> List[Dict]:
        text = str(body or "").strip()
        if not text:
            return [self._paragraph([self._text_node("Tafsilot yo'q")])]

        parts = [part.strip() for part in re.split(r'\s+\|\s+', text) if part.strip()]
        if len(parts) <= 1:
            return [self._paragraph([self._text_node(text)])]

        content = []
        for part in parts:
            label_match = re.match(r'^([A-Za-zА-Яа-яЁёЎўҚқҒғҲҳІіЇїЄє0-9 _/-]{2,40}):\s*(.+)$', part, re.DOTALL)
            if label_match:
                label = label_match.group(1).strip()
                value = label_match.group(2).strip()
                content.append(self._paragraph([
                    self._bold_text(f"{label}: "),
                    self._text_node(value),
                ]))
            else:
                content.append(self._paragraph([self._text_node(part)]))
        return content

    def _requirement_expand_panels(self, items: List[str], status_emoji: str = "") -> List[Dict]:
        panels = []
        for idx, item in enumerate(items, 1):
            title, body = self._split_requirement_item(item, idx)
            if status_emoji:
                title = f"{status_emoji} {title}"
            panels.append(self._expand_panel(title, self._requirement_panel_content(body)))
        return panels

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # COMMENT DOCUMENT BUILDER
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def build_comment_document(
            self,
            result: Any,
            new_status: str = "Ready to Test",
            footer_text: Optional[str] = None,
            is_recheck: bool = False,
            recheck_text: Optional[str] = None,
            visible_sections: Optional[List[str]] = None,
            dev_objections: Optional[List[Dict]] = None,
            extra_scan_enabled: bool = True
    ) -> Dict:
        """
        To'liq ADF comment document yaratish

        Args:
            result: TZPRAnalysisResult object
            new_status: Yangi status nomi
            footer_text: Settings-dan olingan footer matn (None bo'lsa default)
            is_recheck: Bu re-check (qaytarildigan so'ng) tekshirish ekanmi
            recheck_text: Re-check paneli uchun matn (settings-dan)

        Returns:
            ADF document (dict)
        """
        from datetime import datetime

        content = []

        # ━━━ AI MARKER (comment ajratish uchun) ━━━
        content.append(self._paragraph([self._text_node("[AI_S1]")]))

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

        # AI tahlil bo'limlari — score/scoreboard uchun oldindan hisoblanadi
        sections = self._sections_from_result(result)

        # ━━━ MOSLIK BALI + XULOSA SO'ZI ━━━
        if result.compliance_score is not None:
            score = result.compliance_score
            score_color = self._get_score_color(score)

            content.append(self._paragraph([
                self._bold_text("📊 Moslik Bali: "),
                self._colored_text(f"{score}%", score_color),
                self._text_node("  —  "),
                self._colored_text(self._score_verdict(score), score_color),
            ]))

        # ━━━ SCOREBOARD (talab verdiktlari bir qatorda) ━━━
        scoreboard = self._requirement_scoreboard(sections)
        if scoreboard:
            content.append(self._paragraph(scoreboard))

        summary_lines = self._summary_lines_from_result(result)
        if summary_lines:
            content.append(self._expand_panel("🧭 Xulosa", [self._bullet_list(summary_lines)]))
        content.append(self._rule())

        # ━━━ RE-CHECK PANEL ━━━
        if is_recheck and recheck_text:
            content.append(self._panel([
                self._paragraph([self._text_node(recheck_text)])
            ], "note"))
            content.append(self._rule())

        # ━━━ DEVELOPER IZOHLARI DROPDOWN (faqat recheck + izohlar bo'lsa) ━━━
        if is_recheck and dev_objections:
            obj_items = []
            for c in dev_objections:
                author = c.get('author', 'Unknown')
                created = c.get('created', '')
                body = c.get('body', '').strip()
                obj_items.append(f"👤 {author} ({created}): {body}")
            panel_title = f"💬 Developer izohlari — AI ko'rdi ({len(obj_items)} ta)"
            content.append(self._expand_panel(panel_title, [self._bullet_list(obj_items)]))
            content.append(self._rule())

        # ━━━ RUN SIGNALLARI ━━━
        warnings = [str(item).strip() for item in (getattr(result, "warnings", None) or []) if str(item).strip()]
        if warnings:
            content.append(self._expand_panel("⚠ Run signallari", [self._bullet_list(warnings)]))
            content.append(self._rule())

        # ━━━ STATISTIKA + PR HAVOLALAR (dropdown, default yopiq) ━━━
        stats_items = [
            f"Pull Requests: {result.pr_count} ta",
            f"O'zgargan fayllar: {result.files_changed} ta",
            f"Qo'shilgan: +{result.total_additions}",
            f"O'chirilgan: -{result.total_deletions}"
        ]
        stats_panel_content = [self._bullet_list(stats_items)]

        pr_details = getattr(result, 'pr_details', [])
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
            stats_panel_content.append(self._paragraph(nodes))

        content.append(self._expand_panel("📈 Statistika", stats_panel_content))
        content.append(self._rule())

        # ━━━ AI TAHLIL BO'LIMLARI (EXPAND PANELS) ━━━
        _visible = self._normalize_visible_sections(visible_sections)

        for section_key in self._default_visible_sections:
            if section_key not in _visible:
                continue
            # Extra Scan o'chirilgan bo'lsa (webhook 'Agent2 Extra scan' setting),
            # bu bo'lim commentda umuman ko'rinmaydi.
            if section_key == 'issues' and not extra_scan_enabled:
                continue
            if section_key in sections:
                section = sections[section_key]
                if section.items:
                    display_title = self.section_titles[section_key][0] if section_key == 'issues' else section.title
                    section_title = f"{display_title} ({len(section.items)} ta)"
                    # Bo'lim sarlavhasi — oddiy heading; har bir talab esa ALOHIDA
                    # top-level expand. ADF qoidasi: expand faqat top-level yoki panel
                    # ichida bo'ladi — expand'ni expand ichiga joylab bo'lmaydi
                    # (aks holda JIRA 400 INVALID_INPUT beradi).
                    content.append(self._heading(section_title, 3))
                    content.extend(self._requirement_expand_panels(
                        section.items,
                        self._section_status_emoji.get(section_key, ""),
                    ))

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

            for section_key in self._default_visible_sections:
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

    @staticmethod
    def _score_verdict(score: int) -> str:
        """Ball uchun qisqa xulosa so'zi (rangdan tashqari matn signali)."""
        if score >= 80:
            return "Yaxshi"
        if score >= 60:
            return "O'rtacha"
        return "Past — qayta ishlash kerak"

    def _requirement_scoreboard(self, sections: Dict[str, "AnalysisSection"]) -> List[Dict]:
        """Talab verdiktlarini bitta rangli qatorga yig'ish (bajarildi/bajarilmadi/skip)."""
        order = [
            ('completed', "#36B37E", "bajarildi"),
            ('failed', "#FF5630", "bajarilmadi"),
            ('skipped', "#8b949e", "skip"),
        ]
        nodes: List[Dict] = []
        for key, color, label in order:
            section = sections.get(key)
            count = len(section.items) if section and section.items else 0
            if count == 0:
                continue
            emoji = self._section_status_emoji.get(key, "")
            if nodes:
                nodes.append(self._text_node("   ·   "))
            nodes.append(self._colored_text(f"{emoji} {count} {label}", color))
        return nodes

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SIMPLE TEXT FORMAT (FALLBACK)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def build_simple_comment(
            self,
            result: Any,
            new_status: str = "Ready to Test",
            visible_sections: Optional[List[str]] = None,
            extra_scan_enabled: bool = True,
    ) -> str:
        """
        Oddiy Jira Markup formatda comment (ADF ishlamasa)

        Returns:
            Jira Markup string
        """
        from datetime import datetime

        status_emoji = "🎯" if "Ready" in new_status else "🧪"

        comment = f"""[AI_S1]
{status_emoji} *TZ-PR Checker*

----

*Task:* {result.task_key}
*Vaqt:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
*Status:* {new_status}

----
"""

        sections = self._sections_from_result(result)

        if result.compliance_score is not None:
            comment += f"\n*📊 Moslik Bali:* *{result.compliance_score}%* — {self._score_verdict(result.compliance_score)}\n"
            scoreboard_bits = []
            for key, label in [('completed', 'bajarildi'), ('failed', 'bajarilmadi'), ('skipped', 'skip')]:
                section = sections.get(key)
                count = len(section.items) if section and section.items else 0
                if count:
                    scoreboard_bits.append(f"{self._section_status_emoji.get(key, '')} {count} {label}")
            if scoreboard_bits:
                comment += "  ·  ".join(scoreboard_bits) + "\n"

        summary_lines = self._summary_lines_from_result(result)
        if summary_lines:
            comment += "\n*🧭 Xulosa:*\n"
            for line in summary_lines:
                comment += f"• {line}\n"

        warnings = [str(item).strip() for item in (getattr(result, "warnings", None) or []) if str(item).strip()]
        if warnings:
            comment += "\n*⚠ Run signallari:*\n"
            for warning in warnings:
                comment += f"• {warning}\n"

        comment += f"""
----

*📈 Statistika:*
• Pull Requests: {result.pr_count} ta
• O'zgargan fayllar: {result.files_changed} ta
• Qo'shilgan qatorlar: {{color:green}}+{result.total_additions}{{color}}
• O'chirilgan qatorlar: {{color:red}}-{result.total_deletions}{{color}}

----
"""

        for section_key in self._normalize_visible_sections(visible_sections):
            if section_key == 'issues' and not extra_scan_enabled:
                continue
            section = sections.get(section_key)
            if not section or not section.items:
                continue
            title = self.section_titles[section_key][0] if section_key == 'issues' else section.title
            comment += f"\n*{title}:*\n"
            for item in section.items:
                comment += f"• {item}\n"

        comment += "\n----\n\n_Bu komment AI tomonidan avtomatik yaratilgan. Savollar bo'lsa QA Team ga murojaat qiling._\n"
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
