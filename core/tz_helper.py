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


class CommentSeparator:
    """
    JIRA comment'larini AI va developer tomonidan yozilgan deb ajratish.

    AI comment aniqlash: body boshida [AI_S1] yoki [AI_S2] marker bor.
    Marker jira_adf_formatter.py va testcase_adf_formatter.py tomonidan yoziladi.
    """

    S1_MARKER = "[AI_S1]"
    S2_MARKER = "[AI_S2]"
    @classmethod
    def is_ai_comment(cls, comment: Dict) -> bool:
        body = comment.get('body', '')
        return cls.S1_MARKER in body[:30] or cls.S2_MARKER in body[:30]

    @classmethod
    def get_ai_type(cls, comment: Dict) -> Optional[str]:
        body = comment.get('body', '')
        if cls.S1_MARKER in body[:30]:
            return 'S1'
        if cls.S2_MARKER in body[:30]:
            return 'S2'
        return None

    @classmethod
    def is_valid_dev_comment(cls, comment: Dict) -> bool:
        if cls.is_ai_comment(comment):
            return False
        return bool(comment.get('body', '').strip())

    @classmethod
    def filter_human_comments(cls, comments: List[Dict]) -> List[Dict]:
        """AI yozgan comment'lardan tozalangan human comment'lar."""
        return [comment for comment in comments if cls.is_valid_dev_comment(comment)]

    @classmethod
    def separate(cls, comments: List[Dict], marker: str = 'S1') -> Dict:
        """
        Comment'larni AI va dev tomonidan yozilganlarga ajratadi.

        Oxirgi [AI_S1] (yoki marker='S2' bo'lsa [AI_S2]) comment topiladi.
        Undan OLDINGI dev comment'lar "kontekst", undan KEYINGI dev comment'lar
        "etirozlar" hisoblanadi.

        Args:
            comments: JIRA comment'lar ro'yxati
            marker: 'S1' (default) yoki 'S2' — qaysi AI markerga qarab ajratish

        Returns:
            {
                'last_ai_s1':     Dict or None,   - oxirgi AI comment (marker turiga qarab)
                'dev_before':     List[Dict],     - AI dan oldingi dev comment'lar
                'dev_after':      List[Dict],     - AI dan keyingi dev comment'lar (etirozlar)
                'has_objections': bool            - etirozlar bor-yo'qligi
            }
        """
        last_ai_index = None
        for i, comment in enumerate(comments):
            if cls.get_ai_type(comment) == marker:
                last_ai_index = i

        if last_ai_index is None:
            dev_comments = [c for c in comments if cls.is_valid_dev_comment(c)]
            return {
                'last_ai_s1': None,
                'dev_before': dev_comments,
                'dev_after': [],
                'has_objections': False,
            }

        dev_before = [
            c for c in comments[:last_ai_index]
            if cls.is_valid_dev_comment(c)
        ]
        dev_after = [
            c for c in comments[last_ai_index + 1:]
            if cls.is_valid_dev_comment(c)
        ]

        return {
            'last_ai_s1': comments[last_ai_index],
            'dev_before': dev_before,
            'dev_after': dev_after,
            'has_objections': len(dev_after) > 0,
        }


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
            highlight_changes: bool = True,
            exclude_ai_comments: bool = True,
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
        raw_comments = task_details.get('comments', [])
        comments = (
            CommentSeparator.filter_human_comments(raw_comments)
            if exclude_ai_comments else raw_comments
        )

        if comments:
            # Comment'larni tahlil qilish
            comment_analysis = TZHelper.analyze_comments(
                task_details.get('description', ''),
                comments,
                exclude_ai_comments=False,
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
                'important_comments': [],
                'filtered_out_ai_comments': (
                    len(raw_comments) - len(comments)
                    if exclude_ai_comments else 0
                ),
                'total_comments': 0,
            }

        if exclude_ai_comments:
            comment_analysis['filtered_out_ai_comments'] = len(raw_comments) - len(comments)

        tz_text = "\n".join(parts)
        return tz_text, comment_analysis

    @staticmethod
    def analyze_comments(
            description: str,
            comments: List[Dict],
            exclude_ai_comments: bool = True,
    ) -> Dict:
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
        raw_comments = comments or []
        comments = (
            CommentSeparator.filter_human_comments(raw_comments)
            if exclude_ai_comments else raw_comments
        )

        if not comments:
            return {
                'has_changes': False,
                'summary': "Comment yo'q",
                'change_count': 0,
                'important_comments': [],
                'filtered_out_ai_comments': (
                    len(raw_comments) - len(comments)
                    if exclude_ai_comments else 0
                ),
                'total_comments': 0,
            }

        # O'zgarish bildiruvchi so'zlar (multilingual)
        change_keywords = [
            # O'zbekcha
            'ozgardi', 'ozgarsin', 'yangilandi', 'qoshilsin', 'qoshimcha',
            'orniga', 'kerak emas', 'yangi', 'endi', 'gaplashdik', 'kelishdik', 'keyin qiladigan boldik', 'keyingi sprintga'
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
            'total_comments': len(comments),
            'filtered_out_ai_comments': (
                len(raw_comments) - len(comments)
                if exclude_ai_comments else 0
            ),
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

    @staticmethod
    def format_contradictory_comments_for_ai(comment_analysis: Dict) -> str:
        """
        Zid commentlarni AI uchun formatda tayyorlash

        AI ga aniq warning va barcha zid commentlarni ko'rsatish uchun.

        Args:
            comment_analysis: analyze_comments() natijasi

        Returns:
            str: AI uchun formatted warning text

        Example:
            >>> warning = TZHelper.format_contradictory_comments_for_ai(analysis)
            >>> prompt = tz_text + "\n\n" + warning
        """
        if not comment_analysis.get('has_changes'):
            return ""

        lines = [
            "=" * 70,
            "⚠️ DIQQAT AI! COMMENT'LARDA O'ZGARISHLAR TOPILDI!",
            "=" * 70,
            "",
            f"Jami {comment_analysis['change_count']} ta comment'da TZ'ni o'zgartiruvchi",
            "yoki bekor qiluvchi kalit so'zlar topildi.",
            "",
            "Quyidagi comment'lar TZ'ni o'zgartirgan yoki bekor qilgan bo'lishi mumkin:",
            ""
        ]

        for idx, comment in enumerate(comment_analysis.get('important_comments', []), 1):
            lines.append(f"📌 Comment #{idx}:")
            lines.append(f"   Muallif: {comment['author']}")
            lines.append(f"   Sana: {comment['created']}")
            lines.append(f"   Matn: {comment['full_text']}")
            lines.append("")

        lines.extend([
            "=" * 70,
            "⚠️ MUHIM: Barcha comment'larni diqqat bilan o'qing!",
            "Eng so'nggi talablar va o'zgarishlarni hisobga oling!",
            "=" * 70,
            ""
        ])

        return "\n".join(lines)

    @staticmethod
    def format_contradictory_comments_for_ui(comment_analysis: Dict) -> dict:
        """
        Zid commentlarni UI (Streamlit) uchun formatda tayyorlash

        Streamlit warning va expander'larda ko'rsatish uchun.

        Args:
            comment_analysis: analyze_comments() natijasi

        Returns:
            dict: {
                'show_warning': bool,
                'title': str,
                'summary': str,
                'comments': List[Dict]
            }

        Example:
            >>> ui_data = TZHelper.format_contradictory_comments_for_ui(analysis)
            >>> if ui_data['show_warning']:
            >>>     st.warning(ui_data['title'])
        """
        if not comment_analysis.get('has_changes'):
            return {
                'show_warning': False,
                'title': '',
                'summary': '',
                'comments': []
            }

        change_count = comment_analysis['change_count']
        title = f"⚠️ Diqqat! {change_count} ta comment'da TZ'ga zid yoki bekor qilingan shartlar topildi!"

        summary = (
            f"Tahlil jarayonida {change_count} ta comment'da TZ'ni o'zgartiruvchi "
            "yoki bekor qiluvchi kalit so'zlar topildi. "
            "Quyida har bir comment'ning tafsilotlarini ko'ring."
        )

        formatted_comments = []
        for comment in comment_analysis.get('important_comments', []):
            formatted_comments.append({
                'author': comment['author'],
                'created': comment['created'],
                'preview': comment['preview'],
                'full_text': comment['full_text']
            })

        return {
            'show_warning': True,
            'title': title,
            'summary': summary,
            'comments': formatted_comments
        }
