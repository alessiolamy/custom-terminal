"""
pages/market_data.py — Tab 1: Market Data
Global equities, ETFs, crypto, FX, commodities.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.data import (get_quote, get_history, get_multiple_quotes,
                        get_fred_latest, fmt_price, fmt_pct, fmt_large, color_class)

# ── Default watchlists ─────────────────────────────────────────────────────────
WATCHLISTS = {
    "🌍 Global Indices": ["^GSPC", "^DJI", "^IXIC", "^FTSE", "^GDAXI", "^N225", "^HSI"],
    "🇺🇸 US Equities":   ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","BRK-B"],
    "🇪🇺 Europe":        ["ASML.AS","SAP.DE","MC.PA","NESN.SW","SIE.DE","NOVO-B.CO"],
    "📦 ETFs":           ["SPY","QQQ","IWM","EFA","EEM","GLD","TLT","VXX"],
    "💱 FX":             ["EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","DX-Y.NYB"],
    "₿ Crypto":         ["BTC-USD","ETH-USD","SOL-USD","BNB-USD"],
    "🛢️ Commodities":   ["GC=F","SI=F","CL=F","NG=F","ZW=F"],
}

PERIOD_MAP = {"1D":"1d","5D":"5d","1M":"1mo","3M":"3mo","6M":"6mo",
              "1Y":"1y","2Y":"2y","5Y":"5y"}

def render_ticker_tape(quotes_df: pd.DataFrame):
    parts = []
    for _, row in quotes_df.iterrows():
        if "error" in row or pd.isna(row.get("price")):
            continue
        sym  = row["ticker"]
        px   = fmt_price(row["price"])
        pct  = row.get("change_pct")
        cls  = "tick-up" if (pct and pct > 0) else "tick-down" if (pct and pct < 0) else ""
        sign = "▲" if (pct and pct > 0) else "▼" if (pct and pct < 0) else ""
        pct_s = f"{abs(pct):.2f}%" if pct else ""
        parts.append(f'<span class="{cls}"><b>{sym}</b> {px} {sign}{pct_s}</span>')
    tape = "  &nbsp;|&nbsp;  ".join(parts)
    st.markdown(f'<div class="ticker-bar">{tape}</div>', unsafe_allow_html=True)

def render_chart(ticker: str, period: str, interval: str):
    df = get_history(ticker, period=period, interval=interval)
    if df.empty:
        st.warning(f"No data for {ticker}")
        return
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        increasing_line_color="#00CC66", decreasing_line_color="#FF3333",
        name=ticker,
    ))
    # Volume bars
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"],
        name="Volume", yaxis="y2",
        marker_color="rgba(255,102,0,0.25)",
    ))
    fig.update_layout(
        paper_bgcolor="#141414", plot_bgcolor="#141414",
        font=dict(family="IBM Plex Mono", color="#E0E0E0", size=11),
        xaxis=dict(gridcolor="#2E2E2E", showgrid=True, rangeslider_visible=False),
        yaxis=dict(gridcolor="#2E2E2E", showgrid=True, side="right"),
        yaxis2=dict(overlaying="y", side="left", showgrid=False,
                    range=[0, df["Volume"].max() * 5]),
        legend=dict(bgcolor="#1C1C1C", bordercolor="#2E2E2E"),
        margin=dict(l=0, r=60, t=30, b=0),
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

def render():
    st.markdown("""
        <div class="page-header">
            <span class="page-title">📈 Market Data</span>
            <span class="page-subtitle">Global / Multi-Asset · Real-time via Yahoo Finance</span>
        </div>
    """, unsafe_allow_html=True)

    # ── Macro strip (FRED) ─────────────────────────────────────────────────────
    macro = {
        "Fed Funds Rate": ("FEDFUNDS", "%"),
        "CPI YoY":        ("CPIAUCSL", "idx"),
        "10Y Yield":      ("DGS10", "%"),
        "USD Index":      ("DTWEXBGS", ""),
        "VIX":            ("VIXCLS", ""),
    }
    cols = st.columns(len(macro))
    for (label, (sid, unit)), col in zip(macro.items(), cols):
        val = get_fred_latest(sid)
        val_s = f"{val:.2f}{unit}" if val else "—"
        col.markdown(f"""
            <div class="metric-tile">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{val_s}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Ticker tape (global indices) ───────────────────────────────────────────
    with st.spinner("Loading quotes…"):
        tape_tickers = ["^GSPC","^DJI","^IXIC","^FTSE","^GDAXI","^N225",
                        "BTC-USD","GC=F","CL=F","EURUSD=X"]
        tape_df = get_multiple_quotes(tape_tickers)
    render_ticker_tape(tape_df)

    # ── Main layout: chart left, watchlist right ───────────────────────────────
    col_chart, col_watch = st.columns([3, 1])

    with col_chart:
        st.markdown('<div class="bb-card">', unsafe_allow_html=True)
        st.markdown('<div class="bb-card-title">Chart</div>', unsafe_allow_html=True)

        c1, c2, c3 = st.columns([2, 2, 3])
        with c1:
            chart_ticker = st.text_input("Ticker", value="^GSPC",
                                          placeholder="e.g. AAPL").upper().strip()
        with c2:
            period_label = st.selectbox("Period", list(PERIOD_MAP.keys()), index=5)
        with c3:
            chart_type = st.radio("Type", ["Candle", "Line"], horizontal=True)

        period = PERIOD_MAP[period_label]
        interval = "1h" if period in ["1d","5d"] else "1d"

        if chart_type == "Line":
            df = get_history(chart_ticker, period=period, interval=interval)
            if not df.empty:
                fig = go.Figure(go.Scatter(
                    x=df.index, y=df["Close"],
                    line=dict(color="#0B4B99", width=1.5),
                    fill="tozeroy", fillcolor="rgba(255,102,0,0.08)",
                ))
                fig.update_layout(
                    paper_bgcolor="#141414", plot_bgcolor="#141414",
                    font=dict(family="IBM Plex Mono", color="#E0E0E0", size=11),
                    xaxis=dict(gridcolor="#2E2E2E", showgrid=True),
                    yaxis=dict(gridcolor="#2E2E2E", showgrid=True, side="right"),
                    margin=dict(l=0, r=60, t=30, b=0), height=400,
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            render_chart(chart_ticker, period, interval)

        st.markdown('</div>', unsafe_allow_html=True)

    with col_watch:
        st.markdown('<div class="bb-card-title">Watchlists</div>', unsafe_allow_html=True)
        wl_name = st.selectbox("List", list(WATCHLISTS.keys()), label_visibility="collapsed")
        tickers = WATCHLISTS[wl_name]

        with st.spinner(""):
            qdf = get_multiple_quotes(tickers)

        for _, row in qdf.iterrows():
            if "error" in row: continue
            pct  = row.get("change_pct")
            cls  = color_class(pct)
            sign = "▲" if (pct and pct > 0) else "▼" if (pct and pct < 0) else ""
            pct_s = f"{sign} {abs(pct):.2f}%" if pct else "—"
            st.markdown(f"""
                <div style="display:flex;justify-content:space-between;
                            padding:5px 0;border-bottom:1px solid #2E2E2E;
                            font-family:'IBM Plex Mono';font-size:0.78rem;">
                    <span style="color:#E0E0E0;font-weight:500">{row['ticker']}</span>
                    <span>
                        <span style="color:#E0E0E0">{fmt_price(row.get('price'))}</span>&nbsp;
                        <span class="metric-change {cls}">{pct_s}</span>
                    </span>
                </div>
            """, unsafe_allow_html=True)

    # ── Full quote table ───────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="bb-card-title">Full Quote Table</div>', unsafe_allow_html=True)
    custom_tickers = st.text_input(
        "Tickers (comma-separated)", value="AAPL,MSFT,NVDA,AMZN,META,^GSPC,GC=F,BTC-USD",
        help="Enter any Yahoo Finance ticker symbols"
    )
    if custom_tickers:
        tk_list = [t.strip().upper() for t in custom_tickers.split(",") if t.strip()]
        with st.spinner("Fetching…"):
            full_df = get_multiple_quotes(tk_list)
        if not full_df.empty:
            display = full_df[["ticker","price","change","change_pct",
                                "volume","market_cap"]].copy()
            display.columns = ["Ticker","Price","Change","Chg %","Volume","Mkt Cap"]
            display["Price"]   = display["Price"].apply(lambda x: fmt_price(x))
            display["Change"]  = display["Change"].apply(lambda x: fmt_price(x))
            display["Chg %"]   = display["Chg %"].apply(lambda x: fmt_pct(x))
            display["Volume"]  = display["Volume"].apply(fmt_large)
            display["Mkt Cap"] = display["Mkt Cap"].apply(fmt_large)
            st.dataframe(display, use_container_width=True, hide_index=True)
