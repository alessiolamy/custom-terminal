"""
utils/data.py — Centralised data-fetching helpers.
"""

import os, time
import streamlit as st
import requests
import yfinance as yf
import pandas as pd
from functools import wraps

# ── Secrets ────────────────────────────────────────────────────────────────────
def _secret(key: str, fallback: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, fallback)

FRED_KEY    = lambda: _secret("FRED_API_KEY")
NEWS_KEY    = lambda: _secret("NEWS_API_KEY")
FMP_KEY     = lambda: _secret("FMP_API_KEY")
TRADIER_KEY = lambda: _secret("TRADIER_API_KEY")
POLYGON_KEY = lambda: _secret("POLYGON_API_KEY")

# ── TTL cache ──────────────────────────────────────────────────────────────────
def ttl_cache(seconds=60):
    cache = {}
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            k = str(args) + str(kwargs)
            now = time.time()
            if k in cache and now - cache[k]["ts"] < seconds:
                return cache[k]["val"]
            val = fn(*args, **kwargs)
            cache[k] = {"val": val, "ts": now}
            return val
        return wrapper
    return decorator

# ── Yahoo Finance — full quote ─────────────────────────────────────────────────
@ttl_cache(90)
def get_quote_full(ticker: str) -> dict:
    try:
        t    = yf.Ticker(ticker)
        info = t.info or {}
        fi   = t.fast_info
        curr = fi.last_price if fi.last_price else info.get("regularMarketPrice")
        prev = fi.previous_close if fi.previous_close else info.get("regularMarketPreviousClose")
        chg  = (curr - prev) if (curr and prev) else None
        pct  = (chg / prev * 100) if (chg and prev) else None
        return {
            "ticker":     ticker,
            "price":      curr,
            "prev_close": prev,
            "change":     chg,
            "change_pct": pct,
            "bid":        info.get("bid"),
            "ask":        info.get("ask"),
            "open":       info.get("open") or info.get("regularMarketOpen"),
            "day_high":   fi.day_high if fi.day_high else info.get("dayHigh"),
            "day_low":    fi.day_low  if fi.day_low  else info.get("dayLow"),
            "volume":     fi.last_volume if fi.last_volume else info.get("volume"),
            "market_cap": fi.market_cap if fi.market_cap else info.get("marketCap"),
            "currency":   info.get("currency", ""),
            "name":       info.get("shortName", ""),
            "52w_high":   fi.year_high if fi.year_high else info.get("fiftyTwoWeekHigh"),
            "52w_low":    fi.year_low  if fi.year_low  else info.get("fiftyTwoWeekLow"),
            "pe":         info.get("trailingPE"),
            "yield":      info.get("dividendYield"),
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e), "price": None, "change_pct": None}

get_quote = get_quote_full  # alias

