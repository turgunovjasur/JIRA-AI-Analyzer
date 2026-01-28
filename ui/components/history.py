"""
History Component - Tahlil tarixi

Bu component so'nggi tahlillar tarixini ko'rsatish va
saqlash funksiyalarini taqdim etadi.

Hozir 2 ta sahifada bir xil history pattern takrorlanardi:
- tz_pr_checker.py
- testcase_generator.py
"""

import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional, Callable


def render_history(
        history_key: str,
        max_items: int = 5,
        on_rerun: Optional[Callable[[Dict], None]] = None,
        show_time: bool = True
):
    """
    Tahlil tarixini ko'rsatish

    Bu function session_state'dan tarixni o'qib, ko'rsatadi.
    Har bir elementda qayta tahlil qilish tugmasi bo'ladi.

    Args:
        history_key: Session state key (masalan: 'tz_pr_history')
        max_items: Maksimal ko'rsatiladigan elementlar (default: 5)
        on_rerun: Qayta tahlil callback function
        show_time: Vaqtni ko'rsatish (default: True)

    Example:
        >>> def rerun_analysis(item):
        >>>     task_key = item['key']
        >>>     # Tahlilni qayta ishga tushirish
        >>>
        >>> render_history(
        >>>     history_key='tz_pr_history',
        >>>     on_rerun=rerun_analysis
        >>> )
    """
    # Session state'dan tarixni olish
    if history_key not in st.session_state or not st.session_state[history_key]:
        return

    history = st.session_state[history_key]

    # Header
    st.markdown("---")
    st.markdown(f"### 📜 So'nggi {max_items} ta tahlil")

    # Teskari tartibda ko'rsatish (eng yangi birinchi)
    items_to_show = list(reversed(history[-max_items:]))

    for idx, item in enumerate(items_to_show):
        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            # Status emoji
            if item.get('success'):
                status_emoji = "✅"
            else:
                status_emoji = "❌"

            # Task key
            task_key = item.get('key', 'N/A')
            st.write(f"{status_emoji} {task_key}")

        with col2:
            # Vaqt
            if show_time and 'time' in item:
                st.write(f"🕐 {item['time']}")

        with col3:
            # Qayta tahlil tugmasi
            if on_rerun:
                button_key = f"rerun_{history_key}_{task_key}_{idx}"
                if st.button("🔄", key=button_key, help="Qayta tahlil qilish"):
                    on_rerun(item)


def save_to_history(
        history_key: str,
        item_data: Dict,
        max_history: int = 20
):
    """
    Tahlilni tarixga saqlash

    Bu function yangi tahlil natijasini session_state'ga qo'shadi.

    Args:
        history_key: Session state key
        item_data: Saqlanadigan ma'lumot (Dict)
        max_history: Maksimal tarix hajmi (default: 20)

    Example:
        >>> save_to_history(
        >>>     history_key='tz_pr_history',
        >>>     item_data={
        >>>         'key': 'DEV-123',
        >>>         'success': True,
        >>>         'time': datetime.now().strftime('%Y-%m-%d %H:%M')
        >>>     }
        >>> )
    """
    # Session state'ni tekshirish
    if history_key not in st.session_state:
        st.session_state[history_key] = []

    # Vaqtni qo'shish (agar yo'q bo'lsa)
    if 'time' not in item_data:
        item_data['time'] = datetime.now().strftime('%Y-%m-%d %H:%M')

    # Tarixga qo'shish
    st.session_state[history_key].append(item_data)

    # Maksimal hajmni tekshirish
    if len(st.session_state[history_key]) > max_history:
        st.session_state[history_key] = st.session_state[history_key][-max_history:]


def clear_history(history_key: str):
    """
    Tarixni tozalash

    Args:
        history_key: Session state key

    Example:
        >>> if st.button("Tarixni tozalash"):
        >>>     clear_history('tz_pr_history')
    """
    if history_key in st.session_state:
        st.session_state[history_key] = []


def get_history_count(history_key: str) -> int:
    """
    Tarixdagi elementlar sonini olish

    Args:
        history_key: Session state key

    Returns:
        int: Tarixdagi elementlar soni

    Example:
        >>> count = get_history_count('tz_pr_history')
        >>> st.write(f"Jami: {count} ta tahlil")
    """
    if history_key in st.session_state:
        return len(st.session_state[history_key])
    return 0


def get_last_item(history_key: str) -> Optional[Dict]:
    """
    So'nggi tahlilni olish

    Args:
        history_key: Session state key

    Returns:
        Dict or None: So'nggi tahlil ma'lumoti

    Example:
        >>> last = get_last_item('tz_pr_history')
        >>> if last:
        >>>     st.write(f"So'nggi: {last['key']}")
    """
    if history_key in st.session_state and st.session_state[history_key]:
        return st.session_state[history_key][-1]
    return None


class HistoryManager:
    """
    Tarix boshqarish class

    Bu class tarix bilan ishlashni osonlashtiradi.

    Example:
        >>> history = HistoryManager('tz_pr_history')
        >>> history.add({'key': 'DEV-123', 'success': True})
        >>> history.render(on_rerun=lambda item: print(item))
        >>> print(f"Jami: {history.count()}")
    """

    def __init__(self, history_key: str, max_items: int = 20):
        """
        Initialize history manager

        Args:
            history_key: Session state key
            max_items: Maksimal tarix hajmi
        """
        self.history_key = history_key
        self.max_items = max_items

        # Initialize session state
        if history_key not in st.session_state:
            st.session_state[history_key] = []

    def add(self, item_data: Dict):
        """Yangi element qo'shish"""
        save_to_history(self.history_key, item_data, self.max_items)

    def render(
            self,
            max_display: int = 5,
            on_rerun: Optional[Callable[[Dict], None]] = None,
            show_time: bool = True
    ):
        """Tarixni ko'rsatish"""
        render_history(self.history_key, max_display, on_rerun, show_time)

    def clear(self):
        """Tarixni tozalash"""
        clear_history(self.history_key)

    def count(self) -> int:
        """Elementlar sonini olish"""
        return get_history_count(self.history_key)

    def last(self) -> Optional[Dict]:
        """So'nggi elementni olish"""
        return get_last_item(self.history_key)

    def get_all(self) -> List[Dict]:
        """Barcha tarixni olish"""
        if self.history_key in st.session_state:
            return st.session_state[self.history_key]
        return []