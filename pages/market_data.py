"""
pages/market_data.py — Tab 1: Market Data
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.data import (get_quote, get_history, get_multiple_quotes,
                        get_fred_series, get_fred_latest,
                        fmt_price, fmt_pct, fmt_large, color_class)

WATCHLISTS = {
    "My Watchlist":   ["ASML.AS","BRK-B","BLK","BE","CRWV","SNDK","SXR8.DE","XAD1.MI","TSM"],
    "Global Indices": ["^GSPC","^DJI","^IXIC","^FTSE","^GDAXI","^N225","^HSI"],
    "US Equities":    ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA",
                       "JPM","LMT","CVX","BLK","BRK-B","BE","CRWV","SNDK","TSM"],
    "Europe":         ["ASML.AS","SAP.DE","MC.PA","NESN.SW","SIE.DE","NOVO-B.CO"],
    "ETFs":           ["SPY","QQQ","IWM","EFA","EEM","GLD","TLT","VXX"],
    "FX":             ["EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","DX-Y.NYB"],
    "Crypto":         ["BTC-USD","ETH-USD","SOL-USD","BNB-USD"],
    "Commodities":    ["GC=F","SI=F","CL=F","NG=F","ZW=F"],
    "Futures":        ["SXR8.DE","XAD1.MI","NQ=F","ES=F","YM=F"],
}

# Suggested tickers for the chart dropdown
CHART_SUGGESTIONS = [
    "^GSPC","^DJI","^IXIC","SXR8.DE","XAD1.MI","NQ=F",
    "ASML.AS","BRK-B","BLK","BE","CVX","CRWV","JPM","LMT","SNDK","TSM",
    "AAPL","MSFT","NVDA","AMZN","META","TSLA",
    "BTC-USD","ETH-USD","GC=F","CL=F","EURUSD=X",
]

PERIOD_MAP = {"1D":"1d","5D":"5d","1M":"1mo","3M":"3mo","6M":"6mo",
              "1Y":"1y","2Y":"2y","5Y":"5y"}

CHART_BG = "#141414"

def render_ticker_tape(quotes_df):
    parts = []
    for _, row in quotes_df.iterrows():
        if pd.isna(row.get("price")): continue
        sym   = row["ticker"]
        px    = fmt_price(row["price"])
        pct   = row.get("change_pct")
        cls   = "tick-up" if (pct and pct > 0) else "tick-down" if (pct and pct < 0) else ""
        sign  = "▲" if (pct and pct > 0) else "▼" if (pct and pct < 0) else ""
        pct_s = f"{abs(pct):.2f}%" if pct else ""
        parts.append(f'<span class="{cls}"><b>{sym}</b> {px} {sign}{pct_s}</span>')
    tape = "  &nbsp;|&nbsp;  ".join(parts)
    st.markdown(f'<div class="ticker-bar">{tape}</div>', unsafe_allow_html=True)

def make_candle(ticker, period, interval):
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
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"], name="Volume", yaxis="y2",
        marker_color="rgba(2,66,179,0.25)",
    ))
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font=dict(family="IBM Plex Mono", color="#E0E0E0", size=11),
        xaxis=dict(gridcolor="#2E2E2E", showgrid=True, rangeslider_visible=False),
        yaxis=dict(gridcolor="#2E2E2E", showgrid=True, side="right"),
        yaxis2=dict(overlaying="y", side="left", showgrid=False,
                    range=[0, df["Volume"].max() * 5]),
        legend=dict(bgcolor="#1C1C1C", bordercolor="#2E2E2E"),
        margin=dict(l=0, r=60, t=30, b=0), height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

def make_line(ticker, period, interval):
    df = get_history(ticker, period=period, interval=interval)
    if df.empty:
        st.warning(f"No data for {ticker}")
        return
    fig = go.Figure(go.Scatter(
        x=df.index, y=df["Close"],
        line=dict(color="#0353D9", width=1.5),
        fill="tozeroy", fillcolor="rgba(2,66,179,0.08)",
    ))
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font=dict(family="IBM Plex Mono", color="#E0E0E0", size=11),
        xaxis=dict(gridcolor="#2E2E2E", showgrid=True),
        yaxis=dict(gridcolor="#2E2E2E", showgrid=True, side="right"),
        margin=dict(l=0, r=60, t=30, b=0), height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

def render_vix_chart():
    df = get_fred_series("VIXCLS", limit=252)
    if df.empty:
        return
    fig = go.Figure(go.Scatter(
        x=df["date"], y=df["value"],
        line=dict(color="#0353D9", width=1.5),
        fill="tozeroy", fillcolor="rgba(2,66,179,0.10)",
        name="VIX",
    ))
    # Fear zones
    fig.add_hline(y=20, line_dash="dot", line_color="#FFCC00",
                  annotation_text="20 — Elevated", annotation_position="right")
    fig.add_hline(y=30, line_dash="dot", line_color="#FF3333",
                  annotation_text="30 — Fear", annotation_position="right")
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font=dict(family="IBM Plex Mono", color="#E0E0E0", size=10),
        xaxis=dict(gridcolor="#2E2E2E", showgrid=True),
        yaxis=dict(gridcolor="#2E2E2E", showgrid=True, title="VIX"),
        margin=dict(l=0, r=20, t=20, b=0), height=220,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

def render():
    st.markdown("""
        <div class="page-header">
            <span class="page-title">Market Data</span>
            <span class="page-subtitle">Global / Multi-Asset · Yahoo Finance · FRED</span>
        </div>
    """, unsafe_allow_html=True)

    # ── Macro strip ────────────────────────────────────────────────────────────
    macro = {
        "Fed Funds Rate": ("FEDFUNDS", "%"),
        "CPI":            ("CPIAUCSL", ""),
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

    # ── Ticker tape ────────────────────────────────────────────────────────────
    with st.spinner("Loading quotes…"):
        tape_tickers = ["^GSPC","^DJI","^IXIC","^FTSE","^GDAXI","^N225",
                        "BTC-USD","GC=F","CL=F","EURUSD=X","SXR8.DE","NQ=F"]
        tape_df = get_multiple_quotes(tape_tickers)
    render_ticker_tape(tape_df)

    # ── Chart + Watchlist + VIX ────────────────────────────────────────────────
    col_chart, col_watch = st.columns([3, 1])

    with col_chart:
        st.markdown('<div class="bb-card">', unsafe_allow_html=True)
        st.markdown('<div class="bb-card-title">Chart</div>', unsafe_allow_html=True)

        c1, c2, c3 = st.columns([2, 2, 3])
        with c1:
            # Check for global search override
            default_ticker = st.session_state.pop("search_override", "^GSPC")
            chart_ticker = st.selectbox(
                "Ticker", CHART_SUGGESTIONS,
                index=CHART_SUGGESTIONS.index(default_ticker)
                      if default_ticker in CHART_SUGGESTIONS else 0,
                key="chart_ticker_select"
            )
            custom = st.text_input("Or type any ticker", placeholder="e.g. NVDA",
                                   key="chart_custom")
            if custom:
                chart_ticker = custom.upper().strip()
        with c2:
            period_label = st.selectbox("Period", list(PERIOD_MAP.keys()), index=5)
        with c3:
            chart_type = st.radio("Type", ["Candle", "Line"], horizontal=True)

        period   = PERIOD_MAP[period_label]
        interval = "1h" if period in ["1d","5d"] else "1d"

        if chart_type == "Line":
            make_line(chart_ticker, period, interval)
        else:
            make_candle(chart_ticker, period, interval)

        st.markdown('</div>', unsafe_allow_html=True)

        # VIX chart below main chart
        st.markdown('<div class="bb-card-title" style="margin-top:0.5rem">VIX — CBOE Volatility Index (1Y)</div>',
                    unsafe_allow_html=True)
        render_vix_chart()

    with col_watch:
        st.markdown('<div class="bb-card-title">Watchlist</div>', unsafe_allow_html=True)
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
    st.markdown('<div class="bb-card-title">Quote Table</div>', unsafe_allow_html=True)
    default_tickers = "ASML.AS,BRK-B,BLK,BE,CVX,CRWV,JPM,LMT,SNDK,TSM,SXR8.DE,XAD1.MI,"
    custom_tickers = st.text_input(
        "Tickers (comma-separated)", value=default_tickers,
        help="Any Yahoo Finance ticker symbol"
    )
    if custom_tickers:
        tk_list = [t.strip().upper() for t in custom_tickers.split(",") if t.strip()]
        with st.spinner("Fetching…"):
            full_df = get_multiple_quotes(tk_list)
        if not full_df.empty:
            display = full_df[["ticker","price","change","change_pct",
                                "volume","market_cap"]].copy()
            display.columns = ["Ticker","Price","Change","Chg %","Volume","Mkt Cap"]
            display["Price"]   = display["Price"].apply(fmt_price)
            display["Change"]  = display["Change"].apply(fmt_price)
            display["Chg %"]   = display["Chg %"].apply(fmt_pct)
            display["Volume"]  = display["Volume"].apply(fmt_large)
            display["Mkt Cap"] = display["Mkt Cap"].apply(fmt_large)
            st.dataframe(display, use_container_width=True, hide_index=True)
