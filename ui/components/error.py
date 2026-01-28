"""
Error Component - Xatolik xabarlari

Bu component xatolik, ogohlantirish va ma'lumot xabarlarini
ko'rsatish uchun komponentlarni taqdim etadi.
"""

import streamlit as st
from typing import Optional, Dict, List


def render_error(
        message: str,
        details: Optional[str] = None,
        show_icon: bool = True,
        expandable: bool = False
):
    """
    Xatolik xabarini ko'rsatish

    Args:
        message: Asosiy xatolik xabari
        details: Batafsil ma'lumot (optional)
        show_icon: Icon ko'rsatish (default: True)
        expandable: Expandable qilish (default: False)

    Example:
        >>> render_error(
        >>>     message="Task topilmadi!",
        >>>     details="DEV-123 JIRA'da mavjud emas yoki access yo'q"
        >>> )
    """
    icon = "❌ " if show_icon else ""

    if details and expandable:
        with st.expander(f"{icon}{message}", expanded=False):
            st.error(details)
    elif details:
        st.error(f"{icon}{message}\n\n{details}")
    else:
        st.error(f"{icon}{message}")


def render_warning(
        message: str,
        details: Optional[str] = None,
        show_icon: bool = True
):
    """
    Ogohlantirish xabarini ko'rsatish

    Args:
        message: Asosiy ogohlantirish
        details: Batafsil ma'lumot (optional)
        show_icon: Icon ko'rsatish (default: True)

    Example:
        >>> render_warning(
        >>>     message="PR topilmadi",
        >>>     details="JIRA va GitHub'da bu task uchun PR yo'q"
        >>> )
    """
    icon = "⚠️ " if show_icon else ""

    if details:
        st.warning(f"{icon}{message}\n\n{details}")
    else:
        st.warning(f"{icon}{message}")


def render_info(
        message: str,
        details: Optional[str] = None,
        show_icon: bool = True
):
    """
    Ma'lumot xabarini ko'rsatish

    Args:
        message: Asosiy ma'lumot
        details: Batafsil ma'lumot (optional)
        show_icon: Icon ko'rsatish (default: True)

    Example:
        >>> render_info(
        >>>     message="Jarayon boshlandi",
        >>>     details="Task key: DEV-123"
        >>> )
    """
    icon = "ℹ️ " if show_icon else ""

    if details:
        st.info(f"{icon}{message}\n\n{details}")
    else:
        st.info(f"{icon}{message}")


def render_success(
        message: str,
        details: Optional[str] = None,
        show_icon: bool = True
):
    """
    Muvaffaqiyat xabarini ko'rsatish

    Args:
        message: Asosiy xabar
        details: Batafsil ma'lumot (optional)
        show_icon: Icon ko'rsatish (default: True)

    Example:
        >>> render_success(
        >>>     message="Tahlil tugadi!",
        >>>     details="5 ta o'xshash task topildi"
        >>> )
    """
    icon = "✅ " if show_icon else ""

    if details:
        st.success(f"{icon}{message}\n\n{details}")
    else:
        st.success(f"{icon}{message}")


def render_error_list(
        title: str,
        errors: List[str],
        warnings: Optional[List[str]] = None
):
    """
    Xatoliklar ro'yxatini ko'rsatish

    Args:
        title: Sarlavha
        errors: Xatoliklar ro'yxati
        warnings: Ogohlantirishlar ro'yxati (optional)

    Example:
        >>> render_error_list(
        >>>     title="Quyidagi muammolar topildi:",
        >>>     errors=["PR topilmadi", "TZ bo'sh"],
        >>>     warnings=["Comment'lar yo'q"]
        >>> )
    """
    st.error(f"**{title}**")

    if errors:
        st.markdown("**Xatoliklar:**")
        for error in errors:
            st.markdown(f"• ❌ {error}")

    if warnings:
        st.markdown("\n**Ogohlantirishlar:**")
        for warning in warnings:
            st.markdown(f"• ⚠️ {warning}")


def render_debug_info(
        data: Dict,
        title: str = "Debug Ma'lumoti",
        expanded: bool = False
):
    """
    Debug ma'lumotini ko'rsatish

    Bu function development paytida foydali. Production'da
    o'chirilishi mumkin.

    Args:
        data: Debug data (dict)
        title: Sarlavha
        expanded: Default ochiq bo'lishi (default: False)

    Example:
        >>> render_debug_info(
        >>>     data={'task_key': 'DEV-123', 'pr_count': 3},
        >>>     title="Task Ma'lumoti"
        >>> )
    """
    with st.expander(f"🔍 {title}", expanded=expanded):
        st.json(data)


def render_validation_errors(
        field_errors: Dict[str, str],
        title: str = "Validatsiya xatolari"
):
    """
    Validatsiya xatoliklarini ko'rsatish

    Args:
        field_errors: Field -> xatolik mapping
        title: Sarlavha

    Example:
        >>> errors = {
        >>>     'task_key': 'Task key bosh',
        >>>     'pr_url': 'PR URL notogri format'
        >>> }
        >>> render_validation_errors(errors)
    """
    if not field_errors:
        return

    st.error(f"**{title}**")

    for field, error in field_errors.items():
        st.markdown(f"• **{field}:** {error}")


def render_exception(
        exception: Exception,
        context: Optional[str] = None,
        show_traceback: bool = False
):
    """
    Exception'ni ko'rsatish

    Args:
        exception: Exception object
        context: Kontekst ma'lumoti (optional)
        show_traceback: Traceback ko'rsatish (default: False)

    Example:
        >>> try:
        >>>     # some code
        >>> except Exception as e:
        >>>     render_exception(e, context="PR olishda xatolik")
    """
    error_msg = f"**Xatolik:** {str(exception)}"

    if context:
        error_msg = f"**{context}**\n\n{error_msg}"

    if show_traceback:
        import traceback
        trace = traceback.format_exc()

        st.error(error_msg)

        with st.expander("🔍 Traceback", expanded=False):
            st.code(trace, language="python")
    else:
        st.error(error_msg)


class ErrorCollector:
    """
    Xatoliklarni yig'ish va ko'rsatish

    Bu class bir nechta xatoliklarni yig'ib, oxirida
    bir vaqtning o'zida ko'rsatish imkonini beradi.

    Example:
        >>> errors = ErrorCollector()
        >>> errors.add_error("PR topilmadi")
        >>> errors.add_warning("Comment'lar yo'q")
        >>> errors.render()
    """

    def __init__(self):
        """Initialize error collector"""
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.infos: List[str] = []

    def add_error(self, message: str):
        """Xatolik qo'shish"""
        self.errors.append(message)

    def add_warning(self, message: str):
        """Ogohlantirish qo'shish"""
        self.warnings.append(message)

    def add_info(self, message: str):
        """Ma'lumot qo'shish"""
        self.infos.append(message)

    def has_errors(self) -> bool:
        """Xatolik bormi?"""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Ogohlantirish bormi?"""
        return len(self.warnings) > 0

    def render(self, title: str = "Natijalar"):
        """Barcha xabarlarni ko'rsatish"""
        if self.errors:
            render_error_list(
                title=title,
                errors=self.errors,
                warnings=self.warnings if self.warnings else None
            )
        elif self.warnings:
            st.warning(f"**Ogohlantirishlar:**")
            for warning in self.warnings:
                st.markdown(f"• ⚠️ {warning}")

        if self.infos:
            for info in self.infos:
                st.info(f"ℹ️ {info}")

    def clear(self):
        """Barcha xabarlarni tozalash"""
        self.errors = []
        self.warnings = []
        self.infos = []