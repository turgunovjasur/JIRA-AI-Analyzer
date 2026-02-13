# ui/pages/sidebar.py
"""
Sidebar - Navigation

Yoqilgan modullarni ko'rsatadi.
Barcha sozlamalar alohida unified settings page'da.

Author: JASUR TURGUNOV
Version: 4.0
"""
import streamlit as st


def render_sidebar():
    """
    Sidebar rendering

    Returns:
        tuple: (page_name, None) - settings olib tashlandi (v4.0)
    """
    from config.app_settings import get_app_settings

    app_settings = get_app_settings()

    with st.sidebar:
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # HEADER
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0; margin-bottom: 1rem;">
            <h2 style="color: #e6edf3; font-weight: 700; margin: 0;">QA Assistant</h2>
            <p style="color: #8b949e; font-size: 0.85rem; margin-top: 0.5rem;">AI-Powered Analysis Suite</p>
            <p style="color: #6e7681; font-size: 0.7rem; font-style: italic;">v4.0 by JASUR TURGUNOV</p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # NAVIGATION - Faqat yoqilgan modullar
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        modules = []

        if app_settings.modules.bug_analyzer_enabled:
            modules.append("Bug Analyzer")
        if app_settings.modules.statistics_enabled:
            modules.append("Sprint Statistics")
        if app_settings.modules.tz_pr_checker_enabled:
            modules.append("TZ-PR Checker")
        if app_settings.modules.testcase_generator_enabled:
            modules.append("Test Case Generator")

        st.markdown("### Sahifa tanlang")

        if modules:
            # Default page
            default_index = 0
            if 'selected_page' in st.session_state and st.session_state.selected_page in modules:
                default_index = modules.index(st.session_state.selected_page)

            page = st.radio(
                "Funksiyalar",
                options=modules,
                index=default_index,
                label_visibility="collapsed",
                key="page_selector"
            )

            # Save selected page
            st.session_state.selected_page = page
        else:
            st.warning("⚠️ Hech qaysi modul yoqilmagan!")
            page = None

        st.divider()

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # MONITORING DASHBOARD
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if st.button("📊 Monitoring", use_container_width=True, key="monitoring_btn"):
            st.session_state.show_monitoring = True
            st.rerun()

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # SPRINT REPORT
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if st.button("📈 Sprint Report", use_container_width=True, key="sprint_report_btn"):
            st.session_state.show_sprint_report = True
            st.rerun()

        st.divider()

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # SETTINGS TUGMASI
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if st.button("⚙️ Sozlamalar", use_container_width=True, key="settings_btn"):
            st.session_state.show_settings = True
            st.rerun()

        st.divider()

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STATUS
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        st.markdown("### Status")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("✅ JIRA: OK" if _check_jira() else "❌ JIRA: ERROR")
        with col2:
            st.markdown("✅ GitHub: OK" if _check_github() else "⚠️ GitHub: Optional")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # FOOTER
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        st.markdown("""
        <div style="background: rgba(88, 166, 255, 0.1); padding: 0.75rem; border-radius: 8px; margin-top: 1rem;">
            <p style="color: #8b949e; font-size: 0.75rem; margin: 0;">
                <strong style="color: #58a6ff;">AI:</strong> Gemini 2.5 Flash<br>
                <strong style="color: #58a6ff;">Version:</strong> 4.0
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Settings sahifasi tanlangan bo'lsa
    if st.session_state.get('show_settings', False):
        return "Settings", None

    # Monitoring sahifasi tanlangan bo'lsa
    if st.session_state.get('show_monitoring', False):
        return "Monitoring", None

    # ✅ Sprint Report sahifasi tanlangan bo'lsa
    if st.session_state.get('show_sprint_report', False):
        return "Sprint Report", None

    return page, None


def _check_jira():
    """JIRA ulanishini tekshirish"""
    try:
        from config.settings import settings
        return bool(settings.JIRA_EMAIL and settings.JIRA_API_TOKEN)
    except:
        return False


def _check_github():
    """GitHub ulanishini tekshirish"""
    try:
        from config.settings import settings
        return bool(settings.GITHUB_TOKEN)
    except:
        return False
