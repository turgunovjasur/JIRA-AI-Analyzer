# ui/pages/testcase_generator.py - WITH CUSTOM INPUT (DRY FIXED)
"""
Test Case Generator - REFACTORED with Smart Patch & Custom Input

YANGILIKLAR:
- ✅ UI komponentlar ishlatadi
- ✅ HistoryManager ishlatadi
- ✅ ProgressManager ishlatadi
- ✅ Smart Patch Support qo'shildi
- ✅ Custom Input (AI ga qo'shimcha buyruq)
- ✅ DRY Fixed - pr_code_viewer komponenti ishlatadi

Author: JASUR TURGUNOV
Version: 5.1 DRY FIXED
"""
import streamlit as st
from datetime import datetime
from typing import Optional

# UI Components
from ui.components import (
    render_header,
    render_info,
    ProgressManager,
    HistoryManager,
    render_error,
    render_success,
    render_metrics_grid
)

# ✅ DRY FIX: Umumiy PR viewer komponenti
from ui.components.pr_code_viewer import render_code_changes_tab


def render_testcase_generator():
    """Test Case Generator sahifasi - WITH CUSTOM INPUT"""

    # Header
    render_header(
        title="🧪 Test Case Generator",
        subtitle="TZ, Comments va PR asosida O'zbek tilida QA test case'lar",
        version="v5.1 DRY FIXED"
    )

    # Info
    render_info("""
    📋 **Jarayon:** 
    1. Task key kiriting → 2. TZ va Comments olinadi → 3. PR qidiriladi → 4. AI O'zbek tilida test case'lar yaratadi

    🆕 **YANGI:** Custom Input - AI ga qo'shimcha buyruq bering (product nomi, narxlar, maxsus talablar)

    ⚙️ **Settings:** Sidebar'dan (PR hisobga olish, Smart Patch, Test type'lar)
    """)

    # ═══════════════════════════════════════════════════════════════
    # INPUT SECTION
    # ═══════════════════════════════════════════════════════════════

    # Task Key Input
    col1, col2 = st.columns([3, 1])

    with col1:
        task_key = st.text_input(
            "🔑 Task Key",
            placeholder="DEV-1234",
            help="JIRA task key kiriting"
        ).strip().upper()

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        btn = st.button("🧪 Generate", use_container_width=True, type="primary")

    # ═══════════════════════════════════════════════════════════════
    # CUSTOM INPUT SECTION (Collapsible)
    # ═══════════════════════════════════════════════════════════════

    custom_context = _render_custom_input_section()

    # ═══════════════════════════════════════════════════════════════
    # GENERATION
    # ═══════════════════════════════════════════════════════════════

    if btn and task_key:
        include_pr = st.session_state.get('include_pr', True)
        use_smart_patch = st.session_state.get('use_smart_patch', True)
        test_types = st.session_state.get('test_types', ['positive', 'negative'])

        _run_generation(
            task_key=task_key,
            include_pr=include_pr,
            use_smart_patch=use_smart_patch,
            test_types=test_types,
            custom_context=custom_context
        )
    elif btn:
        render_error("Task key kiriting!")

    # ═══════════════════════════════════════════════════════════════
    # HISTORY
    # ═══════════════════════════════════════════════════════════════

    history = HistoryManager('testcase_history')
    history.render(
        max_display=5,
        on_rerun=lambda item: _run_generation(
            item['key'],
            item.get('include_pr', True),
            item.get('use_smart_patch', True),
            item.get('test_types', ['positive']),
            item.get('custom_context', '')
        )
    )


