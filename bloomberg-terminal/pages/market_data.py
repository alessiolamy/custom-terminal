"""
pages/market_data.py — Tab 1: Market Data
Improved: editable watchlist, rich quote table, DXY chart, holders, world indices.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.data import (get_quote_full, get_multiple_quotes, get_history,
                        get_fred_series, get_fred_latest, get_holders,
                        fmt_price, fmt_pct, fmt_large, color_class)

WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                              "data", "watchlist.json")

DEFAULT_WATCHLIST = [
    "ASML.AS","BRK-B","BLK","BE","CRWV","SNDK","TSM",
    "JPM","LMT","CVX","SXR8.DE","NQ=F","GC=F","BTC-USD",
]

WORLD_INDICES = {
    "Americas":  ["^GSPC","^DJI","^IXIC","^RUT","^BVSP","^MXX"],
    "Europe":    ["^FTSE","^GDAXI","^FCHI","^AEX","^IBEX","^STOXX50E","^SSMI"],
    "Asia/Pac":  ["^N225","^HSI","000001.SS","^KS11","^AXJO","^STI","^TWII"],
    "Commodities":["GC=F","SI=F","CL=F","NG=F","ZW=F","ZC=F","HG=F"],
    "Bonds/FX":  ["^TNX","^TYX","^FVX","DX-Y.NYB","EURUSD=X","GBPUSD=X","USDJPY=X"],
}

PERIOD_MAP = {"1D":"1d","5D":"5d","1M":"1mo","3M":"3mo","6M":"6mo",
              "1Y":"1y","2Y":"2y","5Y":"5y"}
CHART_BG = "#141414"

# ── Watchlist persistence ──────────────────────────────────────────────────────
def load_watchlist() -> list:
    os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_WATCHLIST.copy()

def save_watchlist(tickers: list):
    os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(tickers, f)

# ── Charts ─────────────────────────────────────────────────────────────────────
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
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", yaxis="y2",
                         marker_color="rgba(2,66,179,0.25)"))
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font=dict(family="IBM Plex Mono", color="#E0E0E0", size=11),
        xaxis=dict(gridcolor="#2E2E2E", showgrid=True, rangeslider_visible=False),
        yaxis=dict(gridcolor="#2E2E2E", showgrid=True, side="right"),
        yaxis2=dict(overlaying="y", side="left", showgrid=False,
                    range=[0, df["Volume"].max()*5] if df["Volume"].max() > 0 else [0,1]),
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

def fred_line_chart(series_id: str, label: str, hlines: list = [], height=220):
    df = get_fred_series(series_id, limit=252)
    if df.empty:
        st.caption(f"No FRED data for {series_id}. Check FRED_API_KEY.")
        return
    fig = go.Figure(go.Scatter(
        x=df["date"], y=df["value"],
        line=dict(color="#0353D9", width=1.5),
        fill="tozeroy", fillcolor="rgba(2,66,179,0.10)",
        name=label,
    ))
    for level, color, text in hlines:
        fig.add_hline(y=level, line_dash="dot", line_color=color,
                      annotation_text=text, annotation_position="right")
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font=dict(family="IBM Plex Mono", color="#E0E0E0", size=10),
        xaxis=dict(gridcolor="#2E2E2E", showgrid=True),
        yaxis=dict(gridcolor="#2E2E2E", showgrid=True),
        margin=dict(l=0, r=20, t=20, b=0), height=height,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Ticker tape ────────────────────────────────────────────────────────────────
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
    st.markdown(f'<div class="ticker-bar">{"  &nbsp;|&nbsp;  ".join(parts)}</div>',
                unsafe_allow_html=True)

# ── Rich watchlist table ───────────────────────────────────────────────────────
def render_watchlist_table(tickers: list):
    """Fetch full quotes and render a rich table with price, bid, ask, day range, chg%."""
    if not tickers:
        st.info("No tickers in watchlist.")
        return

    rows = []
    # Use batch for speed, then enrich top ones
    with st.spinner("Updating watchlist…"):
        batch = get_multiple_quotes(tickers)
        batch_map = {r["ticker"]: r for r in batch.to_dict("records")}

    for tk in tickers:
        q = batch_map.get(tk, {})
        price = q.get("price")
        pct   = q.get("change_pct")
        chg   = q.get("change")
        rows.append({
            "Ticker":   tk,
            "Price":    fmt_price(price),
            "Chg":      fmt_price(chg),
            "Chg %":    fmt_pct(pct),
            "direction": pct,
        })

    for row in rows:
        d = row["direction"]
        color = "#00CC66" if (d and d > 0) else "#FF3333" if (d and d < 0) else "#E0E0E0"
        sign  = "▲" if (d and d > 0) else "▼" if (d and d < 0) else ""
        st.markdown(f"""
            <div style="display:grid;grid-template-columns:90px 80px 70px 80px;
                        gap:4px;padding:5px 0;border-bottom:1px solid #2E2E2E;
                        font-family:'IBM Plex Mono';font-size:0.76rem;align-items:center;">
                <span style="color:#E0E0E0;font-weight:600">{row['Ticker']}</span>
                <span style="color:#E0E0E0">{row['Price']}</span>
                <span style="color:{color}">{row['Chg']}</span>
                <span style="color:{color}">{sign} {abs(d):.2f}%</span>
            </div>
        """, unsafe_allow_html=True) if d is not None else st.markdown(f"""
            <div style="display:grid;grid-template-columns:90px 80px 70px 80px;
                        gap:4px;padding:5px 0;border-bottom:1px solid #2E2E2E;
                        font-family:'IBM Plex Mono';font-size:0.76rem;">
                <span style="color:#E0E0E0;font-weight:600">{row['Ticker']}</span>
                <span style="color:#E0E0E0">{row['Price']}</span>
                <span style="color:#888">—</span>
                <span style="color:#888">—</span>
            </div>
        """, unsafe_allow_html=True)

# ── Full quote table ───────────────────────────────────────────────────────────
def render_quote_table(tickers: list):
    """Rich quote table: price, bid, ask, day range, 52w range, vol, mkt cap."""
    if not tickers:
        return
    rows = []
    with st.spinner("Fetching full quotes…"):
        for tk in tickers:
            q = get_quote_full(tk)
            rows.append({
                "Ticker":    tk,
                "Name":      (q.get("name","") or "")[:22],
                "Price":     fmt_price(q.get("price")),
                "Bid":       fmt_price(q.get("bid")),
                "Ask":       fmt_price(q.get("ask")),
                "Chg %":     fmt_pct(q.get("change_pct")),
                "Open":      fmt_price(q.get("open")),
                "High":      fmt_price(q.get("day_high")),
                "Low":       fmt_price(q.get("day_low")),
                "52W High":  fmt_price(q.get("52w_high")),
                "52W Low":   fmt_price(q.get("52w_low")),
                "Volume":    fmt_large(q.get("volume")),
                "Mkt Cap":   fmt_large(q.get("market_cap")),
                "P/E":       fmt_price(q.get("pe"), 1) if q.get("pe") else "—",
                "Yield":     f"{q['yield']*100:.2f}%" if q.get("yield") else "—",
            })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

# ── Holders ────────────────────────────────────────────────────────────────────
def render_holders(ticker: str):
    data = get_holders(ticker)
    inst  = data.get("institutional", pd.DataFrame())
    major = data.get("major", pd.DataFrame())

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="bb-card-title">Institutional Holders</div>',
                    unsafe_allow_html=True)
        if inst is not None and not inst.empty:
            st.dataframe(inst.head(10), use_container_width=True, hide_index=True)
        else:
            st.caption("No institutional holder data available.")

    with c2:
        st.markdown('<div class="bb-card-title">Major Holders</div>',
                    unsafe_allow_html=True)
        if major is not None and not major.empty:
            st.dataframe(major, use_container_width=True, hide_index=True)
        else:
            st.caption("No major holder data available.")

# ── World indices table ────────────────────────────────────────────────────────
def render_world_indices():
    for region, tickers in WORLD_INDICES.items():
        st.markdown(f'<div class="bb-card-title">{region}</div>', unsafe_allow_html=True)
        df = get_multiple_quotes(tickers)
        rows = []
        for _, r in df.iterrows():
            pct = r.get("change_pct")
            rows.append({
                "Ticker": r["ticker"],
                "Price":  fmt_price(r.get("price")),
                "Chg %":  fmt_pct(pct),
            })
        tbl = pd.DataFrame(rows)
        st.dataframe(tbl, use_container_width=True, hide_index=True)
        st.markdown("<br>", unsafe_allow_html=True)

# ── Main render ────────────────────────────────────────────────────────────────
def render():
    st.markdown("""
        <div class="page-header">
            <span class="page-title">Market Data</span>
            <span class="page-subtitle">Global / Multi-Asset · Yahoo Finance · FRED</span>
        </div>
    """, unsafe_allow_html=True)

    # Init watchlist in session
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = load_watchlist()

    # ── Macro strip ────────────────────────────────────────────────────────────
    macro = {
        "Fed Funds":  ("FEDFUNDS", "%"),
        "CPI":        ("CPIAUCSL", ""),
        "10Y Yield":  ("DGS10", "%"),
        "DXY":        ("DTWEXBGS", ""),
        "VIX":        ("VIXCLS", ""),
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
    with st.spinner(""):
        tape_df = get_multiple_quotes(["^GSPC","^DJI","^IXIC","^FTSE","^GDAXI",
                                       "^N225","BTC-USD","GC=F","CL=F","EURUSD=X",
                                       "DX-Y.NYB","NQ=F"])
    render_ticker_tape(tape_df)

    # ── Tabs inside Market Data ─────────────────────────────────────────────────
    t1, t2, t3, t4, t5 = st.tabs([
        "Chart & Watchlist", "Quote Table", "World Indices", "Holders", "VIX & DXY"
    ])

    # ─── TAB 1: Chart + Watchlist ──────────────────────────────────────────────
    with t1:
        col_chart, col_watch = st.columns([3, 1])

        with col_chart:
            st.markdown('<div class="bb-card-title">Chart</div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2, 2, 2])
            with c1:
                default_t = st.session_state.pop("search_override", "^GSPC")
                chart_ticker = st.text_input("Ticker", value=default_t,
                                             placeholder="e.g. AAPL, SXR8.DE").upper().strip()
            with c2:
                period_label = st.selectbox("Period", list(PERIOD_MAP.keys()), index=5)
            with c3:
                chart_type = st.radio("Type", ["Candle","Line"], horizontal=True)

            period   = PERIOD_MAP[period_label]
            interval = "1h" if period in ["1d","5d"] else "1d"
            if chart_type == "Line":
                make_line(chart_ticker, period, interval)
            else:
                make_candle(chart_ticker, period, interval)

        with col_watch:
            st.markdown('<div class="bb-card-title">Watchlist</div>', unsafe_allow_html=True)
            render_watchlist_table(st.session_state.watchlist)

            # Edit watchlist inline
            with st.expander("Edit Watchlist"):
                current_str = ", ".join(st.session_state.watchlist)
                new_str = st.text_area(
                    "Tickers (comma-separated)",
                    value=current_str, height=120,
                    help="Edit, add, or remove tickers. One per line or comma-separated.",
                    key="wl_edit"
                )
                if st.button("Save Watchlist", type="primary", use_container_width=True):
                    new_list = [t.strip().upper() for t in new_str.replace("\n",",").split(",")
                                if t.strip()]
                    st.session_state.watchlist = new_list
                    save_watchlist(new_list)
                    st.success("Saved!")
                    st.rerun()

    # ─── TAB 2: Quote Table ────────────────────────────────────────────────────
    with t2:
        st.markdown('<div class="bb-card-title">Quote Table — Price · Bid · Ask · Range · Volume</div>',
                    unsafe_allow_html=True)
        st.caption("Editing tickers in the Watchlist tab also updates this table.")

        extra_input = st.text_input(
            "Add extra tickers here (comma-separated)",
            placeholder="e.g. NVDA, META, ^VIX",
            key="qt_extra"
        )
        extra = [t.strip().upper() for t in extra_input.split(",") if t.strip()] if extra_input else []
        all_tickers = list(dict.fromkeys(st.session_state.watchlist + extra))

        if st.button("Refresh Quotes", type="primary"):
            st.cache_data.clear() if hasattr(st, "cache_data") else None
        render_quote_table(all_tickers)

    # ─── TAB 3: World Indices ──────────────────────────────────────────────────
    with t3:
        st.markdown('<div class="bb-card-title">World Equity Indices, Commodities & Bonds</div>',
                    unsafe_allow_html=True)
        render_world_indices()

    # ─── TAB 4: Holders ────────────────────────────────────────────────────────
    with t4:
        st.markdown('<div class="bb-card-title">Institutional & Major Holders</div>',
                    unsafe_allow_html=True)
        h_ticker = st.text_input("Ticker", value="AAPL",
                                  placeholder="Enter stock ticker", key="holders_ticker").upper().strip()
        if st.button("Load Holders", type="primary"):
            render_holders(h_ticker)

    # ─── TAB 5: VIX & DXY Charts ──────────────────────────────────────────────
    with t5:
        c_vix, c_dxy = st.columns(2)
        with c_vix:
            st.markdown('<div class="bb-card-title">VIX — Volatility Index (1Y)</div>',
                        unsafe_allow_html=True)
            fred_line_chart("VIXCLS", "VIX",
                            hlines=[(20,"#FFCC00","20 — Elevated"),
                                    (30,"#FF3333","30 — Fear")])
        with c_dxy:
            st.markdown('<div class="bb-card-title">DXY — US Dollar Index (1Y)</div>',
                        unsafe_allow_html=True)
            fred_line_chart("DTWEXBGS", "DXY",
                            hlines=[(100,"#FFCC00","100 — Key level")])
