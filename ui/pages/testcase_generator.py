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


# ============================================================================
# CACHE HELPERS (v5.2)
# ============================================================================

def _init_cache():
    """Initialize task history cache in session state"""
    if 'task_history' not in st.session_state:
        st.session_state.task_history = []
    if 'current_task' not in st.session_state:
        st.session_state.current_task = None


def _add_to_cache(task_key: str, result, params: dict = None):
    """Add task result to cache (max 3 tasks) with generation parameters"""
    _init_cache()

    # Remove existing entry for this task (avoid duplicates)
    st.session_state.task_history = [
        item for item in st.session_state.task_history
        if item['task_key'] != task_key
    ]

    # Add new entry
    st.session_state.task_history.append({
        'task_key': task_key,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'result': result,
        'params': params or {}  # Store generation parameters
    })

    # Keep only last 3 tasks
    if len(st.session_state.task_history) > 3:
        st.session_state.task_history = st.session_state.task_history[-3:]

    # Set as current task
    st.session_state.current_task = task_key


def _get_from_cache(task_key: str):
    """Get task result from cache (returns full cache item with params)"""
    _init_cache()

    for item in st.session_state.task_history:
        if item['task_key'] == task_key:
            return item  # Returns full item (result + params)

    return None


def _get_cached_tasks():
    """Get list of cached task keys"""
    _init_cache()
    return [item['task_key'] for item in st.session_state.task_history]


# ============================================================================
# MAIN PAGE
# ============================================================================

def render_testcase_generator():
    """Test Case Generator sahifasi - WITH CUSTOM INPUT"""

    # Header
    render_header(
        title="🧪 Test Case Generator",
        subtitle="TZ, Comments va PR asosida QA test case'lar",
        version="v5.1 DRY FIXED"
    )

    # Info
    render_info("📋 Task key kiriting → AI test case'lar yaratadi | ⚙️ Settings: Sidebar'dan")

    # ═══════════════════════════════════════════════════════════════
    # CACHE SELECTOR (v5.3 - tuzatilgan)
    # ═══════════════════════════════════════════════════════════════

    _init_cache()
    cached_tasks = _get_cached_tasks()
    current = st.session_state.get('current_task')

    if cached_tasks:
        st.info(f"📦 Keshda: {', '.join(cached_tasks)}")

        # current_task keshda bo'lsa — default sifatida tanlash
        default_idx = 0
        if current and current in cached_tasks:
            default_idx = cached_tasks.index(current) + 1  # +1 chunki '' birinchi element

        col1, col2 = st.columns([3, 1])
        with col1:
            selected_cached = st.selectbox(
                "Keshdan yuklash:",
                options=[''] + cached_tasks,
                index=default_idx,
                key="cache_selector",
                help="Oldingi natijani tanlang"
            )
        with col2:
            if st.button("🗑️ Keshni tozalash", help="Barcha kesh ma'lumotlarini o'chirish"):
                st.session_state.task_history = []
                st.session_state.current_task = None
                st.rerun()

        # Keshdan yuklash
        if selected_cached:
            cached_item = _get_from_cache(selected_cached)
            if cached_item:
                st.session_state.current_task = selected_cached

                result = cached_item['result']
                params = cached_item.get('params', {})

                _display_results(
                    result,
                    include_pr=params.get('include_pr', False),
                    use_smart_patch=params.get('use_smart_patch', False),
                    test_types=params.get('test_types', ['positive']),
                    custom_context=params.get('custom_context', '')
                )
                return

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
        # Get settings from app_settings (v4.0)
        from config.app_settings import get_app_settings
        app_settings = get_app_settings()

        include_pr = app_settings.testcase_generator.default_include_pr
        use_smart_patch = app_settings.testcase_generator.default_use_smart_patch
        test_types = app_settings.testcase_generator.default_test_types

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
        progress = ProgressManager(
            total_steps=4,
            step_labels=["Task tahlili", "TZ & PR olish", "AI generate", "Natija"],
        )

    # Status callback
    def status_callback(stype: str, msg: str):
        if stype != "progress":
            return
        m = msg.lower()
        if "jira" in m or "olinmoqda" in m:
            progress.update(1, msg)
        elif "tz" in m or "comment" in m or "pr" in m or "github" in m:
            progress.update(2, msg)
        elif "ai" in m or "gemini" in m or "yaratmoqda" in m:
            progress.update(3, msg)
        elif "tayyorlan" in m or "yaratildi" in m:
            progress.update(4, msg)

    try:
        from services.generators.testcase_generator import TestCaseGeneratorService
        from utils.auth.auth_manager import get_auth_info
        _auth = get_auth_info()
        _user_id    = _auth.get('user_id')    if _auth.get('role') == 'user' else None
        _company_id = _auth.get('company_id') if _auth.get('role') == 'user' else None
        # UI modul: user_id → user_credentials; company_id faqat settings uchun
        svc = TestCaseGeneratorService(user_id=_user_id, company_id=_company_id)

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

        # Save to cache va sahifani qayta yuklash (v5.3)
        if result.success:
            _add_to_cache(task_key, result, params={
                'include_pr': include_pr,
                'use_smart_patch': use_smart_patch,
                'test_types': test_types,
                'custom_context': custom_context
            })
            # Keshga yozildi — sahifani rerun qilish
            # Shunda kesh selectboxda barcha tasklar ko'rinadi
            # va current_task avtomatik tanlanadi
            st.rerun()

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
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Task Overview",
        "🧪 Test Cases",
        "💻 Kod O'zgarishlari",
        "📋 Texnik Spetsifikatsiya",
        "📥 Eksport"
    ])

    with tab1:
        _render_overview(result, include_pr, use_smart_patch, test_types, custom_context)

    with tab2:
        _render_test_scenarios(result)

    with tab3:
        render_code_changes_tab(result.pr_details, use_smart_patch)

    with tab4:
        _render_technical_spec(result)

    with tab5:
        _render_export(result)


