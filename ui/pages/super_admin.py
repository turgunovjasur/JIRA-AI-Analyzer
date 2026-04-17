"""
Super Admin Panel

Kompaniyalarni yaratish, ko'rish, faollashtirish/o'chirish,
parolini yangilash, modul ruxsatlarini boshqarish va o'chirish.

Author: JASUR TURGUNOV
"""
import streamlit as st
from utils.auth.auth_db import (
    ALL_MODULES,
    get_all_companies,
    create_company,
    update_company_status,
    update_company_password,
    delete_company,
    has_api_keys_configured,
    get_company_modules,
    save_company_modules,
)
from ui.components import render_header

# Modul ikonlari
_MODULE_ICONS = {
    'bug_analyzer':       '🐛',
    'statistics':         '📊',
    'tz_pr_checker':      '🔍',
    'testcase_generator': '🧪',
    'monitoring':         '📈',
    'sprint_report':      '📋',
}


def render_super_admin():
    """Super Admin bosh sahifasi"""

    render_header(
        title="Super Admin Panel",
        subtitle="Kompaniyalarni boshqarish",
        version="v1.0",
        icon="👑"
    )

    st.markdown("---")

    tabs = st.tabs([
        "🏢 Kompaniyalar",
        "➕ Yangi Kompaniya",
    ])

    with tabs[0]:
        _render_companies_list()

    with tabs[1]:
        _render_create_company()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KOMPANIYALAR RO'YXATI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _render_companies_list():
    """Barcha kompaniyalar ro'yxati"""

    companies = get_all_companies()

    if not companies:
        st.info("Hali kompaniya yo'q. 'Yangi Kompaniya' tabidan qo'shing.")
        return

    total = len(companies)
    active = sum(1 for c in companies if c['is_active'])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Jami", total)
    with col2:
        st.metric("Faol", active)
    with col3:
        st.metric("Nofaol", total - active)

    st.markdown("---")

    for company in companies:
        _render_company_card(company)


