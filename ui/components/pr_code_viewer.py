# ui/components/pr_code_viewer.py
"""
PR Code Viewer Component - REUSABLE
PR fayllar va kod o'zgarishlarini ko'rsatish uchun umumiy komponent

Bu komponent quyidagi sahifalarda ishlatiladi:
- TZ-PR Checker
- Test Case Generator

Author: JASUR TURGUNOV
Version: 1.0
"""
import streamlit as st
from typing import Dict, List

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STATE_EMOJIS = {
    'merged': '✅',
    'open': '🟢',
    'closed': '⚪'
}

STATUS_EMOJIS = {
    'modified': '📝',
    'added': '➕',
    'removed': '➖',
    'renamed': '🔄'
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN COMPONENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_code_changes_tab(
        pr_details: List[Dict],
        use_smart_patch: bool = False,
        title: str = "💻 Kod O'zgarishlari"
):
    """
    PR kod o'zgarishlarini ko'rsatish - REUSABLE COMPONENT

    Args:
        pr_details: PR details list (from PRHelper)
        use_smart_patch: Smart Patch yoqilganmi
        title: Section title
    """
    st.markdown(f"### {title}")

    # Mode indicator
    mode_text = "🧠 Smart Patch Mode" if use_smart_patch else "📄 Patch Mode"
    st.info(f"**Rejim:** {mode_text}")

    if not pr_details:
        st.warning("PR'lar topilmadi yoki hisobga olinmadi")
        return

    # Render each PR
    for pr in pr_details:
        render_pr_section(pr, use_smart_patch)


def render_pr_section(pr: Dict, use_smart_patch: bool):
    """
    Bitta PR qismini render qilish

    Args:
        pr: PR dict (url, number, title, state, files, additions, deletions)
        use_smart_patch: Smart Patch yoqilganmi
    """
    st.markdown("---")

    # PR Header
    render_pr_header(pr)

    # PR Stats
    render_pr_stats(pr)

    st.markdown("---")

    # Files
    files = pr.get('files', [])

    if not files:
        st.info("Bu PR'da fayllar yo'q")
        return

    st.markdown(f"### 📂 O'zgargan Fayllar ({len(files)} ta)")

    # Render each file
    for file_data in files:
        render_file_changes(file_data, use_smart_patch)


def render_pr_header(pr: Dict):
    """PR header qismini render qilish"""
    pr_number = pr.get('number', '?')
    pr_title = pr.get('title', 'No title')
    pr_url = pr.get('url', '#')
    pr_state = pr.get('state', 'unknown')

    state_emoji = STATE_EMOJIS.get(pr_state, '❓')

    st.markdown(f"## {state_emoji} PR #{pr_number}")
    st.markdown(f"**{pr_title}**")
    st.markdown(f"🔗 [{pr_url}]({pr_url})")


def render_pr_stats(pr: Dict):
    """PR statistikasini ko'rsatish"""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Fayllar", len(pr.get('files', [])))
    with col2:
        st.metric("➕ Add", pr.get('additions', 0))
    with col3:
        st.metric("➖ Del", pr.get('deletions', 0))


def render_file_changes(file_data: Dict, use_smart_patch: bool):
    """
    Bitta fayl o'zgarishlarini ko'rsatish

    Args:
        file_data: File dict (filename, status, additions, deletions, patch, smart_context)
        use_smart_patch: Smart Patch yoqilganmi
    """
    filename = file_data.get('filename', 'unknown')
    status = file_data.get('status', 'modified')
    additions = file_data.get('additions', 0)
    deletions = file_data.get('deletions', 0)

    status_emoji = STATUS_EMOJIS.get(status, '📄')

    with st.expander(
            f"{status_emoji} {filename} (+{additions} -{deletions})",
            expanded=False
    ):
        # Smart context or patch
        if use_smart_patch and file_data.get('smart_context'):
            st.markdown("#### 🧠 Smart Patch")
            st.markdown(file_data['smart_context'])
        elif file_data.get('patch'):
            st.markdown("#### 📄 Diff Patch")
            st.code(file_data['patch'], language='diff')
        else:
            st.info("Patch ma'lumoti yo'q")

        # File URL
        if file_data.get('blob_url'):
            st.markdown(
                f"[GitHub'da to'liq fayl ko'rish ↗]({file_data['blob_url']})"
            )