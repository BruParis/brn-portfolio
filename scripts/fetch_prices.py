"""Fetch and cache historical prices for all CAC 40 tickers.

Usage (from repo root):
    source .venv/bin/activate
    python scripts/fetch_prices.py [--years 5]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.market.cac40 import CAC40_TICKERS
from src.market.fetcher import fetch_prices


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch CAC 40 price data.")
    parser.add_argument("--years", type=int, default=5, help="Lookback in years (default: 5)")
    args = parser.parse_args()

    end = pd.Timestamp.today().normalize()
    start = end - pd.DateOffset(years=args.years)

    tickers = list(CAC40_TICKERS.keys())
    print(f"Fetching {len(tickers)} tickers from {start.date()} to {end.date()} …")

    prices = fetch_prices(tickers, start=str(start.date()), end=str(end.date()))

    ok = prices.columns.tolist()
    failed = [t for t in tickers if t not in ok]

    print(f"\nOK  ({len(ok)}): {', '.join(ok)}")
    if failed:
        print(f"FAIL({len(failed)}): {', '.join(failed)}")
    else:
        print("All tickers fetched successfully.")

    print(f"\nCache written to data/cache/  ({len(prices)} trading days)")


if __name__ == "__main__":
    main()
