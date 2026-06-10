"""
Bloomberg Terminal — Personal Edition
Entry point with MFA authentication gate.
"""

import streamlit as st
import pyotp
import time
import os
from datetime import datetime

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Terminal | Personal Bloomberg",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load CSS ──────────────────────────────────────────────────────────────────
with open("assets/style.css", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Auth helpers ──────────────────────────────────────────────────────────────
def check_password(pw: str) -> bool:
    import hashlib, hmac
    stored = os.environ.get("APP_PASSWORD_HASH", "")
    h = hashlib.sha256(pw.encode()).hexdigest()
    return hmac.compare_digest(h, stored)

def check_totp(code: str) -> bool:
    secret = os.environ.get("TOTP_SECRET", "")
    if not secret:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)

def auth_gate():
    """Show login screen; returns True if authenticated."""
    if st.session_state.get("authenticated"):
        return True

    st.markdown("""
        <div class="auth-container">
            <div class="auth-logo">
                <span class="auth-logo-bb">BB</span>
                <span class="auth-logo-text">TERMINAL</span>
            </div>
            <p class="auth-subtitle">Personal Bloomberg — Secure Access</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container():
            st.markdown('<div class="auth-card">', unsafe_allow_html=True)

            step = st.session_state.get("auth_step", "password")

            if step == "password":
                st.markdown("#### 🔐 Password")
                pw = st.text_input("Password", type="password", key="pw_input",
                                   placeholder="Enter your password")
                if st.button("Continue →", use_container_width=True, type="primary"):
                    if check_password(pw):
                        st.session_state.auth_step = "totp"
                        st.rerun()
                    else:
                        st.error("Incorrect password.")

            elif step == "totp":
                st.markdown("#### 📱 Two-Factor Authentication")
                st.caption("Enter the 6-digit code from your authenticator app (Google Authenticator / Authy).")
                code = st.text_input("TOTP Code", key="totp_input",
                                     placeholder="000000", max_chars=6)
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("← Back", use_container_width=True):
                        st.session_state.auth_step = "password"
                        st.rerun()
                with col_b:
                    if st.button("Verify ✓", use_container_width=True, type="primary"):
                        if check_totp(code):
                            st.session_state.authenticated = True
                            st.session_state.auth_step = "password"
                            st.rerun()
                        else:
                            st.error("Invalid or expired code.")

            st.markdown('</div>', unsafe_allow_html=True)
    return False

# ── Navigation ─────────────────────────────────────────────────────────────────
TABS = {
    "📈 Market Data":        "pages/market_data.py",
    "📰 News Feed":          "pages/news_feed.py",
    "💼 Earnings & Fundamentals": "pages/earnings.py",
    "🎯 Options & Derivatives": "pages/options.py",
    "📊 Portfolio Tracker":  "pages/portfolio.py",
}

def sidebar_nav():
    with st.sidebar:
        st.markdown("""
            <div class="sidebar-header">
                <span class="bb-logo">BB</span> TERMINAL
            </div>
        """, unsafe_allow_html=True)

        now = datetime.utcnow()
        st.markdown(f'<div class="sidebar-clock">🕐 {now.strftime("%H:%M:%S")} UTC</div>',
                    unsafe_allow_html=True)
        st.markdown("---")

        selected = st.radio("Navigation", list(TABS.keys()),
                            label_visibility="collapsed")

        st.markdown("---")
        st.markdown('<div class="sidebar-footer">Global / Multi-Asset</div>',
                    unsafe_allow_html=True)

        if st.button("🔒 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.auth_step = "password"
            st.rerun()

    return selected

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    if not auth_gate():
        return

    tab = sidebar_nav()

    # Dynamically load the selected page module
    import importlib.util, sys
    path = TABS[tab]
    spec = importlib.util.spec_from_file_location("page_module", path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.render()

if __name__ == "__main__":
    main()
