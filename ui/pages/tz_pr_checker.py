# ui/pages/tz_pr_checker.py
"""
TZ-PR Moslik Tekshirish - Refactored Version (DRY FIXED)

TAB 1: AI Tahlil Natijalari
TAB 2: GitHub Kod O'zgarishlari (pr_code_viewer komponenti)

Author: JASUR TURGUNOV
Version: 6.0 DRY FIXED
"""
import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional, Callable

# UI Components
from ui.components import (
    render_header,
    render_info,
    ProgressManager,
    HistoryManager,
    render_error
)

# Reusable components
from ui.components.pr_info_card import render_pr_info_card

# ✅ DRY FIX: Umumiy PR Code Viewer komponenti
from ui.components.pr_code_viewer import render_code_changes_tab

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HISTORY_KEY = 'tz_pr_history'
PROGRESS_STEPS = 4

COMPLIANCE_COLORS = {
    'high': '#2ea043',    # Green (>=80%)
    'medium': '#d29922',  # Yellow (60-79%)
    'low': '#da3633'      # Red (<60%)
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN PAGE RENDERER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_tz_pr_checker():
    """TZ-PR Moslik Checker asosiy sahifasi"""

    # Header
    render_header(
        title="🔍 TZ-PR Moslik Tekshirish",
        subtitle="Task TZ va GitHub kod o'zgarishlarini solishtiring",
        version="v3"
    )

    # Info
    render_info("""
    📋 **Qanday ishlaydi:** JIRA task key → TZ olish → PR olish → AI tahlil
    """)

    # Input section
    task_key = _render_input_section()

    # History
    history = HistoryManager(HISTORY_KEY)
    history.render(
        max_display=5,
        on_rerun=lambda item: _run_analysis(item['key'])
    )


def _render_input_section() -> Optional[str]:
    """Input va tugma qismini render qilish"""
    col1, col2 = st.columns([3, 1])

    with col1:
        task_key = st.text_input(
            "🔑 Task Key",
            placeholder="DEV-1234"
        ).strip().upper()

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_button = st.button(
            "🔍 Tekshirish",
            use_container_width=True,
            type="primary"
        )

    # Analysis trigger
    if analyze_button:
        if not task_key:
            render_error("Task key kiriting!")
            return None
        _run_analysis(task_key)

    return task_key


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ANALYSIS ORCHESTRATOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _run_analysis(task_key: str):
    """Tahlil jarayonini boshlash va boshqarish"""

    # Settings
    settings = _get_analysis_settings()
    _display_settings_info(settings)

    # Containers
    progress_container = st.container()
    result_container = st.container()

    # Progress Manager
    with progress_container:
        progress = ProgressManager(total_steps=PROGRESS_STEPS)

    try:
        # Service import
        from services.tz_pr_service import TZPRService
        service = TZPRService()

        # Status callback
        status_callback = _create_status_callback(progress)

        # Run analysis
        progress.update(1, "📋 JIRA dan ma'lumot olinmoqda...")

        result = service.analyze_task(
            task_key=task_key,
            max_files=settings['max_files'],
            show_full_diff=settings['show_full_diff'],
            use_smart_patch=settings['use_smart_patch'],
            status_callback=status_callback
        )

        # Clear progress
        progress.clear()

        # Display results
        with result_container:
            if result.success:
                _display_success_result(result, settings)
            else:
                _display_error_result(result)

            # Save to history
            _save_to_history(task_key, result.success)

    except Exception as e:
        progress.error(f"❌ Xatolik: {str(e)}")
        _display_debug_info(e)


def _get_analysis_settings() -> Dict:
    """Tahlil sozlamalarini olish (v4.0 - app_settings'dan)"""
    from config.app_settings import get_app_settings
    app_settings = get_app_settings()

    return {
        'max_files': None,  # No limit by default
        'show_full_diff': True,  # Always show full diff
        'use_smart_patch': True  # Always use smart patch
    }


def _display_settings_info(settings: Dict):
    """Sozlamalar haqida ma'lumot ko'rsatish"""
    parts = []

    if settings['max_files']:
        parts.append(f"Max {settings['max_files']} fayl")

    parts.append("To'liq diff" if settings['show_full_diff'] else "Qisqa diff")

    if settings['use_smart_patch']:
        parts.append("🧠 Smart Patch")

    if parts:
        st.caption(f"⚙️ {' | '.join(parts)}")


def _create_status_callback(progress: ProgressManager) -> Callable:
    """Status callback funksiyasini yaratish"""

    def callback(status_type: str, message: str):
        if status_type == "progress":
            step = _detect_progress_step(message)
            progress.update(step, message)
        elif status_type == "error":
            progress.error(message)

    return callback


def _detect_progress_step(message: str) -> int:
    """Message'dan progress step'ni aniqlash"""
    if "TZ olinmoqda" in message:
        return 1
    elif "PR" in message and "qidiril" in message:
        return 2
    elif "PR" in message and "tahlil" in message:
        return 2
    elif "AI tahlil" in message:
        return 3
    return 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RESULT DISPLAY SECTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _display_success_result(result, settings: Dict):
    """Muvaffaqiyatli natijani ko'rsatish"""

    # PR Info Card
    render_pr_info_card(
        result,
        settings['use_smart_patch'],
        settings['max_files']
    )

    st.markdown("---")

    # 2 Tabs
    tab1, tab2 = st.tabs([
        "🤖 AI Tahlil Natijalari",
        "💻 GitHub Kod O'zgarishlari"
    ])

    with tab1:
        _render_ai_analysis_tab(result)

    with tab2:
        # ✅ DRY FIX: Umumiy komponent ishlatamiz
        render_code_changes_tab(
            pr_details=result.pr_details,
            use_smart_patch=settings['use_smart_patch']
        )


def _display_error_result(result):
    """Xatolik natijasini ko'rsatish"""
    render_error(
        message=result.error_message,
        details="\n".join(result.warnings) if result.warnings else None
    )

    if result.tz_content:
        with st.expander("📋 TZ (olingan ma'lumot)"):
            st.text_area(
                "TZ",
                result.tz_content,
                height=200,
                key="tz_error",
                label_visibility="collapsed"
            )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 1: AI ANALYSIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _render_ai_analysis_tab(result):
    """TAB 1: AI Tahlil natijalari"""

    # Compliance Score Section
    _render_compliance_score(result)

    st.markdown("---")

    # AI Analysis
    st.markdown("### 🤖 Gemini AI Tahlili")
    st.markdown(result.ai_analysis)

    # Warnings
    if result.warnings:
        _render_warnings(result.warnings)

    # Technical Details
    _render_technical_details(result)


def _render_compliance_score(result):
    """Moslik bali qismini render qilish"""
    color = _get_compliance_color(result.compliance_score)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 🎯 Moslik Bali")
        st.markdown(
            f"""<div style="font-size: 3rem; font-weight: bold; color: {color};">
                {result.compliance_score}%
            </div>""",
            unsafe_allow_html=True
        )

    with col2:
        st.markdown("### 📊 Statistika")
        st.write(f"**Task:** {result.task_key}")
        st.write(f"**PR:** {result.pr_count} ta")
        st.write(f"**Files:** {result.files_changed} ta")


def _render_warnings(warnings: List[str]):
    """Ogohlantirishlarni ko'rsatish"""
    st.markdown("---")
    st.markdown("### ⚠️ Ogohlantirishlar")
    for warning in warnings:
        st.warning(warning)


def _render_technical_details(result):
    """Texnik ma'lumotlarni ko'rsatish"""
    with st.expander("📊 Texnik Ma'lumotlar"):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("AI Retry", result.ai_retry_count)
        with col2:
            st.metric("Fayllar tahlil", result.files_analyzed)
        with col3:
            st.metric("Prompt size", f"{result.total_prompt_size:,}")

        st.markdown("---")
        st.markdown("### 📋 TZ Content")
        st.text_area(
            "TZ Matni",
            result.tz_content,
            height=300,
            key="tz_in_tab1",
            label_visibility="collapsed"
        )

        # BARCHA comment'larni ko'rsatish (v5.2 - FIXED)
        comments = []
        if result.comment_analysis:
            comments = result.comment_analysis.get('comments', [])

        if comments:
            st.markdown("---")
            st.markdown(f"### 💬 JIRA Comment'lar ({len(comments)} ta)")

            for i, comment in enumerate(comments, 1):
                author = comment.get('author', 'Unknown')
                created = comment.get('created', '')
                body = comment.get('body', '').strip()

                with st.expander(f"[#{i}] {author} - {created}", expanded=False):
                    st.markdown(body)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPER FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _get_compliance_color(score: int) -> str:
    """Compliance score'ga ko'ra rang"""
    if score is None:
        return COMPLIANCE_COLORS['low']
    if score >= 80:
        return COMPLIANCE_COLORS['high']
    elif score >= 60:
        return COMPLIANCE_COLORS['medium']
    else:
        return COMPLIANCE_COLORS['low']


def _save_to_history(task_key: str, success: bool):
    """Tarixga saqlash"""
    history = HistoryManager(HISTORY_KEY)
    history.add({
        'key': task_key,
        'success': success,
        'time': datetime.now().strftime('%Y-%m-%d %H:%M')
    })


def _display_debug_info(error: Exception):
    """Debug ma'lumotlarini ko'rsatish"""
    import traceback
    with st.expander("🔧 Debug Info"):
        st.code(traceback.format_exc())