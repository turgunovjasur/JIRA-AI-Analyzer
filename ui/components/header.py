"""
Header Component - Sahifa sarlavhalari

Bu component barcha sahifalarda ishlatiladigan header patternni
bitta joyda to'playdi.

Hozir 4 ta sahifada bir xil kod takrorlanardi:
- bug_analyzer.py
- tz_pr_checker.py
- testcase_generator.py
- statistics.py
"""

import streamlit as st


def render_header(
        title: str,
        subtitle: str = "",
        version: str = "",
        author: str = "Developed by JASUR TURGUNOV",
        icon: str = ""
):
    """
    Sahifa headerini render qilish

    Bu function sahifa boshida ko'rinadigan sarlavha, tavsif va
    muallif ma'lumotini HTML formatda ko'rsatadi.

    Args:
        title: Asosiy sarlavha (h1)
        subtitle: Qo'shimcha tavsif (p)
        version: Versiya raqami (optional)
        author: Muallif (default: "Developed by JASUR TURGUNOV")
        icon: Emoji icon (optional, title boshida)

    Example:
        >>> render_header(
        >>>     title="🐛 Bug Root Cause Analyzer",
        >>>     subtitle="AI yordamida bugning asosiy sababini toping"
        >>> )

        >>> render_header(
        >>>     title="Test Case Generator",
        >>>     subtitle="TZ va PR asosida test case'lar",
        >>>     version="v3.3",
        >>>     icon="🧪"
        >>> )
    """
    # Title with optional icon
    full_title = f"{icon} {title}" if icon else title

    # Version tag
    version_html = f'<span class="version-tag">{version}</span>' if version else ""

    # Author with version
    author_html = f"{author} {version_html}" if version else author

    st.markdown(f"""
    <div class="main-header">
        <h1>{full_title}</h1>
        {f'<p>{subtitle}</p>' if subtitle else ''}
        <p class="author">{author_html}</p>
    </div>
    """, unsafe_allow_html=True)


def render_info_box(text: str, icon: str = "📋"):
    """
    Info box render qilish

    Sahifa boshida ko'rinadigan ma'lumot qutisi.

    Args:
        text: Ko'rsatiladigan text (markdown supported)
        icon: Icon emoji (default: 📋)

    Example:
        >>> render_info_box('''
        >>> **Qanday ishlaydi:**
        >>> 1. Task key kiriting
        >>> 2. TZ va PR olinadi
        >>> 3. AI tahlil qiladi
        >>> ''')
    """
    st.info(f"{icon} {text}")


def render_divider(style: str = "default"):
    """
    Bo'luvchi chiziq

    Args:
        style: "default", "thick", "dotted"

    Example:
        >>> render_divider()
        >>> render_divider("thick")
    """
    if style == "thick":
        st.markdown("<hr style='border: 2px solid #333; margin: 2rem 0;'>", unsafe_allow_html=True)
    elif style == "dotted":
        st.markdown("<hr style='border-style: dotted; margin: 1.5rem 0;'>", unsafe_allow_html=True)
    else:
        st.markdown("---")


# CSS Styles (agar kerak bo'lsa)
HEADER_STYLES = """
<style>
.main-header {
    text-align: center;
    padding: 2rem 0;
    margin-bottom: 2rem;
}

.main-header h1 {
    font-size: 2.5rem;
    font-weight: 700;
    color: #e6edf3;
    margin-bottom: 0.5rem;
}

.main-header p {
    font-size: 1.1rem;
    color: #8b949e;
    margin-bottom: 0.3rem;
}

.main-header .author {
    font-size: 0.9rem;
    color: #6e7681;
    font-style: italic;
}

.version-tag {
    display: inline-block;
    background: #238636;
    color: white;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-left: 0.5rem;
}
</style>
"""


def inject_header_styles():
    """
    Header styles ni inject qilish

    Agar app.py yoki styles.py da style'lar bo'lmasa,
    bu function orqali inject qilish mumkin.

    Example:
        >>> inject_header_styles()
    """
    st.markdown(HEADER_STYLES, unsafe_allow_html=True)