def _render_custom_input_section() -> str:
    """
    Custom Input section - AI ga qo'shimcha buyruq

    Returns:
        str: Custom context text (bo'sh bo'lishi mumkin)
    """
    with st.expander("💬 AI ga Qo'shimcha Buyruq (Optional)", expanded=False):
        st.markdown("""
        <div style="background: rgba(88, 166, 255, 0.1); padding: 0.75rem; 
                    border-radius: 8px; margin-bottom: 1rem; font-size: 0.85rem;">
            <strong>💡 Maslahat:</strong> Bu yerda AI ga qo'shimcha ma'lumot bering:
            <ul style="margin: 0.5rem 0 0 0; padding-left: 1.2rem;">
                <li>Product/Mahsulot nomlari</li>
                <li>Test ma'lumotlari (narxlar, miqdorlar)</li>
                <li>Maxsus test talablari</li>
                <li>E'tibor qaratish kerak bo'lgan joylar</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        # Custom context input
        custom_context = st.text_area(
            "AI ga buyruq",
            placeholder="""Misol:
• Product nomi: "Olma" narxi: 15000 so'm
• Minimal buyurtma: 1 kg, Maksimal: 100 kg
• Chegirma: 10 kg dan ortiq xaridda 5%
• To'lov: Naqd, Karta, Click
• E'tibor: Chegirma hisoblashni alohida test qiling""",
            height=150,
            help="AI bu ma'lumotlarni test case yaratishda hisobga oladi",
            label_visibility="collapsed"
        )

        # Quick templates
        st.markdown("**🚀 Tezkor shablonlar:**")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🛒 E-commerce", use_container_width=True, key="tmpl_ecom"):
                st.session_state['custom_template'] = """• Product: [MAHSULOT_NOMI]
• Narx: [NARX] so'm
• Minimal: 1 dona, Maksimal: 999 dona
• Chegirma: 5 donadan ortiq - 10%
• To'lov: Naqd, Karta, Click, Payme"""

        with col2:
            if st.button("📝 Form/Input", use_container_width=True, key="tmpl_form"):
                st.session_state['custom_template'] = """• Field'lar: Ism, Telefon, Email
• Telefon format: +998 XX XXX-XX-XX
• Email: @gmail.com, @mail.ru
• Required: Barcha fieldlar majburiy
• Validation xatolarini test qiling"""

        with col3:
            if st.button("🔐 Auth/Login", use_container_width=True, key="tmpl_auth"):
                st.session_state['custom_template'] = """• Login: Email yoki Telefon
• Parol: Minimal 8 ta belgi
• OTP: 6 ta raqam, 60 sek timeout
• Blocked: 5 ta noto'g'ri urinishdan keyin
• "Parolni unutdim" funksiyasi"""

        # Apply template if selected
        if 'custom_template' in st.session_state and st.session_state['custom_template']:
            if not custom_context:  # Faqat bo'sh bo'lsa
                custom_context = st.session_state['custom_template']
            st.session_state['custom_template'] = ''  # Clear
            st.rerun()

    return custom_context.strip()


def _run_generation(
        task_key: str,
        include_pr: bool,
        use_smart_patch: bool,
        test_types: list,
        custom_context: str = ""
):
    """Test case generatsiya - WITH CUSTOM CONTEXT"""

    # Containers
    prog_cont = st.container()
    res_cont = st.container()

    # Progress Manager
    with prog_cont:
        progress = ProgressManager(total_steps=4)

    # Status callback
    def status_callback(stype: str, msg: str):
        if "tahlil qilinmoqda" in msg:
            progress.update(1, msg)
        elif "TZ" in msg:
            progress.update(2, msg)
        elif "PR" in msg:
            progress.update(2, msg)
        elif "AI" in msg:
            progress.update(3, msg)
        elif "yaratildi" in msg:
            progress.update(4, msg)

    try:
        from services.testcase_generator_service import TestCaseGeneratorService

        # Service
        svc = TestCaseGeneratorService()

        # Generate
        progress.update(1, "🔍 Task tahlil qilinmoqda...")

        # Custom context info
        if custom_context:
            progress.update(1, "📝 Custom context qo'shilmoqda...")

        result = svc.generate_test_cases(
            task_key=task_key,
            include_pr=include_pr,
            use_smart_patch=use_smart_patch,
            test_types=test_types,
            custom_context=custom_context,
            status_callback=status_callback
        )

        # Clear progress
        progress.clear()
        prog_cont.empty()

        # Display results
        with res_cont:
            _display_results(result, include_pr, use_smart_patch, test_types, custom_context)

        # Save to history
        history = HistoryManager('testcase_history')
        history.add({
            'key': task_key,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'success': result.success,
            'include_pr': include_pr,
            'use_smart_patch': use_smart_patch,
            'test_types': test_types,
            'custom_context': custom_context[:100] if custom_context else ''
        })

    except Exception as e:
        progress.error(f"❌ Xatolik: {str(e)}")
        with st.expander("🔧 Debug"):
            import traceback
            st.code(traceback.format_exc())


def _display_results(
        result,
        include_pr: bool,
        use_smart_patch: bool,
        test_types: list,
        custom_context: str = ""
):
    """Natijalarni ko'rsatish"""

    if not result.success:
        render_error(result.error_message)
        if result.warnings:
            for w in result.warnings:
                st.warning(f"• {w}")
        return

    render_success(f"{result.task_key} uchun {result.total_test_cases} ta test case yaratildi!")

    # Metrics
    metrics = [
        {'value': str(result.total_test_cases), 'label': 'Test Cases', 'icon': '📋', 'color': 'success'},
        {'value': str(result.pr_count), 'label': 'PR', 'icon': '🔗'},
        {'value': str(result.files_changed), 'label': 'Files', 'icon': '📂'},
        {'value': str(result.by_priority.get('High', 0)), 'label': 'High Priority', 'icon': '⚠️', 'color': 'warning'}
    ]
    render_metrics_grid(metrics)

    st.markdown("---")

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Task Overview",
        "🧪 Test Scenarios",
        "💻 Code Changes",
        "📈 Statistics",
        "📋 Technical Specification",
        "📥 Export"
    ])

    with tab1:
        _render_overview(result, include_pr, use_smart_patch, test_types, custom_context)

    with tab2:
        _render_test_scenarios(result)

    with tab3:
        # ✅ DRY FIX: Umumiy komponent ishlatamiz
        render_code_changes_tab(result.pr_details, use_smart_patch)

    with tab4:
        _render_statistics(result)

    with tab5:
        _render_technical_spec(result)

    with tab6:
        _render_export(result)


