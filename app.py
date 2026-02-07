# app.py
"""
JIRA Bug Analyzer - Main Application v4.0

4 ta asosiy modul:
1. Bug Analyzer - Bug root cause analysis
2. Sprint Statistics - Sprint statistikasi
3. TZ-PR Checker - TZ va kod mosligi
4. Test Case Generator - Test case lar generatsiya

Yangiliklar v4.0:
- Yagona sozlamalar tizimi
- Modul ko'rinishini boshqarish
- Lazy loading - o'chirilgan modullar yuklanmaydi

Author: JASUR TURGUNOV
Version: 4.0.0
"""
import streamlit as st

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="JIRA Bug Analyzer",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': """
        # JIRA Bug Analyzer v4.0

        AI-powered bug analysis system.

        **Features:**
        - Bug Root Cause Analysis
        - Sprint Statistics
        - TZ-PR Compliance Check
        - Test Case Generator

        **Author:** JASUR TURGUNOV
        """
    }
)

# ==================== STYLES ====================
from ui.styles import CUSTOM_CSS

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ==================== MAIN APP ====================
def main():
    """Main application entry point"""

    # Sidebar - page selection & settings
    from ui.pages.sidebar import render_sidebar
    from config.app_settings import get_app_settings

    page, _ = render_sidebar()  # settings olib tashlandi (v4.0)
    app_settings = get_app_settings()

    # ==================== PAGE ROUTING ====================

    if page == "Settings":
        # Yagona Sozlamalar sahifasi
        from ui.pages.unified_settings import render_unified_settings
        render_unified_settings()

        # Sozlamalardan chiqish tugmasi
        st.markdown("---")
        if st.button("← Orqaga qaytish", use_container_width=False):
            st.session_state.show_settings = False
            st.rerun()

    elif page == "Bug Analyzer":
        # Bug Analyzer sahifasi
        if app_settings.modules.bug_analyzer_enabled:
            from ui.pages.bug_analyzer import render_bug_analyzer
            render_bug_analyzer()
        else:
            _render_module_disabled("Bug Analyzer")

    elif page == "Sprint Statistics":
        # Statistics sahifasi
        if app_settings.modules.statistics_enabled:
            from ui.pages.statistics import render_statistics
            render_statistics()
        else:
            _render_module_disabled("Sprint Statistics")

    elif page == "TZ-PR Checker":
        # TZ-PR Checker sahifasi
        if app_settings.modules.tz_pr_checker_enabled:
            from ui.pages.tz_pr_checker import render_tz_pr_checker
            render_tz_pr_checker()
        else:
            _render_module_disabled("TZ-PR Checker")

    elif page == "Test Case Generator":
        # Test Case Generator sahifasi
        if app_settings.modules.testcase_generator_enabled:
            from ui.pages.testcase_generator import render_testcase_generator
            render_testcase_generator()
        else:
            _render_module_disabled("Test Case Generator")

    elif page is None:
        # Hech qaysi modul yoqilmagan
        st.warning("⚠️ Hech qaysi modul yoqilmagan!")
        st.info("Sozlamalar → Modullar bo'limidan kamida bitta modulni yoqing.")

        if st.button("⚙️ Sozlamalarni ochish"):
            st.session_state.show_settings = True
            st.rerun()

    else:
        # Fallback
        st.error(f"Noma'lum sahifa: {page}")


def _render_module_disabled(module_name: str):
    """O'chirilgan modul uchun xabar"""
    st.warning(f"⚠️ {module_name} moduli o'chirilgan")

    st.markdown(f"""
    <div style="background: rgba(210, 153, 34, 0.1); padding: 1.5rem; border-radius: 12px; margin-top: 1rem;">
        <h3 style="color: #d29922; margin: 0;">🔒 Modul o'chirilgan</h3>
        <p style="color: #8b949e; margin-top: 0.5rem;">
            <strong>{module_name}</strong> moduli hozirda o'chirilgan.
            Uni yoqish uchun Sozlamalar → Modullar bo'limiga o'ting.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("⚙️ Sozlamalarni ochish", key=f"open_settings_{module_name}"):
        st.session_state.show_settings = True
        st.rerun()


# ==================== ERROR HANDLER ====================
def handle_error(error: Exception):
    """Global error handler"""
    st.error(f"Xatolik yuz berdi: {str(error)}")

    with st.expander("Debug ma'lumotlar"):
        import traceback
        st.code(traceback.format_exc())

    st.info("""
    **Mumkin sabablar:**
    - JIRA/GitHub credentials noto'g'ri
    - Network xatolik
    - API rate limit

    **Yechim:** .env faylini tekshiring
    """)


# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        handle_error(e)