@ttl_cache(300)
def get_history(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    try:
        return yf.Ticker(ticker).history(period=period, interval=interval)
    except Exception:
        return pd.DataFrame()

@ttl_cache(120)
def get_multiple_quotes(tickers: list) -> pd.DataFrame:
    """
    Sequential fast_info fetch — reliable for indices, ETFs, FX, futures.
    Slightly slower than batch download but works for all ticker types.
    """
    if not tickers:
        return pd.DataFrame()
    rows = []
    for tk in tickers:
        try:
            t  = yf.Ticker(tk)
            fi = t.fast_info
            curr = fi.last_price if fi.last_price else None
            prev = fi.previous_close if fi.previous_close else None
            chg  = (curr - prev) if (curr and prev) else None
            pct  = (chg / prev * 100) if (chg and prev) else None
            rows.append({
                "ticker":     tk,
                "price":      curr,
                "prev_close": prev,
                "change":     chg,
                "change_pct": pct,
                "volume":     fi.three_month_average_volume,
                "market_cap": fi.market_cap,
            })
        except Exception:
            rows.append({"ticker": tk, "price": None, "change_pct": None,
                         "change": None, "volume": None, "market_cap": None})
    return pd.DataFrame(rows)

# ── Institutional holders ──────────────────────────────────────────────────────
@ttl_cache(3600)
def get_holders(ticker: str) -> dict:
    try:
        t = yf.Ticker(ticker)
        return {"institutional": t.institutional_holders,
                "major":         t.major_holders}
    except Exception:
        return {"institutional": pd.DataFrame(), "major": pd.DataFrame()}

# ── FRED ───────────────────────────────────────────────────────────────────────
FRED_BASE = "https://api.stlouisfed.org/fred"

@ttl_cache(3600)
def get_fred_series(series_id: str, limit: int = 252) -> pd.DataFrame:
    key = FRED_KEY()
    if not key:
        return pd.DataFrame(columns=["date", "value"])
    try:
        r = requests.get(f"{FRED_BASE}/series/observations",
                         params={"series_id": series_id, "api_key": key,
                                 "file_type": "json", "sort_order": "desc",
                                 "limit": limit}, timeout=10)
        r.raise_for_status()
        obs = r.json().get("observations", [])
        df  = pd.DataFrame(obs)[["date", "value"]]
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["date"]  = pd.to_datetime(df["date"])
        return df.dropna().sort_values("date")
    except Exception:
        return pd.DataFrame(columns=["date", "value"])

@ttl_cache(3600)
def get_fred_latest(series_id: str):
    df = get_fred_series(series_id, limit=5)
    return float(df["value"].iloc[-1]) if not df.empty else None

# ── News / RSS ─────────────────────────────────────────────────────────────────
@ttl_cache(900)
def get_news(query="finance economy", page_size=20) -> list:
    key = NEWS_KEY()
    if not key:
        return []
    try:
        r = requests.get("https://newsapi.org/v2/everything",
                         params={"q": query, "apiKey": key, "language": "en",
                                 "sortBy": "publishedAt", "pageSize": page_size},
                         timeout=10)
        r.raise_for_status()
        return r.json().get("articles", [])
    except Exception:
        return []

@ttl_cache(900)
def get_rss_feed(url: str) -> list:
    import xml.etree.ElementTree as ET
    try:
        r = requests.get(url, timeout=12,
                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = []
        for item in root.iter("item"):
            title = item.findtext("title", "").strip()
            link  = item.findtext("link", "").strip()
            pub   = item.findtext("pubDate", "").strip()
            desc  = item.findtext("description", "").strip()
            items.append({"title": title, "link": link,
                          "published": pub, "summary": desc})
        return items[:40]
    except Exception:
        return []

# ── ForexFactory calendar ──────────────────────────────────────────────────────
@ttl_cache(1800)
def get_forex_factory_calendar() -> list:
    urls = [
        "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
        "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.forexfactory.com/",
    }
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code == 200:
                return r.json()
        except Exception:
            continue
    return []

# ── FMP ───────────────────────────────────────────────────────────────────────
FMP_BASE = "https://financialmodelingprep.com/api/v3"

@ttl_cache(3600)
def get_fmp(endpoint: str, ticker: str = "", extra: dict = {}) -> object:
    key = FMP_KEY()
    if not key:
        return {}
    url = f"{FMP_BASE}/{endpoint}/{ticker}" if ticker else f"{FMP_BASE}/{endpoint}"
    try:
        r = requests.get(url, params={"apikey": key, **extra}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}

# ── Options (Tradier) ─────────────────────────────────────────────────────────
@ttl_cache(120)
def get_options_chain(ticker, expiration=""):
    key = TRADIER_KEY()
    if not key:
        return {}
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    params  = {"symbol": ticker, "greeks": "true"}
    if expiration:
        params["expiration"] = expiration
    try:
        r = requests.get("https://api.tradier.com/v1/markets/options/chains",
                         headers=headers, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("options", {})
    except Exception:
        return {}

@ttl_cache(300)
def get_options_expirations(ticker):
    key = TRADIER_KEY()
    if not key:
        return []
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    try:
        r = requests.get("https://api.tradier.com/v1/markets/options/expirations",
                         headers=headers, params={"symbol": ticker}, timeout=10)
        r.raise_for_status()
        return r.json().get("expirations", {}).get("date", []) or []
    except Exception:
        return []

# ── Formatters ─────────────────────────────────────────────────────────────────
def fmt_price(v, d=2):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return f"{v:,.{d}f}"

def fmt_pct(v, d=2):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    sign = "▲" if v > 0 else "▼" if v < 0 else ""
    return f"{sign} {abs(v):.{d}f}%"

def fmt_large(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if v >= 1e12: return f"{v/1e12:.2f}T"
    if v >= 1e9:  return f"{v/1e9:.2f}B"
    if v >= 1e6:  return f"{v/1e6:.2f}M"
    return f"{v:,.0f}"

def color_class(v):
    if v is None:
        return "flat"
    return "up" if v > 0 else "down" if v < 0 else "flat"
