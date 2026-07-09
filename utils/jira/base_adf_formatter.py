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

    def _heading_nodes(self, content: List[Dict], level: int = 3) -> Dict:
        """Heading node — rangli/bold text nodelardan tuzilgan sarlavha."""
        return {
            "type": "heading",
            "attrs": {"level": level},
            "content": content,
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

    def _agent_runs_by_key(self, agent_runs: Optional[List[Dict]]) -> Dict[str, Dict]:
        """agent_runs snapshot ro'yxatini agent_key bo'yicha dict qiladi."""
        by_key: Dict[str, Dict] = {}
        for item in (agent_runs or []):
            if isinstance(item, dict):
                by_key[str(item.get("agent_key") or "")] = item
        return by_key

    def _agent_model_suffix(self, row: Dict) -> str:
        """Agent qaysi modelda ishlaganini — fallback bo'lsa o'tishni ham — matn qiladi."""
        actual = str(row.get("actual_model") or "").strip()
        primary = str(row.get("primary_model") or "").strip()
        if bool(row.get("used_fallback")) and actual and primary and actual != primary:
            return f"model: {primary} → {actual} (fallback)"
        model = actual or primary
        return f"model: {model}" if model else ""

    def _agent_line(self, row: Dict, label: str) -> str:
        """Bitta agent uchun debug qatori — nima qilgani + model + xato (input YO'Q)."""
        state = str(row.get("state") or "").strip() or "?"
        output = str(row.get("output_summary") or "").strip()
        error = str(row.get("error_text") or "").strip()
        detail = f"{label} [{state}]"
        body = output or (error if state in {"failed", "blocked"} else "")
        if body:
            detail = f"{detail}: {body}"
        model_suffix = self._agent_model_suffix(row)
        if model_suffix:
            detail = f"{detail} — {model_suffix}"
        if error and state in {"failed", "blocked"} and error != body:
            detail = f"{detail} · xato: {error}"
        return detail

    def _agent_pipeline_lines(
        self,
        agent_runs: Optional[List[Dict]],
        labels: List[tuple],
    ) -> List[str]:
        """Multi-agent pipeline debug qatorlari — har agent nima qilgani + model.

        `labels` — [(agent_key, ko'rinadigan_nom), ...] tartibida. Servis-1 va
        Servis-2 formatterlari shu umumiy metodni o'z agent_key'lari bilan chaqiradi.
        Input qatorlari ko'rsatilmaydi; faqat agent nima qilgani, qaysi modelda
        ishlagani (fallback bo'lsa o'tish) va xato bo'lsa u yoziladi.
        """
        by_key = self._agent_runs_by_key(agent_runs)
        lines: List[str] = []
        for key, label in labels:
            row = by_key.get(key)
            if not row:
                continue
            lines.append(self._agent_line(row, label))
        return lines
