"""Market data fetching via yfinance with SQLite caching."""

import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from dashboard.data import cache

logger = logging.getLogger(__name__)


def get_quote(ticker: str) -> dict:
    """Get current quote for a ticker (price, change, pct change)."""
    cache_key = f"quote:{ticker}"
    cached = cache.get(cache_key, ttl=60)
    if cached is not None:
        return cached

    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        hist = t.history(period="2d")

        if hist.empty:
            return {"price": None, "change": None, "pct_change": None, "error": True}

        current = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
        change = current - prev
        pct = (change / prev * 100) if prev != 0 else 0

        result = {
            "price": round(current, 4),
            "change": round(change, 4),
            "pct_change": round(pct, 2),
            "volume": int(hist["Volume"].iloc[-1]) if "Volume" in hist else 0,
            "error": False,
        }
        cache.put(cache_key, result)
        return result

    except Exception as e:
        logger.warning(f"Failed to fetch quote for {ticker}: {e}")
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
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval)
        if not df.empty:
            serializable = df.reset_index()
            serializable.columns = [str(c) for c in serializable.columns]
            cache.put(cache_key, serializable.to_dict(orient="list"))
        return df

    except Exception as e:
        logger.warning(f"Failed to fetch history for {ticker}: {e}")
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

    try:
        t = yf.Ticker(ticker)
        info = t.info
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
        logger.warning(f"Failed to fetch info for {ticker}: {e}")
        stale = cache.get(cache_key, ttl=86400)
        return stale or {}


def get_news(ticker: str) -> list[dict]:
    """Get recent news for a ticker."""
    cache_key = f"news:{ticker}"
    cached = cache.get(cache_key, ttl=600)
    if cached is not None:
        return cached

    try:
        t = yf.Ticker(ticker)
        news = t.news or []
        items = []
        for n in news[:15]:
            items.append({
                "title": n.get("title", ""),
                "publisher": n.get("publisher", ""),
                "link": n.get("link", ""),
                "providerPublishTime": n.get("providerPublishTime", 0),
            })
        cache.put(cache_key, items)
        return items

    except Exception as e:
        logger.warning(f"Failed to fetch news for {ticker}: {e}")
        stale = cache.get(cache_key, ttl=86400)
        return stale or []


def get_multiple_quotes(tickers: dict[str, str]) -> dict[str, dict]:
    """Get quotes for multiple tickers. tickers = {label: symbol}."""
    results = {}
    for label, symbol in tickers.items():
        results[label] = get_quote(symbol)
        results[label]["symbol"] = symbol
    return results
