"""
pages/earnings.py — Tab 3: Earnings & Fundamentals
FMP for financials, yfinance as fallback.

Changes:
  - Added Institutional Holders section in Company Deep-Dive
  - Fixed FMP earning_calendar API call (correct endpoint + params)
  - FMP API key debug helper shown inline if key is missing
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
import requests
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.data import get_fmp, get_history, fmt_price, fmt_large, fmt_pct

METRIC_LABELS = {
    "trailingPE":         "P/E (TTM)",
    "forwardPE":          "P/E (Fwd)",
    "priceToBook":        "P/B",
    "priceToSalesTrailing12Months": "P/S",
    "enterpriseToEbitda": "EV/EBITDA",
    "debtToEquity":       "D/E",
    "returnOnEquity":     "ROE",
    "returnOnAssets":     "ROA",
    "profitMargins":      "Net Margin",
    "grossMargins":       "Gross Margin",
    "revenueGrowth":      "Revenue Growth",
    "earningsGrowth":     "Earnings Growth",
    "dividendYield":      "Div Yield",
    "beta":               "Beta",
    "52WeekChange":       "52W Return",
}

def _fmp_key() -> str:
    """Retrieve FMP API key from secrets or environment."""
    try:
        k = st.secrets.get("FMP_API_KEY", "")
        if k:
            return k
    except Exception:
        pass
    return os.environ.get("FMP_API_KEY", "")

def render_kpi_row(info: dict):
    metrics_to_show = [
        ("trailingPE",    "P/E (TTM)",   False),
        ("forwardPE",     "P/E (Fwd)",   False),
        ("priceToBook",   "P/B",         False),
        ("enterpriseToEbitda", "EV/EBITDA", False),
        ("debtToEquity",  "D/E",         False),
        ("returnOnEquity","ROE",          True),
        ("profitMargins", "Net Margin",   True),
        ("dividendYield", "Div Yield",    True),
        ("beta",          "Beta",         False),
        ("52WeekChange",  "52W Return",   True),
    ]
    cols = st.columns(5)
    for i, (key, label, is_pct) in enumerate(metrics_to_show):
        val = info.get(key)
        if val is not None:
            val_s = f"{val*100:.2f}%" if is_pct else f"{val:.2f}"
        else:
            val_s = "—"
        cols[i % 5].markdown(f"""
            <div class="metric-tile" style="margin-bottom:8px">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="font-size:1.1rem">{val_s}</div>
            </div>
        """, unsafe_allow_html=True)


def render_income_chart(ticker: str):
    """Revenue + Net Income bar chart via FMP or yfinance."""
    fmp_data = get_fmp("income-statement", ticker, {"limit": 8})
    if isinstance(fmp_data, list) and fmp_data:
        dates   = [r.get("date", "")[:4] for r in fmp_data][::-1]
        revenue = [r.get("revenue", 0) / 1e9 for r in fmp_data][::-1]
        net_inc = [r.get("netIncome", 0) / 1e9 for r in fmp_data][::-1]
    else:
        try:
            t  = yf.Ticker(ticker)
            fs = t.financials
            if fs is None or fs.empty:
                st.info("No income statement data available.")
                return
            dates   = [str(c)[:10] for c in fs.columns][::-1]
            revenue = [fs.loc["Total Revenue", c] / 1e9
                       if "Total Revenue" in fs.index else 0 for c in fs.columns][::-1]
            net_inc = [fs.loc["Net Income", c] / 1e9
                       if "Net Income" in fs.index else 0 for c in fs.columns][::-1]
        except Exception:
            st.info("Financial data unavailable.")
            return

    fig = go.Figure()
    fig.add_trace(go.Bar(x=dates, y=revenue, name="Revenue (B)",  marker_color="#0242B3"))
    fig.add_trace(go.Bar(x=dates, y=net_inc, name="Net Income (B)", marker_color="#00CC66"))
    fig.update_layout(
        barmode="group",
        paper_bgcolor="#141414", plot_bgcolor="#141414",
        font=dict(family="IBM Plex Mono", color="#E0E0E0", size=11),
        xaxis=dict(gridcolor="#2E2E2E"),
        yaxis=dict(gridcolor="#2E2E2E", title="USD Billions"),
        legend=dict(bgcolor="#1C1C1C"),
        margin=dict(l=0, r=0, t=30, b=0),
        height=280,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_institutional_holders(ticker: str):
    """
    Institutional & mutual fund holders.
    Primary: FMP /institutional-holder/{ticker}
    Fallback: yfinance .institutional_holders + .mutualfund_holders
    """
    st.markdown('<div class="bb-card-title" style="margin-top:1rem">Institutional Holders</div>',
                unsafe_allow_html=True)

    fmp_key = _fmp_key()
    fmp_holders = []

    # ── Try FMP first ──────────────────────────────────────────────────────────
    if fmp_key:
        try:
            url = f"https://financialmodelingprep.com/api/v3/institutional-holder/{ticker}"
            resp = requests.get(url, params={"apikey": fmp_key}, timeout=8)
            data = resp.json()
            if isinstance(data, list) and data:
                fmp_holders = data
        except Exception:
            pass

    if fmp_holders:
        df = pd.DataFrame(fmp_holders)
        # Normalise column names from FMP response
        rename = {
            "holder":     "Institution",
            "shares":     "Shares",
            "dateReported": "Date",
            "change":     "Change",
            "value":      "Value (USD)",
        }
        df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
        # Keep the columns we have
        keep = [c for c in ["Institution","Shares","Value (USD)","Change","Date"] if c in df.columns]
        df = df[keep].head(20)
        if "Shares" in df.columns:
            df["Shares"] = df["Shares"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
        if "Value (USD)" in df.columns:
            df["Value (USD)"] = df["Value (USD)"].apply(fmt_large)
        if "Change" in df.columns:
            df["Change"] = df["Change"].apply(
                lambda x: f"+{int(x):,}" if (pd.notna(x) and x >= 0) else f"{int(x):,}" if pd.notna(x) else "—"
            )
        st.dataframe(df, use_container_width=True, hide_index=True)
        return

    # ── yfinance fallback ──────────────────────────────────────────────────────
    try:
        t   = yf.Ticker(ticker)
        ih  = t.institutional_holders
        mfh = t.mutualfund_holders

        col_inst, col_mf = st.columns(2)

        with col_inst:
            st.markdown('<div style="font-family:IBM Plex Mono;font-size:0.7rem;'
                        'color:#0353D9;margin-bottom:4px">INSTITUTIONS</div>',
                        unsafe_allow_html=True)
            if ih is not None and not ih.empty:
                ih2 = ih.copy()
                if "Shares" in ih2.columns:
                    ih2["Shares"] = ih2["Shares"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
                if "Value" in ih2.columns:
                    ih2["Value"] = ih2["Value"].apply(fmt_large)
                if "% Out" in ih2.columns:
                    ih2["% Out"] = ih2["% Out"].apply(lambda x: f"{x*100:.2f}%" if pd.notna(x) else "—")
                st.dataframe(ih2, use_container_width=True, hide_index=True)
            else:
                st.info("No institutional holder data.")

        with col_mf:
            st.markdown('<div style="font-family:IBM Plex Mono;font-size:0.7rem;'
                        'color:#0353D9;margin-bottom:4px">MUTUAL FUNDS</div>',
                        unsafe_allow_html=True)
            if mfh is not None and not mfh.empty:
                mf2 = mfh.copy()
                if "Shares" in mf2.columns:
                    mf2["Shares"] = mf2["Shares"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
                if "Value" in mf2.columns:
                    mf2["Value"] = mf2["Value"].apply(fmt_large)
                if "% Out" in mf2.columns:
                    mf2["% Out"] = mf2["% Out"].apply(lambda x: f"{x*100:.2f}%" if pd.notna(x) else "—")
                st.dataframe(mf2, use_container_width=True, hide_index=True)
            else:
                st.info("No mutual fund holder data.")

    except Exception as e:
        st.warning(f"Holder data unavailable: {e}")


def render_earnings_calendar():
    """
    Upcoming earnings via FMP.

    FIX: The old code called get_fmp("earning_calendar", extra=...) which
    passes ticker as a path segment → wrong URL.  The earning_calendar endpoint
    takes NO ticker — it's a date-range query at v3/earning_calendar?from=&to=.
    We call it directly here so we control the full URL.
    """
    from datetime import date, timedelta

    fmp_key = _fmp_key()
    if not fmp_key:
        st.warning("⚠️ FMP_API_KEY not found in secrets.toml or environment variables. "
                   "Add it as FMP_API_KEY = 'your_key_here'")
        return

    today = date.today().isoformat()
    week  = (date.today() + timedelta(days=7)).isoformat()

    try:
        url  = "https://financialmodelingprep.com/api/v3/earning_calendar"
        resp = requests.get(url, params={"from": today, "to": week, "apikey": fmp_key}, timeout=10)
        data = resp.json()
    except Exception as e:
        st.error(f"FMP request failed: {e}")
        return

    # FMP returns {"Error Message": "..."} when key is invalid
    if isinstance(data, dict) and "Error Message" in data:
        st.error(f"FMP API error: {data['Error Message']}")
        st.caption("Check that your FMP_API_KEY is valid at financialmodelingprep.com")
        return

    if not isinstance(data, list) or not data:
        st.info("No earnings events found for the next 7 days.")
        return

    df = pd.DataFrame(data)
    cols_want = ["symbol", "date", "eps", "epsEstimated", "revenue", "revenueEstimated", "time"]
    df = df[[c for c in cols_want if c in df.columns]].copy()

    rename = {
        "symbol":           "Ticker",
        "date":             "Date",
        "eps":              "EPS Act.",
        "epsEstimated":     "EPS Est.",
        "revenue":          "Rev. Act.",
        "revenueEstimated": "Rev. Est.",
        "time":             "Time",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    for col in ["EPS Act.", "EPS Est."]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"${x:.2f}" if pd.notna(x) and x else "—")
    for col in ["Rev. Act.", "Rev. Est."]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: fmt_large(x) if pd.notna(x) and x else "—")

    st.dataframe(df, use_container_width=True, hide_index=True)


def render():
    st.markdown("""
        <div class="page-header">
            <span class="page-title">Earnings & Fundamentals</span>
            <span class="page-subtitle">FMP · Yahoo Finance</span>
        </div>
    """, unsafe_allow_html=True)

    tab_search, tab_cal = st.tabs(["🔍 Company Deep-Dive", "📅 Earnings Calendar"])

    with tab_search:
        c1, c2 = st.columns([2, 3])
        with c1:
            ticker = st.text_input("Ticker symbol", value="AAPL",
                                   placeholder="e.g. MSFT, ASML.AS").upper().strip()
        with c2:
            st.markdown("<br>", unsafe_allow_html=True)
            load = st.button("Load Fundamentals →", type="primary")

        if ticker and load:
            with st.spinner(f"Loading {ticker}…"):
                t    = yf.Ticker(ticker)
                info = t.info or {}

            name     = info.get("longName") or info.get("shortName", ticker)
            sector   = info.get("sector",   "—")
            industry = info.get("industry", "—")
            mktcap   = fmt_large(info.get("marketCap"))
            exch     = info.get("exchange", "—")
            curr     = info.get("currency", "USD")

            st.markdown(f"""
                <div class="bb-card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start">
                        <div>
                            <div style="font-family:'IBM Plex Mono';font-size:1.3rem;
                                        font-weight:600;color:#0242B3">{ticker}</div>
                            <div style="font-size:1rem;color:#E0E0E0">{name}</div>
                            <div style="font-size:0.72rem;color:#888;font-family:'IBM Plex Mono';
                                        margin-top:4px">{sector} · {industry} · {exch} · {curr}</div>
                        </div>
                        <div style="text-align:right;font-family:'IBM Plex Mono'">
                            <div style="font-size:0.65rem;color:#888">MARKET CAP</div>
                            <div style="font-size:1.2rem;color:#E0E0E0">{mktcap}</div>
                        </div>
                    </div>
                    <div style="font-size:0.78rem;color:#999;margin-top:0.75rem;line-height:1.5">
                        {(info.get('longBusinessSummary','')[:400] + '…') if info.get('longBusinessSummary') else ''}
                    </div>
                </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="bb-card-title">Key Metrics</div>', unsafe_allow_html=True)
            render_kpi_row(info)

            st.markdown('<div class="bb-card-title" style="margin-top:1rem">Income Statement</div>',
                        unsafe_allow_html=True)
            render_income_chart(ticker)

            # ── Institutional Holders (NEW) ────────────────────────────────────
            render_institutional_holders(ticker)

            # Analyst targets
            target = info.get("targetMeanPrice")
            rec    = info.get("recommendationKey", "—").upper()
            recs   = info.get("numberOfAnalystOpinions", "—")
            if target:
                st.markdown(f"""
                    <div class="bb-card" style="margin-top:0.5rem">
                        <div class="bb-card-title">Analyst Consensus</div>
                        <div style="display:flex;gap:2rem;font-family:'IBM Plex Mono'">
                            <div>
                                <div style="font-size:0.65rem;color:#888">CONSENSUS</div>
                                <div style="font-size:1.2rem;color:#0242B3;font-weight:600">{rec}</div>
                            </div>
                            <div>
                                <div style="font-size:0.65rem;color:#888">PRICE TARGET</div>
                                <div style="font-size:1.2rem;color:#E0E0E0">${target:.2f}</div>
                            </div>
                            <div>
                                <div style="font-size:0.65rem;color:#888"># ANALYSTS</div>
                                <div style="font-size:1.2rem;color:#E0E0E0">{recs}</div>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    with tab_cal:
        st.markdown('<div class="bb-card-title">Upcoming Earnings — Next 7 Days</div>',
                    unsafe_allow_html=True)
        render_earnings_calendar()
        st.caption("Source: Financial Modeling Prep · Requires FMP_API_KEY in secrets.toml")