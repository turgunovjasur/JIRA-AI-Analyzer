# utils/jira/jira_figma_helper.py
"""
JIRA Figma Helper - JIRA task'lardan Figma link'larni olish
"""
import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class FigmaLink:
    """Figma link ma'lumotlari"""
    url: str
    file_key: str
    name: str
    source: str
    author: str = None
    node_id: str = None  # node-id parametri (masalan: "1337:16")


class JiraFigmaHelper:
    """JIRA'dan Figma link'larni topish"""

    FIGMA_PATTERN = r'https://(?:www\.)?figma\.com/(?:file|proto|design)/([A-Za-z0-9]+)[^"\s<]*'

    @staticmethod
    def extract_figma_urls(task_details: Dict) -> List[FigmaLink]:
        """Extract Figma URLs from task description only."""
        figma_links = []
        seen_file_keys = set()

        description = task_details.get('description', '')
        if description:
            matches = re.finditer(JiraFigmaHelper.FIGMA_PATTERN, description)

            for match in matches:
                url = match.group(0)
                file_key = match.group(1)

                if file_key in seen_file_keys:
                    continue

                seen_file_keys.add(file_key)
                clean_url = JiraFigmaHelper._clean_url(url)
                name = JiraFigmaHelper._extract_name_from_url(clean_url)
                node_id = JiraFigmaHelper._extract_node_id(clean_url)

                figma_links.append(FigmaLink(
                    url=clean_url,
                    file_key=file_key,
                    name=name,
                    source='description',
                    node_id=node_id
                ))

        return figma_links

    @staticmethod
    def _clean_url(raw_url: str) -> str:
        """JIRA smart-card formatidagi URL ni tozalash.

        JIRA ADF da link: https://figma.com/.../File?node-id=X|https://...|smart-card]
        Pipe belgisidan oldingi qism — haqiqiy URL.
        """
        url = raw_url.split('|')[0]
        url = url.replace('&amp;', '&').rstrip('<>[]')
        return url

    @staticmethod
    def _extract_node_id(url: str) -> str | None:
        """URL dan node-id parametrini olish (masalan: "1337-16" → "1337:16")."""
        match = re.search(r'node-id=([^&\s|]+)', url)
        if match:
            return match.group(1).replace('-', ':')
        return None

    @staticmethod
    def _extract_name_from_url(url: str) -> str:
        """Extract file name from URL"""
        pattern = r'/(?:file|design|proto)/[A-Za-z0-9]+/([^?]+)'
        match = re.search(pattern, url)

        if match:
            name = match.group(1)
            name = name.replace('-', ' ').replace('_', ' ')
            return name

        return "Figma Design"

    @staticmethod
    def format_figma_summary(figma_links: List[FigmaLink]) -> str:
        """Format Figma links as summary"""
        if not figma_links:
            return "🎨 Figma dizayn topilmadi"

        lines = [f"🎨 FIGMA DIZAYNLAR ({len(figma_links)} ta)", "=" * 60]

        for i, link in enumerate(figma_links, 1):
            lines.append(f"\n{i}. {link.name}")
            lines.append(f"   File Key: {link.file_key}")
            lines.append(f"   URL: {link.url}")
            lines.append(f"   Source: {link.source}")

            if link.author:
                lines.append(f"   Author: {link.author}")

        return "\n".join(lines)
