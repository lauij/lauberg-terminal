"""Application configuration."""

import os
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY", "")
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8050"))
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache.db")

# Bloomberg-style color palette
COLORS = {
    "bg": "#0a0a0a",
    "panel_bg": "#1a1a2e",
    "card_bg": "#16213e",
    "border": "#2a2a4a",
    "text": "#e0e0e0",
    "text_muted": "#888888",
    "accent": "#ff9800",
    "accent_secondary": "#ffc107",
    "green": "#00c853",
    "red": "#ff1744",
    "blue": "#2196f3",
    "cyan": "#00bcd4",
    "header_bg": "#0d1117",
    "input_bg": "#1e1e3f",
}

# Watchlist tickers for market overview
MARKET_TICKERS = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DAX": "^GDAXI",
    "FTSE 100": "^FTSE",
    "WTI Crude": "CL=F",
    "Brent Crude": "BZ=F",
    "Gold": "GC=F",
    "EUR/USD": "EURUSD=X",
    "USD/DKK": "DKK=X",
    "US 10Y": "^TNX",
}

# FRED series IDs
FRED_SERIES = {
    "Fed Funds Rate": "FEDFUNDS",
    "CPI YoY": "CPIAUCSL",
    "PCE YoY": "PCEPI",
    "Unemployment": "UNRATE",
    "Real GDP Growth": "A191RL1Q225SBEA",
    "M2 Money Supply": "M2SL",
    "HY Spread": "BAMLH0A0HYM2",
    "IG Spread": "BAMLC0A0CM",
    "Sahm Rule": "SAHMREALTIME",
}

TREASURY_MATURITIES = {
    "3M": "DGS3MO",
    "6M": "DGS6MO",
    "1Y": "DGS1",
    "2Y": "DGS2",
    "3Y": "DGS3",
    "5Y": "DGS5",
    "7Y": "DGS7",
    "10Y": "DGS10",
    "20Y": "DGS20",
    "30Y": "DGS30",
}

FX_PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "USD/DKK": "DKK=X",
    "USD/CNY": "CNY=X",
    "EUR/GBP": "EURGBP=X",
}

COMMODITIES = {
    "Crude Oil (WTI)": "CL=F",
    "Brent Crude": "BZ=F",
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Natural Gas": "NG=F",
    "Copper": "HG=F",
}

REFRESH_INTERVAL_MS = 60_000  # 60 seconds
