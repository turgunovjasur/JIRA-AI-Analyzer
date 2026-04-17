# ui/pages/unified_settings.py
"""
Yagona Sozlamalar Sahifasi

Barcha modullar uchun yagona sozlamalar interfeysi:
- Modul ko'rinishi (yoqish/o'chirish)
- Bug Analyzer sozlamalari
- Statistics sozlamalari
- TZ-PR Checker sozlamalari
- Testcase Generator sozlamalari

Har bir sozlama yonida yordam matni ko'rsatiladi.

Author: JASUR TURGUNOV
Version: 1.0
"""
import streamlit as st
from dataclasses import replace
from utils.auth.auth_manager import is_company, get_auth_info

from config.app_settings import (
    AppSettings,
    ModuleVisibility,
    BugAnalyzerSettings,
    StatisticsSettings,
    TZPRCheckerSettings,
    TestcaseGeneratorSettings,
    QueueSettings,
    get_app_settings,
    save_app_settings,
)
from ui.components import render_header


def render_unified_settings():
    """Yagona Sozlamalar sahifasi"""

    render_header(
        title="Tizim Sozlamalari",
        subtitle="Barcha modullar uchun yagona sozlamalar",
        version="v1.0",
        icon="⚙️"
    )

    settings = get_app_settings()
    st.markdown("---")

    if 'settings_changed' not in st.session_state:
        st.session_state.settings_changed = False

    # Kompaniya uchun — faqat ruxsat berilgan modullar ko'rsatiladi
    if is_company():
        _render_company_settings(settings)
        return

    # Super admin uchun — barcha tablar
    tabs = st.tabs([
        "🔧 Modullar", "🐛 Bug Analyzer", "📊 Statistics",
        "🔍 TZ-PR Checker", "🧪 Test Case Generator", "⚙️ Tizim"
    ])

    with tabs[0]:
        modules = _render_module_visibility_settings(settings)
    with tabs[1]:
        bug_analyzer = _render_bug_analyzer_settings(settings)
    with tabs[2]:
        statistics = _render_statistics_settings(settings)
    with tabs[3]:
        tz_pr = _render_tz_pr_settings(settings)
    with tabs[4]:
        testcase = _render_testcase_settings(settings)
    with tabs[5]:
        system, allowed_issue_types_filter, excluded_assignees_filter, min_tz_chars_filter = _render_system_settings(settings)

    st.markdown("---")
    _render_save_buttons(
        settings, modules, bug_analyzer, statistics, tz_pr, testcase, system,
        allowed_issue_types_filter, excluded_assignees_filter, min_tz_chars_filter
    )


def _render_company_settings(settings):
    """
    Kompaniya uchun Settings sahifasi.
    Faqat 2 bo'lim: API Kalitlar + super admin tomonidan ochilgan modullar sozlamalari.
    "Modullar" tab yo'q — modullarni faqat super admin boshqaradi.
    """
    company_mods = st.session_state.get('company_modules', {})

    # Qaysi modul config tablari ko'rsatilsin
    # (faqat kompaniyaga ruxsat berilgan modullar)
    MODULE_TABS = [
        ('bug_analyzer',       '🐛 Bug Analyzer',        _render_bug_analyzer_settings),
        ('statistics',         '📊 Statistics',           _render_statistics_settings),
        ('tz_pr_checker',      '🔍 TZ-PR Checker',        _render_tz_pr_settings),
        ('testcase_generator', '🧪 Test Case Generator',  _render_testcase_settings),
    ]

    enabled_tabs = [(key, label, fn) for key, label, fn in MODULE_TABS
                    if company_mods.get(key, False)]

    # Tab ro'yxati: API Kalitlar + ochilgan modullar sozlamalari
    tab_labels = ["🔑 API Kalitlar"] + [label for _, label, _ in enabled_tabs]

    if not enabled_tabs:
        # Faqat API kalitlar tab
        with st.tabs(["🔑 API Kalitlar"])[0]:
            _render_api_keys_settings()
        return

    tabs = st.tabs(tab_labels)

    with tabs[0]:
        _render_api_keys_settings()

    # Ochilgan modul sozlamalari
    rendered = {}

    for i, (mod_key, _, render_fn) in enumerate(enabled_tabs):
        with tabs[i + 1]:
            rendered[mod_key] = render_fn(settings)

    st.markdown("---")

    # Saqlash (faqat ochilgan modullarning sozlamalari)
    _render_company_save_buttons(settings, rendered)


def _render_company_save_buttons(settings, rendered: dict):
    """Kompaniya uchun saqlash tugmasi — faqat ruxsat berilgan modullar sozlamalari saqlanadi"""
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("💾 Saqlash", type="primary", use_container_width=True):
            new_settings = AppSettings(
                modules=settings.modules,   # modullarni faqat super admin boshqaradi
                bug_analyzer=rendered.get('bug_analyzer', settings.bug_analyzer),
                statistics=rendered.get('statistics', settings.statistics),
                tz_pr_checker=rendered.get('tz_pr_checker', settings.tz_pr_checker),
                testcase_generator=rendered.get('testcase_generator', settings.testcase_generator),
                queue=settings.queue,
            )
            if save_app_settings(new_settings):
                _show_save_success_animation()
                st.balloons()
                st.session_state.show_settings = False
            else:
                st.error("❌ Saqlashda xato yuz berdi")
    with col2:
        if st.button("🔙 Ortga", use_container_width=True):
            st.session_state.show_settings = False
            st.rerun()


def _render_setting_with_help(
        label: str,
        value,
        help_text: str,
        setting_type: str,
        key: str,
        **kwargs
):
    """Sozlama va yordam matnini ko'rsatish"""

    # Yordam matnini info box ko'rinishida ko'rsatish
    if setting_type == "slider":
        result = st.slider(
            label,
            value=value,
            help=help_text,
            key=key,
            **kwargs
        )
    elif setting_type == "checkbox":
        result = st.checkbox(
            label,
            value=value,
            help=help_text,
            key=key
        )
    elif setting_type == "text":
        result = st.text_input(
            label,
            value=value,
            help=help_text,
            key=key,
            **kwargs
        )
    elif setting_type == "selectbox":
        options = kwargs.pop('options', [])
        index = options.index(value) if value in options else 0
        result = st.selectbox(
            label,
            options=options,
            index=index,
            help=help_text,
            key=key
        )
    elif setting_type == "multiselect":
        options = kwargs.pop('options', [])
        result = st.multiselect(
            label,
            options=options,
            default=value,
            help=help_text,
            key=key
        )
    else:
        result = value

    return result


