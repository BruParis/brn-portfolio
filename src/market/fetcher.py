"""yfinance wrapper: fetch, cache, and refresh historical price data."""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd
import yfinance as yf

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(ticker: str) -> Path:
    return CACHE_DIR / f"{ticker.replace('/', '_')}.parquet"


def _load_cache(ticker: str) -> pd.DataFrame | None:
    path = _cache_path(ticker)
    if path.exists():
        return pd.read_parquet(path)
    return None


def _is_stale(df: pd.DataFrame) -> bool:
    """Return True if the cache does not include today's date (or the most recent trading day)."""
    today = pd.Timestamp.today().normalize()
    last = df.index[-1]
    # If last date is before today (and today is a weekday), cache is stale
    return last < today - pd.tseries.offsets.BDay(1)


def fetch_prices(
    tickers: list[str],
    start: str | pd.Timestamp,
    end: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Return a DataFrame of adjusted close prices indexed by date.

    Data is cached per-ticker in data/cache/{ticker}.parquet.
    Stale caches are refreshed automatically.
    """
    if end is None:
        end = pd.Timestamp.today().normalize()

    start = pd.Timestamp(start)
    end = pd.Timestamp(end)

    frames: dict[str, pd.Series] = {}

    for ticker in tickers:
        cached = _load_cache(ticker)

        if cached is None or _is_stale(cached):
            # Download full history up to today; we'll slice later
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                raw = yf.download(
                    ticker,
                    start="2015-01-01",
                    end=(pd.Timestamp.today() + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                    auto_adjust=True,
                    progress=False,
                )
            if raw.empty:
                continue
            # yfinance may return MultiIndex columns
            if isinstance(raw.columns, pd.MultiIndex):
                close = raw["Close"][ticker] if ticker in raw["Close"].columns else raw["Close"].iloc[:, 0]
            else:
                close = raw["Close"]
            close = close.dropna()
            close.name = ticker
            close.index = pd.DatetimeIndex(close.index).normalize()
            df_to_cache = close.to_frame()
            df_to_cache.to_parquet(_cache_path(ticker))
            cached = df_to_cache

        series = cached.iloc[:, 0]
        series.index = pd.DatetimeIndex(series.index).normalize()
        mask = (series.index >= start) & (series.index <= end)
        frames[ticker] = series[mask]

    if not frames:
        return pd.DataFrame()

    result = pd.DataFrame(frames)
    result.index.name = "Date"
    return result.dropna(how="all")
