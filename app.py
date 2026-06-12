"""
Custom Terminal — Personal Edition
Entry point with MFA authentication gate.
Top navigation bar layout.
"""

import streamlit as st
import pyotp
import os
from datetime import datetime

st.set_page_config(
    page_title="Custom Terminal",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

with open("assets/style.css", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Auth helpers ───────────────────────────────────────────────────────────────
def _get_secret(key: str) -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, "")

def check_password(pw: str) -> bool:
    import hashlib, hmac
    stored = _get_secret("APP_PASSWORD_HASH")
    h = hashlib.sha256(pw.encode()).hexdigest()
    return hmac.compare_digest(h, stored)

def check_demo_password(pw: str) -> bool:
    """Demo password — skips TOTP entirely, for recruiters."""
    import hashlib, hmac
    stored = _get_secret("DEMO_PASSWORD_HASH")
    if not stored:
        return False
    h = hashlib.sha256(pw.encode()).hexdigest()
    return hmac.compare_digest(h, stored)

def check_totp(code: str) -> bool:
    secret = _get_secret("TOTP_SECRET")
    if not secret:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)

def auth_gate():
    if st.session_state.get("authenticated"):
        return True

    st.markdown("""
        <div class="auth-container">
            <div class="auth-logo">
                <span class="auth-logo-bb">CT</span>
                <span class="auth-logo-text">CUSTOM TERMINAL</span>
            </div>
            <p class="auth-subtitle">Secure Access</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        step = st.session_state.get("auth_step", "password")

        if step == "password":
            st.markdown("#### Password")
            pw = st.text_input("Password", type="password", key="pw_input",
                               placeholder="Enter your password")
            if st.button("Continue", use_container_width=True, type="primary"):
                if check_demo_password(pw):
                    # Demo account — skip TOTP
                    st.session_state.authenticated = True
                    st.session_state.is_demo = True
                    st.session_state.auth_step = "password"
                    st.rerun()
                elif check_password(pw):
                    st.session_state.auth_step = "totp"
                    st.rerun()
                else:
                    st.error("Incorrect password.")

        elif step == "totp":
            st.markdown("#### Two-Factor Authentication")
            st.caption("Enter the 6-digit code from your authenticator app.")
            code = st.text_input("TOTP Code", key="totp_input",
                                 placeholder="000000", max_chars=6)
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Back", use_container_width=True):
                    st.session_state.auth_step = "password"
                    st.rerun()
            with col_b:
                if st.button("Verify", use_container_width=True, type="primary"):
                    if check_totp(code):
                        st.session_state.authenticated = True
                        st.session_state.is_demo = False
                        st.session_state.auth_step = "password"
                        st.rerun()
                    else:
                        st.error("Invalid or expired code.")
        st.markdown('</div>', unsafe_allow_html=True)
    return False

# ── Navigation ─────────────────────────────────────────────────────────────────
TABS = {
    "Market Data":             "pages/market_data.py",
    "News Feed":               "pages/news_feed.py",
    "Earnings & Fundamentals": "pages/earnings.py",
    "Options & Derivatives":   "pages/options.py",
    "Portfolio Tracker":       "pages/portfolio.py",
}

def top_nav():
    now = datetime.utcnow().strftime("%d/%m/%y  %H:%M UTC")
    tab_keys = list(TABS.keys())
    current  = st.session_state.get("active_tab", tab_keys[0])

    st.markdown(f"""
        <div class="topbar">
            <div class="topbar-left">
                <span class="topbar-logo">CT</span>
                <span class="topbar-title">CUSTOM TERMINAL</span>
            </div>
            <div class="topbar-clock">{now}</div>
        </div>
    """, unsafe_allow_html=True)

    cols = st.columns(len(tab_keys) + 2)
    for i, tab_name in enumerate(tab_keys):
        with cols[i]:
            if st.button(tab_name, key=f"tab_{i}",
                         use_container_width=True,
                         type="primary" if tab_name == current else "secondary"):
                st.session_state.active_tab = tab_name
                st.rerun()

    with cols[len(tab_keys)]:
        search_query = st.text_input("", placeholder="Search ticker...",
                                     label_visibility="collapsed",
                                     key="global_search")
        if search_query:
            st.session_state.active_tab = "Market Data"
            st.session_state.search_override = search_query.upper().strip()
            st.rerun()

    with cols[len(tab_keys) + 1]:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Log out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.is_demo = False
            st.session_state.auth_step = "password"
            st.rerun()

    st.markdown('<div class="tab-divider"></div>', unsafe_allow_html=True)
    return current

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    if not auth_gate():
        return

    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Market Data"

    tab = top_nav()
    active = st.session_state.get("active_tab", tab)

    import importlib.util, sys
    path = TABS[active]
    spec = importlib.util.spec_from_file_location("page_module", path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.render()

if __name__ == "__main__":
    main()