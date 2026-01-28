# ui/components/figma_tab.py
"""
Figma Tab Component - TZ-PR Checker uchun

Bu component Figma dizayn ma'lumotlarini ko'rsatadi
"""
import streamlit as st
from typing import Dict, Optional, List


def render_figma_tab(figma_data: Optional[Dict]):
    """
    Figma tab content'ini render qilish

    Args:
        figma_data: TZPRAnalysisResult.figma_data
    """
    if not figma_data:
        _render_no_figma()
        return

    summaries = figma_data.get('summaries', [])

    if not summaries:
        _render_no_figma()
        return

    # Header
    st.markdown("### 🎨 Figma Dizayn Ma'lumotlari")
    st.markdown(f"**Topildi:** {len(summaries)} ta dizayn fayl")
    st.markdown("---")

    # Render each Figma file
    for idx, summary_data in enumerate(summaries, 1):
        _render_figma_file(idx, summary_data)


def _render_no_figma():
    """Figma yo'q bo'lganda ko'rsatish"""
    st.info("🎨 **Figma dizayn topilmadi**")
    st.markdown("""
    Task'da Figma link qo'shish uchun:
    1. JIRA task'ni oching
    2. Description yoki Comment'ga Figma URL qo'shing
    3. Qaytadan tahlil qiling

    **Misol:** `https://www.figma.com/design/ABC123/Design-Name`
    """)


def _render_figma_file(index: int, summary_data: Dict):
    """Bitta Figma file'ni render qilish"""
    name = summary_data.get('name', 'Unnamed')
    url = summary_data.get('url', '')
    summary = summary_data.get('summary', '')

    with st.expander(f"📐 {index}. {name}", expanded=(index == 1)):
        # Link
        if url:
            st.markdown(f"**🔗 Link:** [{name}]({url})")

        # Summary
        if 'Error:' in summary:
            st.error(f"⚠️ {summary}")
        elif 'access yo\'q' in summary.lower():
            st.warning(f"⚠️ {summary}")
            st.markdown("""
            **Yechim:**
            - Figma file sharing settings'ni tekshiring
            - Token'ga access berganligingizni tasdiqlang
            """)
        else:
            # Success - show summary
            st.markdown("**📊 Ma'lumot:**")
            st.code(summary, language="text")

        st.markdown("---")


# Helper function - bu funksiyani tz_pr_checker.py dan chaqirish mumkin
def should_show_figma_tab(result) -> bool:
    """Figma tab ko'rsatish kerakmi?"""
    return (
            result
            and hasattr(result, 'figma_data')
            and result.figma_data
            and result.figma_data.get('summaries')
    )