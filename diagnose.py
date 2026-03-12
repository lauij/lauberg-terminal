"""Quick diagnostic to check if yfinance works."""
import yfinance as yf
import pandas as pd
import sys

print(f"yfinance version: {yf.__version__}")
print(f"Python version:   {sys.version}")
print(f"pandas version:   {pd.__version__}")
print()

# Test 1: yf.download (this is what the app now uses)
print("=" * 60)
print("Test 1: yf.download('AAPL', period='5d')")
print("=" * 60)
try:
    df = yf.download("AAPL", period="5d", progress=False, auto_adjust=True, timeout=10)
    print(f"  Shape: {df.shape}")
    print(f"  Columns type: {type(df.columns)}")
    print(f"  Columns: {list(df.columns)}")
    if isinstance(df.columns, pd.MultiIndex):
        print("  >> MultiIndex detected -- flattening...")
        df.columns = df.columns.get_level_values(0)
        print(f"  Flattened columns: {list(df.columns)}")
    if not df.empty:
        print(f"  Last close: {df['Close'].iloc[-1]}")
    else:
        print("  >> EMPTY DataFrame!")
    print()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    print()

# Test 2: FX pair
print("=" * 60)
print("Test 2: yf.download('EURUSD=X', period='5d')")
print("=" * 60)
try:
    df = yf.download("EURUSD=X", period="5d", progress=False, auto_adjust=True, timeout=10)
    print(f"  Shape: {df.shape}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if not df.empty:
        print(f"  Last close: {df['Close'].iloc[-1]}")
    else:
        print("  >> EMPTY DataFrame!")
    print()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    print()

# Test 3: Index
print("=" * 60)
print("Test 3: yf.download('^GSPC', period='5d')  [S&P 500]")
print("=" * 60)
try:
    df = yf.download("^GSPC", period="5d", progress=False, auto_adjust=True, timeout=10)
    print(f"  Shape: {df.shape}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if not df.empty:
        print(f"  Last close: {df['Close'].iloc[-1]}")
    else:
        print("  >> EMPTY DataFrame!")
    print()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    print()

# Test 4: Ticker.info
print("=" * 60)
print("Test 4: yf.Ticker('AAPL').info")
print("=" * 60)
try:
    t = yf.Ticker("AAPL")
    info = t.info
    if info:
        keys_to_show = ["shortName", "marketCap", "trailingPE", "sector"]
        for k in keys_to_show:
            print(f"  {k}: {info.get(k, 'MISSING')}")
    else:
        print("  >> info is empty/None!")
    print()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    print()

print("=" * 60)
print("DONE. If all tests show data, the app should work.")
print("If tests fail, check your internet and try: pip install --upgrade yfinance")
