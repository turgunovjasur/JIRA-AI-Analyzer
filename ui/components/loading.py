"""
Loading Component - Loading va Progress

Bu component loading animatsiyalar va progress barlarni
boshqaradi.

Hozir 3 ta sahifada bir xil loading pattern takrorlanardi:
- bug_analyzer.py
- tz_pr_checker.py
- testcase_generator.py
"""

import streamlit as st
from typing import Optional, Callable


def render_loading_animation(text: str, subtext: str = "Iltimos kuting..."):
    """
    Modern loading animation

    Pulse animation bilan loading ko'rsatadi.

    Args:
        text: Asosiy text (masalan: "🔧 Modellar yuklanmoqda...")
        subtext: Qo'shimcha text (masalan: "Iltimos kuting...")

    Example:
        >>> loading_placeholder = st.empty()
        >>> with loading_placeholder.container():
        >>>     render_loading_animation(
        >>>         "🔧 Modellar yuklanmoqda...",
        >>>         "Iltimos kuting..."
        >>>     )
    """
    st.markdown(f"""
    <div class="modern-loading">
        <div class="pulse-animation">
            <div class="pulse-ring"></div>
            <div class="pulse-ring"></div>
            <div class="pulse-ring"></div>
            <div class="pulse-core"></div>
        </div>
        <div class="loading-text">{text}</div>
        <div class="loading-subtext">{subtext}</div>
    </div>
    """, unsafe_allow_html=True)


def render_progress_bar(
        current_step: int,
        total_steps: int,
        message: str,
        show_percentage: bool = True
):
    """
    Progress bar ko'rsatish

    Bu function progress bar va status textni bir vaqtda
    ko'rsatadi.

    Args:
        current_step: Joriy qadam (1, 2, 3, ...)
        total_steps: Jami qadamlar soni
        message: Status xabari
        show_percentage: Foizni ko'rsatish (default: True)

    Returns:
        tuple: (progress_bar, status_text) - Streamlit elementlar

    Example:
        >>> progress_bar, status_text = render_progress_bar(1, 4, "TZ olinmoqda...")
        >>> # Keyinroq yangilash:
        >>> progress_bar.progress(2 / 4)
        >>> status_text.info("**[2/4]** PR qidirilmoqda...")
    """
    progress_value = current_step / total_steps

    # Progress bar
    progress_bar = st.progress(progress_value)

    # Status text
    if show_percentage:
        percentage = int(progress_value * 100)
        status_msg = f"**[{current_step}/{total_steps}] {percentage}%** {message}"
    else:
        status_msg = f"**[{current_step}/{total_steps}]** {message}"

    status_text = st.empty()
    status_text.info(status_msg)

    return progress_bar, status_text


class ProgressManager:
    """
    Progress boshqarish class

    Bu class progress bar va status textni boshqarish uchun
    qulayroq interface beradi.

    Example:
        >>> progress = ProgressManager(total_steps=4)
        >>> progress.update(1, "TZ olinmoqda...")
        >>> progress.update(2, "PR qidirilmoqda...")
        >>> progress.complete("Tayyor!")
        >>> progress.clear()
    """

    def __init__(self, total_steps: int, show_percentage: bool = True):
        """
        Initialize progress manager

        Args:
            total_steps: Jami qadamlar soni
            show_percentage: Foizni ko'rsatish
        """
        self.total_steps = total_steps
        self.show_percentage = show_percentage
        self.current_step = 0

        # Create streamlit elements
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()

    def update(self, step: int, message: str):
        """
        Progress yangilash

        Args:
            step: Joriy qadam
            message: Status xabari
        """
        self.current_step = step
        progress_value = step / self.total_steps

        self.progress_bar.progress(progress_value)

        if self.show_percentage:
            percentage = int(progress_value * 100)
            status_msg = f"**[{step}/{self.total_steps}] {percentage}%** {message}"
        else:
            status_msg = f"**[{step}/{self.total_steps}]** {message}"

        self.status_text.info(status_msg)

    def complete(self, message: str = "✅ Tayyor!"):
        """
        Progress tugadi

        Args:
            message: Yakuniy xabar
        """
        self.progress_bar.progress(1.0)
        self.status_text.success(message)

    def error(self, message: str):
        """
        Xatolik

        Args:
            message: Xatolik xabari
        """
        self.status_text.error(message)

    def clear(self):
        """Progress barni tozalash"""
        self.progress_bar.empty()
        self.status_text.empty()


def clear_loading(loading_placeholder):
    """
    Loading animatsiyani tozalash

    Args:
        loading_placeholder: st.empty() dan yaratilgan placeholder

    Example:
        >>> loading_placeholder = st.empty()
        >>> with loading_placeholder.container():
        >>>     render_loading_animation("Loading...")
        >>> # Ishlar tugagach:
        >>> clear_loading(loading_placeholder)
    """
    if loading_placeholder:
        loading_placeholder.empty()


# CSS Styles
LOADING_STYLES = """
<style>
.modern-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem 0;
}

.pulse-animation {
    position: relative;
    width: 120px;
    height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.pulse-ring {
    position: absolute;
    width: 100%;
    height: 100%;
    border: 3px solid #238636;
    border-radius: 50%;
    animation: pulse 2s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
    opacity: 0;
}

.pulse-ring:nth-child(2) {
    animation-delay: 0.5s;
}

.pulse-ring:nth-child(3) {
    animation-delay: 1s;
}

.pulse-core {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
    border-radius: 50%;
    box-shadow: 0 0 20px rgba(35, 134, 54, 0.5);
}

@keyframes pulse {
    0% {
        transform: scale(0.5);
        opacity: 0;
    }
    50% {
        opacity: 1;
    }
    100% {
        transform: scale(1.5);
        opacity: 0;
    }
}

.loading-text {
    margin-top: 1.5rem;
    font-size: 1.2rem;
    font-weight: 600;
    color: #e6edf3;
    text-align: center;
}

.loading-subtext {
    margin-top: 0.5rem;
    font-size: 0.95rem;
    color: #8b949e;
    text-align: center;
}
</style>
"""


def inject_loading_styles():
    """Loading styles ni inject qilish"""
    st.markdown(LOADING_STYLES, unsafe_allow_html=True)