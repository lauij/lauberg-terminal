"""Market data fetching via yfinance with SQLite caching.

Uses batched yf.download() calls and a custom requests session with
proper headers to avoid Yahoo Finance rate limiting (429 errors).
"""

import logging
import time
from datetime import datetime, timedelta

import pandas as pd
import requests
import yfinance as yf

from dashboard.data import cache

logger = logging.getLogger(__name__)

# ─── Custom session to avoid 429s ────────────────────────────────────────────
_session = requests.Session()
_session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
})

# Minimum seconds between Yahoo API calls
_RATE_LIMIT_DELAY = 0.5
_last_call_time = 0.0


def _rate_limit():
    """Simple rate limiter to avoid 429 Too Many Requests."""
    global _last_call_time
    now = time.time()
    elapsed = now - _last_call_time
    if elapsed < _RATE_LIMIT_DELAY:
        time.sleep(_RATE_LIMIT_DELAY - elapsed)
    _last_call_time = time.time()


# ─── Core download functions ─────────────────────────────────────────────────

def _download_single(ticker: str, period: str = "5d", interval: str = "1d") -> pd.DataFrame:
    """Download data for a single ticker with rate limiting."""
    _rate_limit()
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
            timeout=15,
            session=_session,
        )
        if df.empty:
            logger.warning(f"Empty data for {ticker} (period={period})")
            return pd.DataFrame()

        # yfinance >= 0.2.39 returns MultiIndex columns even for single tickers
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return df

    except Exception as e:
        logger.error(f"Download failed for {ticker}: {e}")
        return pd.DataFrame()


def _download_batch(tickers: list[str], period: str = "5d", interval: str = "1d") -> dict[str, pd.DataFrame]:
    """Download data for multiple tickers in ONE request (much less rate limiting)."""
    if not tickers:
        return {}

    _rate_limit()
    ticker_str = " ".join(tickers)

    try:
        df = yf.download(
            ticker_str,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
            timeout=20,
            session=_session,
            group_by="ticker",
            threads=False,
        )
    except Exception as e:
        logger.error(f"Batch download failed for {ticker_str}: {e}")
        return {}

    if df.empty:
        logger.warning(f"Batch download returned empty for {ticker_str}")
        return {}

    results = {}

    # Single ticker: no MultiIndex on columns or grouped differently
    if len(tickers) == 1:
        t = tickers[0]
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        results[t] = df
        return results

    # Multiple tickers: columns are MultiIndex (ticker, field)
    if isinstance(df.columns, pd.MultiIndex):
        for t in tickers:
            try:
                ticker_df = df[t].copy() if t in df.columns.get_level_values(0) else pd.DataFrame()
                if not ticker_df.empty:
                    ticker_df = ticker_df.dropna(how="all")
                if not ticker_df.empty:
                    results[t] = ticker_df
            except (KeyError, TypeError):
                logger.warning(f"Could not extract {t} from batch download")
    else:
        # Fallback: treat as single ticker
        results[tickers[0]] = df

    return results


# ─── Public API ──────────────────────────────────────────────────────────────

def get_quote(ticker: str) -> dict:
    """Get current quote for a ticker (price, change, pct change)."""
    cache_key = f"quote:{ticker}"
    cached = cache.get(cache_key, ttl=60)
    if cached is not None:
        return cached

    try:
        hist = _download_single(ticker, period="5d", interval="1d")

        if hist.empty:
            hist = _download_single(ticker, period="1mo", interval="1d")

        if hist.empty:
            stale = cache.get(cache_key, ttl=86400)
            if stale:
                stale["stale"] = True
                return stale
            return {"price": None, "change": None, "pct_change": None, "error": True}

        current = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
        change = current - prev
        pct = (change / prev * 100) if prev != 0 else 0

        vol = 0
        if "Volume" in hist.columns:
            v = hist["Volume"].iloc[-1]
            if pd.notna(v) and v > 0:
                vol = int(v)

        result = {
            "price": round(current, 4),
            "change": round(change, 4),
            "pct_change": round(pct, 2),
            "volume": vol,
            "error": False,
        }
        cache.put(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"get_quote failed for {ticker}: {e}")
        stale = cache.get(cache_key, ttl=86400)
        if stale:
            stale["stale"] = True
            return stale
        return {"price": None, "change": None, "pct_change": None, "error": True}


def get_history(
    ticker: str, period: str = "1y", interval: str = "1d"
) -> pd.DataFrame:
    """Get historical OHLCV data for a ticker."""
    cache_key = f"hist:{ticker}:{period}:{interval}"
    cached = cache.get(cache_key, ttl=300)
    if cached is not None:
        df = pd.DataFrame(cached)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)
        return df

    try:
        df = _download_single(ticker, period=period, interval=interval)
        if not df.empty:
            serializable = df.reset_index()
            serializable.columns = [str(c) for c in serializable.columns]
            cache.put(cache_key, serializable.to_dict(orient="list"))
        return df

    except Exception as e:
        logger.error(f"get_history failed for {ticker}: {e}")
        stale = cache.get(cache_key, ttl=86400)
        if stale:
            df = pd.DataFrame(stale)
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                df.set_index("Date", inplace=True)
            return df
        return pd.DataFrame()


