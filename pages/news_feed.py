"""
pages/news_feed.py — Tab 2: News Feed
Fixed calendar date/time parsing, Walter Bloomberg via embed, no earnings calendar.
"""

import streamlit as st
import re
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
    "Yahoo Finance":         "https://finance.yahoo.com/rss/topfinstories",
}

IMPACT_COLORS = {
    "High":         "#FF3333",
    "Medium":       "#FFCC00",
    "Low":          "#555555",
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
        "%a, %d %b %Y %H:%M:%S GMT",
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
    try:
        dt = datetime.fromisoformat(raw.replace("Z", ""))
        return dt.strftime("%d/%m/%y  %H:%M")
    except Exception:
        return raw[:16]

def parse_ff_datetime(raw: str):
    """
    Parse ForexFactory date strings.
    Formats seen: '06-11-2025 8:30am', '06-11-2025', 'Wednesday Jun 11'
    Returns (date_str, time_str) both as display strings DD/MM/YY and HH:MM
    """
    if not raw:
        return "", ""
    raw = raw.strip()
    date_disp = ""
    time_disp = ""
    try:
        # Format: MM-DD-YYYY HH:MMam/pm  e.g. "06-11-2025 8:30am"
        m = re.match(r"(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}:\d{2}(?:am|pm)?)", raw, re.I)
        if m:
            mon, day, yr, t = m.group(1), m.group(2), m.group(3), m.group(4)
            date_disp = f"{day.zfill(2)}/{mon.zfill(2)}/{yr[2:]}"
            # Convert 12h to 24h
            try:
                dt = datetime.strptime(t.lower(), "%I:%M%p")
                time_disp = dt.strftime("%H:%M")
            except Exception:
                time_disp = t
            return date_disp, time_disp

        # Format: MM-DD-YYYY only
        m2 = re.match(r"(\d{1,2})-(\d{1,2})-(\d{4})", raw)
        if m2:
            mon, day, yr = m2.group(1), m2.group(2), m2.group(3)
            return f"{day.zfill(2)}/{mon.zfill(2)}/{yr[2:]}", ""

        # Format: YYYY-MM-DDTHH:MM:SS
        m3 = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}:\d{2})", raw)
        if m3:
            yr, mon, day, t = m3.group(1), m3.group(2), m3.group(3), m3.group(4)
            return f"{day}/{mon}/{yr[2:]}", t

    except Exception:
        pass

    return raw[:10], ""

def render_article(article: dict, source_label: str):
    title   = (article.get("title") or "").strip() or "No title"
    link    = article.get("link") or article.get("url", "#")
    pub_raw = article.get("published") or article.get("publishedAt", "")
    summary = article.get("summary") or article.get("description", "")
    pub     = fmt_pub_date(str(pub_raw))
    if summary and len(summary) > 200:
        summary = summary[:197] + "…"
    summary = re.sub(r"<[^>]+>", "", summary)

    st.markdown(f"""
        <div class="news-item">
            <div class="news-headline">
                <a href="{link}" target="_blank"
                   style="color:#E0E0E0;text-decoration:none;">{title}</a>
            </div>
            <div class="news-meta">
                <span style="color:#0353D9;font-weight:600">{source_label}</span>
                &nbsp;·&nbsp; {pub}
            </div>
            {"<div style='font-size:0.76rem;color:#777;margin-top:3px'>" + summary + "</div>" if summary else ""}
        </div>
    """, unsafe_allow_html=True)

