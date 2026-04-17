# ui/pages/sidebar.py
"""
Sidebar - Navigation

Yoqilgan modullarni ko'rsatadi.
Barcha sozlamalar alohida unified settings page'da.

Author: JASUR TURGUNOV
Version: 4.0
"""
import streamlit as st
from utils.auth.auth_manager import get_auth_info, logout, is_super_admin


def render_super_admin_sidebar() -> str:
    """Super Admin sidebar — faqat admin panel"""
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center; padding:1rem 0; margin-bottom:1rem;">
            <div style="font-size:2rem;">👑</div>
            <h2 style="color:#e6edf3; font-weight:700; margin:0;">Super Admin</h2>
            <p style="color:#8b949e; font-size:0.8rem; margin-top:0.3rem;">
                JIRA AI Analyzer
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.divider()

        page = "Admin Panel"
        st.markdown("### Panel")
        if st.button("🏢 Kompaniyalar", use_container_width=True, type="primary"):
            page = "Admin Panel"

        st.divider()
        _render_logout_button()

    return page


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
        auth = get_auth_info()
        company_name = auth.get('company_name', '')
        company_code = auth.get('company_code', '')

        st.markdown(f"""
        <div style="text-align: center; padding: 1rem 0; margin-bottom: 0.5rem;">
            <h2 style="color: #e6edf3; font-weight: 700; margin: 0;">QA Assistant</h2>
            <p style="color: #8b949e; font-size: 0.85rem; margin-top: 0.5rem;">AI-Powered Analysis Suite</p>
        </div>
        """, unsafe_allow_html=True)

        # Kompaniya nomi
        if company_name:
            st.markdown(f"""
            <div style="background:rgba(88,166,255,0.1); padding:0.5rem 0.75rem;
                        border-radius:8px; margin-bottom:0.5rem; text-align:center;">
                <p style="color:#58a6ff; font-size:0.8rem; font-weight:600; margin:0;">
                    🏢 {company_name}
                </p>
                <p style="color:#6e7681; font-size:0.7rem; margin:0;">{company_code}</p>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # NAVIGATION - Kompaniyaga ruxsat berilgan modullar
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        modules = []

        # Kompaniya session bo'lsa — company_modules dan, aks holda app_settings dan
        company_mods = st.session_state.get('company_modules', {})

        def _mod_enabled(mod_key: str, settings_attr: str = '', always_on_fallback: bool = False) -> bool:
            """
            Modul yoqilganini tekshirish.
            - company_mods mavjud bo'lsa: faqat company_mods dan
            - company_mods bo'sh (super admin yoki dev): settings_attr yoki always_on_fallback
            """
            if company_mods:
                return bool(company_mods.get(mod_key, False))
            if always_on_fallback:
                return True
            return bool(getattr(app_settings.modules, settings_attr, False))

        if _mod_enabled('bug_analyzer', 'bug_analyzer_enabled'):
            modules.append("Bug Analyzer")
        if _mod_enabled('statistics', 'statistics_enabled'):
            modules.append("Sprint Statistics")
        if _mod_enabled('tz_pr_checker', 'tz_pr_checker_enabled'):
            modules.append("TZ-PR Checker")
        if _mod_enabled('testcase_generator', 'testcase_generator_enabled'):
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
        if _mod_enabled('monitoring', always_on_fallback=True):
            if st.button("📊 Monitoring", use_container_width=True, key="monitoring_btn"):
                st.session_state.show_monitoring = True
                st.rerun()

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # SPRINT REPORT
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if _mod_enabled('sprint_report', always_on_fallback=True):
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
        # LOGOUT
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        _render_logout_button()

        st.divider()

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STATUS
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        st.markdown("### Status")
        col1, col2 = st.columns(2)
        jira_ok, jira_err = _check_jira()
        with col1:
            if jira_ok:
                st.markdown("✅ JIRA: OK")
            else:
                st.markdown("❌ JIRA: ERROR")
                if jira_err:
                    st.caption(f"⚠️ {jira_err}")
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


def _render_logout_button():
    """Tizimdan chiqish tugmasi"""
    if st.button("🚪 Chiqish", use_container_width=True, key="logout_btn"):
        logout()
        st.rerun()


def _check_jira():
    """JIRA ulanishini tekshirish — credentials mavjudligini tekshiradi"""
    try:
        from config.settings import settings
        has_creds = bool(settings.JIRA_EMAIL and settings.JIRA_API_TOKEN)
        if not has_creds:
            return False, "JIRA_EMAIL yoki JIRA_API_TOKEN .env da yo'q"
        return True, None
    except Exception as e:
        return False, str(e)


def _check_github():
    """GitHub ulanishini tekshirish"""
    try:
        from config.settings import settings
        return bool(settings.GITHUB_TOKEN)
    except:
        return False
