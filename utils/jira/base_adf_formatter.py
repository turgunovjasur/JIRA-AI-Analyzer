# utils/jira/base_adf_formatter.py
"""
BaseADFFormatter - ADF node builder metodlari uchun base class

JiraADFFormatter va TestcaseADFFormatter tomonidan umumiy ishlatiladi.
Bu class faqat ADF node builder primitivlarni o'z ichiga oladi.

ADF Hujjatlar: https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/
"""
from typing import Dict, List, Optional


class BaseADFFormatter:
    """
    Atlassian Document Format (ADF) node builder primitivlari.

    Barcha formatter klasslar shu klassdan meros oladi.
    To'g'ridan-to'g'ri instantiate qilinmaydi.
    """

    # Subklasslar bu atributni override qiladi (contradictory panel uchun)
    _contradictory_action_text: str = "ishlov bering!"

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
                "content": [self._paragraph([self._text_node(item)])]
            })
        return {"type": "bulletList", "content": list_items}

    def _expand_panel(self, title: str, content: List[Dict]) -> Dict:
        """
        Expand panel (dropdown/collapsible) yaratish.

        Foydalanuvchi ko'rmoqchi bo'lgan bo'limni ochib ko'radi,
        qolganlari yopiq turadi.
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
        Panel node.

        panel_type: info, note, warning, error, success
        """
        return {
            "type": "panel",
            "attrs": {"panelType": panel_type},
            "content": content
        }

    def _link_text(self, text: str, href: str) -> Dict:
        """Havola (link) text node"""
        return self._text_node(text, [{"type": "link", "attrs": {"href": href}}])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SHARED PANEL BUILDERS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_contradictory_comments_panel(self, comment_analysis: Dict) -> Optional[Dict]:
        """
        Zid commentlar uchun expand panel yaratish.

        Subklasslar _contradictory_action_text ni override qilib
        harakatga undash matnini o'zgartirishi mumkin.

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

        warning_para = [
            self._colored_text("⚠️ DIQQAT: ", "#FF5630"),
            self._text_node(
                "Quyidagi comment'larda TZ'ni o'zgartiruvchi yoki bekor qiluvchi "
                "kalit so'zlar topildi. "
            ),
            self._text_node(f"Eng so'nggi talablar asosida {self._contradictory_action_text}")
        ]
        panel_content.append(self._paragraph(warning_para))

        for idx, comment in enumerate(comment_analysis.get('important_comments', []), 1):
            comment_header = [
                self._bold_text(f"Comment #{idx}:"),
                self._text_node(f" {comment['author']} - {comment['created']}")
            ]
            panel_content.append(self._paragraph(comment_header))
            panel_content.append(self._code_block(comment['full_text']))

        return self._expand_panel(panel_title, panel_content)
