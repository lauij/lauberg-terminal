"""Diagnostic: test yfinance (no custom session — v1.x uses curl_cffi)."""
import time
import yfinance as yf
import pandas as pd
import sys

print(f"yfinance version: {yf.__version__}")
print(f"Python version:   {sys.version}")
print(f"pandas version:   {pd.__version__}")
print()

def flatten(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# Test 1: Single ticker
print("=" * 60)
print("Test 1: yf.download('AAPL', period='5d')")
print("=" * 60)
try:
    df = yf.download("AAPL", period="5d", progress=False, auto_adjust=True, timeout=15)
    df = flatten(df)
    if not df.empty:
        print(f"  Last close: {df['Close'].iloc[-1]}")
        print("  >> SUCCESS")
    else:
        print("  >> EMPTY")
except Exception as e:
    print(f"  ERROR: {e}")
print()
time.sleep(1)

# Test 2: Batch download
print("=" * 60)
print("Test 2: BATCH download (^GSPC AAPL EURUSD=X GC=F)")
print("=" * 60)
try:
    df = yf.download("^GSPC AAPL EURUSD=X GC=F", period="5d", progress=False,
                     auto_adjust=True, timeout=20, group_by="ticker", threads=False)
    if not df.empty and isinstance(df.columns, pd.MultiIndex):
        for t in ["^GSPC", "AAPL", "EURUSD=X", "GC=F"]:
            try:
                if t in df.columns.get_level_values(0):
                    sub = df[t].dropna(how="all")
                    if not sub.empty:
                        print(f"  {t}: {sub['Close'].iloc[-1]}")
                    else:
                        print(f"  {t}: EMPTY")
                else:
                    print(f"  {t}: NOT FOUND")
            except Exception as e2:
                print(f"  {t}: ERROR - {e2}")
        print("  >> SUCCESS")
    elif not df.empty:
        print(f"  Shape: {df.shape} (single-level columns)")
    else:
        print("  >> EMPTY")
except Exception as e:
    print(f"  ERROR: {e}")
print()
time.sleep(1)

# Test 3: Ticker.info
print("=" * 60)
print("Test 3: yf.Ticker('AAPL').info")
print("=" * 60)
try:
    t = yf.Ticker("AAPL")
    info = t.info
    if info:
        for k in ["shortName", "marketCap", "trailingPE", "sector"]:
            print(f"  {k}: {info.get(k, 'MISSING')}")
        print("  >> SUCCESS")
    else:
        print("  >> EMPTY")
except Exception as e:
    print(f"  ERROR: {e}")
print()
time.sleep(1)

# Test 4: News
print("=" * 60)
print("Test 4: yf.Ticker('AAPL').news")
print("=" * 60)
try:
    t = yf.Ticker("AAPL")
    news = t.news
    if news:
        print(f"  Got {len(news)} items")
        first = news[0]
        content = first.get("content", first)
        title = content.get("title", first.get("title", "N/A"))
        print(f"  First: {title[:80]}")
        print("  >> SUCCESS")
    else:
        print("  >> No news")
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("=" * 60)
print("DONE.")
