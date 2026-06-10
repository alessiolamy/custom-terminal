"""
utils/data.py — Centralised data-fetching helpers.
All API keys are read from st.secrets (secrets.toml) or environment variables.
"""

import os
import streamlit as st
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from functools import wraps
import time

# ── Secret helpers ─────────────────────────────────────────────────────────────
def _secret(key: str, fallback: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, fallback)

FRED_KEY      = lambda: _secret("FRED_API_KEY")
NEWS_KEY      = lambda: _secret("NEWS_API_KEY")
ALPHA_KEY     = lambda: _secret("ALPHA_VANTAGE_KEY")
POLYGON_KEY   = lambda: _secret("POLYGON_API_KEY")
TRADIER_KEY   = lambda: _secret("TRADIER_API_KEY")
FMP_KEY       = lambda: _secret("FMP_API_KEY")

# ── Cache decorator (simple TTL) ───────────────────────────────────────────────
def ttl_cache(seconds=60):
    cache = {}
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            now = time.time()
            if key in cache and now - cache[key]["ts"] < seconds:
                return cache[key]["val"]
            val = fn(*args, **kwargs)
            cache[key] = {"val": val, "ts": now}
            return val
        return wrapper
    return decorator

# ── Yahoo Finance ──────────────────────────────────────────────────────────────
@ttl_cache(60)
def get_quote(ticker: str) -> dict:
    """Return a simple quote dict for a ticker."""
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        hist = t.history(period="2d", interval="1d")
        prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else None
        curr = float(info.last_price) if info.last_price else None
        chg  = curr - prev if (curr and prev) else None
        pct  = (chg / prev * 100) if (chg and prev) else None
        return {
            "ticker": ticker,
            "price": curr,
            "prev_close": prev,
            "change": chg,
            "change_pct": pct,
            "volume": info.three_month_average_volume,
            "market_cap": info.market_cap,
            "currency": info.currency,
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}

@ttl_cache(300)
def get_history(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    try:
        t = yf.Ticker(ticker)
        return t.history(period=period, interval=interval)
    except Exception:
        return pd.DataFrame()

@ttl_cache(120)
def get_multiple_quotes(tickers: list) -> pd.DataFrame:
    rows = []
    for tk in tickers:
        q = get_quote(tk)
        rows.append(q)
    return pd.DataFrame(rows)

# ── FRED API ───────────────────────────────────────────────────────────────────
FRED_BASE = "https://api.stlouisfed.org/fred"

@ttl_cache(3600)
def get_fred_series(series_id: str, limit: int = 100) -> pd.DataFrame:
    key = FRED_KEY()
    if not key:
        return pd.DataFrame(columns=["date", "value"])
    url = f"{FRED_BASE}/series/observations"
    params = {"series_id": series_id, "api_key": key,
              "file_type": "json", "sort_order": "desc", "limit": limit}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        obs = r.json().get("observations", [])
        df = pd.DataFrame(obs)[["date", "value"]]
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["date"]  = pd.to_datetime(df["date"])
        return df.dropna().sort_values("date")
    except Exception as e:
        return pd.DataFrame(columns=["date", "value"])

@ttl_cache(3600)
def get_fred_latest(series_id: str) -> float | None:
    df = get_fred_series(series_id, limit=5)
    if df.empty:
        return None
    return float(df["value"].iloc[-1])

# ── NewsAPI ────────────────────────────────────────────────────────────────────
@ttl_cache(900)
def get_news(query: str = "finance economy", sources: str = "",
             page_size: int = 20) -> list[dict]:
    key = NEWS_KEY()
    if not key:
        return []
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query, "apiKey": key,
        "language": "en", "sortBy": "publishedAt",
        "pageSize": page_size,
    }
    if sources:
        params["sources"] = sources
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("articles", [])
    except Exception:
        return []

@ttl_cache(900)
def get_rss_feed(url: str) -> list[dict]:
    """Fetch and parse an RSS feed without extra deps."""
    import xml.etree.ElementTree as ET
    try:
        r = requests.get(url, timeout=10,
                         headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(r.content)
        items = []
        for item in root.iter("item"):
            title = item.findtext("title", "").strip()
            link  = item.findtext("link", "").strip()
            pub   = item.findtext("pubDate", "").strip()
            desc  = item.findtext("description", "").strip()
            items.append({"title": title, "link": link,
                          "published": pub, "summary": desc})
        return items[:30]
    except Exception:
        return []

# ── Financial Modeling Prep ────────────────────────────────────────────────────
FMP_BASE = "https://financialmodelingprep.com/api/v3"

@ttl_cache(3600)
def get_fmp(endpoint: str, ticker: str = "", extra: dict = {}) -> dict | list:
    key = FMP_KEY()
    if not key:
        return {}
    url = f"{FMP_BASE}/{endpoint}/{ticker}" if ticker else f"{FMP_BASE}/{endpoint}"
    params = {"apikey": key, **extra}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}

# ── Polygon.io ────────────────────────────────────────────────────────────────
@ttl_cache(60)
def get_polygon_quote(ticker: str) -> dict:
    key = POLYGON_KEY()
    if not key:
        return {}
    url = f"https://api.polygon.io/v2/last/nbbo/{ticker}"
    try:
        r = requests.get(url, params={"apiKey": key}, timeout=10)
        r.raise_for_status()
        return r.json().get("results", {})
    except Exception:
        return {}

# ── Options via Tradier ────────────────────────────────────────────────────────
@ttl_cache(120)
def get_options_chain(ticker: str, expiration: str = "") -> dict:
    key = TRADIER_KEY()
    if not key:
        return {}
    base = "https://api.tradier.com/v1/markets/options/chains"
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    params = {"symbol": ticker, "greeks": "true"}
    if expiration:
        params["expiration"] = expiration
    try:
        r = requests.get(base, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("options", {})
    except Exception:
        return {}

@ttl_cache(300)
def get_options_expirations(ticker: str) -> list[str]:
    key = TRADIER_KEY()
    if not key:
        return []
    url = "https://api.tradier.com/v1/markets/options/expirations"
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    try:
        r = requests.get(url, headers=headers,
                         params={"symbol": ticker}, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("expirations", {}).get("date", []) or []
    except Exception:
        return []

# ── Forex Factory calendar (public JSON) ──────────────────────────────────────
@ttl_cache(3600)
def get_forex_factory_calendar() -> list[dict]:
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []

# ── Formatting helpers ─────────────────────────────────────────────────────────
def fmt_price(v, decimals=2):
    if v is None: return "—"
    return f"{v:,.{decimals}f}"

def fmt_pct(v, decimals=2):
    if v is None: return "—"
    sign = "▲" if v > 0 else "▼" if v < 0 else "—"
    return f"{sign} {abs(v):.{decimals}f}%"

def fmt_large(v):
    if v is None: return "—"
    if v >= 1e12: return f"{v/1e12:.2f}T"
    if v >= 1e9:  return f"{v/1e9:.2f}B"
    if v >= 1e6:  return f"{v/1e6:.2f}M"
    return f"{v:,.0f}"

def color_class(v):
    if v is None: return "flat"
    return "up" if v > 0 else "down" if v < 0 else "flat"
