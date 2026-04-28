"""
Login Sahifasi

Forma: Username + Parol
  - Oddiy user:   "olim@smartup" + parol
  - Super admin:  "superadmin"   + parol

Author: JASUR TURGUNOV
"""
import streamlit as st
from utils.auth.auth_manager import login


def render_login_page():
    """Login sahifasini ko'rsatish"""

    col1, col2, col3 = st.columns([1, 1.4, 1])

    with col2:
        # ━━━ Logo / Header ━━━
        st.markdown("""
        <div style="text-align:center; padding: 2rem 0 1rem 0;">
            <div style="font-size: 3.5rem; margin-bottom: 0.5rem;">🔬</div>
            <h1 style="color:#e6edf3; font-weight:700; margin:0; font-size:1.8rem;">
                QA Assistant
            </h1>
            <p style="color:#8b949e; font-size:0.9rem; margin-top:0.4rem;">
                AI-Powered Analysis Suite
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ━━━ Login Card ━━━
        st.markdown("""
        <div style="
            background: rgba(22,27,34,0.8);
            border: 1px solid rgba(48,54,61,0.8);
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        ">
        """, unsafe_allow_html=True)

        st.markdown(
            "<h3 style='color:#e6edf3; margin:0 0 1.5rem 0; font-size:1.1rem;'>"
            "🔐 Tizimga kirish</h3>",
            unsafe_allow_html=True
        )

        # Xato xabari (agar bo'lsa)
        if st.session_state.get('login_error'):
            st.error(st.session_state['login_error'])
            st.session_state.pop('login_error', None)

        # Form
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input(
                "Login",
                placeholder="olim@smartup",
                key="login_username_input"
            )
            password = st.text_input(
                "Parol",
                type="password",
                placeholder="••••••••",
                key="login_pass_input"
            )

            st.markdown("<br>", unsafe_allow_html=True)

            submitted = st.form_submit_button(
                "Kirish",
                type="primary",
                use_container_width=True
            )

        if submitted:
            if not username or not password:
                st.session_state['login_error'] = "Login va parolni kiriting"
                st.rerun()
            else:
                success, error_msg = login(username.strip(), password)
                if success:
                    st.rerun()
                else:
                    st.session_state['login_error'] = f"❌ {error_msg}"
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

        # ━━━ Footer ━━━
        st.markdown("""
        <div style="text-align:center; margin-top: 2rem;">
            <p style="color:#6e7681; font-size:0.75rem;">
                Login: <b style="color:#8b949e">username@kompaniya_kodi</b><br>
                Muammo bo'lsa admin bilan bog'laning.
            </p>
        </div>
        """, unsafe_allow_html=True)