def render_calendar(events: list):
    filtered = [e for e in events
                if str(e.get("country", "")).upper() in CURRENCIES_FILTER]

    if not filtered:
        st.info("No events this week for USD / EUR / CHF / GBP / JPY.")
        return

    # Column header
    st.markdown("""
        <div style="display:grid;
                    grid-template-columns:80px 60px 50px 1fr 70px 70px 130px;
                    gap:8px;padding:6px 4px;font-family:'IBM Plex Mono';
                    font-size:0.65rem;color:#0353D9;
                    border-bottom:2px solid #0242B3;margin-bottom:2px;
                    font-weight:700;text-transform:uppercase;letter-spacing:0.06em;">
            <span>Date</span>
            <span>Time</span>
            <span>CCY</span>
            <span>Event</span>
            <span>Impact</span>
            <span>Actual</span>
            <span>Fore / Prev</span>
        </div>
    """, unsafe_allow_html=True)

    for ev in filtered[:120]:
        impact   = ev.get("impact", "")
        imp_col  = IMPACT_COLORS.get(impact, "#444")
        title    = ev.get("title", "")
        ccy      = str(ev.get("country", "")).upper()
        raw_date = str(ev.get("date", ""))
        actual   = ev.get("actual", "") or "—"
        fore     = ev.get("forecast", "") or "—"
        prev     = ev.get("previous", "") or "—"

        date_disp, time_disp = parse_ff_datetime(raw_date)

        row_bg = "rgba(255,51,51,0.06)" if impact == "High" else "transparent"

        st.markdown(f"""
            <div style="display:grid;
                        grid-template-columns:80px 60px 50px 1fr 70px 70px 130px;
                        gap:8px;padding:5px 4px;border-bottom:1px solid #222;
                        font-family:'IBM Plex Mono';font-size:0.72rem;
                        align-items:center;background:{row_bg}">
                <span style="color:#C0C0C0;font-weight:500">{date_disp}</span>
                <span style="color:#999">{time_disp}</span>
                <span style="color:#E0E0E0;font-weight:700">{ccy}</span>
                <span style="color:#E0E0E0">{title}</span>
                <span style="color:{imp_col};font-weight:600">{impact}</span>
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
        c1, c2 = st.columns([2, 1])
        with c1:
            selected = st.multiselect(
                "Sources", list(RSS_FEEDS.keys()),
                default=["Financial Times", "The Economist",
                         "Wall Street Journal", "Reuters Business"]
            )
        with c2:
            keyword = st.text_input("Filter", placeholder="e.g. ECB, tariffs")

        all_articles = []
        with st.spinner("Fetching…"):
            for name in selected:
                arts = get_rss_feed(RSS_FEEDS[name])
                for a in arts:
                    a["_source"] = name
                all_articles.extend(arts)

            try:
                nk = st.secrets.get("NEWS_API_KEY", "")
            except Exception:
                nk = os.environ.get("NEWS_API_KEY", "")
            if nk:
                for a in get_news("finance economy markets", 20):
                    a["_source"] = a.get("source", {}).get("name", "NewsAPI")
                    a["link"]    = a.get("url", "")
                    a["published"] = a.get("publishedAt", "")
                    a["summary"] = a.get("description", "")
                    all_articles.append(a)

        if keyword:
            kw = keyword.lower()
            all_articles = [a for a in all_articles
                            if kw in (a.get("title","") + a.get("summary","")).lower()]

        st.markdown(f'<div style="font-family:IBM Plex Mono;font-size:0.7rem;'
                    f'color:#555;margin-bottom:6px">{len(all_articles)} articles</div>',
                    unsafe_allow_html=True)
        for art in all_articles[:60]:
            render_article(art, art.get("_source", "—"))

    # ── WALTER BLOOMBERG ──────────────────────────────────────────────────────
    with tab_walter:
        st.markdown('<div class="bb-card-title">Walter Bloomberg · @DeItaone · Real-time market headlines</div>',
                    unsafe_allow_html=True)
        st.caption("Public Nitter RSS mirrors are unreliable. The embedded feed below is the most stable option.")

        # Embed X/Twitter timeline via official embed (no API key needed, read-only public)
        st.components.v1.html("""
            <div style="background:#141414;border:1px solid #2E2E2E;border-radius:4px;
                        max-height:600px;overflow-y:auto;padding:8px;">
                <a class="twitter-timeline"
                   data-theme="dark"
                   data-chrome="noheader nofooter noborders"
                   data-tweet-limit="20"
                   href="https://twitter.com/DeItaone">
                   Loading @DeItaone tweets...
                </a>
                <script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>
            </div>
        """, height=620)

        st.markdown("""
            <div style="font-family:'IBM Plex Mono';font-size:0.7rem;color:#555;margin-top:8px">
                If the feed doesn't load, open
                <a href="https://x.com/DeItaone" target="_blank"
                   style="color:#0353D9">x.com/DeItaone</a> directly.
            </div>
        """, unsafe_allow_html=True)

    # ── ECONOMIC CALENDAR ─────────────────────────────────────────────────────
    with tab_cal:
        st.markdown('<div class="bb-card-title">Economic Calendar — This Week · USD EUR CHF GBP JPY</div>',
                    unsafe_allow_html=True)

        if st.button("Refresh Calendar"):
            st.cache_data.clear() if hasattr(st, "cache_data") else None

        with st.spinner("Loading calendar…"):
            events = get_forex_factory_calendar()

        if not events:
            st.warning("Calendar unavailable — ForexFactory may be temporarily blocking the request. "
                       "Try refreshing in a few minutes.")
        else:
            # Debug: show raw date sample so we can verify parsing
            with st.expander("Raw date sample (for debugging)", expanded=False):
                st.code(str([e.get("date","") for e in events[:5]]))
            render_calendar(events)

        st.caption("Source: ForexFactory · High-impact events highlighted in red")
