"""
Live market data fetching with fallback to hardcoded values.
Fetches 252 trading days of data from yfinance and computes:
  - Annualised return  = mean daily return * 252
  - Annualised volatility = std daily return * sqrt(252)
  - Covariance matrix  = daily returns covariance * 252
Results are cached for 1 hour to avoid API rate limits.
"""

import logging
import time
from functools import lru_cache

import numpy as np

logger = logging.getLogger(__name__)

ASSET_TICKERS: dict[str, str | None] = {
    "Stocks": "SPY",
    "Bonds": "AGG",
    "Cash": None,           # fixed rate
    "Real Estate": "VNQ",
    "Commodities": "GLD",
    "Alternative Investments": None,  # fixed estimate
}

CASH_RATE = 0.05          # approximate current risk-free / SOFR
ALT_INV_RETURN = 0.07
ALT_INV_VOL = 0.18

FALLBACK_MARKET_DATA: dict[str, dict[str, float]] = {
    "Stocks": {"ret": 0.09, "vol": 0.15},
    "Bonds": {"ret": 0.04, "vol": 0.05},
    "Cash": {"ret": 0.02, "vol": 0.01},
    "Real Estate": {"ret": 0.06, "vol": 0.10},
    "Commodities": {"ret": 0.03, "vol": 0.12},
    "Alternative Investments": {"ret": 0.07, "vol": 0.18},
}

ASSET_CLASSES = list(FALLBACK_MARKET_DATA.keys())

# Simple time-based cache: (data, timestamp)
_cache: dict[str, object] = {"data": None, "ts": 0.0}
CACHE_TTL = 3600  # 1 hour


def _fetch_live() -> dict:
    """
    Attempt to download price history and compute market parameters.
    Returns a dict with keys: market_data, cov_matrix, source.
    Raises on failure so the caller can fall back.
    """
    import yfinance as yf  # imported here so the module loads without yfinance if needed
    import pandas as pd

    tickers = [t for t in ASSET_TICKERS.values() if t is not None]
    raw = yf.download(tickers, period="1y", auto_adjust=True, progress=False)

    if raw.empty:
        raise ValueError("yfinance returned empty DataFrame")

    # Support both single and multi-ticker response shapes
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw[["Close"]]
        prices.columns = tickers

    daily_returns = prices.pct_change().dropna()

    if len(daily_returns) < 30:
        raise ValueError("Insufficient data rows from yfinance")

    market_data: dict[str, dict[str, float]] = {}
    returns_series: dict[str, object] = {}

    for asset, ticker in ASSET_TICKERS.items():
        if ticker is None:
            if asset == "Cash":
                market_data[asset] = {"ret": CASH_RATE, "vol": 0.01}
                returns_series[asset] = pd.Series(
                    [CASH_RATE / 252] * len(daily_returns), index=daily_returns.index
                )
            else:  # Alternative Investments
                market_data[asset] = {"ret": ALT_INV_RETURN, "vol": ALT_INV_VOL}
                returns_series[asset] = pd.Series(
                    [ALT_INV_RETURN / 252] * len(daily_returns), index=daily_returns.index
                )
        elif ticker in daily_returns.columns:
            series = daily_returns[ticker]
            ann_ret = float(series.mean() * 252)
            ann_vol = float(series.std() * (252 ** 0.5))
            market_data[asset] = {"ret": ann_ret, "vol": ann_vol}
            returns_series[asset] = series
        else:
            raise ValueError(f"Ticker {ticker} not found in downloaded data")

    returns_df = pd.DataFrame(returns_series)
    cov_matrix = (returns_df.cov() * 252).values  # numpy array

    return {"market_data": market_data, "cov_matrix": cov_matrix, "source": "live"}


def get_market_data() -> dict:
    """
    Return cached market data or fetch fresh data.
    Always returns a dict: {market_data, cov_matrix, source}.
    Falls back to hardcoded values on any error.
    """
    global _cache

    now = time.time()
    if _cache["data"] is not None and (now - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]  # type: ignore[return-value]

    try:
        result = _fetch_live()
        _cache = {"data": result, "ts": now}
        logger.info("Market data fetched live from yfinance")
        return result
    except Exception as exc:
        logger.warning("Live market data fetch failed (%s). Using fallback.", exc)

    # Build fallback covariance matrix from individual volatilities
    # Assume zero correlation between assets as a conservative fallback
    n = len(ASSET_CLASSES)
    vols = np.array([FALLBACK_MARKET_DATA[a]["vol"] for a in ASSET_CLASSES])
    cov_matrix = np.diag(vols ** 2)

    fallback_result = {
        "market_data": FALLBACK_MARKET_DATA,
        "cov_matrix": cov_matrix,
        "source": "fallback",
    }
    # Cache the fallback for a shorter window (5 minutes) so we retry soon
    _cache = {"data": fallback_result, "ts": now - CACHE_TTL + 300}
    return fallback_result
