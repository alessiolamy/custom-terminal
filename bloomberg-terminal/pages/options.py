"""
pages/options.py — Tab 4: Options Chain & Derivatives
Tradier for options chain; yfinance as fallback.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.data import get_options_chain, get_options_expirations, get_fred_latest, fmt_price

def render_chain_from_yfinance(ticker: str, expiry: str):
    """Fallback options chain via yfinance."""
    try:
        t = yf.Ticker(ticker)
        opt = t.option_chain(expiry)
        calls = opt.calls.copy()
        puts  = opt.puts.copy()
        return calls, puts
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()

def render_chain_table(df: pd.DataFrame, side: str):
    if df.empty:
        st.info(f"No {side} data available.")
        return

    cols_yf  = ["strike","lastPrice","bid","ask","volume","openInterest",
                 "impliedVolatility","inTheMoney"]
    cols_tr  = ["strike","last","bid","ask","volume","open_interest","greeks.delta","greeks.gamma"]
    cols_use = cols_yf if "lastPrice" in df.columns else cols_tr

    df2 = df[[c for c in cols_use if c in df.columns]].copy()
    df2.columns = [c.replace("lastPrice","Last").replace("last","Last")
                    .replace("openInterest","OI").replace("open_interest","OI")
                    .replace("impliedVolatility","IV").replace("inTheMoney","ITM")
                    .replace("greeks.delta","Δ").replace("greeks.gamma","Γ")
                    .title() for c in df2.columns]

    # Format IV as pct
    if "Iv" in df2.columns:
        df2["Iv"] = df2["Iv"].apply(lambda x: f"{x*100:.1f}%" if x else "—")
    if "Itm" in df2.columns:
        df2["Itm"] = df2["Itm"].map({True:"✓",False:""})

    color = "#00CC66" if side == "Calls" else "#FF3333"
    st.markdown(f'<div style="color:{color};font-family:IBM Plex Mono;'
                f'font-size:0.7rem;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:0.1em;margin-bottom:4px">{side}</div>',
                unsafe_allow_html=True)
    st.dataframe(df2.head(50), use_container_width=True, hide_index=True)

def render_oi_chart(calls: pd.DataFrame, puts: pd.DataFrame):
    """Open interest by strike — shows max pain / support zones."""
    if calls.empty and puts.empty:
        return
    oi_col = "openInterest" if "openInterest" in calls.columns else "open_interest"
    if oi_col not in calls.columns:
        return

    strikes = sorted(set(calls["strike"].tolist() + puts["strike"].tolist()))
    c_oi = calls.set_index("strike")[oi_col].reindex(strikes, fill_value=0)
    p_oi = puts.set_index("strike")[oi_col].reindex(strikes, fill_value=0)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=strikes, y=c_oi, name="Calls OI",
                         marker_color="rgba(0,204,102,0.6)"))
    fig.add_trace(go.Bar(x=strikes, y=-p_oi, name="Puts OI",
                         marker_color="rgba(255,51,51,0.6)"))
    fig.update_layout(
        barmode="overlay",
        paper_bgcolor="#141414", plot_bgcolor="#141414",
        font=dict(family="IBM Plex Mono", color="#E0E0E0", size=11),
        xaxis=dict(gridcolor="#2E2E2E", title="Strike"),
        yaxis=dict(gridcolor="#2E2E2E", title="Open Interest"),
        legend=dict(bgcolor="#1C1C1C"),
        margin=dict(l=0, r=0, t=30, b=0),
        height=260,
    )
    st.plotly_chart(fig, use_container_width=True)

def render():
    st.markdown("""
        <div class="page-header">
            <span class="page-title">Options & Derivatives</span>
            <span class="page-subtitle">Tradier (if key set) · yfinance fallback</span>
        </div>
    """, unsafe_allow_html=True)

    # VIX strip
    vix = get_fred_latest("VIXCLS")
    vix_s = f"{vix:.2f}" if vix else "—"
    st.markdown(f"""
        <div style="display:flex;gap:1.5rem;margin-bottom:1rem">
            <div class="metric-tile">
                <div class="metric-label">VIX (CBOE)</div>
                <div class="metric-value">{vix_s}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        ticker = st.text_input("Ticker", value="SPY",
                               placeholder="e.g. AAPL, SPY").upper().strip()
    with c2:
        use_tradier = bool(os.environ.get("TRADIER_API_KEY") or _has_secret("TRADIER_API_KEY"))
        if use_tradier:
            expiries = get_options_expirations(ticker)
        else:
            try:
                expiries = list(yf.Ticker(ticker).options) if ticker else []
            except Exception:
                expiries = []

        expiry = st.selectbox("Expiration", expiries if expiries else ["—"])
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        load = st.button("Load Chain →", type="primary")

    if load and ticker and expiry and expiry != "—":
        with st.spinner(f"Loading {ticker} chain for {expiry}…"):
            if use_tradier:
                chain = get_options_chain(ticker, expiry)
                # Parse Tradier response
                options = chain.get("option", []) if isinstance(chain, dict) else []
                calls_df = pd.DataFrame([o for o in options if o.get("option_type")=="call"])
                puts_df  = pd.DataFrame([o for o in options if o.get("option_type")=="put"])
            else:
                calls_df, puts_df = render_chain_from_yfinance(ticker, expiry)

        st.markdown('<div class="bb-card-title">Open Interest by Strike</div>',
                    unsafe_allow_html=True)
        render_oi_chart(calls_df, puts_df)

        col_c, col_p = st.columns(2)
        with col_c:
            render_chain_table(calls_df, "Calls")
        with col_p:
            render_chain_table(puts_df, "Puts")

        if not use_tradier:
            st.caption("💡 Add TRADIER_API_KEY to secrets.toml for live greeks "
                       "(delta, gamma, theta, vega). Currently using yfinance fallback.")
    elif not ticker:
        st.info("Enter a ticker symbol above to load the options chain.")

def _has_secret(key: str) -> bool:
    try:
        return bool(st.secrets.get(key))
    except Exception:
        return False
