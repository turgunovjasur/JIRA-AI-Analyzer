"""
TZHelper - Technical Zadanie (TZ) Formatting

Bu class JIRA task'ning TZ (texnik topshiriq) ni formatlash logikasi

TZ tarkibi:
- Summary (task sarlavhasi)
- Description (asosiy texnik topshiriq)
- Metadata (type, priority, assignee, etc.)
- Comments (qo'shimcha talablar, o'zgarishlar)
"""

from typing import Dict, List, Optional


class TZHelper:
    """
    Technical Zadanie (TZ) formatlash va tahlil qilish

    Funksiyalar:
    - format_tz_basic: Oddiy TZ (summary + description + metadata)
    - format_tz_with_comments: TZ + comments
    - format_tz_full: To'liq TZ (barcha ma'lumotlar)
    - analyze_comments: Comment'larni tahlil qilish
    """

    @staticmethod
    def format_tz_basic(task_details: Dict) -> str:
        """
        Asosiy TZ yaratish (comments siz)

        Bu method faqat task'ning asosiy ma'lumotlarini formatlaydi:
        - Summary
        - Description
        - Metadata (type, priority, assignee, etc.)

        Args:
            task_details: JIRA task details (get_task_details() dan)

        Returns:
            str: Formatlangan TZ text

        Example:
            >>> tz = TZHelper.format_tz_basic(task_details)
        """
        parts = []

        # 1. Summary
        summary = task_details.get('summary', '')
        if summary:
            parts.append(f"📋 SUMMARY:")
            parts.append(summary)

        # 2. Description
        description = task_details.get('description', '')
        if description:
            parts.append(f"\n📝 DESCRIPTION (TZ):")
            parts.append(description)

        # 3. Metadata
        parts.append(f"\n📊 METADATA:")
        parts.append(f"   Type: {task_details.get('type', 'N/A')}")
        parts.append(f"   Priority: {task_details.get('priority', 'N/A')}")
        parts.append(f"   Status: {task_details.get('status', 'N/A')}")
        parts.append(f"   Assignee: {task_details.get('assignee', 'Unassigned')}")
        parts.append(f"   Reporter: {task_details.get('reporter', 'Unknown')}")
        parts.append(f"   Created: {task_details.get('created', 'N/A')}")
        parts.append(f"   Story Points: {task_details.get('story_points', 'N/A')}")

        # 4. Labels
        labels = task_details.get('labels', [])
        if labels:
            parts.append(f"   Labels: {', '.join(labels)}")

        # 5. Components
        components = task_details.get('components', [])
        if components:
            parts.append(f"   Components: {', '.join(components)}")

        return "\n".join(parts)

    @staticmethod
    def format_tz_with_comments(
            task_details: Dict,
            max_comments: Optional[int] = None,
            highlight_changes: bool = True
    ) -> tuple[str, Dict]:
        """
        TZ + Comments (to'liq versiya)

        Bu method asosiy TZ ga comment'larni qo'shadi va
        comment'lardagi o'zgarishlarni tahlil qiladi.

        Args:
            task_details: JIRA task details
            max_comments: Maksimal comment'lar soni (None = barcha)
            highlight_changes: Comment'lardagi o'zgarishlarni ta'kidlash

        Returns:
            tuple: (tz_text: str, comment_analysis: Dict)

        Example:
            >>> tz, analysis = TZHelper.format_tz_with_comments(task_details)
            >>> if analysis['has_changes']:
            >>>     print(f"⚠️ {analysis['change_count']} ta o'zgarish!")
        """
        # 1. Asosiy TZ
        parts = [TZHelper.format_tz_basic(task_details)]

        # 2. Comment'lar
        comments = task_details.get('comments', [])

        if comments:
            # Comment'larni tahlil qilish
            comment_analysis = TZHelper.analyze_comments(
                task_details.get('description', ''),
                comments
            )

            # Comment section
            parts.append(f"\n💬 COMMENTS ({len(comments)} ta):")
            parts.append("=" * 80)

            if highlight_changes and comment_analysis['has_changes']:
                parts.append("⚠️ DIQQAT: Comment'lar TZ'ni o'zgartirishi, yangi talab qo'shishi mumkin!")
                parts.append("⚠️ AI: Comment'larni diqqat bilan o'qing va tahlilda hisobga oling!")
                parts.append("=" * 80)

            # Comment'lar ro'yxati
            comments_to_show = comments[-max_comments:] if max_comments else comments

            for i, comment in enumerate(comments_to_show, 1):
                author = comment.get('author', 'Unknown')
                created = comment.get('created', '')
                body = comment.get('body', '').strip()

                if body:
                    parts.append(f"\n[Comment #{i}] {author} ({created}):")
                    parts.append(body)
                    parts.append("-" * 80)
        else:
            comment_analysis = {
                'has_changes': False,
                'summary': "Comment yo'q",
                'change_count': 0,
                'important_comments': []
            }

        tz_text = "\n".join(parts)
        return tz_text, comment_analysis

    @staticmethod
    def analyze_comments(description: str, comments: List[Dict]) -> Dict:
        """
        Comment'lardagi o'zgarishlarni tahlil qilish

        Bu method comment'larni o'qib, qaysi biri TZ'ni o'zgartirishni
        yoki yangi talab qo'shishni bildirganini aniqlaydi.

        Args:
            description: Task description (original TZ)
            comments: Comment'lar ro'yxati

        Returns:
            Dict: {
                'has_changes': bool,          # O'zgarish bormi?
                'summary': str,               # Qisqacha xulosa
                'change_count': int,          # O'zgarish soni
                'important_comments': List    # Muhim comment'lar
            }

        Example:
            >>> analysis = TZHelper.analyze_comments(desc, comments)
            >>> if analysis['has_changes']:
            >>>     print("Diqqat! TZ o'zgargan!")
        """
        if not comments:
            return {
                'has_changes': False,
                'summary': "Comment yo'q",
                'change_count': 0,
                'important_comments': []
            }

        # O'zgarish bildiruvchi so'zlar (multilingual)
        change_keywords = [
            # O'zbekcha
            'ozgardi', 'ozgarsin', 'yangilandi', 'qoshilsin', 'qoshimcha',
            'orniga', 'kerak emas', 'yangi', 'endi',
            # Ruscha
            'изменилось', 'изменить', 'обновлено', 'добавить', 'дополнительно',
            'вместо', 'не нужно', 'новый', 'теперь',
            # Inglizcha
            'changed', 'change', 'updated', 'update', 'add', 'added',
            'instead', 'not needed', 'new', 'now', 'remove', 'removed'
        ]

        change_count = 0
        important_comments = []

        for comment in comments:
            body = comment.get('body', '').lower()

            # O'zgarish so'zlari bormi?
            has_change_keyword = any(keyword in body for keyword in change_keywords)

            if has_change_keyword:
                change_count += 1

                # Muhim comment sifatida saqlash
                author = comment.get('author', 'Unknown')
                created = comment.get('created', '')
                preview = comment.get('body', '')[:200]

                important_comments.append({
                    'author': author,
                    'created': created,
                    'preview': preview + "..." if len(comment.get('body', '')) > 200 else preview,
                    'full_text': comment.get('body', '')
                })

        # Xulosa
        has_changes = change_count > 0

        if has_changes:
            summary = f"⚠️ {change_count} ta comment'da o'zgarish topildi!"
        else:
            summary = f"ℹ️ {len(comments)} ta comment, lekin o'zgarish yo'q"

        return {
            'has_changes': has_changes,
            'summary': summary,
            'change_count': change_count,
            'important_comments': important_comments,
            'total_comments': len(comments)
        }

    @staticmethod
    def create_task_overview(
            task_details: Dict,
            comment_analysis: Optional[Dict] = None,
            pr_info: Optional[Dict] = None
    ) -> str:
        """
        Task'ning umumiy ko'rinishi (overview)

        Bu method task haqida qisqacha ma'lumot yaratadi:
        - Asosiy metadata
        - Comment tahlili
        - PR statistikasi

        Args:
            task_details: JIRA task details
            comment_analysis: analyze_comments() natijasi
            pr_info: PR ma'lumoti (PRHelper.get_pr_full_info() dan)

        Returns:
            str: Markdown formatdagi overview

        Example:
            >>> overview = TZHelper.create_task_overview(
            >>>     task_details, comment_analysis, pr_info
            >>> )
        """
        lines = [
            f"**Task:** {task_details.get('key', 'N/A')}",
            f"**Summary:** {task_details.get('summary', 'N/A')}",
            "",
            f"**Type:** {task_details.get('type', 'N/A')}",
            f"**Priority:** {task_details.get('priority', 'N/A')}",
            f"**Status:** {task_details.get('status', 'N/A')}",
            f"**Assignee:** {task_details.get('assignee', 'Unassigned')}",
            f"**Reporter:** {task_details.get('reporter', 'Unknown')}",
            f"**Created:** {task_details.get('created', 'N/A')}",
            f"**Story Points:** {task_details.get('story_points', 'N/A')}"
        ]

        # Labels
        labels = task_details.get('labels', [])
        if labels:
            lines.append(f"**Labels:** {', '.join(labels)}")

        # Components
        components = task_details.get('components', [])
        if components:
            lines.append(f"**Components:** {', '.join(components)}")

        # Comment tahlili
        if comment_analysis:
            lines.append("")
            lines.append("**💬 Comment Tahlili:**")
            lines.append(comment_analysis['summary'])

            if comment_analysis['has_changes'] and comment_analysis.get('important_comments'):
                lines.append("\nMuhim comment'lar:")
                for comment in comment_analysis['important_comments'][:3]:
                    lines.append(f"• [{comment['author']}] {comment['preview']}")

        # PR statistikasi
        if pr_info:
            lines.append("")
            lines.append("**📊 Kod O'zgarishlari:**")
            lines.append(f"• PR'lar: {pr_info['pr_count']} ta")
            lines.append(f"• Fayllar: {pr_info['files_changed']} ta")
            lines.append(f"• +{pr_info['total_additions']} / -{pr_info['total_deletions']} qator")
        else:
            lines.append("")
            lines.append("**📊 Kod O'zgarishlari:**")
            lines.append("• PR topilmadi")

        return "\n".join(lines)