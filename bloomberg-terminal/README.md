# 📊 Personal Bloomberg Terminal

> A Bloomberg-style financial terminal built with Python & Streamlit.
> Secured with password + TOTP (2FA). Deployable on Streamlit Cloud via GitHub.

---

## Features

| Tab | Data sources |
|-----|-------------|
| 📈 Market Data | Yahoo Finance (quotes, charts), FRED (VIX, rates, DXY) |
| 📰 News Feed | RSS (FT, Economist, WSJ, Reuters, Bloomberg) + NewsAPI + ForexFactory calendar |
| 💼 Earnings & Fundamentals | Yahoo Finance + Financial Modeling Prep |
| 🎯 Options & Derivatives | yfinance (free) + Tradier (optional, for greeks) |
| 📊 Portfolio Tracker | Trade entry form, live P&L, allocation chart, CSV export |

**Security:** SHA-256 hashed password + TOTP 2FA (Google Authenticator / Authy)

---

## Quick Start (Local)

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/bloomberg-terminal.git
cd bloomberg-terminal
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Generate auth credentials
```bash
python setup_auth.py
```
This prints your `APP_PASSWORD_HASH` and `TOTP_SECRET`. Scan the QR into your authenticator app.

### 4. Create your secrets file
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Fill in the values from step 3, plus your API keys
nano .streamlit/secrets.toml
```

### 5. Run locally
```bash
streamlit run app.py
```
Open http://localhost:8501 and log in.

---

## Deploy to Streamlit Cloud (Free, via GitHub)

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "Initial terminal"
git remote add origin https://github.com/YOUR_USERNAME/bloomberg-terminal.git
git push -u origin main
```

### Step 2 — Connect Streamlit Cloud
1. Go to **[share.streamlit.io](https://share.streamlit.io)**
2. Sign in with GitHub
3. Click **New app** → select your repo → main branch → `app.py`
4. Click **Advanced settings** → paste your secrets:

```toml
APP_PASSWORD_HASH = "your_hash_here"
TOTP_SECRET       = "your_totp_secret"
FRED_API_KEY      = "your_fred_key"
NEWS_API_KEY      = ""
FMP_API_KEY       = ""
TRADIER_KEY       = ""
```

5. Deploy — you get a free `yourname.streamlit.app` URL.

> ⚠️ **NEVER push `.streamlit/secrets.toml` to GitHub.** It's in `.gitignore`.

---

## API Keys (Free Tiers)

| Service | What it unlocks | Get key |
|---------|----------------|---------|
| **FRED** | 800,000 macro series (you already have this ✓) | fred.stlouisfed.org |
| **NewsAPI** | 100 req/day free | newsapi.org |
| **Financial Modeling Prep** | Earnings calendar, income statements | financialmodelingprep.com |
| **Tradier** | Options chain with greeks | developer.tradier.com (free sandbox) |
| **Polygon.io** | Real-time quotes (15-min delay free) | polygon.io |
| **Alpha Vantage** | Extra fundamentals | alphavantage.co |

Yahoo Finance (yfinance) works **without any API key**.

---

## Portfolio — Adding Positions

1. Go to **📊 Portfolio Tracker** → **➕ Add / Edit Trade**
2. Enter ticker, quantity, average purchase price, asset class
3. Click **Add Position**

Positions are saved to `data/portfolio.json` locally.
On Streamlit Cloud, positions reset on redeploy — export CSV regularly, or move to a database (SQLite / Supabase) for persistence.

---

## Project Structure

```
bloomberg-terminal/
├── app.py                    # Entry point + MFA auth
├── requirements.txt
├── setup_auth.py             # One-time credential generator
├── assets/
│   └── style.css             # Bloomberg color scheme
├── pages/
│   ├── market_data.py        # Tab 1
│   ├── news_feed.py          # Tab 2
│   ├── earnings.py           # Tab 3
│   ├── options.py            # Tab 4
│   └── portfolio.py          # Tab 5
├── utils/
│   └── data.py               # All API calls, caching, formatters
├── data/
│   └── portfolio.json        # Your positions (gitignored)
├── .streamlit/
│   ├── config.toml           # Dark Bloomberg theme
│   ├── secrets.toml          # LOCAL ONLY — gitignored
│   └── secrets.toml.example  # Template
└── .github/
    └── workflows/
        └── deploy.yml        # CI syntax check on push
```

---

## Extending the Terminal

### Add a new watchlist ticker
Edit `WATCHLISTS` dict in `pages/market_data.py`.

### Add a new FRED macro indicator
Add to the `macro` dict in `pages/market_data.py` with the FRED series ID.

### Add a new RSS feed
Add to `RSS_FEEDS` dict in `pages/news_feed.py`.

### Add a new tab
1. Create `pages/my_tab.py` with a `render()` function
2. Add to `TABS` dict in `app.py`

---

## Security Notes

- Password is stored as a SHA-256 hash — never in plaintext
- TOTP adds a time-based second factor (30-second rolling codes)
- All secrets via environment / Streamlit secrets — never in code
- `portfolio.json` is gitignored
- Session timeout: refresh page to log out, or use the Logout button
- For higher security: add IP allowlist via a VPN + Tailscale, or use Cloudflare Access in front of your deployment

---

## Bloomberg Color Reference

| Variable | Hex | Use |
|----------|-----|-----|
| `--bb-orange` | `#FF6600` | Primary accent, borders |
| `--bb-dark` | `#0D0D0D` | Background |
| `--bb-card` | `#1C1C1C` | Card backgrounds |
| `--bb-green` | `#00CC66` | Price up / profit |
| `--bb-red` | `#FF3333` | Price down / loss |
| `--bb-text` | `#E0E0E0` | Body text |
| `--bb-muted` | `#777777` | Labels, metadata |
