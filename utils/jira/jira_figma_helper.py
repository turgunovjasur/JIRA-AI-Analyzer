# utils/jira/jira_figma_helper.py
"""
JIRA Figma Helper - JIRA task'lardan Figma link'larni olish
"""
import re
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class FigmaLink:
    """Figma link ma'lumotlari"""
    url: str
    file_key: str
    name: str
    source: str
    author: str = None


class JiraFigmaHelper:
    """JIRA'dan Figma link'larni topish"""

    FIGMA_PATTERN = r'https://(?:www\.)?figma\.com/(?:file|proto|design)/([A-Za-z0-9]+)[^"\s<]*'

    @staticmethod
    def extract_figma_urls(task_details: Dict) -> List[FigmaLink]:
        """Extract Figma URLs from task"""
        figma_links = []
        seen_file_keys = set()

        # 1. Description
        description = task_details.get('description', '')
        if description:
            matches = re.finditer(JiraFigmaHelper.FIGMA_PATTERN, description)

            for match in matches:
                url = match.group(0)
                file_key = match.group(1)

                if file_key in seen_file_keys:
                    continue

                seen_file_keys.add(file_key)
                clean_url = url.replace('&amp;', '&').rstrip('<>')
                name = JiraFigmaHelper._extract_name_from_url(clean_url)

                figma_links.append(FigmaLink(
                    url=clean_url,
                    file_key=file_key,
                    name=name,
                    source='description'
                ))

        # 2. Comments
        comments = task_details.get('comments', [])
        for comment in comments:
            comment_body = comment.get('body', '')
            matches = re.finditer(JiraFigmaHelper.FIGMA_PATTERN, comment_body)

            for match in matches:
                url = match.group(0)
                file_key = match.group(1)

                if file_key in seen_file_keys:
                    continue

                seen_file_keys.add(file_key)
                clean_url = url.replace('&amp;', '&').rstrip('<>')
                name = JiraFigmaHelper._extract_name_from_url(clean_url)

                figma_links.append(FigmaLink(
                    url=clean_url,
                    file_key=file_key,
                    name=name,
                    source='comment',
                    author=comment.get('author', 'Unknown')
                ))

        return figma_links

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