def _render_overview(
        result,
        include_pr: bool,
        use_smart_patch: bool,
        test_types: list,
        custom_context: str = ""
):
    """Task Overview"""
    st.markdown("### 📊 Task Overview")

    # Header card
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 1.5rem; border-radius: 12px; margin-bottom: 1rem;">
        <h2 style="color: white; margin: 0;">{result.task_key}</h2>
        <p style="color: #e0e0e0; margin: 0.5rem 0 0 0;">{result.task_summary}</p>
    </div>
    """, unsafe_allow_html=True)

    # Settings info
    settings_parts = []
    if include_pr:
        settings_parts.append("🔎 PR hisobga olindi")
    if use_smart_patch:
        settings_parts.append("🧠 Smart Patch")
    settings_parts.append(f"🎯 Test types: {', '.join(test_types)}")
    if custom_context:
        settings_parts.append("💬 Custom Input")

    if settings_parts:
        st.info(" | ".join(settings_parts))

    # Custom Context Display
    if custom_context:
        with st.expander("💬 Qo'shimcha Buyruq (Custom Input)", expanded=False):
            st.markdown(f"""
            <div style="background: rgba(88, 166, 255, 0.1); padding: 1rem; 
                        border-radius: 8px; white-space: pre-wrap;">
{custom_context}
            </div>
            """, unsafe_allow_html=True)

    # Overview content
    st.markdown(result.task_overview)

    # Comment Analysis
    if result.comment_changes_detected:
        st.warning(f"⚠️ {result.comment_summary}")

        if result.comment_details:
            with st.expander("🔍 Muhim Comment'lar"):
                for comment in result.comment_details:
                    st.markdown(f"• {comment}")


def _render_test_scenarios(result):
    """Test Scenarios"""
    st.markdown("### 🧪 Test Scenarios")

    if not result.test_cases:
        st.info("Test case'lar topilmadi")
        return

    # Filter by type
    test_type = st.selectbox(
        "Test Type",
        options=['All'] + list(result.by_type.keys()),
        label_visibility="visible"
    )

    # Filter test cases
    filtered_cases = result.test_cases
    if test_type != 'All':
        filtered_cases = [tc for tc in result.test_cases if tc.test_type == test_type]

    # Display test cases
    for tc in filtered_cases:
        with st.expander(f"{tc.id}: {tc.title} [{tc.priority}]"):
            st.markdown(f"**🔍 Description:** {tc.description}")
            st.markdown(f"**🔧 Preconditions:** {tc.preconditions}")

            st.markdown("**📋 Steps:**")
            for step in tc.steps:
                st.markdown(f"• {step}")

            st.markdown(f"**✅ Expected Result:** {tc.expected_result}")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Type:** `{tc.test_type}`")
            with col2:
                st.markdown(f"**Priority:** `{tc.priority}`")
            with col3:
                st.markdown(f"**Severity:** `{tc.severity}`")


def _render_statistics(result):
    """Statistics"""
    st.markdown("### 📈 Statistics")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### By Type")
        for test_type, count in result.by_type.items():
            percentage = (count / result.total_test_cases * 100) if result.total_test_cases > 0 else 0
            st.markdown(f"• **{test_type}:** {count} ({percentage:.1f}%)")

    with col2:
        st.markdown("#### By Priority")
        for priority, count in result.by_priority.items():
            percentage = (count / result.total_test_cases * 100) if result.total_test_cases > 0 else 0
            st.markdown(f"• **{priority}:** {count} ({percentage:.1f}%)")


def _render_technical_spec(result):
    """Technical Specification"""
    st.markdown("### 📋 Technical Specification")

    st.markdown("#### TZ Content")
    st.text_area(
        "TZ Content",
        result.tz_content,
        height=400,
        key="tz_view",
        label_visibility="collapsed"
    )


def _render_export(result):
    """Export"""
    st.markdown("### 📥 Export Test Cases")

    import json
    import io
    import csv

    # JSON Export
    test_cases_json = [
        {
            'id': tc.id,
            'title': tc.title,
            'description': tc.description,
            'preconditions': tc.preconditions,
            'steps': tc.steps,
            'expected_result': tc.expected_result,
            'test_type': tc.test_type,
            'priority': tc.priority,
            'severity': tc.severity,
            'tags': tc.tags
        }
        for tc in result.test_cases
    ]

    json_str = json.dumps(test_cases_json, indent=2, ensure_ascii=False)

    st.download_button(
        label="📥 Download JSON",
        data=json_str,
        file_name=f"{result.task_key}_test_cases.json",
        mime="application/json"
    )

    # CSV Export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Title', 'Type', 'Priority', 'Severity', 'Steps Count'])

    for tc in result.test_cases:
        writer.writerow([tc.id, tc.title, tc.test_type, tc.priority, tc.severity, len(tc.steps)])

    st.download_button(
        label="📥 Download CSV",
        data=output.getvalue(),
        file_name=f"{result.task_key}_test_cases.csv",
        mime="text/csv"
    )