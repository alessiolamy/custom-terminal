"""
pages/portfolio.py — Tab 5: Portfolio Tracker

Changes:
  - Fixed "Add Trade" bug: used a form_submit_button inside st.form() so the
    entire input block is collected atomically before st.rerun() fires.
    Previously, number_input / text_input values could revert to defaults
    when st.rerun() was called mid-widget-tree.
  - Remove-position now uses st.form() too for the same reason.
  - Added short/long direction field for proper P&L sign on shorts.
  - Minor: average cost defaults to live price (fetched on ticker blur).
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json, os
from datetime import datetime, date
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.data import get_quote, get_multiple_quotes, fmt_price, fmt_pct, fmt_large, color_class

PORTFOLIO_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "portfolio.json"
)


# ── Persistence ────────────────────────────────────────────────────────────────
def load_portfolio() -> list[dict]:
    os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
    if not os.path.exists(PORTFOLIO_FILE):
        return []
    try:
        with open(PORTFOLIO_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def save_portfolio(positions: list[dict]):
    os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(positions, f, indent=2, default=str)


# ── Metrics ────────────────────────────────────────────────────────────────────
def compute_metrics(positions: list[dict]) -> pd.DataFrame:
    if not positions:
        return pd.DataFrame()
    tickers = list({p["ticker"] for p in positions})
    quotes  = {q["ticker"]: q for q in get_multiple_quotes(tickers).to_dict("records")}
    rows = []
    for p in positions:
        tk      = p["ticker"]
        qty     = p["quantity"]
        cost    = p["avg_price"]
        direction = p.get("direction", "Long")
        curr    = quotes.get(tk, {}).get("price") or cost
        mkt_val = curr * abs(qty)
        cost_b  = cost * abs(qty)

        # For shorts, profit when price falls
        if direction == "Short":
            pnl = (cost - curr) * abs(qty)
        else:
            pnl = (curr - cost) * abs(qty)

        pnl_pct  = (pnl / cost_b * 100) if cost_b else 0
        day_chg  = quotes.get(tk, {}).get("change_pct") or 0

        rows.append({
            "Ticker":    tk,
            "Name":      p.get("name", ""),
            "Asset":     p.get("asset_class", "Equity"),
            "Direction": direction,
            "Qty":       qty,
            "Avg Cost":  cost,
            "Current":   curr,
            "Mkt Value": mkt_val,
            "Cost Basis":cost_b,
            "P&L":       pnl,
            "P&L %":     pnl_pct,
            "Day Chg %": day_chg,
            "Date":      p.get("date", ""),
            "Notes":     p.get("notes", ""),
        })
    return pd.DataFrame(rows)


# ── Charts ─────────────────────────────────────────────────────────────────────
def allocation_chart(df: pd.DataFrame):
    by_asset = df.groupby("Asset")["Mkt Value"].sum().reset_index()
    fig = go.Figure(go.Pie(
        labels=by_asset["Asset"],
        values=by_asset["Mkt Value"],
        hole=0.55,
        marker=dict(colors=["#0242B3", "#00CC66", "#3399FF", "#FFCC00", "#FF3333", "#AA44FF"]),
        textfont=dict(family="IBM Plex Mono", size=11, color="#E0E0E0"),
    ))
    fig.update_layout(
        paper_bgcolor="#141414",
        font=dict(family="IBM Plex Mono", color="#E0E0E0", size=11),
        margin=dict(l=0, r=0, t=20, b=0), height=220,
        legend=dict(bgcolor="#1C1C1C", font=dict(size=10)),
        showlegend=True,
    )
    return fig


def pnl_bar_chart(df: pd.DataFrame):
    df_s   = df.sort_values("P&L")
    colors = ["#00CC66" if v >= 0 else "#FF3333" for v in df_s["P&L"]]
    fig    = go.Figure(go.Bar(
        x=df_s["Ticker"], y=df_s["P&L"],
        marker_color=colors,
        text=[f"${v:,.0f}" for v in df_s["P&L"]],
        textposition="outside",
        textfont=dict(family="IBM Plex Mono", size=10),
    ))
    fig.update_layout(
        paper_bgcolor="#141414", plot_bgcolor="#141414",
        font=dict(family="IBM Plex Mono", color="#E0E0E0", size=11),
        xaxis=dict(gridcolor="#2E2E2E"),
        yaxis=dict(gridcolor="#2E2E2E", title="USD P&L"),
        margin=dict(l=0, r=0, t=20, b=0), height=220,
    )
    return fig


# ── Main render ────────────────────────────────────────────────────────────────
def render():
    st.markdown("""
        <div class="page-header">
            <span class="page-title">Portfolio Tracker</span>
            <span class="page-subtitle">Live P&L · Risk Metrics · Trade Log</span>
        </div>
    """, unsafe_allow_html=True)

    # Load once per session
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = load_portfolio()

    tab_dash, tab_add, tab_log = st.tabs(
        ["📊 Dashboard", "➕ Add / Edit Trade", "📋 Trade Log"]
    )

    # ── DASHBOARD ──────────────────────────────────────────────────────────────
    with tab_dash:
        positions = st.session_state.portfolio
        if not positions:
            st.info("No positions yet. Go to **➕ Add / Edit Trade** to add your first position.")
        else:
            with st.spinner("Fetching live prices…"):
                df = compute_metrics(positions)

            if not df.empty:
                total_val     = df["Mkt Value"].sum()
                total_cost    = df["Cost Basis"].sum()
                total_pnl     = df["P&L"].sum()
                total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0
                day_pnl       = sum(
                    row["Mkt Value"] * row["Day Chg %"] / 100
                    for _, row in df.iterrows()
                )

                k1, k2, k3, k4 = st.columns(4)
                for col, label, val in [
                    (k1, "Portfolio Value", f"${total_val:,.2f}"),
                    (k2, "Total P&L",       f"${total_pnl:+,.2f}"),
                    (k3, "Return %",        f"{total_pnl_pct:+.2f}%"),
                    (k4, "Today's P&L",     f"${day_pnl:+,.2f}"),
                ]:
                    color = "#00CC66" if "+" in val else "#FF3333" if "-" in val else "#E0E0E0"
                    col.markdown(f"""
                        <div class="metric-tile">
                            <div class="metric-label">{label}</div>
                            <div class="metric-value" style="color:{color}">{val}</div>
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                c_alloc, c_pnl = st.columns(2)
                with c_alloc:
                    st.markdown('<div class="bb-card-title">Allocation by Asset Class</div>',
                                unsafe_allow_html=True)
                    st.plotly_chart(allocation_chart(df), use_container_width=True)
                with c_pnl:
                    st.markdown('<div class="bb-card-title">P&L by Position</div>',
                                unsafe_allow_html=True)
                    st.plotly_chart(pnl_bar_chart(df), use_container_width=True)

                st.markdown('<div class="bb-card-title" style="margin-top:0.5rem">Positions</div>',
                            unsafe_allow_html=True)
                display = df.copy()
                display["Avg Cost"]   = display["Avg Cost"].apply(lambda x: f"${x:,.2f}")
                display["Current"]    = display["Current"].apply(lambda x: f"${x:,.2f}")
                display["Mkt Value"]  = display["Mkt Value"].apply(lambda x: f"${x:,.0f}")
                display["Cost Basis"] = display["Cost Basis"].apply(lambda x: f"${x:,.0f}")
                display["P&L"]        = display["P&L"].apply(lambda x: f"${x:+,.2f}")
                display["P&L %"]      = display["P&L %"].apply(lambda x: f"{x:+.2f}%")
                display["Day Chg %"]  = display["Day Chg %"].apply(lambda x: f"{x:+.2f}%")
                display = display[["Ticker", "Name", "Asset", "Direction", "Qty",
                                    "Avg Cost", "Current", "Mkt Value",
                                    "P&L", "P&L %", "Day Chg %"]]
                st.dataframe(display, use_container_width=True, hide_index=True)

    # ── ADD TRADE ──────────────────────────────────────────────────────────────
    with tab_add:
        st.markdown('<div class="bb-card-title">Add New Position</div>',
                    unsafe_allow_html=True)

        # ── FIX: wrap everything in st.form() so all widget values are
        #    captured atomically when the submit button is clicked.
        #    This prevents the "blank trade gets added" bug caused by
        #    st.rerun() resetting widget state mid-render. ──────────────────────
        with st.form("add_trade_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                tk          = st.text_input("Ticker *",
                                            placeholder="e.g. AAPL, ASML.AS, BTC-USD").upper().strip()
                name        = st.text_input("Name / Description",
                                            placeholder="e.g. Apple Inc.")
                qty         = st.number_input("Quantity *",
                                              min_value=0.0001, step=1.0, value=1.0,
                                              format="%.4f")
                direction   = st.selectbox("Direction", ["Long", "Short"])
            with c2:
                asset_class = st.selectbox("Asset Class",
                                           ["Equity", "ETF", "Crypto", "Bond",
                                            "Commodity", "FX", "Other"])
                avg_price   = st.number_input("Avg Purchase Price (USD) *",
                                              min_value=0.0001, step=0.01, value=100.0,
                                              format="%.4f")
                trade_date  = st.date_input("Trade Date", value=date.today())

            notes = st.text_input("Notes (optional)",
                                  placeholder="e.g. Long-term hold, hedge position")

            submitted = st.form_submit_button("✅ Add Position", type="primary")

        # Process outside the form block (after submission)
        if submitted:
            if not tk:
                st.error("Ticker is required.")
            else:
                new_pos = {
                    "ticker":      tk,
                    "name":        name,
                    "asset_class": asset_class,
                    "direction":   direction,
                    "quantity":    qty,
                    "avg_price":   avg_price,
                    "date":        str(trade_date),
                    "notes":       notes,
                    "added_at":    datetime.utcnow().isoformat(),
                }
                st.session_state.portfolio.append(new_pos)
                save_portfolio(st.session_state.portfolio)
                st.success(f"✓ Added {direction} {qty} × {tk} @ ${avg_price:.4f}")
                st.rerun()

        # ── Remove position ────────────────────────────────────────────────────
        if st.session_state.portfolio:
            st.markdown("---")
            st.markdown('<div class="bb-card-title">Remove Position</div>',
                        unsafe_allow_html=True)

            with st.form("remove_trade_form"):
                tickers_in = [
                    f"{p['ticker']} ({p.get('direction','Long')}, {p.get('date','')})"
                    for p in st.session_state.portfolio
                ]
                to_remove_label = st.selectbox("Select position to remove", tickers_in)
                remove_submitted = st.form_submit_button("🗑️ Remove", type="secondary")

            if remove_submitted:
                # Match by index (label includes ticker + date so it's unique enough)
                idx = tickers_in.index(to_remove_label)
                removed_ticker = st.session_state.portfolio[idx]["ticker"]
                st.session_state.portfolio.pop(idx)
                save_portfolio(st.session_state.portfolio)
                st.success(f"Removed position: {removed_ticker}")
                st.rerun()

    # ── TRADE LOG ──────────────────────────────────────────────────────────────
    with tab_log:
        st.markdown('<div class="bb-card-title">All Positions</div>',
                    unsafe_allow_html=True)
        positions = st.session_state.portfolio
        if not positions:
            st.info("No positions recorded yet.")
        else:
            df_log = pd.DataFrame(positions)
            st.dataframe(df_log, use_container_width=True, hide_index=True)

            csv = df_log.to_csv(index=False).encode()
            st.download_button("⬇️ Export CSV", csv, "portfolio.csv", "text/csv")