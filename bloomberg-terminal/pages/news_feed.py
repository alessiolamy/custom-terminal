"""
pages/news_feed.py — Tab 2: News Feed
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.data import get_news, get_rss_feed, get_forex_factory_calendar

RSS_FEEDS = {
    "Financial Times":    "https://www.ft.com/rss/home",
    "The Economist":      "https://www.economist.com/finance-and-economics/rss.xml",
    "Wall Street Journal":"https://feeds.a.omnimarc.com/rss/rss.wsj.com/wsj/pub/rss/market",
    "Reuters Business":   "https://feeds.reuters.com/reuters/businessNews",
    "Bloomberg Markets":  "https://feeds.bloomberg.com/markets/news.rss",
    "CNBC":               "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "Seeking Alpha":      "https://seekingalpha.com/market_currents.xml",
    "Yahoo Finance":      "https://finance.yahoo.com/rss/topfinstories",
}

IMPACT_COLORS = {
    "High":         "#FF3333",
    "Medium":       "#FFCC00",
    "Low":          "#888888",
    "Non-Economic": "#444444",
}

CURRENCIES_FILTER = {"USD", "EUR", "CHF", "GBP", "JPY"}

def render_article(article: dict, source_label: str):
    title   = article.get("title") or article.get("headline", "No title")
    link    = article.get("link") or article.get("url", "#")
    pub     = article.get("published") or article.get("publishedAt", "")
    summary = article.get("summary") or article.get("description", "")
    if summary and len(summary) > 180:
        summary = summary[:177] + "…"
    try:
        if "T" in str(pub):
            dt = datetime.fromisoformat(str(pub).replace("Z",""))
            pub = dt.strftime("%d/%m/%y  %H:%M")
    except Exception:
        pass
    st.markdown(f"""
        <div class="news-item">
            <div class="news-headline">
                <a href="{link}" target="_blank"
                   style="color:#E0E0E0;text-decoration:none;">{title}</a>
            </div>
            <div class="news-meta">
                <span class="news-source">{source_label}</span>
                &nbsp;·&nbsp; {pub}
            </div>
            {"<div style='font-size:0.78rem;color:#777;margin-top:3px'>" + summary + "</div>" if summary else ""}
        </div>
    """, unsafe_allow_html=True)

def render_calendar(events: list):
    if not events:
        st.info("Economic calendar data unavailable.")
        return

    # Filter to selected currencies only
    filtered = [e for e in events
                if e.get("country","").upper() in CURRENCIES_FILTER]

    if not filtered:
        st.info("No events found for USD, EUR, CHF, GBP, JPY this week.")
        return

    # Header row
    st.markdown("""
        <div style="display:grid;grid-template-columns:90px 55px 1fr 70px 80px 80px 80px;
                    gap:6px;padding:5px 0;font-family:'IBM Plex Mono';
                    font-size:0.65rem;color:#0353D9;
                    border-bottom:1px solid #0242B3;margin-bottom:4px;">
            <span>Date</span><span>Time</span><span>Event</span>
            <span>CCY</span><span>Impact</span><span>Actual</span><span>Fore/Prev</span>
        </div>
    """, unsafe_allow_html=True)

    for ev in filtered[:80]:
        impact = ev.get("impact","")
        col    = IMPACT_COLORS.get(impact, "#444")
        title  = ev.get("title","")
        ccy    = ev.get("country","").upper()
        date   = ev.get("date","")   # format: MM-DD-YYYY HH:MM:SS or similar
        actual = ev.get("actual","")
        fore   = ev.get("forecast","")
        prev   = ev.get("previous","")

        # Reformat date → DD/MM/YY  HH:MM
        date_part = ""
        time_part = ""
        try:
            # ForexFactory format is typically "MM-DD-YYYY"
            if date:
                parts = str(date).replace("/","-").split(" ")
                d = parts[0]  # MM-DD-YYYY or YYYY-MM-DD
                t = parts[1] if len(parts) > 1 else ""
                segs = d.split("-")
                if len(segs) == 3:
                    if len(segs[0]) == 4:   # YYYY-MM-DD
                        date_part = f"{segs[2]}/{segs[1]}/{segs[0][2:]}"
                    else:                    # MM-DD-YYYY
                        date_part = f"{segs[1]}/{segs[0]}/{segs[2][2:]}"
                if t:
                    time_part = t[:5]
        except Exception:
            date_part = date

        st.markdown(f"""
            <div style="display:grid;grid-template-columns:90px 55px 1fr 70px 80px 80px 80px;
                        gap:6px;padding:5px 0;border-bottom:1px solid #2E2E2E;
                        font-family:'IBM Plex Mono';font-size:0.72rem;align-items:center;">
                <span style="color:#888">{date_part}</span>
                <span style="color:#888">{time_part}</span>
                <span style="color:#E0E0E0">{title}</span>
                <span style="color:#E0E0E0;font-weight:600">{ccy}</span>
                <span style="color:{col};font-weight:600">{impact}</span>
                <span style="color:#00CC66">{actual or "—"}</span>
                <span style="color:#888">{fore or "—"} / {prev or "—"}</span>
            </div>
        """, unsafe_allow_html=True)

def render():
    st.markdown("""
        <div class="page-header">
            <span class="page-title">News Feed</span>
            <span class="page-subtitle">FT · Economist · WSJ · Reuters · ForexFactory</span>
        </div>
    """, unsafe_allow_html=True)

    tab_news, tab_cal = st.tabs(["News Headlines", "Economic Calendar"])

    with tab_news:
        c1, c2 = st.columns([2, 1])
        with c1:
            selected_feeds = st.multiselect(
                "Sources", list(RSS_FEEDS.keys()),
                default=["Financial Times","The Economist",
                         "Wall Street Journal","Reuters Business"],
            )
        with c2:
            keyword = st.text_input("Filter keyword", placeholder="e.g. ECB, inflation")

        if not selected_feeds:
            st.info("Select at least one source.")
            return

        all_articles = []
        with st.spinner("Fetching news…"):
            for name in selected_feeds:
                arts = get_rss_feed(RSS_FEEDS[name])
                for a in arts:
                    a["_source"] = name
                all_articles.extend(arts)

            try:
                key = st.secrets.get("NEWS_API_KEY","")
            except Exception:
                key = os.environ.get("NEWS_API_KEY","")
            if key:
                api_arts = get_news(query="finance economy markets", page_size=20)
                for a in api_arts:
                    a["_source"] = a.get("source",{}).get("name","NewsAPI")
                    a["link"]    = a.get("url","")
                    a["published"] = a.get("publishedAt","")
                    a["summary"] = a.get("description","")
                all_articles.extend(api_arts)

        if keyword:
            kw = keyword.lower()
            all_articles = [a for a in all_articles
                            if kw in (a.get("title","") + a.get("summary","")).lower()]

        if not all_articles:
            st.warning("No articles found — RSS feeds may be rate-limited. Try again shortly.")
        else:
            st.markdown(f'<div style="font-family:IBM Plex Mono;font-size:0.7rem;'
                        f'color:#777;margin-bottom:8px">{len(all_articles)} articles</div>',
                        unsafe_allow_html=True)
            for art in all_articles[:60]:
                render_article(art, art.get("_source","—"))

    with tab_cal:
        st.markdown('<div class="bb-card-title">Economic Calendar — This Week · USD EUR CHF GBP JPY</div>',
                    unsafe_allow_html=True)
        with st.spinner("Loading calendar…"):
            events = get_forex_factory_calendar()
        render_calendar(events)
        st.caption("Source: ForexFactory · Updates hourly")
