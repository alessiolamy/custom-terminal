"""
pages/news_feed.py — Tab 2: News Feed

Changes:
  - Economic calendar date/time text: was color:#888 (invisible on dark bg).
    Fixed to color:#C8D0D8 (light grey, clearly visible).
  - Added "Walter Bloomberg (X)" section that scrapes/links @DeItaone posts
    via Nitter public RSS (no Twitter API key needed).
  - News tab now has three sub-sections: RSS headlines | Walter Bloomberg | Economic Calendar
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.data import get_news, get_rss_feed, get_forex_factory_calendar

RSS_FEEDS = {
    "Financial Times":     "https://www.ft.com/rss/home",
    "The Economist":       "https://www.economist.com/finance-and-economics/rss.xml",
    "Wall Street Journal": "https://feeds.a.omnimarc.com/rss/rss.wsj.com/wsj/pub/rss/market",
    "Reuters Business":    "https://feeds.reuters.com/reuters/businessNews",
    "Bloomberg Markets":   "https://feeds.bloomberg.com/markets/news.rss",
    "CNBC":                "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "Seeking Alpha":       "https://seekingalpha.com/market_currents.xml",
    "Yahoo Finance":       "https://finance.yahoo.com/rss/topfinstories",
}

# Walter Bloomberg / @DeItaone — public Nitter RSS mirrors (fallback chain)
# Nitter instances go up/down; we try several in order.
WALTER_BLOOMBERG_NITTER_FEEDS = [
    "https://nitter.poast.org/DeItaone/rss",
    "https://nitter.privacydev.net/DeItaone/rss",
    "https://nitter.net/DeItaone/rss",
    "https://nitter.1d4.us/DeItaone/rss",
]
WALTER_BLOOMBERG_X_URL = "https://x.com/DeItaone"

IMPACT_COLORS = {
    "High":         "#FF3333",
    "Medium":       "#FFCC00",
    "Low":          "#00CC66",
    "Non-Economic": "#555555",
}

CURRENCIES_FILTER = {"USD", "EUR", "CHF", "GBP", "JPY"}


# ── Article renderer ───────────────────────────────────────────────────────────
def render_article(article: dict, source_label: str):
    title   = article.get("title") or article.get("headline", "No title")
    link    = article.get("link") or article.get("url", "#")
    pub     = article.get("published") or article.get("publishedAt", "")
    summary = article.get("summary") or article.get("description", "")
    if summary and len(summary) > 180:
        summary = summary[:177] + "…"
    try:
        if "T" in str(pub):
            dt  = datetime.fromisoformat(str(pub).replace("Z", ""))
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


# ── Walter Bloomberg section ───────────────────────────────────────────────────
def render_walter_bloomberg():
    """
    Fetches @DeItaone posts via Nitter public RSS mirrors.
    Nitter is an open-source Twitter front-end that exposes RSS without an API key.
    Falls back gracefully if all mirrors are down.
    """
    st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
            <div style="font-family:'IBM Plex Mono';font-size:0.8rem;font-weight:600;color:#0353D9">
                Walter Bloomberg
            </div>
            <div style="font-size:0.7rem;color:#666">@DeItaone</div>
            <a href="{WALTER_BLOOMBERG_X_URL}" target="_blank"
               style="font-size:0.68rem;color:#0353D9;text-decoration:none;margin-left:auto">
               Open on X ↗
            </a>
        </div>
        <div style="font-size:0.7rem;color:#555;margin-bottom:10px;font-family:'IBM Plex Mono'">
            Real-time Bloomberg terminal headlines re-posted on X
        </div>
    """, unsafe_allow_html=True)

    posts = []
    for feed_url in WALTER_BLOOMBERG_NITTER_FEEDS:
        try:
            items = get_rss_feed(feed_url)
            if items:
                posts = items
                break
        except Exception:
            continue

    if not posts:
        st.markdown(f"""
            <div style="background:#1C1C1C;border:1px solid #2E2E2E;border-radius:6px;
                        padding:12px 16px;font-family:'IBM Plex Mono';font-size:0.78rem;">
                <div style="color:#FFCC00;margin-bottom:6px">⚠ Nitter mirrors currently unavailable</div>
                <div style="color:#888;line-height:1.6">
                    Walter Bloomberg posts Bloomberg terminal headlines in real-time on X.<br>
                    Follow directly at
                    <a href="{WALTER_BLOOMBERG_X_URL}" target="_blank"
                       style="color:#0353D9">x.com/DeItaone</a>
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    for post in posts[:30]:
        title   = post.get("title", "")
        link    = post.get("link", "#")
        pub     = post.get("published", "")
        try:
            if pub:
                dt  = datetime.fromisoformat(str(pub).replace("Z", ""))
                pub = dt.strftime("%d/%m/%y  %H:%M")
        except Exception:
            pass

        # Clean up Nitter title artifacts (sometimes wraps in RT: or @)
        display_title = title.replace("R to @DeItaone:", "").strip()

        st.markdown(f"""
            <div style="padding:7px 0;border-bottom:1px solid #2E2E2E;
                        font-family:'IBM Plex Mono'">
                <div style="font-size:0.8rem;color:#E0E0E0;line-height:1.5">
                    <a href="{link}" target="_blank"
                       style="color:#E0E0E0;text-decoration:none">{display_title}</a>
                </div>
                <div style="font-size:0.65rem;color:#555;margin-top:2px">{pub}</div>
            </div>
        """, unsafe_allow_html=True)


# ── Economic calendar ──────────────────────────────────────────────────────────
def render_calendar(events: list):
    if not events:
        st.info("Economic calendar data unavailable.")
        return

    filtered = [e for e in events if e.get("country", "").upper() in CURRENCIES_FILTER]
    if not filtered:
        st.info("No events found for USD, EUR, CHF, GBP, JPY this week.")
        return

    # Header
    st.markdown("""
        <div style="display:grid;
                    grid-template-columns:90px 60px 1fr 55px 70px 80px 110px;
                    gap:6px;padding:5px 0;font-family:'IBM Plex Mono';
                    font-size:0.65rem;color:#0353D9;
                    border-bottom:1px solid #0242B3;margin-bottom:4px;">
            <span>DATE</span>
            <span>TIME</span>
            <span>EVENT</span>
            <span>CCY</span>
            <span>IMPACT</span>
            <span>ACTUAL</span>
            <span>FORE / PREV</span>
        </div>
    """, unsafe_allow_html=True)

    for ev in filtered[:80]:
        impact = ev.get("impact", "")
        col    = IMPACT_COLORS.get(impact, "#555555")
        title  = ev.get("title", "")
        ccy    = ev.get("country", "").upper()
        date   = ev.get("date", "")
        actual = ev.get("actual", "")
        fore   = ev.get("forecast", "")
        prev   = ev.get("previous", "")

        # ── Date / time parsing ────────────────────────────────────────────────
        date_part = ""
        time_part = ""
        try:
            if date:
                parts = str(date).replace("/", "-").split(" ")
                d     = parts[0]
                t     = parts[1] if len(parts) > 1 else ""
                segs  = d.split("-")
                if len(segs) == 3:
                    if len(segs[0]) == 4:           # YYYY-MM-DD
                        date_part = f"{segs[2]}/{segs[1]}/{segs[0][2:]}"
                    else:                            # MM-DD-YYYY
                        date_part = f"{segs[1]}/{segs[0]}/{segs[2][2:]}"
                time_part = t[:5] if t else ""
        except Exception:
            date_part = str(date)

        # FIX: date/time were colour:#888 (near-invisible on dark bg).
        # Now using #C8D0D8 (clearly readable light grey).
        st.markdown(f"""
            <div style="display:grid;
                        grid-template-columns:90px 60px 1fr 55px 70px 80px 110px;
                        gap:6px;padding:5px 0;border-bottom:1px solid #2E2E2E;
                        font-family:'IBM Plex Mono';font-size:0.72rem;align-items:center;">
                <span style="color:#C8D0D8;font-weight:500">{date_part}</span>
                <span style="color:#C8D0D8;font-weight:500">{time_part}</span>
                <span style="color:#E0E0E0">{title}</span>
                <span style="color:#E0E0E0;font-weight:600">{ccy}</span>
                <span style="color:{col};font-weight:600">{impact}</span>
                <span style="color:#00CC66">{actual or "—"}</span>
                <span style="color:#A0A8B0">{fore or "—"} / {prev or "—"}</span>
            </div>
        """, unsafe_allow_html=True)


# ── Main render ────────────────────────────────────────────────────────────────
def render():
    st.markdown("""
        <div class="page-header">
            <span class="page-title">News Feed</span>
            <span class="page-subtitle">FT · Economist · WSJ · Reuters · Walter Bloomberg · ForexFactory</span>
        </div>
    """, unsafe_allow_html=True)

    tab_news, tab_wb, tab_cal = st.tabs([
        "📰 Headlines",
        "⚡ Walter Bloomberg",
        "📅 Economic Calendar",
    ])

    # ── TAB 1: Headlines ───────────────────────────────────────────────────────
    with tab_news:
        c1, c2 = st.columns([2, 1])
        with c1:
            selected_feeds = st.multiselect(
                "Sources", list(RSS_FEEDS.keys()),
                default=["Financial Times", "The Economist",
                         "Wall Street Journal", "Reuters Business"],
            )
        with c2:
            keyword = st.text_input("Filter keyword", placeholder="e.g. ECB, inflation")

        if not selected_feeds:
            st.info("Select at least one source.")
        else:
            all_articles = []
            with st.spinner("Fetching news…"):
                for name in selected_feeds:
                    arts = get_rss_feed(RSS_FEEDS[name])
                    for a in arts:
                        a["_source"] = name
                    all_articles.extend(arts)

                try:
                    key = st.secrets.get("NEWS_API_KEY", "")
                except Exception:
                    key = os.environ.get("NEWS_API_KEY", "")
                if key:
                    api_arts = get_news(query="finance economy markets", page_size=20)
                    for a in api_arts:
                        a["_source"]   = a.get("source", {}).get("name", "NewsAPI")
                        a["link"]      = a.get("url", "")
                        a["published"] = a.get("publishedAt", "")
                        a["summary"]   = a.get("description", "")
                    all_articles.extend(api_arts)

            if keyword:
                kw = keyword.lower()
                all_articles = [a for a in all_articles
                                if kw in (a.get("title", "") + a.get("summary", "")).lower()]

            if not all_articles:
                st.warning("No articles found — RSS feeds may be rate-limited. Try again shortly.")
            else:
                st.markdown(
                    f'<div style="font-family:IBM Plex Mono;font-size:0.7rem;'
                    f'color:#777;margin-bottom:8px">{len(all_articles)} articles</div>',
                    unsafe_allow_html=True,
                )
                for art in all_articles[:60]:
                    render_article(art, art.get("_source", "—"))

    # ── TAB 2: Walter Bloomberg ────────────────────────────────────────────────
    with tab_wb:
        st.markdown('<div class="bb-card-title">Walter Bloomberg — @DeItaone</div>',
                    unsafe_allow_html=True)
        st.caption(
            "Real-time Bloomberg terminal headlines posted on X by @DeItaone. "
            "Fetched via Nitter public RSS (no API key required). "
            "If mirrors are down, click 'Open on X' to view directly."
        )
        with st.spinner("Fetching @DeItaone feed…"):
            render_walter_bloomberg()

    # ── TAB 3: Economic Calendar ───────────────────────────────────────────────
    with tab_cal:
        st.markdown(
            '<div class="bb-card-title">Economic Calendar — This Week · USD EUR CHF GBP JPY</div>',
            unsafe_allow_html=True,
        )
        with st.spinner("Loading calendar…"):
            events = get_forex_factory_calendar()
        render_calendar(events)
        st.caption("Source: ForexFactory · Updates hourly")