def _render_overview(
        result,
        include_pr: bool,
        use_smart_patch: bool,
        test_types: list,
        custom_context: str = ""
):
    """Task Overview - yaxshilangan dizayn"""

    details = result.task_full_details or {}

    # ── A) Header Card ──
    task_type = details.get('type', '')
    type_badge = f'<span style="background: rgba(255,255,255,0.25); padding: 2px 10px; border-radius: 12px; font-size: 0.8rem;">{task_type}</span>' if task_type else ''

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 1.5rem; border-radius: 12px; margin-bottom: 1rem;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <h2 style="color: white; margin: 0;">{result.task_key}</h2>
            {type_badge}
        </div>
        <p style="color: #e0e0e0; margin: 0.5rem 0 0 0; font-size: 1.05rem;">{result.task_summary}</p>
    </div>
    """, unsafe_allow_html=True)

    # ── B) Task Ma'lumotlari ──
    status = details.get('status', '')
    priority = details.get('priority', '')
    assignee = details.get('assignee', '')
    reporter = details.get('reporter', '')
    created = details.get('created', '')
    story_points = details.get('story_points', '')

    has_info = any([status, priority, assignee, reporter, created])

    if has_info:
        col1, col2, col3 = st.columns(3)
        with col1:
            if status:
                st.markdown(f"""
                <div style="background: rgba(88, 166, 255, 0.08); padding: 0.6rem 0.8rem;
                            border-radius: 8px; border-left: 3px solid #58a6ff;">
                    <div style="font-size: 0.75rem; color: #888;">Status</div>
                    <div style="font-weight: 600;">{status}</div>
                </div>
                """, unsafe_allow_html=True)
        with col2:
            if priority:
                st.markdown(f"""
                <div style="background: rgba(88, 166, 255, 0.08); padding: 0.6rem 0.8rem;
                            border-radius: 8px; border-left: 3px solid #f0883e;">
                    <div style="font-size: 0.75rem; color: #888;">Priority</div>
                    <div style="font-weight: 600;">{priority}</div>
                </div>
                """, unsafe_allow_html=True)
        with col3:
            if assignee:
                st.markdown(f"""
                <div style="background: rgba(88, 166, 255, 0.08); padding: 0.6rem 0.8rem;
                            border-radius: 8px; border-left: 3px solid #3fb950;">
                    <div style="font-size: 0.75rem; color: #888;">Assignee</div>
                    <div style="font-weight: 600;">{assignee}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='height: 0.5rem'></div>", unsafe_allow_html=True)

        col4, col5, col6 = st.columns(3)
        with col4:
            if reporter:
                st.markdown(f"""
                <div style="background: rgba(88, 166, 255, 0.08); padding: 0.6rem 0.8rem;
                            border-radius: 8px; border-left: 3px solid #bc8cff;">
                    <div style="font-size: 0.75rem; color: #888;">Reporter</div>
                    <div style="font-weight: 600;">{reporter}</div>
                </div>
                """, unsafe_allow_html=True)
        with col5:
            if created:
                st.markdown(f"""
                <div style="background: rgba(88, 166, 255, 0.08); padding: 0.6rem 0.8rem;
                            border-radius: 8px; border-left: 3px solid #8b949e;">
                    <div style="font-size: 0.75rem; color: #888;">Yaratilgan</div>
                    <div style="font-weight: 600;">{created}</div>
                </div>
                """, unsafe_allow_html=True)
        with col6:
            if story_points:
                st.markdown(f"""
                <div style="background: rgba(88, 166, 255, 0.08); padding: 0.6rem 0.8rem;
                            border-radius: 8px; border-left: 3px solid #d29922;">
                    <div style="font-size: 0.75rem; color: #888;">Story Points</div>
                    <div style="font-weight: 600;">{story_points}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

    # ── C) Generation Settings ──
    settings_parts = []
    if include_pr:
        settings_parts.append("🔎 PR hisobga olindi")
    if use_smart_patch:
        settings_parts.append("🧠 Smart Patch")
    settings_parts.append(f"🎯 Test turlari: {', '.join(test_types)}")
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

    # ── D) Comment'lar ──
    if result.comment_changes_detected:
        st.warning(f"⚠️ {result.comment_summary}")

    if details.get('comments'):
        all_comments = details['comments']

        # Settingdagi comment limitni inobatga olish
        from config.app_settings import get_app_settings
        max_c = get_app_settings().testcase_generator.max_comments_to_read
        if max_c and max_c > 0:
            comments = all_comments[-max_c:]
        else:
            comments = all_comments

        st.markdown(f"#### 💬 JIRA Comment'lar ({len(comments)} / {len(all_comments)} ta)")

        # Oxirgi commentlar yuqorida
        for i, comment in enumerate(reversed(comments), 1):
            author = comment.get('author', 'Noma\'lum')
            created = comment.get('created', '')
            body = comment.get('body', '').strip()

            # Author bosh harfi
            initial = author[0].upper() if author else '?'

            st.markdown(f"""
            <div style="background: rgba(88, 166, 255, 0.05); padding: 0.8rem 1rem;
                        border-radius: 10px; margin-bottom: 0.5rem;
                        border: 1px solid rgba(88, 166, 255, 0.15);">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.4rem;">
                    <div style="width: 32px; height: 32px; border-radius: 50%;
                                background: linear-gradient(135deg, #667eea, #764ba2);
                                display: flex; align-items: center; justify-content: center;
                                color: white; font-weight: bold; font-size: 0.85rem;">{initial}</div>
                    <div>
                        <span style="font-weight: 600;">{author}</span>
                        <span style="color: #888; font-size: 0.8rem; margin-left: 8px;">{created}</span>
                    </div>
                </div>
                <div style="padding-left: 42px; font-size: 0.9rem; line-height: 1.5;">
                    {body[:500]}{'...' if len(body) > 500 else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)


@st.fragment
def _render_test_scenarios(result):
    """Test Cases (v5.3 - @st.fragment bilan filter sahifani qayta yuklamaydi)"""
    st.markdown("### 🧪 Test Cases")

    if not result.test_cases:
        st.info("Test case'lar topilmadi")
        return

    # Filter by type (fragment ichida - faqat shu qism rerun bo'ladi)
    test_type = st.selectbox(
        "Test turi bo'yicha filterlash",
        options=['Barchasi'] + list(result.by_type.keys()),
        key="scenarios_filter_select",
        label_visibility="visible",
        help="Test case'larni turi bo'yicha filterlang"
    )

    # Filter test cases
    filtered_cases = result.test_cases
    if test_type != 'Barchasi':
        filtered_cases = [tc for tc in result.test_cases if tc.test_type == test_type]

    # Show filtered count
    st.caption(f"📊 {len(filtered_cases)} / {len(result.test_cases)} ta test case ko'rsatilmoqda")

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


@st.fragment
def _render_export(result):
    """Export - JSON, CSV (v5.3 - @st.fragment bilan filter sahifani qayta yuklamaydi)"""
    st.markdown("### 📥 Export Test Cases")

    import json
    import io
    import csv

    # Export tab filter (independent from Test Scenarios tab)
    export_filter = st.selectbox(
        "Filter for Export (JSON/CSV)",
        options=['All'] + list(result.by_type.keys()),
        key="export_filter_select",  # Unique key
        help="Filter test cases before exporting to JSON/CSV"
    )

    # Apply filter
    filtered_cases = result.test_cases
    if export_filter != 'All':
        filtered_cases = [tc for tc in result.test_cases if tc.test_type == export_filter]

    # Show count
    st.caption(f"📊 {len(filtered_cases)} test case(s) will be exported")

    # 2 ta ustun: JSON, CSV
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📄 JSON")
        # JSON Export - uses FILTERED cases
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
            for tc in filtered_cases
        ]

        json_str = json.dumps(test_cases_json, indent=2, ensure_ascii=False)

        st.download_button(
            label="📥 JSON yuklab olish",
            data=json_str,
            file_name=f"{result.task_key}_test_cases.json",
            mime="application/json",
            use_container_width=True
        )

    with col2:
        st.markdown("#### 📊 CSV")
        # CSV Export - uses FILTERED cases
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Title', 'Type', 'Priority', 'Severity', 'Steps Count'])

        for tc in filtered_cases:
            writer.writerow([tc.id, tc.title, tc.test_type, tc.priority, tc.severity, len(tc.steps)])

        st.download_button(
            label="📥 CSV yuklab olish",
            data=output.getvalue(),
            file_name=f"{result.task_key}_test_cases.csv",
            mime="text/csv",
            use_container_width=True
        )