def get_ticker_info(ticker: str) -> dict:
    """Get detailed ticker info (fundamentals, stats)."""
    cache_key = f"info:{ticker}"
    cached = cache.get(cache_key, ttl=600)
    if cached is not None:
        return cached

    _rate_limit()
    try:
        t = yf.Ticker(ticker, session=_session)
        info = t.info or {}

        result = {
            "shortName": info.get("shortName", ticker),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "marketCap": info.get("marketCap"),
            "enterpriseValue": info.get("enterpriseValue"),
            "trailingPE": info.get("trailingPE"),
            "forwardPE": info.get("forwardPE"),
            "pegRatio": info.get("pegRatio"),
            "priceToBook": info.get("priceToBook"),
            "enterpriseToEbitda": info.get("enterpriseToEbitda"),
            "revenueGrowth": info.get("revenueGrowth"),
            "earningsGrowth": info.get("earningsGrowth"),
            "grossMargins": info.get("grossMargins"),
            "operatingMargins": info.get("operatingMargins"),
            "profitMargins": info.get("profitMargins"),
            "returnOnEquity": info.get("returnOnEquity"),
            "dividendYield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
            "targetMeanPrice": info.get("targetMeanPrice"),
            "targetHighPrice": info.get("targetHighPrice"),
            "targetLowPrice": info.get("targetLowPrice"),
            "numberOfAnalystOpinions": info.get("numberOfAnalystOpinions"),
            "recommendationKey": info.get("recommendationKey"),
            "currency": info.get("currency", "USD"),
        }
        cache.put(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"get_ticker_info failed for {ticker}: {e}")
        stale = cache.get(cache_key, ttl=86400)
        return stale or {}


def get_news(ticker: str) -> list[dict]:
    """Get recent news for a ticker."""
    cache_key = f"news:{ticker}"
    cached = cache.get(cache_key, ttl=600)
    if cached is not None:
        return cached

    _rate_limit()
    try:
        t = yf.Ticker(ticker, session=_session)
        raw_news = t.news or []
        items = []
        for n in raw_news[:15]:
            # yfinance >= 0.2.36 nests data under "content"
            content = n.get("content", n)
            title = content.get("title", n.get("title", ""))
            publisher = content.get("provider", {})
            if isinstance(publisher, dict):
                publisher = publisher.get("displayName", "")
            else:
                publisher = n.get("publisher", str(publisher))
            link = content.get("canonicalUrl", {})
            if isinstance(link, dict):
                link = link.get("url", "")
            else:
                link = n.get("link", str(link))
            pub_time = content.get("pubDate", n.get("providerPublishTime", 0))
            if isinstance(pub_time, str):
                try:
                    from datetime import datetime as _dt
                    pub_time = int(_dt.fromisoformat(pub_time.replace("Z", "+00:00")).timestamp())
                except (ValueError, TypeError):
                    pub_time = 0
            items.append({
                "title": title,
                "publisher": publisher,
                "link": link,
                "providerPublishTime": pub_time,
            })
        cache.put(cache_key, items)
        return items

    except Exception as e:
        logger.warning(f"Failed to fetch news for {ticker}: {e}")
        stale = cache.get(cache_key, ttl=86400)
        return stale or []


def get_multiple_quotes(tickers: dict[str, str]) -> dict[str, dict]:
    """Get quotes for multiple tickers in a SINGLE batch request."""
    # Check cache first
    results = {}
    uncached_labels = {}
    for label, symbol in tickers.items():
        cache_key = f"quote:{symbol}"
        cached = cache.get(cache_key, ttl=60)
        if cached is not None:
            results[label] = cached
            results[label]["symbol"] = symbol
        else:
            uncached_labels[label] = symbol

    if not uncached_labels:
        return results

    # Batch download all uncached tickers in ONE request
    symbols = list(uncached_labels.values())
    batch_data = _download_batch(symbols, period="5d", interval="1d")

    for label, symbol in uncached_labels.items():
        try:
            hist = batch_data.get(symbol, pd.DataFrame())

            if hist.empty:
                results[label] = {
                    "symbol": symbol, "price": None, "change": None,
                    "pct_change": None, "error": True,
                }
                continue

            current = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
            change = current - prev
            pct = (change / prev * 100) if prev != 0 else 0

            vol = 0
            if "Volume" in hist.columns:
                v = hist["Volume"].iloc[-1]
                if pd.notna(v) and v > 0:
                    vol = int(v)

            quote = {
                "price": round(current, 4),
                "change": round(change, 4),
                "pct_change": round(pct, 2),
                "volume": vol,
                "error": False,
                "symbol": symbol,
            }
            cache.put(f"quote:{symbol}", quote)
            results[label] = quote

        except Exception as e:
            logger.warning(f"Failed to process {label} ({symbol}): {e}")
            results[label] = {
                "symbol": symbol, "price": None, "change": None,
                "pct_change": None, "error": True,
            }

    return results
