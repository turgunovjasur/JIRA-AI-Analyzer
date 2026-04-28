"""
Super Admin Panel

Kompaniyalar va ularning foydalanuvchilarini boshqarish.
Har bir kompaniyada: yaratish, modul ruxsat, seat_limit, faollashtirish, o'chirish.
Har bir kompaniya ichida: user qo'shish, parol reset, o'chirish.

Author: JASUR TURGUNOV
"""
import streamlit as st
from utils.auth.auth_db import (
    ALL_MODULES,
    get_all_companies,
    create_company,
    update_company_status,
    update_company_seat_limit,
    delete_company,
    has_api_keys_configured,
    get_company_modules,
    save_company_modules,
    count_users_in_company,
    get_users_by_company,
    create_user,
    update_user_password,
    update_user_status,
    delete_user,
)
from ui.components import render_header

_MODULE_ICONS = {
    'bug_analyzer':       '🐛',
    'statistics':         '📊',
    'tz_pr_checker':      '🔍',
    'testcase_generator': '🧪',
    'monitoring':         '📈',
    'sprint_report':      '📋',
    'webhook':            '🔗',
}


def render_super_admin():
    """Super Admin bosh sahifasi"""
    render_header(
        title="Super Admin Panel",
        subtitle="Kompaniyalar va foydalanuvchilarni boshqarish",
        version="v2.0",
        icon="👑"
    )
    st.markdown("---")

    tabs = st.tabs(["🏢 Kompaniyalar", "➕ Yangi Kompaniya"])

    with tabs[0]:
        _render_companies_list()
    with tabs[1]:
        _render_create_company()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KOMPANIYALAR RO'YXATI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _render_companies_list():
    companies = get_all_companies()

    if not companies:
        st.info("Hali kompaniya yo'q. 'Yangi Kompaniya' tabidan qo'shing.")
        return

    total  = len(companies)
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
    cid        = company['id']
    code       = company['company_code']
    name       = company['company_name']
    is_active  = bool(company['is_active'])
    seat_limit = company.get('seat_limit', 1)
    created    = company.get('created_at', '')[:10]
    has_keys   = has_api_keys_configured(cid)
    modules    = get_company_modules(cid)
    user_count = count_users_in_company(cid)

    status_color = "#36B37E" if is_active else "#FF5630"
    keys_icon    = "✅" if has_keys else "⚠️"

    mod_badges = " ".join(
        f'<span style="background:rgba(88,166,255,0.15); color:#58a6ff; '
        f'padding:2px 8px; border-radius:12px; font-size:0.72rem;">'
        f'{_MODULE_ICONS.get(k, "")} {ALL_MODULES[k]}</span>'
        for k, v in modules.items() if v
    ) or '<span style="color:#8b949e; font-size:0.8rem;">Hech qaysi modul yoqilmagan</span>'

    seat_color = "#FF5630" if user_count >= seat_limit else "#36B37E"
    title = f"{'✅' if is_active else '❌'} **{code}** — {name}  ({user_count}/{seat_limit} user)"

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
                <strong style="color:#e6edf3;">Userlar:</strong>
                    <span style="color:{seat_color};">{user_count}/{seat_limit}</span>
                &nbsp;|&nbsp;
                <strong style="color:#e6edf3;">Yaratilgan:</strong> {created}
            </p>
            <div style="margin-top:0.4rem;">{mod_badges}</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Foydalanuvchilar ──────────────────────────
        with st.expander(f"👥 Foydalanuvchilar ({user_count}/{seat_limit})"):
            _render_users_section(cid, code, seat_limit)

        # ── Seat limit ────────────────────────────────
        with st.expander("💺 Seat Limit O'zgartirish"):
            st.caption(f"Hozirgi limit: {seat_limit} ta. Joriy userlar: {user_count} ta.")
            new_limit = st.number_input(
                "Yangi seat limit",
                min_value=max(1, user_count),
                max_value=100,
                value=seat_limit,
                step=1,
                key=f"seat_{cid}"
            )
            if st.button("💾 Saqlash", key=f"save_seat_{cid}"):
                if update_company_seat_limit(cid, int(new_limit)):
                    st.success(f"✅ Seat limit {new_limit} ga o'zgartirildi!")
                    st.rerun()
                else:
                    st.error("Xato yuz berdi")

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

        # ── O'chirish ─────────────────────────────────
        with st.expander("🗑️ Kompaniyani O'chirish"):
            st.warning(
                f"**{name}** ni butunlay o'chirasizmi? "
                f"Barcha {user_count} ta user ham o'chiriladi!"
            )
            confirm = st.text_input(
                f"Tasdiqlash: kompaniya kodini yozing (`{code}`)",
                key=f"del_confirm_{cid}"
            )
            if st.button("O'chirish", key=f"del_btn_{cid}", type="primary"):
                if confirm.strip().lower() == code.lower():
                    if delete_company(cid):
                        st.success(f"{name} o'chirildi!")
                        st.rerun()
                    else:
                        st.error("Xato yuz berdi")
                else:
                    st.error("Kod noto'g'ri. O'chirish bekor qilindi.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FOYDALANUVCHILAR BO'LIMI (har bir kompaniya ichida)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _render_users_section(company_id: int, company_code: str, seat_limit: int):
    """Kompaniya foydalanuvchilari ro'yxati + qo'shish"""

    users = get_users_by_company(company_id)

    # ── Mavjud userlar ────────────────────────────────
    if users:
        for user in users:
            _render_user_row(user, company_code)
    else:
        st.info("Hali foydalanuvchi yo'q.")

    st.markdown("---")

    # ── Yangi user qo'shish ───────────────────────────
    current_count = len(users)
    if current_count >= seat_limit:
        st.warning(
            f"Seat limit to'ldi ({current_count}/{seat_limit}). "
            "Yangi user qo'shish uchun avval seat limitni oshiring."
        )
        return

    st.markdown(f"##### ➕ Yangi User ({current_count}/{seat_limit} band)")
    st.caption(f"Login formati: **username@{company_code.lower()}**")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        new_name = st.text_input(
            "Username",
            placeholder="olim",
            help=f"Faqat kichik lotin harf, raqam, nuqta, tire. Login: olim@{company_code.lower()}",
            key=f"new_user_name_{company_id}"
        )
    with col2:
        new_pass = st.text_input(
            "Parol",
            type="password",
            placeholder="Kamida 6 ta belgi",
            key=f"new_user_pass_{company_id}"
        )
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        add_clicked = st.button("➕ Qo'shish", key=f"add_user_{company_id}", use_container_width=True)

    if add_clicked:
        if not new_name.strip():
            st.error("Username kiritilishi shart")
        elif len(new_pass) < 6:
            st.error("Parol kamida 6 ta belgi bo'lishi kerak")
        else:
            user, err = create_user(company_id, new_name.strip().lower(), new_pass)
            if user:
                full = user['username']   # DB dan to'liq: 'olim@smartup'
                st.success(f"✅ **{full}** yaratildi! Login: `{full}`")
                st.rerun()
            else:
                st.error(f"❌ {err}")


def _render_user_row(user: dict, company_code: str):
    """Bitta user satri: info + parol reset + o'chirish"""

    uid        = user['id']
    full_login = user['username']   # DB da to'liq saqlanadi: 'olim@smartup'
    is_active  = bool(user.get('is_active', 1))
    created    = user.get('created_at', '')[:10]
    status_icon = "✅" if is_active else "❌"

    with st.container():
        col1, col2, col3, col4 = st.columns([3, 1.5, 1.5, 1.5])

        with col1:
            st.markdown(
                f"{status_icon} `{full_login}` "
                f"<span style='color:#8b949e; font-size:0.78rem;'>  yaratilgan: {created}</span>",
                unsafe_allow_html=True
            )

        with col2:
            toggle_label = "Nofaol" if is_active else "Faollashtir"
            if st.button(toggle_label, key=f"utoggle_{uid}", use_container_width=True):
                update_user_status(uid, not is_active)
                st.rerun()

        with col3:
            if st.button("Parol", key=f"upreset_show_{uid}", use_container_width=True):
                st.session_state[f"show_reset_{uid}"] = not st.session_state.get(f"show_reset_{uid}", False)

        with col4:
            if st.button("O'chirish", key=f"udel_{uid}", use_container_width=True, type="secondary"):
                st.session_state[f"confirm_del_{uid}"] = True

    # Parol reset formasi
    if st.session_state.get(f"show_reset_{uid}"):
        with st.container():
            c1, c2 = st.columns([3, 1])
            with c1:
                new_p = st.text_input(
                    f"Yangi parol ({name})",
                    type="password",
                    placeholder="Kamida 6 ta belgi",
                    key=f"reset_pass_{uid}"
                )
            with c2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Saqlash", key=f"do_reset_{uid}"):
                    if len(new_p) < 6:
                        st.error("Kamida 6 ta belgi bo'lishi kerak")
                    elif update_user_password(uid, new_p):
                        st.success(f"✅ Parol yangilandi!")
                        st.session_state.pop(f"show_reset_{uid}", None)
                        st.rerun()
                    else:
                        st.error("Xato yuz berdi")

    # O'chirish tasdiqi
    if st.session_state.get(f"confirm_del_{uid}"):
        st.warning(f"**{full_login}** ni o'chirasizmi?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Ha, o'chirish", key=f"do_del_{uid}", type="primary"):
                if delete_user(uid):
                    st.success(f"✅ {full_login} o'chirildi")
                    st.session_state.pop(f"confirm_del_{uid}", None)
                    st.rerun()
                else:
                    st.error("Xato yuz berdi")
        with c2:
            if st.button("Bekor qilish", key=f"cancel_del_{uid}"):
                st.session_state.pop(f"confirm_del_{uid}", None)
                st.rerun()

    st.markdown('<hr style="margin:0.3rem 0; opacity:0.15;">', unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# YANGI KOMPANIYA YARATISH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _render_create_company():
    st.markdown("### ➕ Yangi Kompaniya")

    st.markdown("""
    <div style="background:rgba(88,166,255,0.08); padding:1rem; border-radius:8px; margin-bottom:1.2rem;">
        <p style="color:#8b949e; margin:0; font-size:0.85rem;">
            💡 Kompaniya yaratgandan so'ng userlarni qo'shing.
            Har bir user o'z <code>username@company_code</code> va paroli bilan kiradi.
            Kompaniya foydalanuvchilari bir xil API kalitlarini (JIRA, GitHub, Gemini) baham ko'radi.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        company_code = st.text_input(
            "Kompaniya Kodi *",
            placeholder="smartup",
            help="Faqat kichik lotin harf va raqam. Login: username@bu_kod"
        )
        company_name = st.text_input(
            "Kompaniya Nomi *",
            placeholder="Smartup Inc"
        )
    with col2:
        seat_limit = st.number_input(
            "Seat Limit *",
            min_value=1,
            max_value=100,
            value=1,
            step=1,
            help="Kompaniyada nechta user bo'lishi mumkin? Default: 1"
        )
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Keyinroq seat limitni oshirish mumkin.")

    st.markdown("---")

    # ── Modul ruxsatlari ────────────────────────────
    st.markdown("#### 🔧 Modul Ruxsatlari")
    st.caption("Bu kompaniya userlariga qaysi modullar ko'rinsin?")

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

    selected = [ALL_MODULES[k] for k, v in new_mods.items() if v]
    if selected:
        st.success(f"✅ Tanlangan modullar: {', '.join(selected)}")
    else:
        st.warning("⚠️ Hech qaysi modul tanlanmagan. Userlar tizimga kirsa bo'sh sahifa ko'radi.")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("➕ Kompaniya Yaratish", type="primary"):
        errors = []
        clean_code = company_code.strip().lower()
        if not clean_code:
            errors.append("Kompaniya kodi kiritilishi shart")
        elif not clean_code.replace('-', '').replace('_', '').isalnum():
            errors.append("Kompaniya kodi: faqat kichik lotin harf va raqam")
        if not company_name.strip():
            errors.append("Kompaniya nomi kiritilishi shart")

        if errors:
            for e in errors:
                st.error(e)
        else:
            result = create_company(
                clean_code,
                company_name.strip(),
                seat_limit=int(seat_limit),
                enabled_modules=new_mods
            )
            if result:
                st.success(f"✅ **{company_name.strip()}** kompaniyasi yaratildi!")
                st.markdown(f"""
                <div style="background:rgba(54,179,126,0.1); border:1px solid #36B37E;
                            padding:1.2rem; border-radius:10px; margin-top:1rem;">
                    <h4 style="color:#36B37E; margin:0 0 0.8rem 0;">
                        📋 Kompaniya ma'lumotlari
                    </h4>
                    <p style="color:#e6edf3; margin:0; font-size:0.95rem; line-height:1.8;">
                        <strong>Kompaniya Kodi:</strong>
                        <code style="background:rgba(88,166,255,0.15); padding:2px 10px;
                                     border-radius:4px;">{clean_code}</code><br>
                        <strong>Seat Limit:</strong> {seat_limit} ta user<br>
                        <strong>Login formati:</strong>
                        <code style="background:rgba(88,166,255,0.15); padding:2px 10px;
                                     border-radius:4px;">username@{clean_code}</code><br>
                        <strong>Modullar:</strong>
                        {', '.join(selected) if selected else 'Hech qaysi'}
                    </p>
                    <p style="color:#8b949e; margin-top:0.8rem; font-size:0.78rem;">
                        Endi "Kompaniyalar" tabidan userlarni qo'shing.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"❌ '{clean_code}' kodi allaqachon mavjud yoki xato yuz berdi.")
