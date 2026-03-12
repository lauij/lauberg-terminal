"""Diagnostic: test yfinance with custom session (same as the app uses)."""
import time
import yfinance as yf
import pandas as pd
import requests
import sys

print(f"yfinance version: {yf.__version__}")
print(f"Python version:   {sys.version}")
print(f"pandas version:   {pd.__version__}")
print()

# Custom session with browser User-Agent (avoids 429)
session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
})

# Test 1: Single ticker with session
print("=" * 60)
print("Test 1: yf.download('AAPL', period='5d') WITH session")
print("=" * 60)
try:
    df = yf.download("AAPL", period="5d", progress=False, auto_adjust=True,
                     timeout=15, session=session)
    print(f"  Shape: {df.shape}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if not df.empty:
        print(f"  Last close: {df['Close'].iloc[-1]}")
        print("  >> SUCCESS")
    else:
        print("  >> EMPTY DataFrame")
except Exception as e:
    print(f"  ERROR: {e}")
print()
time.sleep(1)

# Test 2: Batch download (market overview style)
print("=" * 60)
print("Test 2: BATCH download (^GSPC AAPL EURUSD=X GC=F)")
print("=" * 60)
try:
    tickers = "^GSPC AAPL EURUSD=X GC=F"
    df = yf.download(tickers, period="5d", progress=False, auto_adjust=True,
                     timeout=20, session=session, group_by="ticker", threads=False)
    print(f"  Shape: {df.shape}")
    print(f"  Columns type: {type(df.columns)}")

    if isinstance(df.columns, pd.MultiIndex):
        for t in ["^GSPC", "AAPL", "EURUSD=X", "GC=F"]:
            try:
                if t in df.columns.get_level_values(0):
                    sub = df[t].dropna(how="all")
                    if not sub.empty:
                        print(f"  {t}: last close = {sub['Close'].iloc[-1]}")
                    else:
                        print(f"  {t}: EMPTY after dropna")
                else:
                    print(f"  {t}: NOT in columns")
            except Exception as e2:
                print(f"  {t}: ERROR - {e2}")
    else:
        print(f"  Columns: {list(df.columns)}")
        if not df.empty:
            print(f"  Last close: {df['Close'].iloc[-1]}")
        else:
            print("  >> EMPTY")
except Exception as e:
    print(f"  ERROR: {e}")
print()
time.sleep(1)

# Test 3: Ticker.info with session
print("=" * 60)
print("Test 3: yf.Ticker('AAPL', session=session).info")
print("=" * 60)
try:
    t = yf.Ticker("AAPL", session=session)
    info = t.info
    if info:
        for k in ["shortName", "marketCap", "trailingPE", "sector"]:
            print(f"  {k}: {info.get(k, 'MISSING')}")
        print("  >> SUCCESS")
    else:
        print("  >> info is empty/None")
except Exception as e:
    print(f"  ERROR: {e}")
print()
time.sleep(1)

# Test 4: News
print("=" * 60)
print("Test 4: yf.Ticker('AAPL', session=session).news")
print("=" * 60)
try:
    t = yf.Ticker("AAPL", session=session)
    news = t.news
    if news:
        print(f"  Got {len(news)} news items")
        first = news[0]
        print(f"  Keys in first item: {list(first.keys())}")
        # Show title depending on structure
        content = first.get("content", first)
        title = content.get("title", first.get("title", "N/A"))
        print(f"  First title: {title}")
        print("  >> SUCCESS")
    else:
        print("  >> No news returned")
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("=" * 60)
print("DONE.")
print()
print("If tests STILL fail with JSONDecodeError/429:")
print("  1. Wait 5-10 minutes (Yahoo rate limit cooldown)")
print("  2. Try: pip install --upgrade yfinance")
print("  3. Check if Yahoo Finance works in your browser")
