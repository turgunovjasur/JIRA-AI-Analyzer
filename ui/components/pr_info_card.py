# ui/components/pr_info_card.py
"""
PR Info Card Component
Reusable component for displaying PR fetch information

Author: JASUR TURGUNOV
"""
import streamlit as st
from typing import Dict, List, Optional


def render_pr_info_card(
        result,
        use_smart_patch: bool = False,
        max_files: Optional[int] = None
):
    """
    PR ma'lumotlarini card'da ko'rsatish

    Args:
        result: TZPRAnalysisResult
        use_smart_patch: Smart Patch yoqilganmi
        max_files: Max fayllar limiti
    """

    # PR source detection
    pr_source = _detect_pr_source(result)

    # Stats
    files_total = result.files_changed
    files_analyzed = getattr(result, 'files_analyzed', files_total)
    files_limited = files_analyzed < files_total

    # Card with columns
    st.markdown("### 📊 PR Ma'lumotlar")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="PR Manbai",
            value=pr_source['name'],
            help=pr_source['description']
        )
        st.caption(pr_source['icon'])

    with col2:
        st.metric(
            label="Pull Requests",
            value=f"{result.pr_count} ta"
        )
        st.caption("🔗 PR'lar")

    with col3:
        files_label = f"{files_analyzed}" + (f"/{files_total}" if files_limited else "")
        st.metric(
            label="Fayllar",
            value=files_label
        )
        if files_limited:
            st.caption("⚠️ Limitlangan")
        else:
            st.caption("📁 Barcha")

    with col4:
        patch_mode = "🧠 Smart" if use_smart_patch else "📄 Oddiy"
        st.metric(
            label="Patch Mode",
            value=patch_mode
        )
        st.caption("Patch rejimi")

    # Additional info
    st.info(f"""
    **O'zgarishlar:** ➕ {result.total_additions} qator | ➖ {result.total_deletions} qator

    **Limit:** {f'Max {max_files} fayl' if max_files else 'Barcha fayllar'}
    """)


def _detect_pr_source(result) -> Dict[str, str]:
    """PR manbai aniqlash"""

    if not result.pr_details:
        return {
            'icon': '❓',
            'name': 'Unknown',
            'description': 'PR manbai noma\'lum'
        }

    # pr_details ichidagi source field'ni tekshirish
    first_pr = result.pr_details[0]

    if isinstance(first_pr, dict):
        source = first_pr.get('source', '')

        if 'JIRA' in source:
            return {
                'icon': '📎',
                'name': 'JIRA',
                'description': 'JIRA Development Panel orqali topildi'
            }
        elif 'GitHub' in source:
            return {
                'icon': '🔍',
                'name': 'GitHub',
                'description': 'GitHub Search orqali topildi (JIRA key)'
            }

    # Default: PR Links
    return {
        'icon': '🔗',
        'name': 'PR Links',
        'description': 'PR URL\'lar orqali'
    }


def render_pr_details_list(result):
    """
    PR'lar ro'yxatini ko'rsatish

    Args:
        result: TZPRAnalysisResult
    """
    st.markdown("### 🔗 PR'lar Ro'yxati")

    if not result.pr_details:
        st.warning("PR'lar topilmadi")
        return

    for i, pr in enumerate(result.pr_details, 1):
        pr_number = pr.get('number', '?')
        pr_title = pr.get('title', 'No title')
        pr_url = pr.get('url', '#')
        pr_state = pr.get('state', 'unknown')
        pr_files_count = len(pr.get('files', []))
        pr_additions = pr.get('additions', 0)
        pr_deletions = pr.get('deletions', 0)

        # State emoji
        state_emoji = {
            'merged': '✅',
            'open': '🟢',
            'closed': '⚪'
        }.get(pr_state, '❓')

        with st.expander(f"{state_emoji} PR #{pr_number}: {pr_title}", expanded=False):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Link:** [{pr_url}]({pr_url})")
                st.markdown(f"**Status:** {pr_state}")

            with col2:
                st.metric("Fayllar", pr_files_count)
                st.caption(f"➕ {pr_additions} | ➖ {pr_deletions}")