def _render_api_keys_settings():
    """Kompaniya API kalitlari sozlamalari"""
    from utils.auth.auth_db import get_company_settings, save_company_settings
    from utils.auth.auth_manager import get_auth_info

    auth = get_auth_info()
    company_id = auth.get('company_id')
    if not company_id:
        st.error("Kompaniya ID topilmadi")
        return

    st.markdown("### 🔑 API Kalitlar")
    st.markdown("""
    <div style="background:rgba(88,166,255,0.08); padding:1rem; border-radius:8px; margin-bottom:1rem;">
        <p style="color:#8b949e; margin:0; font-size:0.85rem;">
            💡 Bu yerga siz foydalanayotgan servislarning API kalitlarini kiriting.
            Kalitlar xavfsiz tarzda saqlanadi va faqat sizning kompaniyangizga tegishli.
            Boshqa kompaniyalar bu ma'lumotlarni ko'ra olmaydi.
        </p>
    </div>
    """, unsafe_allow_html=True)

    cs = get_company_settings(company_id)

    # ━━━ JIRA ━━━
    st.markdown("#### 🔵 JIRA")
    col1, col2 = st.columns(2)
    with col1:
        jira_server = st.text_input(
            "JIRA Server URL",
            value=cs.get('jira_server', ''),
            placeholder="https://yourcompany.atlassian.net",
            key="cs_jira_server"
        )
        jira_email = st.text_input(
            "JIRA Email",
            value=cs.get('jira_email', ''),
            placeholder="admin@yourcompany.com",
            key="cs_jira_email"
        )
    with col2:
        jira_token = st.text_input(
            "JIRA API Token",
            value=cs.get('jira_token', ''),
            type="password",
            placeholder="ATATT3xFf...",
            key="cs_jira_token",
            help="Atlassian account → Security → API tokens"
        )

    st.markdown("---")

    # ━━━ GitHub ━━━
    st.markdown("#### 🐙 GitHub")
    col1, col2 = st.columns(2)
    with col1:
        github_token = st.text_input(
            "GitHub Token",
            value=cs.get('github_token', ''),
            type="password",
            placeholder="ghp_xxxx...",
            key="cs_github_token",
            help="GitHub → Settings → Developer settings → Personal access tokens"
        )
    with col2:
        github_org = st.text_input(
            "GitHub Organization",
            value=cs.get('github_org', ''),
            placeholder="your-org-name",
            key="cs_github_org"
        )

    st.markdown("---")

    # ━━━ Figma ━━━
    st.markdown("#### 🎨 Figma")
    figma_token = st.text_input(
        "Figma Access Token",
        value=cs.get('figma_token', ''),
        type="password",
        placeholder="figd_xxxx...",
        key="cs_figma_token",
        help="Figma → Account Settings → Personal Access Tokens"
    )

    st.markdown("---")

    # ━━━ Google Gemini ━━━
    st.markdown("#### 🤖 Google Gemini AI")
    col1, col2 = st.columns(2)
    with col1:
        gemini_key_1 = st.text_input(
            "Gemini API Key (asosiy)",
            value=cs.get('gemini_api_key_1', ''),
            type="password",
            placeholder="AIzaSy...",
            key="cs_gemini_1",
            help="Google AI Studio → Get API Key"
        )
    with col2:
        gemini_key_2 = st.text_input(
            "Gemini API Key (zaxira)",
            value=cs.get('gemini_api_key_2', ''),
            type="password",
            placeholder="AIzaSy...",
            key="cs_gemini_2",
            help="Ixtiyoriy: birinchi kalit limitga tushsa ishlatiladi"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("💾 API Kalitlarni Saqlash", type="primary"):
        new_settings = {
            'jira_server':      jira_server.strip(),
            'jira_email':       jira_email.strip(),
            'jira_token':       jira_token.strip(),
            'github_token':     github_token.strip(),
            'github_org':       github_org.strip(),
            'figma_token':      figma_token.strip(),
            'gemini_api_key_1': gemini_key_1.strip(),
            'gemini_api_key_2': gemini_key_2.strip(),
        }
        if save_company_settings(company_id, new_settings):
            st.success("✅ API kalitlar saqlandi! Sahifa qayta yuklanmoqda...")
            st.rerun()
        else:
            st.error("❌ Saqlashda xato yuz berdi")


def _render_module_visibility_settings(settings: AppSettings) -> ModuleVisibility:
    """Modul ko'rinishi sozlamalari"""

    st.markdown("### 📦 Modul Ko'rinishi")

    st.markdown("""
    <div style="background: rgba(88, 166, 255, 0.1); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
        <p style="color: #8b949e; margin: 0; font-size: 0.9rem;">
            💡 <strong>Eslatma:</strong> O'chirilgan modullar navbar'da ko'rinmaydi va ularning resurslari (embedding model, VectorDB va h.k.) yuklanmaydi.
            Bu tizim tezligini oshiradi va resurslarni tejaydi.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        bug_analyzer_enabled = _render_setting_with_help(
            "🐛 Bug Analyzer",
            settings.modules.bug_analyzer_enabled,
            settings.modules.bug_analyzer_help,
            "checkbox",
            "module_bug_analyzer"
        )

        statistics_enabled = _render_setting_with_help(
            "📊 Sprint Statistics",
            settings.modules.statistics_enabled,
            settings.modules.statistics_help,
            "checkbox",
            "module_statistics"
        )

    with col2:
        tz_pr_checker_enabled = _render_setting_with_help(
            "🔍 TZ-PR Checker",
            settings.modules.tz_pr_checker_enabled,
            settings.modules.tz_pr_checker_help,
            "checkbox",
            "module_tz_pr"
        )

        testcase_generator_enabled = _render_setting_with_help(
            "🧪 Test Case Generator",
            settings.modules.testcase_generator_enabled,
            settings.modules.testcase_generator_help,
            "checkbox",
            "module_testcase"
        )

    # Hech qaysi modul yoqilmagan bo'lsa ogohlantirish
    if not any([bug_analyzer_enabled, statistics_enabled, tz_pr_checker_enabled, testcase_generator_enabled]):
        st.error("⚠️ Kamida bitta modul yoqilgan bo'lishi kerak!")

    return ModuleVisibility(
        bug_analyzer_enabled=bug_analyzer_enabled,
        statistics_enabled=statistics_enabled,
        tz_pr_checker_enabled=tz_pr_checker_enabled,
        testcase_generator_enabled=testcase_generator_enabled
    )


def _render_bug_analyzer_settings(settings: AppSettings) -> BugAnalyzerSettings:
    """Bug Analyzer sozlamalari"""

    st.markdown("### 🐛 Bug Analyzer Sozlamalari")

    if not settings.modules.bug_analyzer_enabled:
        st.warning("⚠️ Bu modul hozirda o'chirilgan. Sozlamalarni o'zgartirish uchun avval modulni yoqing.")

    st.markdown("""
    <div style="background: rgba(88, 166, 255, 0.1); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
        <p style="color: #8b949e; margin: 0; font-size: 0.9rem;">
            🔍 Bug Analyzer - o'xshash buglarni topish va tahlil qilish uchun embedding model va VectorDB ishlatadi.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        default_top_n = _render_setting_with_help(
            "Default Top N",
            settings.bug_analyzer.default_top_n,
            settings.bug_analyzer.top_n_help,
            "slider",
            "ba_top_n",
            min_value=1,
            max_value=10,
            step=1
        )

    with col2:
        default_min_similarity = _render_setting_with_help(
            "Default Min Similarity (%)",
            settings.bug_analyzer.default_min_similarity,
            settings.bug_analyzer.min_similarity_help,
            "slider",
            "ba_min_similarity",
            min_value=50,
            max_value=95,
            step=5
        )

    return BugAnalyzerSettings(
        default_top_n=default_top_n,
        default_min_similarity=default_min_similarity
    )


def _render_statistics_settings(settings: AppSettings) -> StatisticsSettings:
    """Statistics sozlamalari"""

    st.markdown("### 📊 Statistics Sozlamalari")

    if not settings.modules.statistics_enabled:
        st.warning("⚠️ Bu modul hozirda o'chirilgan. Sozlamalarni o'zgartirish uchun avval modulni yoqing.")

    st.markdown("""
    <div style="background: rgba(88, 166, 255, 0.1); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
        <p style="color: #8b949e; margin: 0; font-size: 0.9rem;">
            📈 Sprint Statistics - sprint va jamoa statistikasini ko'rsatish uchun.
        </p>
    </div>
    """, unsafe_allow_html=True)

    default_chart_theme = _render_setting_with_help(
        "Default Chart Theme",
        settings.statistics.default_chart_theme,
        settings.statistics.chart_theme_help,
        "selectbox",
        "stat_theme",
        options=["Dark", "Light"]
    )

    return StatisticsSettings(
        default_chart_theme=default_chart_theme
    )


def _render_tz_pr_settings(settings: AppSettings) -> TZPRCheckerSettings:
    """TZ-PR Checker sozlamalari"""

    st.markdown("### 🔍 TZ-PR Checker Sozlamalari")

    if not settings.modules.tz_pr_checker_enabled:
        st.warning("⚠️ Bu modul hozirda o'chirilgan. Sozlamalarni o'zgartirish uchun avval modulni yoqing.")

    st.markdown("""
    <div style="background: rgba(88, 166, 255, 0.1); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
        <p style="color: #8b949e; margin: 0; font-size: 0.9rem;">
            🎯 TZ-PR Checker - Technical Specification va Pull Request mosligini tekshiradi.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ━━━ 1. Trigger Status Sozlamalari ━━━
    st.markdown("#### 📋 Trigger Status")
    st.caption("Qaysi statusda TZ-PR tekshirish boshlanadi")

    col1, col2 = st.columns(2)

    with col1:
        trigger_status = _render_setting_with_help(
            "Trigger Status",
            settings.tz_pr_checker.trigger_status,
            settings.tz_pr_checker.trigger_status_help,
            "text",
            "tzpr_trigger",
            placeholder="Ready to Test"
        )

    with col2:
        trigger_aliases = _render_setting_with_help(
            "Alternativ nomlar",
            settings.tz_pr_checker.trigger_status_aliases,
            settings.tz_pr_checker.trigger_aliases_help,
            "text",
            "tzpr_aliases",
            placeholder="READY TO TEST, Testing"
        )

    st.markdown("---")

    # ━━━ 2. Avtomatik Return ━━━
    st.markdown("#### 🔄 Avtomatik Return")

    auto_return_enabled = _render_setting_with_help(
        "🔄 Avtomatik Return yoqish",
        settings.tz_pr_checker.auto_return_enabled,
        settings.tz_pr_checker.auto_return_help,
        "checkbox",
        "tzpr_auto_return"
    )

    if auto_return_enabled:
        st.success("✅ Avtomatik Return YOQILGAN")

        # ━━━ 3. Return-related sozlamalari (faqat auto_return yoqilgan bo'lsa) ━━━
        col1, col2 = st.columns(2)

        with col1:
            return_threshold = _render_setting_with_help(
                "Return Threshold (%)",
                settings.tz_pr_checker.return_threshold,
                settings.tz_pr_checker.return_threshold_help,
                "slider",
                "tzpr_threshold",
                min_value=0,
                max_value=100,
                step=5
            )

            # Threshold vizualizatsiyasi
            st.markdown(f"""
            <div style="background: rgba(255,86,48,0.1); padding: 0.5rem; border-radius: 8px;">
                <p style="color: #8b949e; font-size: 0.8rem; margin: 0;">
                    Moslik < <strong style="color: #FF5630;">{return_threshold}%</strong> → Task qaytariladi
                </p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            return_status = _render_setting_with_help(
                "Return Status",
                settings.tz_pr_checker.return_status,
                settings.tz_pr_checker.return_status_help,
                "text",
                "tzpr_return",
                placeholder="NEED CLARIFICATION"
            )

        # Qaytarish notification matn
        return_notification_text = st.text_area(
            "Qaytarish Notification Matn",
            value=settings.tz_pr_checker.return_notification_text,
            help=settings.tz_pr_checker.return_notification_help,
            key="tzpr_return_notif_text",
            height=80
        )

        # Re-check xabari (task qaytarildigan so'ng yana Ready to Test)
        recheck_comment_text = st.text_area(
            "Re-check Xabari",
            value=settings.tz_pr_checker.recheck_comment_text,
            help=settings.tz_pr_checker.recheck_comment_help,
            key="tzpr_recheck_text",
            height=60
        )
        st.caption("Task qaytarildigan so'ng yana tekshirilgan vaqtda JIRA ga yoziladigan xabar")

    else:
        st.info("ℹ️ Faqat comment yoziladi, status o'zgarmaydi")
        # Qiymatlar saqlash (UI ko'rsatilmasa da o'zgartirilmaydi)
        return_threshold = settings.tz_pr_checker.return_threshold
        return_status = settings.tz_pr_checker.return_status
        return_notification_text = settings.tz_pr_checker.return_notification_text
        recheck_comment_text = settings.tz_pr_checker.recheck_comment_text

    st.markdown("---")

    # ━━━ 4. Comment Bo'limlarini Ko'rsatish ━━━
    st.markdown("#### 📝 Comment Bo'limlarini Ko'rsatish")
    st.caption("Yoqilgan bo'limlar faqat JIRA comment'ga yoziladigan (token tejash)")

    _ALL_SECTIONS = ['completed', 'partial', 'failed', 'issues', 'figma']
    _SECTION_LABELS = {
        'completed': '✅ Bajarilgan',
        'partial':   '⚠️ Qisman bajarilgan',
        'failed':    '❌ Bajarilmagan',
        'issues':    '🐛 Potensial muammolar',
        'figma':     '🎨 Figma dizayn mosligi',
    }

    cols = st.columns(3)
    visible_sections = []
    for i, section_key in enumerate(_ALL_SECTIONS):
        with cols[i % 3]:
            if st.checkbox(
                _SECTION_LABELS[section_key],
                value=(section_key in settings.tz_pr_checker.visible_sections),
                key=f"tzpr_section_{section_key}"
            ):
                visible_sections.append(section_key)

    if not visible_sections:
        st.error("⚠️ Kamida bitta bo'lim yoqilgan bo'lishi kerak!")
        visible_sections = ['completed']

    # Zid commentlar checkbox (shu bo'lim ichida)
    show_contradictory_comments = st.checkbox(
        "🚨 Zid Commentlar",
        value=settings.tz_pr_checker.show_contradictory_comments,
        help=settings.tz_pr_checker.show_contradictory_comments_help,
        key="tzpr_show_contradictory"
    )

    st.markdown("---")

    # ━━━ 5.1 AI ma'lumotlar darajasi (TZ-PR) ━━━
    st.markdown("#### 📊 AI ga ma'lumotlar darajasi (tartibi)")
    st.caption("Sozlamadagi tartib bo'yicha AI promtiga bo'limlar qo'shiladi. Servis qat'iy amal qiladi.")

    _TZPR_ORDER_OPTIONS = [
        ("tz", "📄 TZ (Texnik topshiriq)"),
        ("comments", "💬 Comment'lar (developer izohlari)"),
        ("figma", "🎨 Figma (dizayn)"),
        ("code", "💻 Kod o'zgarishlari"),
    ]
    _tzpr_order_keys = [k for k, _ in _TZPR_ORDER_OPTIONS]
    _tzpr_order_default = [x for x in settings.tz_pr_checker.ai_data_section_order if x in _tzpr_order_keys]
    if not _tzpr_order_default or "tz" not in _tzpr_order_default or "code" not in _tzpr_order_default:
        _tzpr_order_default = ["tz", "comments", "figma", "code"]
    tzpr_data_order = st.multiselect(
        "Tartib (birinchi o'rinda eng ustun)",
        options=[k for k, _ in _TZPR_ORDER_OPTIONS],
        default=_tzpr_order_default,
        format_func=lambda k: dict(_TZPR_ORDER_OPTIONS).get(k, k),
        key="tzpr_ai_data_order"
    )
    if "tz" not in tzpr_data_order or "code" not in tzpr_data_order:
        st.warning("⚠️ Kamida TZ va Kod bo'lishi shart. Saqlashda standart tartib qo'llanadi.")
        tzpr_data_order = _tzpr_order_default

    st.markdown("---")

    # ━━━ 6. Comment O'qish ━━━
    st.markdown("#### 📖 Comment O'qish")

    tzpr_read_comments = st.checkbox(
        "📖 JIRA comment'lar o'qish",
        value=settings.tz_pr_checker.read_comments_enabled,
        help=settings.tz_pr_checker.read_comments_help,
        key="tzpr_comment_read_enabled"
    )

    tzpr_max_comments = 0
    if tzpr_read_comments:
        tzpr_max_comments = st.slider(
            "Qancha comment o'qilsin?",
            min_value=0,
            max_value=50,
            value=settings.tz_pr_checker.max_comments_to_read,
            step=1,
            help=settings.tz_pr_checker.max_comments_help,
            key="tzpr_comment_max_count"
        )
        if tzpr_max_comments == 0:
            st.caption("📊 Barcha comment'lar o'qiladi")
        else:
            st.caption(f"📊 So'nggi {tzpr_max_comments} ta comment o'qiladi")
    else:
        st.info("ℹ️ Comment'lar o'qilmaydi — AI faqat TZ (description) asosida ishlaydi")

    st.markdown("---")

    # ━━━ 7. DEV Skip Sozlamalari ━━━
    st.markdown("#### ⏭️ DEV Skip Sozlamalari")

    st.markdown("""
    <div style="background: rgba(88, 166, 255, 0.1); padding: 0.8rem; border-radius: 8px; margin-bottom: 0.8rem;">
        <p style="color: #8b949e; margin: 0; font-size: 0.85rem;">
            💡 DEV bu <strong>skip kodini</strong> JIRA comment'ga yozsa — AI tekshirish o'chadi va faqat skip xabari yoziladi.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        skip_code = st.text_input(
            "Skip Kodi",
            value=settings.tz_pr_checker.skip_code,
            help=settings.tz_pr_checker.skip_code_help,
            key="tzpr_skip_code",
            placeholder="AI_SKIP"
        )

    with col2:
        st.markdown(f"""
        <div style="background: rgba(255,171,0,0.1); padding: 0.5rem; border-radius: 8px;">
            <p style="color: #8b949e; font-size: 0.8rem; margin: 0;">
                DEV comment'ga <strong style="color: #FFAB00;">"{skip_code or 'AI_SKIP'}"</strong> yozadi → AI o'chadi
            </p>
        </div>
        """, unsafe_allow_html=True)

    skip_comment_text = st.text_area(
        "Skip Xabari (JIRA ga yoziladigan)",
        value=settings.tz_pr_checker.skip_comment_text,
        help=settings.tz_pr_checker.skip_comment_help,
        key="tzpr_skip_comment",
        height=70
    )

    st.markdown("---")

    # ━━━ 7. Comment Format va Ko'rsatish ━━━
    st.markdown("#### 🎨 Comment Format va Ko'rsatish")

    use_adf_format = st.checkbox(
        "ADF Format (Dropdown Panellar)",
        value=settings.tz_pr_checker.use_adf_format,
        help=settings.tz_pr_checker.use_adf_help,
        key="tzpr_use_adf"
    )

    show_statistics = st.checkbox(
        "PR Statistika Ko'rsatish",
        value=settings.tz_pr_checker.show_statistics,
        help=settings.tz_pr_checker.show_statistics_help,
        key="tzpr_show_statistics"
    )

    show_compliance_score = st.checkbox(
        "Moslik Bali Ko'rsatish",
        value=settings.tz_pr_checker.show_compliance_score,
        help=settings.tz_pr_checker.show_compliance_help,
        key="tzpr_show_compliance"
    )

    max_skip_check_comments = st.slider(
        "Skip Code Tekshirish (nechta comment)",
        min_value=3,
        max_value=50,
        value=settings.tz_pr_checker.max_skip_check_comments,
        step=1,
        help=settings.tz_pr_checker.max_skip_check_comments_help,
        key="tzpr_max_skip_check"
    )
    st.caption(f"AI_SKIP kodi qidirilganda oxirgi {max_skip_check_comments} ta comment tekshiriladi")

    st.markdown("---")

    # ━━━ 8. TZ-PR Comment Footer ━━━
    st.markdown("#### 📝 Comment Footer")

    tz_pr_footer_text = st.text_area(
        "TZ-PR Comment Footer",
        value=settings.tz_pr_checker.tz_pr_footer_text,
        help=settings.tz_pr_checker.tz_pr_footer_help,
        key="tzpr_footer_text",
        height=70
    )

    return TZPRCheckerSettings(
        return_threshold=return_threshold,
        auto_return_enabled=auto_return_enabled,
        trigger_status=trigger_status,
        trigger_status_aliases=trigger_aliases,
        return_status=return_status,
        use_adf_format=use_adf_format,
        show_statistics=show_statistics,
        show_compliance_score=show_compliance_score,
        read_comments_enabled=tzpr_read_comments,
        max_comments_to_read=tzpr_max_comments,
        max_skip_check_comments=max_skip_check_comments,
        tz_pr_footer_text=tz_pr_footer_text,
        return_notification_text=return_notification_text,
        skip_code=skip_code,
        skip_comment_text=skip_comment_text,
        recheck_comment_text=recheck_comment_text,
        show_contradictory_comments=show_contradictory_comments,
        visible_sections=visible_sections,
        ai_data_section_order=tzpr_data_order
    )


def _render_testcase_settings(settings: AppSettings) -> TestcaseGeneratorSettings:
    """Testcase Generator sozlamalari"""

    st.markdown("### 🧪 Test Case Generator Sozlamalari")

    if not settings.modules.testcase_generator_enabled:
        st.warning("⚠️ Bu modul hozirda o'chirilgan. Sozlamalarni o'zgartirish uchun avval modulni yoqing.")

    st.markdown("""
    <div style="background: rgba(88, 166, 255, 0.1); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
        <p style="color: #8b949e; margin: 0; font-size: 0.9rem;">
            🧪 Test Case Generator - TZ va PR asosida AI yordamida test case'lar yaratadi.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Default Sozlamalar
    st.markdown("#### ⚙️ Default Sozlamalar")

    col1, col2 = st.columns(2)

    with col1:
        default_include_pr = _render_setting_with_help(
            "🔎 GitHub PR hisobga olish",
            settings.testcase_generator.default_include_pr,
            settings.testcase_generator.include_pr_help,
            "checkbox",
            "tc_include_pr"
        )

        default_use_smart_patch = _render_setting_with_help(
            "🧠 Smart Patch",
            settings.testcase_generator.default_use_smart_patch,
            settings.testcase_generator.smart_patch_help,
            "checkbox",
            "tc_smart_patch"
        )

    with col2:
        default_test_types = _render_setting_with_help(
            "🎯 Default Test Types",
            settings.testcase_generator.default_test_types,
            settings.testcase_generator.test_types_help,
            "multiselect",
            "tc_test_types",
            options=['positive', 'negative']  # Only positive and negative test types
        )

    max_test_cases = _render_setting_with_help(
        "🎯 Max Test Cases",
        settings.testcase_generator.max_test_cases,
        settings.testcase_generator.max_test_cases_help,
        "slider",
        "tc_max_test_cases",
        min_value=1,
        max_value=30,
        step=1
    )

    st.markdown("---")

    # ━━━ AI ma'lumotlar darajasi (Testcase) ━━━
    st.markdown("#### 📊 AI ga ma'lumotlar darajasi (tartibi)")
    st.caption("Sozlamadagi tartib bo'yicha AI promtiga bo'limlar qo'shiladi. Servis qat'iy amal qiladi.")

    _TC_ORDER_OPTIONS = [
        ("tz", "📄 TZ (Texnik topshiriq)"),
        ("comments", "💬 Comment'lar"),
        ("custom_context", "📌 Qo'shimcha kontekst"),
        ("code", "💻 Kod statistikasi (PR)"),
    ]
    _tc_order_keys = [k for k, _ in _TC_ORDER_OPTIONS]
    _tc_order_default = [x for x in settings.testcase_generator.ai_data_section_order if x in _tc_order_keys]
    if not _tc_order_default or "tz" not in _tc_order_default:
        _tc_order_default = ["tz", "comments", "custom_context", "code"]
    tc_data_order = st.multiselect(
        "Tartib (birinchi o'rinda eng ustun)",
        options=[k for k, _ in _TC_ORDER_OPTIONS],
        default=_tc_order_default,
        format_func=lambda k: dict(_TC_ORDER_OPTIONS).get(k, k),
        key="tc_ai_data_order"
    )
    if "tz" not in tc_data_order:
        st.warning("⚠️ TZ bo'lishi shart. Saqlashda standart tartib qo'llanadi.")
        tc_data_order = _tc_order_default

    st.markdown("---")

    # ━━━ Comment O'qish ━━━
    st.markdown("#### 📖 Comment O'qish")

    tc_read_comments = st.checkbox(
        "📖 JIRA comment'lar o'qish",
        value=settings.testcase_generator.read_comments_enabled,
        help=settings.testcase_generator.read_comments_help,
        key="tc_comment_read_enabled"
    )

    tc_max_comments = 0
    if tc_read_comments:
        tc_max_comments = st.slider(
            "Qancha comment o'qilsin?",
            min_value=0,
            max_value=50,
            value=settings.testcase_generator.max_comments_to_read,
            step=1,
            help=settings.testcase_generator.max_comments_help,
            key="tc_comment_max_count"
        )
        if tc_max_comments == 0:
            st.caption("📊 Barcha comment'lar o'qiladi")
        else:
            st.caption(f"📊 So'nggi {tc_max_comments} ta comment o'qiladi")
    else:
        st.info("ℹ️ Comment'lar o'qilmaydi — AI faqat TZ (description) asosida ishlaydi")

    st.markdown("---")

    # JIRA Avtomatik Comment
    st.markdown("#### 📝 JIRA Avtomatik Comment")

    auto_comment_enabled = _render_setting_with_help(
        "🤖 Avtomatik Comment yoqish",
        settings.testcase_generator.auto_comment_enabled,
        settings.testcase_generator.auto_comment_help,
        "checkbox",
        "tc_auto_comment"
    )

    if auto_comment_enabled:
        st.success("✅ Task 'Ready to Test' ga tushganda avtomatik test case yoziladi")

        col1, col2 = st.columns(2)

        with col1:
            auto_comment_trigger_status = _render_setting_with_help(
                "Trigger Status",
                settings.testcase_generator.auto_comment_trigger_status,
                settings.testcase_generator.trigger_status_help,
                "text",
                "tc_trigger",
                placeholder="READY TO TEST"
            )

        with col2:
            auto_comment_trigger_aliases = _render_setting_with_help(
                "Alternativ nomlar",
                settings.testcase_generator.auto_comment_trigger_aliases,
                settings.testcase_generator.trigger_aliases_help,
                "text",
                "tc_aliases",
                placeholder="Ready To Test,READY TO TEST"
            )

        # Footer matn (faqat avtomatik comment uchun)
        testcase_footer_text = st.text_area(
            "Test Case Comment Footer",
            value=settings.testcase_generator.testcase_footer_text,
            help=settings.testcase_generator.testcase_footer_help,
            key="tc_footer_text",
            height=70
        )
    else:
        auto_comment_trigger_status = settings.testcase_generator.auto_comment_trigger_status
        auto_comment_trigger_aliases = settings.testcase_generator.auto_comment_trigger_aliases
        testcase_footer_text = settings.testcase_generator.testcase_footer_text

    # Note: Comment format (ADF) is hardcoded to True for all testcase comments
    return TestcaseGeneratorSettings(
        default_include_pr=default_include_pr,
        default_use_smart_patch=default_use_smart_patch,
        default_test_types=default_test_types if default_test_types else ['positive'],
        max_test_cases=max_test_cases,
        ai_data_section_order=tc_data_order,
        read_comments_enabled=tc_read_comments,
        max_comments_to_read=tc_max_comments,
        auto_comment_enabled=auto_comment_enabled,
        auto_comment_trigger_status=auto_comment_trigger_status,
        auto_comment_trigger_aliases=auto_comment_trigger_aliases,
        use_adf_format=True,
        testcase_footer_text=testcase_footer_text
    )


def _render_system_settings(settings: AppSettings):
    """Tizim Sozlamalari — Webhook Filtrlari + AI Queue

    Returns:
        tuple: (QueueSettings, allowed_issue_types: str, excluded_assignees: str, min_tz_chars: int)
    """

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # WEBHOOK FILTRLARI
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    st.markdown("### 🔒 Webhook Filtrlari")

    st.markdown("""
    <div style="background: rgba(255,171,0,0.1); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
        <p style="color: #8b949e; margin: 0; font-size: 0.9rem;">
            🎯 Bu filtrllar webhook qabul qilgandan keyin, har qanday servis ishga tushishidan
            <strong>oldin</strong> tekshiriladi. Ikkala servis (TZ-PR Checker va Test Case Generator)
            uchun amal qiladi.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ━━━ Filter 1: Issue Type ━━━
    st.markdown("#### 📋 Issue Type Filtri")
    st.caption("Faqat bu type'lar uchun servislar ishga tushadi — qolganlar avtomatik o'tkazib yuboriladi")

    allowed_issue_types = st.text_input(
        "Ruxsat etilgan Issue Type'lar",
        value=settings.tz_pr_checker.allowed_issue_types,
        help=settings.tz_pr_checker.allowed_issue_types_help,
        key="sys_allowed_issue_types",
        placeholder="DEV-BUG,DEV-TECHTASK,DEV- PROD TASK,DEV-CLIENT TASK"
    )

    if allowed_issue_types.strip():
        types_list = [t.strip() for t in allowed_issue_types.split(',') if t.strip()]
        st.markdown(
            "**Ruxsat etilgan type'lar:** " +
            " · ".join([f"`{t}`" for t in types_list])
        )
    else:
        st.info("ℹ️ Bo'sh — barcha issue type'lar uchun ishlaydi (filter o'chiq)")

    st.markdown("---")

    # ━━━ Filter 2: Excluded Assignees ━━━
    st.markdown("#### 👤 Assignee Filtri (Istisno)")
    st.caption("Bu assignee'lar uchun webhook signal kelsa — servislar ishga tushmaydi")

    excluded_assignees = st.text_input(
        "Istisno Assignee'lar (JIRA displayName)",
        value=settings.tz_pr_checker.excluded_assignees,
        help=settings.tz_pr_checker.excluded_assignees_help,
        key="sys_excluded_assignees",
        placeholder="Alisher Karimov, Bobur Toshmatov"
    )

    if excluded_assignees.strip():
        assignees_list = [a.strip() for a in excluded_assignees.split(',') if a.strip()]
        st.markdown(
            "**Skip bo'ladigan assignee'lar:** " +
            " · ".join([f"`{a}`" for a in assignees_list])
        )
    else:
        st.info("ℹ️ Bo'sh — assignee bo'yicha filter yo'q (hammaga ishlaydi)")

    st.markdown("---")

    # ━━━ Filter 3: TZ Minimal Uzunlik ━━━
    st.markdown("#### 📄 TZ Minimal Uzunlik Filtri")
    st.caption("Ikkala servis uchun: description shu belgidan qisqa bo'lsa task qaytariladi va JIRA'ga error yoziladi")

    min_tz_description_chars = _render_setting_with_help(
        "📄 TZ minimal uzunlik (belgilar)",
        getattr(settings.tz_pr_checker, 'min_tz_description_chars', 50),
        getattr(settings.tz_pr_checker, 'min_tz_description_chars_help', ''),
        "slider",
        "sys_min_tz_chars",
        min_value=0,
        max_value=500,
        step=10
    )
    if min_tz_description_chars == 0:
        st.info("ℹ️ 0 — TZ uzunlik filtri o'chiq (har qanday uzunlikda ishlaydi)")
    else:
        st.warning(f"⚠️ {min_tz_description_chars} belgidan qisqa TZ → task qaytariladi (ikkala servis)")

    st.markdown("---")
    st.markdown("---")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # AI QUEUE SOZLAMALARI
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    st.markdown("### ⚙️ AI Queue Sozlamalari")

    st.markdown("""
    <div style="background: rgba(88, 166, 255, 0.1); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
        <p style="color: #8b949e; margin: 0; font-size: 0.9rem;">
            🔄 Bir vaqtda ko'p task "Ready to Test" statusga tushgan bo'lsa,
            ikkinchi task birinchisi tugangungacha kutadi. Bitta task ichida
            checker comment yozgandan so'ng testcase commentgacha delay bo'ladi.
        </p>
    </div>
    """, unsafe_allow_html=True)

    queue_enabled = _render_setting_with_help(
        "🔄 AI Queue Yoqilgan",
        settings.queue.queue_enabled,
        settings.queue.queue_enabled_help,
        "checkbox",
        "sys_queue_enabled"
    )

    if queue_enabled:
        st.success("✅ AI Queue YOQILGAN — rate limit himoya aktiv")

        st.markdown("---")

        # ━━━ Task kutish vaqti ━━━
        st.markdown("#### ⏳ Task Kutish Vaqti")
        st.markdown("""
        <div style="background: rgba(255,171,0,0.08); padding: 0.7rem; border-radius: 8px; margin-bottom: 0.7rem;">
            <p style="color: #8b949e; margin: 0; font-size: 0.85rem;">
                💡 <strong>Masalan:</strong> Task A tekshirilmoqda. Task B keldi.
                B — A tugangungacha kutadi. Agar kutish vaqti o'tgan so'ng
                B'ga JIRA'da error comment yoziladi va manual tekshirish tavsiya etiladi.
            </p>
        </div>
        """, unsafe_allow_html=True)

        task_wait_timeout = _render_setting_with_help(
            "Task Kutish Vaqti (sek)",
            settings.queue.task_wait_timeout,
            settings.queue.task_wait_timeout_help,
            "slider",
            "sys_task_wait_timeout",
            min_value=30,
            max_value=300,
            step=30
        )

        st.caption(f"Ikkinchi task max {task_wait_timeout}s kutadi. Timeout → JIRA error comment")

        st.markdown("---")

        # ━━━ Servislar Orasidagi Kutish Vaqti ━━━
        st.markdown("#### ⏱️ Servislar Orasidagi Kutish Vaqti")
        st.markdown("""
        <div style="background: rgba(88, 166, 255, 0.08); padding: 0.7rem; border-radius: 8px; margin-bottom: 0.7rem;">
            <p style="color: #8b949e; margin: 0; font-size: 0.85rem;">
                💡 TZ-PR Tahlil (Servis-1) tugagandan so'ng <strong>N sekunda kutiladi</strong>, keyin Test Case (Servis-2) ishga tushadi.
            </p>
        </div>
        """, unsafe_allow_html=True)

        checker_testcase_delay = _render_setting_with_help(
            "Servislar Orasidagi Kutish Vaqti (sek)",
            settings.queue.checker_testcase_delay,
            settings.queue.checker_testcase_delay_help,
            "slider",
            "sys_checker_testcase_delay",
            min_value=5,
            max_value=60,
            step=5
        )

        st.caption(f"1-servis tugagandan so'ng {checker_testcase_delay}s kutiladi, keyin 2-servis ishga tushadi")

        st.markdown("---")

        # ━━━ Blocked Task Qayta Ishlash ━━━
        st.markdown("#### 🔒 Blocked Task Qayta Ishlash")
        st.markdown("""
        <div style="background: rgba(76, 154, 255, 0.08); padding: 0.7rem; border-radius: 8px; margin-bottom: 0.7rem;">
            <p style="color: #8b949e; margin: 0; font-size: 0.85rem;">
                💡 AI timeout yoki 429 rate limit sabab blocked bo'lgan task
                belgilangan vaqtdan keyin avtomatik qayta ishga tushiriladi.
            </p>
        </div>
        """, unsafe_allow_html=True)

        blocked_retry_delay = _render_setting_with_help(
            "Blocked Task Qayta Ishlash Vaqti (daqiqa)",
            settings.queue.blocked_retry_delay,
            settings.queue.blocked_retry_delay_help,
            "slider",
            "sys_blocked_retry_delay",
            min_value=1,
            max_value=60,
            step=1
        )

        st.caption(f"Blocked task {blocked_retry_delay} daqiqadan keyin qayta urinadi")

        st.markdown("---")

        # ━━━ AI va Tizim Sozlamalari ━━━
        st.markdown("#### 🔧 AI va Tizim Sozlamalari")
        st.markdown("""
        <div style="background: rgba(88, 166, 255, 0.08); padding: 0.7rem; border-radius: 8px; margin-bottom: 0.7rem;">
            <p style="color: #8b949e; margin: 0; font-size: 0.85rem;">
                💡 AI so'rovlar, DB va HTTP so'rovlar uchun ichki sozlamalar.
                O'zgartirish faqat muammo bo'lganda tavsiya etiladi.
            </p>
        </div>
        """, unsafe_allow_html=True)

        gemini_min_interval = _render_setting_with_help(
            "Gemini So'rov Intervali (sek)",
            settings.queue.gemini_min_interval,
            settings.queue.gemini_min_interval_help,
            "slider",
            "sys_gemini_min_interval",
            min_value=3,
            max_value=15,
            step=1
        )

        blocked_check_interval = _render_setting_with_help(
            "Blocked Tekshirish Oraligi (sek)",
            settings.queue.blocked_check_interval,
            settings.queue.blocked_check_interval_help,
            "slider",
            "sys_blocked_check_interval",
            min_value=10,
            max_value=120,
            step=10
        )

        key_freeze_duration = _render_setting_with_help(
            "KEY Muzlatish Muddati (daqiqa)",
            settings.queue.key_freeze_duration // 60,
            settings.queue.key_freeze_duration_help,
            "slider",
            "sys_key_freeze_duration",
            min_value=1,
            max_value=30,
            step=1
        )
        # Convert back to seconds for storage
        key_freeze_duration_seconds = key_freeze_duration * 60

        ai_max_retries = _render_setting_with_help(
            "AI Qayta Urinish Limiti",
            settings.queue.ai_max_retries,
            settings.queue.ai_max_retries_help,
            "slider",
            "sys_ai_max_retries",
            min_value=1,
            max_value=10,
            step=1
        )

        ai_max_input_tokens = _render_setting_with_help(
            "AI Max Input Token (K)",
            settings.queue.ai_max_input_tokens // 1000,
            settings.queue.ai_max_input_tokens_help,
            "slider",
            "sys_ai_max_input_tokens",
            min_value=500,
            max_value=1500,
            step=50
        )
        # Convert back to tokens for storage
        ai_max_input_tokens_value = ai_max_input_tokens * 1000

        chars_per_token = _render_setting_with_help(
            "Token Koeffitsiyenti (belgi/token)",
            settings.queue.chars_per_token,
            settings.queue.chars_per_token_help,
            "slider",
            "sys_chars_per_token",
            min_value=2,
            max_value=8,
            step=1
        )

        db_busy_timeout = _render_setting_with_help(
            "DB Busy Timeout (sek)",
            settings.queue.db_busy_timeout // 1000,
            settings.queue.db_busy_timeout_help,
            "slider",
            "sys_db_busy_timeout",
            min_value=5,
            max_value=60,
            step=5
        )
        # Convert back to milliseconds for storage
        db_busy_timeout_ms = db_busy_timeout * 1000

        db_connection_timeout = _render_setting_with_help(
            "DB Connection Timeout (sek)",
            settings.queue.db_connection_timeout,
            settings.queue.db_connection_timeout_help,
            "slider",
            "sys_db_connection_timeout",
            min_value=5,
            max_value=60,
            step=5
        )

        http_timeout = _render_setting_with_help(
            "HTTP So'rov Timeout (sek)",
            settings.queue.http_timeout,
            settings.queue.http_timeout_help,
            "slider",
            "sys_http_timeout",
            min_value=10,
            max_value=120,
            step=10
        )

        executor_timeout = _render_setting_with_help(
            "Executor Timeout (sek)",
            settings.queue.executor_timeout,
            settings.queue.executor_timeout_help,
            "slider",
            "sys_executor_timeout",
            min_value=60,
            max_value=600,
            step=30
        )

    else:
        st.warning("⚠️ Queue o'chirilgan — ko'p task birdan kelgan bo'lsa API limit mumkin")
        # Qiymatlar saqlash (UI ko'rsatilmasa da o'zgartirilmaydi)
        task_wait_timeout = settings.queue.task_wait_timeout
        checker_testcase_delay = settings.queue.checker_testcase_delay
        blocked_retry_delay = settings.queue.blocked_retry_delay
        gemini_min_interval = settings.queue.gemini_min_interval
        blocked_check_interval = settings.queue.blocked_check_interval
        key_freeze_duration_seconds = settings.queue.key_freeze_duration
        ai_max_retries = settings.queue.ai_max_retries
        ai_max_input_tokens_value = settings.queue.ai_max_input_tokens
        chars_per_token = settings.queue.chars_per_token
        db_busy_timeout_ms = settings.queue.db_busy_timeout
        db_connection_timeout = settings.queue.db_connection_timeout
        http_timeout = settings.queue.http_timeout
        executor_timeout = settings.queue.executor_timeout
    queue = QueueSettings(
        queue_enabled=queue_enabled,
        task_wait_timeout=task_wait_timeout,
        checker_testcase_delay=checker_testcase_delay,
        blocked_retry_delay=blocked_retry_delay,
        gemini_min_interval=gemini_min_interval,
        blocked_check_interval=blocked_check_interval,
        key_freeze_duration=key_freeze_duration_seconds,
        ai_max_retries=ai_max_retries,
        ai_max_input_tokens=ai_max_input_tokens_value,
        chars_per_token=chars_per_token,
        db_busy_timeout=db_busy_timeout_ms,
        db_connection_timeout=db_connection_timeout,
        http_timeout=http_timeout,
        executor_timeout=executor_timeout
    )
    return queue, allowed_issue_types, excluded_assignees, min_tz_description_chars


def _show_save_success_animation():
    """
    Saqlash muvaffaqiyatligi uchun CSS keyframe animatsiya ko'rsatish.
    3 sekunda ichida scale-in + green pulse + fade-out.
    """
    st.markdown("""
    <style>
        @keyframes save-pop-in {
            0%   { transform: scale(0.85); opacity: 0; }
            60%  { transform: scale(1.03); }
            100% { transform: scale(1.0);  opacity: 1; }
        }
        @keyframes save-pulse-border {
            0%, 100% { border-color: #36B37E; box-shadow: 0 0 0px #36B37E44; }
            50%      { border-color: #2ea043; box-shadow: 0 0 12px #36B37E88; }
        }
        @keyframes save-fade-out {
            0%   { opacity: 1; }
            100% { opacity: 0; }
        }
        .save-success-card {
            animation:
                save-pop-in 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) forwards,
                save-pulse-border 0.6s ease-in-out 0.4s 3 forwards,
                save-fade-out 0.5s ease-out 2.2s forwards;
            background: linear-gradient(135deg, rgba(46, 160, 67, 0.12), rgba(54, 179, 126, 0.08));
            border: 2px solid #36B37E;
            border-radius: 12px;
            padding: 1.2rem 1.6rem;
            margin: 0.8rem 0;
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }
        .save-success-card .checkmark {
            font-size: 2rem;
            line-height: 1;
        }
        .save-success-card .text-block h3 {
            color: #36B37E;
            margin: 0 0 0.2rem 0;
            font-size: 1.1rem;
        }
        .save-success-card .text-block p {
            color: #8b949e;
            margin: 0;
            font-size: 0.85rem;
        }
    </style>
    <div class="save-success-card">
        <div class="checkmark">&#10003;</div>
        <div class="text-block">
            <h3>Sozlamalar saqlandi!</h3>
            <p>Barcha o'zgarishlar muvaffaqiyatli saqlanilgan.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_save_buttons(
        current_settings: AppSettings,
        modules: ModuleVisibility,
        bug_analyzer: BugAnalyzerSettings,
        statistics: StatisticsSettings,
        # comment_reading: CommentReadingSettings,
        tz_pr: TZPRCheckerSettings,
        testcase: TestcaseGeneratorSettings,
        system: QueueSettings = None,
        allowed_issue_types_filter: str = None,
        excluded_assignees_filter: str = None,
        min_tz_chars_filter: int = None,
):
    """Saqlash tugmalari"""

    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("💾 Saqlash", type="primary", use_container_width=True):
            # Tizim tabidan kelgan qiymatlarni TZ-PR sozlamalariga qo'shish
            replace_kwargs = {}
            if allowed_issue_types_filter is not None:
                replace_kwargs["allowed_issue_types"] = allowed_issue_types_filter
            if excluded_assignees_filter is not None:
                replace_kwargs["excluded_assignees"] = excluded_assignees_filter
            if min_tz_chars_filter is not None:
                replace_kwargs["min_tz_description_chars"] = min_tz_chars_filter
            if replace_kwargs:
                tz_pr = replace(tz_pr, **replace_kwargs)

            # Yangi sozlamalar yaratish
            new_settings = AppSettings(
                modules=modules,
                bug_analyzer=bug_analyzer,
                statistics=statistics,
                # comment_reading=comment_reading,
                tz_pr_checker=tz_pr,
                testcase_generator=testcase,
                queue=system if system else current_settings.queue
            )

            # Saqlash
            if save_app_settings(new_settings):
                _show_save_success_animation()
                st.balloons()
                # Session state'ni tozalash
                st.session_state.show_settings = False
            else:
                st.error("❌ Saqlashda xato yuz berdi")

    with col2:
        if st.button("🔙 Ortga", use_container_width=True):
            st.session_state.show_settings = False
            st.rerun()
