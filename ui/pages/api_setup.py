"""
Majburiy API Kalitlar Setup Sahifasi

Kompaniya birinchi marta kirganida (yoki JIRA/GitHub token yo'q bo'lsa)
bu sahifa ko'rsatiladi. JIRA va GitHub majburiy, Figma ixtiyoriy.

Kalitlar "Mening API Kalitlarim" (user_credentials) ga saqlanadi.
Webhook API Kalitlari alohida sozlamalar sahifasida.

Author: JASUR TURGUNOV
"""
import streamlit as st
from utils.auth.auth_db import (
    get_user_credentials,
    save_user_credentials,
    has_user_credentials_configured,
)
from utils.auth.auth_manager import get_auth_info, logout


def needs_api_setup() -> bool:
    """User majburiy API kalitlarini kirmagan bo'lsa True"""
    auth = get_auth_info()
    if auth.get('role') != 'user':
        return False
    user_id = auth.get('user_id')
    if not user_id:
        return False
    return not has_user_credentials_configured(user_id)


def render_api_setup():
    """Majburiy API kalitlar kiritish sahifasi"""
    auth = get_auth_info()
    company_name = auth.get('company_name', '')
    user_id = auth.get('user_id')

    uc = get_user_credentials(user_id) if user_id else {}

    # ━━━ Header ━━━
    col1, col2, col3 = st.columns([1, 1.6, 1])
    with col2:
        st.markdown(f"""
        <div style="text-align:center; padding:1.5rem 0 1rem 0;">
            <div style="font-size:3rem;">🔑</div>
            <h2 style="color:#e6edf3; font-weight:700; margin:0.5rem 0 0.3rem 0;">
                API Kalitlarni Sozlang
            </h2>
            <p style="color:#58a6ff; font-size:0.95rem; margin:0;">
                {company_name}
            </p>
            <p style="color:#8b949e; font-size:0.85rem; margin-top:0.4rem;">
                Tizimdan foydalanish uchun API kalitlarni bir marta kiriting
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:

        # ━━━ Progress indikator ━━━
        jira_done   = bool(uc.get('jira_email') and uc.get('jira_token') and uc.get('jira_project_keys'))
        github_done = bool(uc.get('github_token'))
        gemini_done = bool(uc.get('gemini_api_key_1'))

        def _badge(done, label):
            bg  = 'rgba(54,179,126,0.15)' if done else 'rgba(255,86,48,0.1)'
            clr = '#36B37E' if done else '#FF5630'
            ico = '✅' if done else '⏳'
            return (f'<div style="flex:1; padding:0.5rem; border-radius:8px; text-align:center;'
                    f'background:{bg}; border:1px solid {clr};">'
                    f'<span style="font-size:0.8rem; color:{clr};">{ico} {label}</span></div>')

        st.markdown(f"""
        <div style="display:flex; gap:0.5rem; margin-bottom:1.5rem;">
            {_badge(jira_done,   'JIRA')}
            {_badge(github_done, 'GitHub')}
            {_badge(gemini_done, 'Gemini AI')}
            <div style="flex:1; padding:0.5rem; border-radius:8px; text-align:center;
                        background:rgba(88,166,255,0.08); border:1px solid rgba(88,166,255,0.2);">
                <span style="font-size:0.8rem; color:#58a6ff;">🔵 Figma (ixtiyoriy)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ━━━ JIRA ━━━
        st.markdown("""
        <div style="background:rgba(22,27,34,0.7); border:1px solid rgba(48,54,61,0.8);
                    border-radius:12px; padding:1.5rem; margin-bottom:1rem;">
        <h4 style="color:#58a6ff; margin:0 0 1rem 0;">🔵 JIRA — Majburiy</h4>
        """, unsafe_allow_html=True)

        jira_server = st.text_input(
            "JIRA Server URL",
            value=uc.get('jira_server', ''),
            placeholder="https://yourcompany.atlassian.net",
            key="setup_jira_server"
        )
        jira_email = st.text_input(
            "JIRA Email *",
            value=uc.get('jira_email', ''),
            placeholder="admin@yourcompany.com",
            key="setup_jira_email"
        )
        jira_token = st.text_input(
            "JIRA API Token *",
            value=uc.get('jira_token', ''),
            type="password",
            placeholder="ATATT3xFf...",
            key="setup_jira_token",
            help="Atlassian hesob → Xavfsizlik → API tokenlar sahifasidan oling"
        )
        jira_project_keys = st.text_input(
            "JIRA Project Key(lar) *",
            value=uc.get('jira_project_keys', ''),
            placeholder="DEV, QA, PROD",
            key="setup_jira_project_keys",
            help="Vergul bilan ajrating. Masalan: DEV, QA, PRODUCT"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # ━━━ GitHub ━━━
        st.markdown("""
        <div style="background:rgba(22,27,34,0.7); border:1px solid rgba(48,54,61,0.8);
                    border-radius:12px; padding:1.5rem; margin-bottom:1rem;">
        <h4 style="color:#e6edf3; margin:0 0 1rem 0;">🐙 GitHub — Majburiy</h4>
        """, unsafe_allow_html=True)

        github_token = st.text_input(
            "GitHub Token *",
            value=uc.get('github_token', ''),
            type="password",
            placeholder="ghp_xxxx...",
            key="setup_github_token",
            help="GitHub → Settings → Developer settings → Personal access tokens → Generate new token"
        )
        github_org = st.text_input(
            "GitHub Organization nomi",
            value=uc.get('github_org', ''),
            placeholder="your-org-name",
            key="setup_github_org"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # ━━━ Gemini AI ━━━
        st.markdown("""
        <div style="background:rgba(22,27,34,0.7); border:1px solid rgba(48,54,61,0.8);
                    border-radius:12px; padding:1.5rem; margin-bottom:1rem;">
        <h4 style="color:#f78166; margin:0 0 1rem 0;">🤖 Google Gemini AI — Majburiy</h4>
        """, unsafe_allow_html=True)

        gemini_key_1 = st.text_input(
            "Gemini API Key *",
            value=uc.get('gemini_api_key_1', ''),
            type="password",
            placeholder="AIzaSy...",
            key="setup_gemini_1",
            help="Google AI Studio (aistudio.google.com) → Get API Key → Create API key"
        )
        gemini_key_2 = st.text_input(
            "Gemini API Key (zaxira, ixtiyoriy)",
            value=uc.get('gemini_api_key_2', ''),
            type="password",
            placeholder="AIzaSy...",
            key="setup_gemini_2",
            help="Birinchi kalit limitga tushsa avtomatik ishlatiladi"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # ━━━ Figma (ixtiyoriy) ━━━
        figma_token = uc.get('figma_token', '')
        with st.expander("🎨 Figma — Ixtiyoriy"):
            figma_token = st.text_input(
                "Figma Access Token",
                value=figma_token,
                type="password",
                placeholder="figd_xxxx...",
                key="setup_figma_token",
                help="Figma → Account Settings → Personal Access Tokens"
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ━━━ Xato xabari ━━━
        if st.session_state.get('setup_error'):
            st.error(st.session_state.pop('setup_error'))

        # ━━━ Saqlash tugmasi ━━━
        col_a, col_b = st.columns([2, 1])
        with col_a:
            if st.button("✅ Saqlash va Davom Etish", type="primary", use_container_width=True):
                errors = []
                if not jira_email.strip():
                    errors.append("JIRA Email kiritilishi shart")
                if not jira_token.strip():
                    errors.append("JIRA API Token kiritilishi shart")
                if not jira_project_keys.strip():
                    errors.append("JIRA Project Key(lar) kiritilishi shart (masalan: DEV)")
                if not github_token.strip():
                    errors.append("GitHub Token kiritilishi shart")
                if not gemini_key_1.strip():
                    errors.append("Gemini API Key kiritilishi shart")

                if errors:
                    st.session_state['setup_error'] = " | ".join(errors)
                    st.rerun()
                else:
                    new_creds = {
                        'jira_server':        jira_server.strip(),
                        'jira_email':         jira_email.strip(),
                        'jira_token':         jira_token.strip(),
                        'jira_project_keys':  jira_project_keys.strip(),
                        'github_token':       github_token.strip(),
                        'github_org':         github_org.strip(),
                        'figma_token':        figma_token.strip(),
                        'gemini_api_key_1':   gemini_key_1.strip(),
                        'gemini_api_key_2':   gemini_key_2.strip(),
                    }
                    if save_user_credentials(user_id, new_creds):
                        st.success("✅ Saqlandi!")
                        st.rerun()
                    else:
                        st.session_state['setup_error'] = "Saqlashda xato yuz berdi"
                        st.rerun()

        with col_b:
            if st.button("🚪 Chiqish", use_container_width=True):
                logout()
                st.rerun()