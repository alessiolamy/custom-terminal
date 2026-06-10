"""
pages/earnings.py — Tab 3: Earnings & Fundamentals
FMP for financials, yfinance as fallback.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
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

def render_kpi_row(info: dict):
    metrics_to_show = [
        ("trailingPE","P/E (TTM)", False),
        ("forwardPE","P/E (Fwd)", False),
        ("priceToBook","P/B", False),
        ("enterpriseToEbitda","EV/EBITDA", False),
        ("debtToEquity","D/E", False),
        ("returnOnEquity","ROE", True),
        ("profitMargins","Net Margin", True),
        ("dividendYield","Div Yield", True),
        ("beta","Beta", False),
        ("52WeekChange","52W Return", True),
    ]
    cols = st.columns(5)
    for i, (key, label, is_pct) in enumerate(metrics_to_show):
        val = info.get(key)
        if val is not None:
            if is_pct:
                val_s = f"{val*100:.2f}%"
            else:
                val_s = f"{val:.2f}"
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
        dates    = [r.get("date","")[:4] for r in fmp_data][::-1]
        revenue  = [r.get("revenue",0)/1e9 for r in fmp_data][::-1]
        net_inc  = [r.get("netIncome",0)/1e9 for r in fmp_data][::-1]
    else:
        # yfinance fallback
        try:
            t  = yf.Ticker(ticker)
            fs = t.financials
            if fs is None or fs.empty:
                st.info("No income statement data available.")
                return
            dates    = [str(c)[:10] for c in fs.columns][::-1]
            revenue  = [fs.loc["Total Revenue", c]/1e9
                        if "Total Revenue" in fs.index else 0 for c in fs.columns][::-1]
            net_inc  = [fs.loc["Net Income", c]/1e9
                        if "Net Income" in fs.index else 0 for c in fs.columns][::-1]
        except Exception:
            st.info("Financial data unavailable.")
            return

    fig = go.Figure()
    fig.add_trace(go.Bar(x=dates, y=revenue, name="Revenue (B)",
                         marker_color="#0B4B99"))
    fig.add_trace(go.Bar(x=dates, y=net_inc, name="Net Income (B)",
                         marker_color="#00CC66"))
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

def render_earnings_calendar():
    """Upcoming earnings via FMP."""
    from datetime import date, timedelta
    today = date.today().isoformat()
    week  = (date.today() + timedelta(days=7)).isoformat()
    data  = get_fmp(f"earning_calendar", extra={"from": today, "to": week})
    if isinstance(data, list) and data:
        df = pd.DataFrame(data)[["symbol","date","epsEstimated","revenueEstimated","time"]]
        df.columns = ["Ticker","Date","EPS Est.","Rev. Est. (B)","Time"]
        df["Rev. Est. (B)"] = df["Rev. Est. (B)"].apply(
            lambda x: f"{x/1e9:.2f}B" if x else "—"
        )
        df["EPS Est."] = df["EPS Est."].apply(
            lambda x: f"${x:.2f}" if x else "—"
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Earnings calendar requires an FMP API key. "
                "Add FMP_API_KEY to your secrets.")

def render():
    st.markdown("""
        <div class="page-header">
            <span class="page-title">💼 Earnings & Fundamentals</span>
            <span class="page-subtitle">FMP · Yahoo Finance · Alpha Vantage</span>
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
                t = yf.Ticker(ticker)
                info = t.info or {}

            # Header
            name = info.get("longName") or info.get("shortName", ticker)
            sector   = info.get("sector","—")
            industry = info.get("industry","—")
            mktcap   = fmt_large(info.get("marketCap"))
            exch     = info.get("exchange","—")
            curr     = info.get("currency","USD")

            st.markdown(f"""
                <div class="bb-card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start">
                        <div>
                            <div style="font-family:'IBM Plex Mono';font-size:1.3rem;
                                        font-weight:600;color:#FF6600">{ticker}</div>
                            <div style="font-size:1rem;color:#E0E0E0">{name}</div>
                            <div style="font-size:0.72rem;color:#888;font-family:'IBM Plex Mono';
                                        margin-top:4px">{sector} · {industry} · {exch} · {curr}</div>
                        </div>
                        <div style="text-align:right;font-family:'IBM Plex Mono'">
                            <div style="font-size:0.65rem;color:#888">MARKET CAP</div>
                            <div style="font-size:1.2rem;color:#E0E0E0">{mktcap}</div>
                        </div>
                    </div>
                    <div style="font-size:0.78rem;color:#999;margin-top:0.75rem;
                                line-height:1.5">
                        {(info.get('longBusinessSummary','')[:400] + '…') if info.get('longBusinessSummary') else ''}
                    </div>
                </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="bb-card-title">Key Metrics</div>', unsafe_allow_html=True)
            render_kpi_row(info)

            st.markdown('<div class="bb-card-title" style="margin-top:1rem">Income Statement</div>',
                        unsafe_allow_html=True)
            render_income_chart(ticker)

            # Analyst targets
            target = info.get("targetMeanPrice")
            rec    = info.get("recommendationKey","—").upper()
            recs   = info.get("numberOfAnalystOpinions","—")
            if target:
                st.markdown(f"""
                    <div class="bb-card" style="margin-top:0.5rem">
                        <div class="bb-card-title">Analyst Consensus</div>
                        <div style="display:flex;gap:2rem;font-family:'IBM Plex Mono'">
                            <div>
                                <div style="font-size:0.65rem;color:#888">CONSENSUS</div>
                                <div style="font-size:1.2rem;color:#FF6600;font-weight:600">{rec}</div>
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
        st.caption("Requires FMP_API_KEY. Add to .streamlit/secrets.toml")
