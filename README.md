# LAUBERG TERMINAL

A Bloomberg Terminal-inspired financial dashboard built with Python, Dash/Plotly, yfinance, and FRED.

Professional, data-dense, and analytical — designed to feel like a tool a sell-side analyst would actually use.

## Features

### Market Overview (Top Bar)
- Real-time-ish prices for S&P 500, NASDAQ, DAX, FTSE, WTI/Brent crude, gold, EUR/USD, USD/DKK, US 10Y yield
- Color-coded green/red for up/down moves
- Auto-refreshes every 60 seconds

### Equity Deep-Dive (F1)
- Candlestick charts with 50d/200d moving averages and volume bars
- Timeframes: 1D, 5D, 1M, 3M, 1Y, 5Y
- Key stats: P/E, EV/EBITDA, margins, growth rates, ROE, beta
- Analyst consensus targets (low/mean/high)
- News feed per ticker

### Macro Dashboard (F2)
- US Treasury yield curve: current vs 1 year ago
- Inflation: CPI YoY vs PCE YoY with 2% target line
- Fed Funds Rate history (5Y)
- Credit spreads: HY vs IG (OAS)
- Recession indicators: Sahm Rule, yield curve inversion flags, 10Y-2Y and 10Y-3M spreads

### Portfolio Tracker (F3)
- Custom portfolio: enter tickers and weights
- Performance vs SPY benchmark (cumulative returns)
- Risk metrics: annualized return, volatility, Sharpe ratio, max drawdown
- Correlation matrix heatmap
- Sector exposure pie chart
- Returns attribution by holding

### FX & Commodities (F4)
- FX pairs: EUR/USD, GBP/USD, USD/JPY, USD/DKK, USD/CNY, EUR/GBP
- Commodities: WTI, Brent, Gold, Silver, Natural Gas, Copper
- Period returns: 1D, 1W, 1M, YTD
- Mini sparkline charts (3M)

### Screener / Comparator (F5)
- Compare up to 5 tickers side by side
- Normalized price performance chart (rebased to 100)
- Key multiples comparison table
- Export to CSV

### News Feed (F6)
- Aggregated headlines from yfinance
- Filter by topic: All, Tech, Energy, Macro, Crypto
- Custom ticker filter
- Auto-refresh every 5 minutes

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd lauberg-terminal
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
```

Edit `.env` and add your FRED API key:
- Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html
- The app works without a FRED key, but the Macro Dashboard will show no data

### 3. Run the dashboard

```bash
python app.py
```

Open http://127.0.0.1:8050 in your browser.

## Keyboard Shortcuts

| Key | Panel |
|-----|-------|
| F1  | Equity Deep-Dive |
| F2  | Macro Dashboard |
| F3  | Portfolio Tracker |
| F4  | FX & Commodities |
| F5  | Screener / Comparator |
| F6  | News Feed |

## Architecture

```
lauberg-terminal/
├── app.py                      # Main Dash application
├── requirements.txt            # Pinned dependencies
├── .env.example                # Environment variable template
├── assets/
│   └── bloomberg.css           # Bloomberg-style dark theme
├── dashboard/
│   ├── config.py               # Colors, tickers, FRED series, settings
│   ├── data/
│   │   ├── cache.py            # SQLite caching layer
│   │   ├── market.py           # yfinance data fetching
│   │   └── fred.py             # FRED API data fetching
│   ├── panels/
│   │   ├── market_overview.py  # Top ticker bar
│   │   ├── equity.py           # Equity deep-dive
│   │   ├── macro.py            # Macro dashboard
│   │   ├── portfolio.py        # Portfolio tracker
│   │   ├── fx_commodities.py   # FX & commodities
│   │   ├── screener.py         # Screener / comparator
│   │   └── news.py             # News feed
│   └── utils/
│       └── formatting.py       # Number formatting, colors, chart layouts
└── tests/
```

## Adding New Data Sources

1. Create a new module in `dashboard/data/` (e.g., `dashboard/data/openbb.py`)
2. Use the `dashboard/data/cache.py` layer for caching: call `cache.get(key)` before fetching, `cache.put(key, data)` after
3. Create a new panel in `dashboard/panels/` with `layout()` and `register_callbacks(app)` functions
4. Import and register in `app.py`

## Configuration

All configuration is in `dashboard/config.py`:
- `MARKET_TICKERS`: Watchlist for the market overview bar
- `FRED_SERIES`: FRED series IDs for macro indicators
- `TREASURY_MATURITIES`: Yield curve tenors
- `FX_PAIRS` / `COMMODITIES`: Asset lists
- `COLORS`: Bloomberg-style color palette
- `REFRESH_INTERVAL_MS`: Auto-refresh interval (default 60s)

Environment variables (`.env`):
- `FRED_API_KEY`: Required for macro data
- `CACHE_TTL`: Cache expiry in seconds (default 300)
- `HOST` / `PORT`: Server bind address (default 127.0.0.1:8050)

## Tech Stack

- **Dash** + **Plotly**: Interactive web dashboard with rich charting
- **dash-bootstrap-components**: Layout and responsive design
- **yfinance**: Equities, ETFs, indices, FX, crypto, commodities
- **fredapi**: Macro data (GDP, CPI, unemployment, Fed funds, yield curves)
- **SQLite**: Local data cache to avoid redundant API calls
- **pandas** + **numpy**: Data manipulation and portfolio analytics