def _render_company_card(company: dict):
    """Bitta kompaniya kartasi"""

    cid       = company['id']
    code      = company['company_code']
    name      = company['company_name']
    is_active = bool(company['is_active'])
    created   = company.get('created_at', '')[:10]
    has_keys  = has_api_keys_configured(cid)
    modules   = get_company_modules(cid)

    active_mods = [ALL_MODULES[k] for k, v in modules.items() if v]
    status_color = "#36B37E" if is_active else "#FF5630"
    keys_icon    = "✅" if has_keys else "⚠️"

    # Modul badge'lar
    mod_badges = " ".join(
        f'<span style="background:rgba(88,166,255,0.15); color:#58a6ff; '
        f'padding:2px 8px; border-radius:12px; font-size:0.72rem;">'
        f'{_MODULE_ICONS.get(k, "")} {ALL_MODULES[k]}</span>'
        for k, v in modules.items() if v
    ) or '<span style="color:#8b949e; font-size:0.8rem;">Hech qaysi modul yoqilmagan</span>'

    title = f"{'✅' if is_active else '❌'} **{code}** — {name}"

    with st.expander(title, expanded=False):

        # ── Info ──────────────────────────────────────
        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.6); padding:1rem;
                    border-radius:8px; margin-bottom:0.8rem;">
            <p style="margin:0 0 0.6rem 0; color:#8b949e; font-size:0.85rem;">
                <strong style="color:#e6edf3;">Kod:</strong> {code} &nbsp;|&nbsp;
                <strong style="color:#e6edf3;">Nom:</strong> {name} &nbsp;|&nbsp;
                <strong style="color:#e6edf3;">Status:</strong>
                    <span style="color:{status_color};">● {'Faol' if is_active else 'Nofaol'}</span>
                &nbsp;|&nbsp;
                <strong style="color:#e6edf3;">API:</strong> {keys_icon}
                &nbsp;|&nbsp;
                <strong style="color:#e6edf3;">Yaratilgan:</strong> {created}
            </p>
            <div style="margin-top:0.4rem;">{mod_badges}</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Modul ruxsatlari ──────────────────────────
        with st.expander("🔧 Modul Ruxsatlarini Tahrirlash"):
            st.caption("Kompaniyaga qaysi modullar ko'rinsin?")

            cols = st.columns(2)
            new_mods = {}
            for i, (mod_key, mod_label) in enumerate(ALL_MODULES.items()):
                icon = _MODULE_ICONS.get(mod_key, '')
                with cols[i % 2]:
                    new_mods[mod_key] = st.checkbox(
                        f"{icon} {mod_label}",
                        value=modules.get(mod_key, False),
                        key=f"mod_{cid}_{mod_key}"
                    )

            if st.button("💾 Modullarni Saqlash", key=f"save_mods_{cid}"):
                if save_company_modules(cid, new_mods):
                    enabled_count = sum(1 for v in new_mods.values() if v)
                    st.success(f"✅ Saqlandi! {enabled_count} ta modul yoqilgan.")
                    st.rerun()
                else:
                    st.error("Xato yuz berdi")

        # ── Faollashtirish / Nofaol qilish ────────────
        btn_label = "❌ Nofaol qilish" if is_active else "✅ Faollashtirish"
        if st.button(btn_label, key=f"toggle_{cid}"):
            update_company_status(cid, not is_active)
            st.rerun()

        # ── Parol yangilash ───────────────────────────
        with st.expander("🔑 Parolni Yangilash"):
            new_pass = st.text_input(
                "Yangi parol",
                type="password",
                key=f"new_pass_{cid}",
                placeholder="Kamida 6 ta belgi"
            )
            if st.button("Yangilash", key=f"upd_pass_{cid}"):
                if len(new_pass) < 6:
                    st.error("Parol kamida 6 ta belgi bo'lishi kerak")
                elif update_company_password(cid, new_pass):
                    st.success("✅ Parol yangilandi!")
                else:
                    st.error("Xato yuz berdi")

        # ── O'chirish ─────────────────────────────────
        with st.expander("🗑️ Kompaniyani O'chirish"):
            st.warning(f"**{name}** ni butunlay o'chirasizmi? Bu amalni qaytarib bo'lmaydi!")
            confirm = st.text_input(
                f"Tasdiqlash: kompaniya kodini yozing (`{code}`)",
                key=f"del_confirm_{cid}"
            )
            if st.button("O'chirish", key=f"del_btn_{cid}", type="primary"):
                if confirm.strip().upper() == code:
                    if delete_company(cid):
                        st.success(f"{name} o'chirildi!")
                        st.rerun()
                    else:
                        st.error("Xato yuz berdi")
                else:
                    st.error("Kod noto'g'ri. O'chirish bekor qilindi.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# YANGI KOMPANIYA YARATISH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _render_create_company():
    """Yangi kompaniya yaratish formasi"""

    st.markdown("### ➕ Yangi Kompaniya")

    st.markdown("""
    <div style="background:rgba(88,166,255,0.08); padding:1rem; border-radius:8px; margin-bottom:1.2rem;">
        <p style="color:#8b949e; margin:0; font-size:0.85rem;">
            💡 Kompaniya yaratgandan so'ng ularga <strong>Kompaniya Kodi</strong> va
            <strong>Parolni</strong> bering. Ular tizimga kirib JIRA va GitHub
            tokenlarini bir marta kiritishadi — keyin faqat siz ochgan modullari ko'rinadi.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Asosiy ma'lumotlar ──────────────────────
    col1, col2 = st.columns(2)
    with col1:
        company_code = st.text_input(
            "Kompaniya Kodi *",
            placeholder="PEPSI",
            help="Faqat lotin harflar va raqamlar. Avtomatik KATTA harfga o'giriladi."
        )
        company_name = st.text_input(
            "Kompaniya Nomi *",
            placeholder="Pepsi Co"
        )
    with col2:
        password = st.text_input(
            "Dastlabki Parol *",
            type="password",
            placeholder="Kamida 6 ta belgi"
        )
        password_confirm = st.text_input(
            "Parolni Tasdiqlang *",
            type="password",
            placeholder="Yuqoridagi parolni qaytaring"
        )

    st.markdown("---")

    # ── Modul ruxsatlari ────────────────────────
    st.markdown("#### 🔧 Modul Ruxsatlari")
    st.caption("Bu kompaniyaga qaysi modullar ko'rinsin? (Har bir modul alohida to'lov)")

    new_mods = {}
    cols = st.columns(3)
    for i, (mod_key, mod_label) in enumerate(ALL_MODULES.items()):
        icon = _MODULE_ICONS.get(mod_key, '')
        with cols[i % 3]:
            new_mods[mod_key] = st.checkbox(
                f"{icon} {mod_label}",
                value=False,
                key=f"create_mod_{mod_key}"
            )

    # Tanlangan modullar preview
    selected = [ALL_MODULES[k] for k, v in new_mods.items() if v]
    if selected:
        st.success(f"✅ Tanlangan modullar: {', '.join(selected)}")
    else:
        st.warning("⚠️ Hech qaysi modul tanlanmagan. Kompaniya tizimga kirsa bo'sh sahifa ko'radi.")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("➕ Kompaniya Yaratish", type="primary"):
        errors = []
        if not company_code.strip():
            errors.append("Kompaniya kodi kiritilishi shart")
        if not company_name.strip():
            errors.append("Kompaniya nomi kiritilishi shart")
        if not password:
            errors.append("Parol kiritilishi shart")
        elif len(password) < 6:
            errors.append("Parol kamida 6 ta belgi bo'lishi kerak")
        elif password != password_confirm:
            errors.append("Parollar bir xil emas")

        clean_code = ''.join(c for c in company_code.upper() if c.isalnum() or c in '-_')
        if not clean_code:
            errors.append("Kompaniya kodi noto'g'ri (faqat harf va raqam)")

        if errors:
            for e in errors:
                st.error(e)
        else:
            result = create_company(
                clean_code,
                company_name.strip(),
                password,
                enabled_modules=new_mods
            )
            if result:
                st.success(f"✅ **{company_name}** kompaniyasi yaratildi!")
                enabled_list = [ALL_MODULES[k] for k, v in new_mods.items() if v]
                st.markdown(f"""
                <div style="background:rgba(54,179,126,0.1); border:1px solid #36B37E;
                            padding:1.2rem; border-radius:10px; margin-top:1rem;">
                    <h4 style="color:#36B37E; margin:0 0 0.8rem 0;">
                        📋 Kompaniyaga beriladigan ma'lumotlar
                    </h4>
                    <p style="color:#e6edf3; margin:0; font-size:0.95rem; line-height:1.8;">
                        <strong>Kompaniya Kodi:</strong>
                        <code style="background:rgba(88,166,255,0.15); padding:2px 10px;
                                     border-radius:4px; font-size:1.05rem;">{clean_code}</code><br>
                        <strong>Parol:</strong>
                        <code style="background:rgba(88,166,255,0.15); padding:2px 10px;
                                     border-radius:4px; font-size:1.05rem;">{password}</code><br>
                        <strong>Ochilgan modullar:</strong>
                        {', '.join(enabled_list) if enabled_list else 'Hech qaysi'}
                    </p>
                    <p style="color:#8b949e; margin-top:0.8rem; font-size:0.78rem;">
                        ⚠️ Parolni xavfsiz joyda saqlang. Tizim paroli ko'rinmaydi.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"❌ '{clean_code}' kodi allaqachon mavjud yoki xato yuz berdi.")
