"""
Market data retrieval for regime detection and portfolio monitoring.
Uses yfinance for price data and FRED for credit spread data.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
from typing import Optional

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from engine.config import (
    FRED_API_BASE,
    FRED_SPREAD_SERIES,
    MSCI_WORLD_PROXY,
    SP500_TICKER,
    VIX_TICKER,
)

logger = logging.getLogger(__name__)

_CACHE: dict = {}
_CACHE_TTL = dt.timedelta(minutes=30)


def _is_fresh(key: str) -> bool:
    if key not in _CACHE:
        return False
    ts, _ = _CACHE[key]
    return (dt.datetime.now() - ts) < _CACHE_TTL


def _put(key: str, value):
    _CACHE[key] = (dt.datetime.now(), value)


def _get(key: str):
    return _CACHE[key][1] if key in _CACHE else None


def fetch_index_history(
    ticker: str = MSCI_WORLD_PROXY,
    period: str = "5y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Return adjusted-close history for *ticker*."""
    cache_key = f"hist_{ticker}_{period}_{interval}"
    if _is_fresh(cache_key):
        return _get(cache_key)

    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if data.empty:
            raise ValueError(f"No data returned for {ticker}")

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        df = data[["Close"]].copy()
        df.columns = ["close"]
        df.dropna(inplace=True)
        _put(cache_key, df)
        return df
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", ticker, exc)
        return pd.DataFrame(columns=["close"])


def compute_drawdown(df: pd.DataFrame) -> dict:
    """Compute current drawdown from ATH and related statistics."""
    if df.empty:
        return {
            "current_price": None,
            "ath": None,
            "drawdown_pct": 0.0,
            "ath_date": None,
            "trough": None,
            "trough_date": None,
        }

    close = df["close"]
    running_max = close.cummax()
    drawdown_series = (close - running_max) / running_max

    current_price = float(close.iloc[-1])
    ath = float(running_max.iloc[-1])
    ath_date = running_max.idxmax()
    if hasattr(ath_date, "strftime"):
        ath_date = ath_date.strftime("%Y-%m-%d")
    else:
        ath_date = str(ath_date)

    current_dd = float(drawdown_series.iloc[-1])

    trough_idx = drawdown_series.idxmin()
    trough_val = float(close.loc[trough_idx])
    if hasattr(trough_idx, "strftime"):
        trough_date = trough_idx.strftime("%Y-%m-%d")
    else:
        trough_date = str(trough_idx)

    return {
        "current_price": round(current_price, 2),
        "ath": round(ath, 2),
        "drawdown_pct": round(current_dd * 100, 2),
        "ath_date": ath_date,
        "trough": round(trough_val, 2),
        "trough_date": trough_date,
    }


def fetch_vix() -> Optional[float]:
    """Return the latest VIX close."""
    cache_key = "vix_latest"
    if _is_fresh(cache_key):
        return _get(cache_key)

    try:
        data = yf.download(VIX_TICKER, period="5d", interval="1d", progress=False)
        if data.empty:
            return None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        val = float(data["Close"].dropna().iloc[-1])
        _put(cache_key, val)
        return round(val, 2)
    except Exception as exc:
        logger.warning("VIX fetch failed: %s", exc)
        return None


def fetch_credit_spread(fred_api_key: Optional[str] = None) -> Optional[float]:
    """
    Fetch the latest BBB corporate OAS from FRED.
    Falls back to a heuristic estimate if no API key is available.
    """
    cache_key = "credit_spread"
    if _is_fresh(cache_key):
        return _get(cache_key)

    api_key = fred_api_key or os.environ.get("FRED_API_KEY")

    if api_key:
        try:
            params = {
                "series_id": FRED_SPREAD_SERIES,
                "api_key": api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 5,
            }
            resp = requests.get(FRED_API_BASE, params=params, timeout=10)
            resp.raise_for_status()
            obs = resp.json().get("observations", [])
            for o in obs:
                if o["value"] != ".":
                    val = float(o["value"])
                    _put(cache_key, val)
                    return round(val, 2)
        except Exception as exc:
            logger.warning("FRED fetch failed: %s", exc)

    # Heuristic fallback: use VIX as a proxy for credit stress
    vix = fetch_vix()
    if vix is not None:
        # Rough mapping: VIX 12→spread ~1.2, VIX 30→spread ~2.8, VIX 50→spread ~5.0
        estimated = 0.5 + vix * 0.09
        _put(cache_key, estimated)
        return round(estimated, 2)

    return None


def fetch_dashboard_data() -> dict:
    """Aggregate all market data needed for the regime dashboard."""
    hist = fetch_index_history()
    dd_info = compute_drawdown(hist)
    vix = fetch_vix()
    spread = fetch_credit_spread()

    # Build a small drawdown chart (last 252 trading days ≈ 1 year)
    chart_data = []
    if not hist.empty:
        recent = hist.tail(504)  # ~2 years
        running_max = recent["close"].cummax()
        dd_series = ((recent["close"] - running_max) / running_max) * 100
        for date, val in dd_series.items():
            d = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)
            chart_data.append({"date": d, "drawdown": round(float(val), 2)})

    price_chart = []
    if not hist.empty:
        recent = hist.tail(504)
        for date, row in recent.iterrows():
            d = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)
            price_chart.append({"date": d, "price": round(float(row["close"]), 2)})

    return {
        "drawdown": dd_info,
        "vix": vix,
        "credit_spread": spread,
        "drawdown_chart": chart_data,
        "price_chart": price_chart,
        "last_updated": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
