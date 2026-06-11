"""
pages/news_feed.py — Tab 2: News Feed
Includes Walter Bloomberg (@DeItaone) via Nitter RSS, fixed calendar dates.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.data import get_rss_feed, get_news, get_forex_factory_calendar

RSS_FEEDS = {
    "Financial Times":       "https://www.ft.com/rss/home",
    "The Economist":         "https://www.economist.com/finance-and-economics/rss.xml",
    "Wall Street Journal":   "https://feeds.a.omnimarc.com/rss/rss.wsj.com/wsj/pub/rss/market",
    "Reuters Business":      "https://feeds.reuters.com/reuters/businessNews",
    "Bloomberg Markets":     "https://feeds.bloomberg.com/markets/news.rss",
    "CNBC":                  "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "Seeking Alpha":         "https://seekingalpha.com/market_currents.xml",
    "Yahoo Finance":         "https://finance.yahoo.com/rss/topfinstories",
    # Walter Bloomberg / @DeItaone — via public Nitter RSS mirrors
    "Walter Bloomberg (X)":  "https://nitter.poast.org/DeItaone/rss",
}

IMPACT_COLORS = {
    "High":         "#FF3333",
    "Medium":       "#FFCC00",
    "Low":          "#666666",
    "Non-Economic": "#333333",
}

CURRENCIES_FILTER = {"USD", "EUR", "CHF", "GBP", "JPY"}

def fmt_pub_date(raw: str) -> str:
    """Parse various date formats → DD/MM/YY  HH:MM"""
    if not raw:
        return ""
    fmts = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(raw.strip(), fmt)
            return dt.strftime("%d/%m/%y  %H:%M")
        except Exception:
            pass
    # Try fromisoformat as last resort
    try:
        dt = datetime.fromisoformat(raw.replace("Z",""))
        return dt.strftime("%d/%m/%y  %H:%M")
    except Exception:
        return raw[:16]

def render_article(article: dict, source_label: str):
    title   = (article.get("title") or "").strip() or "No title"
    link    = article.get("link") or article.get("url","#")
    pub_raw = article.get("published") or article.get("publishedAt","")
    summary = article.get("summary") or article.get("description","")
    pub     = fmt_pub_date(str(pub_raw))
    if summary and len(summary) > 200:
        summary = summary[:197] + "…"
    # Strip HTML tags from summary
    import re
    summary = re.sub(r"<[^>]+>","", summary)

    is_x = "Walter Bloomberg" in source_label
    source_color = "#1DA1F2" if is_x else "#0353D9"

    st.markdown(f"""
        <div class="news-item">
            <div class="news-headline">
                <a href="{link}" target="_blank"
                   style="color:#E0E0E0;text-decoration:none;">{title}</a>
            </div>
            <div class="news-meta">
                <span style="color:{source_color};font-weight:600">{source_label}</span>
                &nbsp;·&nbsp; {pub}
            </div>
            {"<div style='font-size:0.76rem;color:#777;margin-top:3px'>" + summary + "</div>" if summary else ""}
        </div>
    """, unsafe_allow_html=True)

def render_calendar(events: list):
    filtered = [e for e in events
                if str(e.get("country","")).upper() in CURRENCIES_FILTER]

    if not filtered:
        st.info("No events this week for USD / EUR / CHF / GBP / JPY.")
        return

    # Header
    st.markdown("""
        <div style="display:grid;
                    grid-template-columns:85px 60px 55px 1fr 75px 75px 75px;
                    gap:6px;padding:6px 0;font-family:'IBM Plex Mono';
                    font-size:0.65rem;color:#0353D9;
                    border-bottom:2px solid #0242B3;margin-bottom:4px;
                    font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">
            <span>Date</span><span>Time</span><span>CCY</span>
            <span>Event</span><span>Impact</span><span>Actual</span>
            <span>Fore/Prev</span>
        </div>
    """, unsafe_allow_html=True)

    for ev in filtered[:100]:
        impact  = ev.get("impact","")
        col     = IMPACT_COLORS.get(impact, "#444")
        title   = ev.get("title","")
        ccy     = str(ev.get("country","")).upper()
        raw_date = str(ev.get("date",""))
        actual  = ev.get("actual","") or "—"
        fore    = ev.get("forecast","") or "—"
        prev    = ev.get("previous","") or "—"

        # Parse ForexFactory date: "MM-DD-YYYY" or "YYYY-MM-DDTHH:MM:SS"
        date_disp = ""
        time_disp = ""
        try:
            parts = raw_date.replace("T"," ").split(" ")
            d_str = parts[0]
            t_str = parts[1][:5] if len(parts) > 1 else ""
            segs = d_str.replace("/","-").split("-")
            if len(segs) == 3:
                if len(segs[0]) == 4:        # YYYY-MM-DD
                    date_disp = f"{segs[2]}/{segs[1]}/{segs[0][2:]}"
                else:                         # MM-DD-YYYY
                    date_disp = f"{segs[1]}/{segs[0]}/{segs[2][2:]}"
            time_disp = t_str
        except Exception:
            date_disp = raw_date[:10]

        row_bg = "rgba(255,51,51,0.05)" if impact == "High" else "transparent"
        st.markdown(f"""
            <div style="display:grid;
                        grid-template-columns:85px 60px 55px 1fr 75px 75px 75px;
                        gap:6px;padding:5px 2px;border-bottom:1px solid #2E2E2E;
                        font-family:'IBM Plex Mono';font-size:0.72rem;
                        align-items:center;background:{row_bg}">
                <span style="color:#B0B0B0;font-weight:500">{date_disp}</span>
                <span style="color:#888">{time_disp}</span>
                <span style="color:#E0E0E0;font-weight:700">{ccy}</span>
                <span style="color:#E0E0E0">{title}</span>
                <span style="color:{col};font-weight:600">{impact}</span>
                <span style="color:#00CC66;font-weight:500">{actual}</span>
                <span style="color:#888">{fore} / {prev}</span>
            </div>
        """, unsafe_allow_html=True)

def render():
    st.markdown("""
        <div class="page-header">
            <span class="page-title">News Feed</span>
            <span class="page-subtitle">FT · Economist · WSJ · Reuters · Walter Bloomberg</span>
        </div>
    """, unsafe_allow_html=True)

    tab_news, tab_walter, tab_cal = st.tabs([
        "News Headlines", "Walter Bloomberg (X)", "Economic Calendar"
    ])

    # ── NEWS ──────────────────────────────────────────────────────────────────
    with tab_news:
        c1, c2 = st.columns([2,1])
        with c1:
            selected = st.multiselect("Sources", list(RSS_FEEDS.keys()),
                                      default=["Financial Times","The Economist",
                                               "Wall Street Journal","Reuters Business"])
        with c2:
            keyword = st.text_input("Filter", placeholder="e.g. ECB, tariffs")

        all_articles = []
        with st.spinner("Fetching…"):
            for name in selected:
                arts = get_rss_feed(RSS_FEEDS[name])
                for a in arts: a["_source"] = name
                all_articles.extend(arts)
            # NewsAPI supplement
            try:
                nk = st.secrets.get("NEWS_API_KEY","")
            except Exception:
                nk = os.environ.get("NEWS_API_KEY","")
            if nk:
                for a in get_news("finance economy markets", 20):
                    a["_source"] = a.get("source",{}).get("name","NewsAPI")
                    a["link"] = a.get("url","")
                    a["published"] = a.get("publishedAt","")
                    a["summary"] = a.get("description","")
                    all_articles.append(a)

        if keyword:
            kw = keyword.lower()
            all_articles = [a for a in all_articles
                            if kw in (a.get("title","") + a.get("summary","")).lower()]

        st.markdown(f'<div style="font-family:IBM Plex Mono;font-size:0.7rem;color:#555;'
                    f'margin-bottom:6px">{len(all_articles)} articles</div>',
                    unsafe_allow_html=True)
        for art in all_articles[:60]:
            render_article(art, art.get("_source","—"))

    # ── WALTER BLOOMBERG ──────────────────────────────────────────────────────
    with tab_walter:
        st.markdown('<div class="bb-card-title">Walter Bloomberg · @DeItaone · Real-time market headlines</div>',
                    unsafe_allow_html=True)
        st.caption("Feed via Nitter public mirror. If empty, the mirror may be down — try refreshing.")

        # Try multiple Nitter mirrors for reliability
        mirrors = [
            "https://nitter.poast.org/DeItaone/rss",
            "https://nitter.privacydev.net/DeItaone/rss",
            "https://nitter.1d4.us/DeItaone/rss",
        ]
        tweets = []
        with st.spinner("Loading Walter Bloomberg feed…"):
            for mirror in mirrors:
                tweets = get_rss_feed(mirror)
                if tweets:
                    break

        if not tweets:
            st.warning("Walter Bloomberg RSS feed is currently unavailable via public mirrors. "
                       "This is a known limitation — Nitter mirrors go up and down. "
                       "Check back shortly or follow directly at x.com/DeItaone.")
        else:
            for tw in tweets[:40]:
                render_article(tw, "Walter Bloomberg (X)")

    # ── ECONOMIC CALENDAR ─────────────────────────────────────────────────────
    with tab_cal:
        st.markdown('<div class="bb-card-title">Economic Calendar — This Week · USD EUR CHF GBP JPY</div>',
                    unsafe_allow_html=True)
        with st.spinner("Loading calendar…"):
            events = get_forex_factory_calendar()

        if not events:
            st.warning("Calendar feed unavailable. ForexFactory may be blocking the request. "
                       "Try refreshing in a few minutes.")
        else:
            render_calendar(events)
        st.caption("Source: ForexFactory · High-impact events highlighted in red")
