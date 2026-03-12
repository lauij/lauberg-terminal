"""FRED data fetching with caching."""

import logging
from datetime import datetime, timedelta

import pandas as pd

from dashboard.config import FRED_API_KEY, TREASURY_MATURITIES, FRED_SERIES
from dashboard.data import cache

logger = logging.getLogger(__name__)

_fred = None


def _get_fred():
    global _fred
    if _fred is None:
        if not FRED_API_KEY:
            logger.warning("FRED_API_KEY not set — macro data will be unavailable")
            return None
        from fredapi import Fred
        _fred = Fred(api_key=FRED_API_KEY)
    return _fred


def get_series(
    series_id: str, start: str | None = None, ttl: int = 3600
) -> pd.Series:
    """Fetch a FRED series with caching."""
    cache_key = f"fred:{series_id}:{start or 'default'}"
    cached = cache.get(cache_key, ttl=ttl)
    if cached is not None:
        s = pd.Series(cached["values"], index=pd.to_datetime(cached["index"]))
        s.name = series_id
        return s

    fred = _get_fred()
    if fred is None:
        return pd.Series(dtype=float, name=series_id)

    try:
        if start:
            data = fred.get_series(series_id, observation_start=start)
        else:
            data = fred.get_series(series_id)

        data = data.dropna()
        cache.put(cache_key, {
            "values": data.values.tolist(),
            "index": data.index.strftime("%Y-%m-%d").tolist(),
        })
        return data

    except Exception as e:
        logger.warning(f"Failed to fetch FRED series {series_id}: {e}")
        stale = cache.get(cache_key, ttl=86400 * 7)
        if stale:
            return pd.Series(
                stale["values"],
                index=pd.to_datetime(stale["index"]),
                name=series_id,
            )
        return pd.Series(dtype=float, name=series_id)


def get_yield_curve() -> dict:
    """Fetch current and 1Y-ago yield curve data."""
    cache_key = "fred:yield_curve"
    cached = cache.get(cache_key, ttl=3600)
    if cached is not None:
        return cached

    maturities = list(TREASURY_MATURITIES.keys())
    current_yields = []
    year_ago_yields = []
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    for label, series_id in TREASURY_MATURITIES.items():
        s = get_series(series_id, start=one_year_ago, ttl=3600)
        if not s.empty:
            current_yields.append(s.iloc[-1])
            # Find value closest to 1 year ago
            target = pd.Timestamp(one_year_ago)
            closest_idx = s.index.get_indexer([target], method="nearest")[0]
            year_ago_yields.append(s.iloc[closest_idx])
        else:
            current_yields.append(None)
            year_ago_yields.append(None)

    result = {
        "maturities": maturities,
        "current": current_yields,
        "year_ago": year_ago_yields,
    }
    cache.put(cache_key, result)
    return result


def get_macro_summary() -> dict:
    """Get latest values for key macro indicators."""
    cache_key = "fred:macro_summary"
    cached = cache.get(cache_key, ttl=3600)
    if cached is not None:
        return cached

    start = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y-%m-%d")
    result = {}

    for label, series_id in FRED_SERIES.items():
        s = get_series(series_id, start=start, ttl=3600)
        if not s.empty:
            latest = s.iloc[-1]
            prev = s.iloc[-2] if len(s) > 1 else latest
            result[label] = {
                "value": round(float(latest), 2),
                "prev": round(float(prev), 2),
                "change": round(float(latest - prev), 2),
                "date": s.index[-1].strftime("%Y-%m-%d"),
            }
        else:
            result[label] = {"value": None, "prev": None, "change": None, "date": None}

    # Compute YoY for CPI and PCE
    for label, series_id in [("CPI YoY", "CPIAUCSL"), ("PCE YoY", "PCEPI")]:
        s = get_series(series_id, start=start, ttl=3600)
        if len(s) >= 13:
            yoy = ((s.iloc[-1] / s.iloc[-13]) - 1) * 100
            result[label]["yoy"] = round(float(yoy), 2)

    # Yield curve inversion check
    ten_year = get_series("DGS10", start=start, ttl=3600)
    two_year = get_series("DGS2", start=start, ttl=3600)
    three_month = get_series("DGS3MO", start=start, ttl=3600)
    result["_yield_curve_inverted"] = False
    result["_10y2y_spread"] = None
    result["_10y3m_spread"] = None
    if not ten_year.empty and not two_year.empty:
        spread = float(ten_year.iloc[-1] - two_year.iloc[-1])
        result["_10y2y_spread"] = round(spread, 2)
        if spread < 0:
            result["_yield_curve_inverted"] = True
    if not ten_year.empty and not three_month.empty:
        result["_10y3m_spread"] = round(
            float(ten_year.iloc[-1] - three_month.iloc[-1]), 2
        )

    cache.put(cache_key, result)
    return result


def get_fed_funds_history() -> pd.Series:
    """Get Fed Funds Rate history for the past 5 years."""
    start = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")
    return get_series("FEDFUNDS", start=start, ttl=3600)
