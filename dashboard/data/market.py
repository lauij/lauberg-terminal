"""Market data fetching via yfinance with SQLite caching."""

import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from dashboard.data import cache

logger = logging.getLogger(__name__)


def _download(ticker: str, period: str = "5d", interval: str = "1d") -> pd.DataFrame:
    """Robust wrapper around yf.download that handles MultiIndex columns."""
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
            timeout=10,
        )
        if df.empty:
            logger.warning(f"yf.download returned empty for {ticker} (period={period})")
            return pd.DataFrame()

        # yfinance >= 0.2.39 returns MultiIndex columns for single tickers too
        # e.g. ('Close', 'AAPL') instead of just 'Close'
        if isinstance(df.columns, pd.MultiIndex):
            # Drop the ticker level, keep only the price level
            df.columns = df.columns.get_level_values(0)

        return df

    except Exception as e:
        logger.error(f"yf.download failed for {ticker}: {e}", exc_info=True)
        return pd.DataFrame()


def get_quote(ticker: str) -> dict:
    """Get current quote for a ticker (price, change, pct change)."""
    cache_key = f"quote:{ticker}"
    cached = cache.get(cache_key, ttl=60)
    if cached is not None:
        return cached

    try:
        hist = _download(ticker, period="5d", interval="1d")

        if hist.empty:
            # Fallback: try 1mo for instruments with sparse data
            hist = _download(ticker, period="1mo", interval="1d")

        if hist.empty:
            logger.warning(f"No data available for {ticker}")
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
        logger.error(f"get_quote failed for {ticker}: {e}", exc_info=True)
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
        df = _download(ticker, period=period, interval=interval)
        if not df.empty:
            serializable = df.reset_index()
            serializable.columns = [str(c) for c in serializable.columns]
            cache.put(cache_key, serializable.to_dict(orient="list"))
        return df

    except Exception as e:
        logger.error(f"get_history failed for {ticker}: {e}", exc_info=True)
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
        info = t.info or {}

        if not info or info.get("trailingPegRatio") is None and info.get("marketCap") is None:
            logger.warning(f"Ticker.info returned minimal data for {ticker}, trying fast_info")
            # Fallback: build from fast_info + history
            try:
                fi = t.fast_info
                hist = _download(ticker, period="5d")
                price = float(hist["Close"].iloc[-1]) if not hist.empty else None
                info = {
                    "shortName": ticker,
                    "marketCap": getattr(fi, "market_cap", None),
                    "fiftyTwoWeekHigh": getattr(fi, "year_high", None),
                    "fiftyTwoWeekLow": getattr(fi, "year_low", None),
                    "currency": getattr(fi, "currency", "USD"),
                }
            except Exception:
                pass

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
        logger.error(f"get_ticker_info failed for {ticker}: {e}", exc_info=True)
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
            # Convert ISO date string to timestamp if needed
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
    """Get quotes for multiple tickers. tickers = {label: symbol}."""
    results = {}
    for label, symbol in tickers.items():
        try:
            results[label] = get_quote(symbol)
            results[label]["symbol"] = symbol
        except Exception as e:
            logger.warning(f"Failed to get quote for {label} ({symbol}): {e}")
            results[label] = {
                "symbol": symbol, "price": None, "change": None,
                "pct_change": None, "error": True,
            }
    return results
