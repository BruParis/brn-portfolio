"""Run the Markowitz optimizer from the command line.

Replicates the exact same computation as Page 3 of the Streamlit app.

Usage (from repo root):
    source .venv/bin/activate
    python scripts/run_optimizer.py
    python scripts/run_optimizer.py --lookback 1y --objective min-variance
    python scripts/run_optimizer.py --lookback 5y --risk-free 3.5 --min-weight 0 --max-weight 15
    python scripts/run_optimizer.py --tickers MC.PA OR.PA SAN.PA TTE.PA
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.analytics.markowitz import (
    compute_efficient_frontier,
    max_sharpe_portfolio,
    min_variance_portfolio,
)
from src.analytics.metrics import daily_returns
from src.market.cac40 import CAC40_TICKERS, TICKERS
from src.market.fetcher import fetch_prices


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Markowitz portfolio optimization on CAC 40 stocks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--lookback",
        choices=["1y", "3y", "5y"],
        default="3y",
        help="Historical lookback window (default: 3y)",
    )
    parser.add_argument(
        "--risk-free",
        type=float,
        default=3.0,
        metavar="PCT",
        help="Risk-free rate in %% (default: 3.0)",
    )
    parser.add_argument(
        "--objective",
        choices=["max-sharpe", "min-variance"],
        default="max-sharpe",
        help="Optimization objective (default: max-sharpe)",
    )
    parser.add_argument(
        "--min-weight",
        type=float,
        default=0.0,
        metavar="PCT",
        help="Minimum weight per stock in %% (default: 0)",
    )
    parser.add_argument(
        "--max-weight",
        type=float,
        default=20.0,
        metavar="PCT",
        help="Maximum weight per stock in %% (default: 20)",
    )
    parser.add_argument(
        "--frontier-points",
        type=int,
        default=50,
        metavar="N",
        help="Number of points on the efficient frontier (default: 50)",
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        metavar="TICKER",
        help="Restrict universe to these tickers (default: all 40 CAC 40 stocks)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        metavar="N",
        help="Number of top holdings to display (default: 10)",
    )
    args = parser.parse_args()

    # ── Parameters (mirrors the Streamlit sidebar) ─────────────────────────────
    lookback_years = {"1y": 1, "3y": 3, "5y": 5}[args.lookback]
    risk_free = args.risk_free / 100
    min_w = args.min_weight / 100
    max_w = args.max_weight / 100
    objective = "Max Sharpe" if args.objective == "max-sharpe" else "Min Variance"

    selected_tickers = args.tickers if args.tickers else TICKERS

    unknown = [t for t in selected_tickers if t not in CAC40_TICKERS]
    if unknown:
        print(f"Unknown tickers: {', '.join(unknown)}", file=sys.stderr)
        sys.exit(1)

    if len(selected_tickers) < 2:
        print("Need at least 2 tickers.", file=sys.stderr)
        sys.exit(1)

    print(f"Objective      : {objective}")
    print(f"Lookback       : {args.lookback}")
    print(f"Risk-free rate : {args.risk_free:.1f}%")
    print(f"Weight bounds  : [{args.min_weight:.0f}%, {args.max_weight:.0f}%]")
    print(f"Universe       : {len(selected_tickers)} stocks")
    print()

    # ── Fetch data (mirrors the page fetch block) ──────────────────────────────
    end_date = pd.Timestamp.today().normalize()
    start_date = end_date - pd.DateOffset(years=lookback_years)

    print(f"Fetching prices from {start_date.date()} to {end_date.date()} …")
    prices = fetch_prices(
        selected_tickers,
        start=str(start_date.date()),
        end=str(end_date.date()),
    )

    if prices.empty or prices.shape[1] < 2:
        print("Not enough data for optimization.", file=sys.stderr)
        sys.exit(1)

    prices = prices.dropna(axis=1, thresh=int(len(prices) * 0.8))
    prices = prices.dropna()

    if prices.shape[1] < 2:
        print("Not enough valid price data after cleaning.", file=sys.stderr)
        sys.exit(1)

    dropped = [t for t in selected_tickers if t not in prices.columns]
    if dropped:
        print(f"Dropped (insufficient data): {', '.join(dropped)}")

    print(f"Optimizing over {prices.shape[1]} stocks, {len(prices)} trading days.\n")

    returns = daily_returns(prices)

    # ── Run optimization (mirrors the page computation block) ──────────────────
    print("Computing efficient frontier …")
    frontier = compute_efficient_frontier(
        returns, n_points=args.frontier_points, min_weight=min_w, max_weight=max_w
    )

    print(f"Running {objective} optimization …\n")
    if objective == "Max Sharpe":
        optimal = max_sharpe_portfolio(
            returns, risk_free_rate=risk_free, min_weight=min_w, max_weight=max_w
        )
    else:
        optimal = min_variance_portfolio(returns, min_weight=min_w, max_weight=max_w)

    # ── Results ────────────────────────────────────────────────────────────────
    sharpe = (optimal.ret - risk_free) / optimal.risk if optimal.risk > 0 else 0.0

    print("=" * 50)
    print(f"  Optimal Portfolio — {objective}")
    print("=" * 50)
    print(f"  Expected Return (ann.) : {optimal.ret:.2%}")
    print(f"  Volatility (ann.)      : {optimal.risk:.2%}")
    print(f"  Sharpe Ratio           : {sharpe:.2f}")
    print()

    top_weights = optimal.weights[optimal.weights > 0.001].sort_values(ascending=False)
    display_n = min(args.top, len(top_weights))
    print(f"  Top {display_n} holdings:")
    for ticker, w in top_weights.head(display_n).items():
        name = CAC40_TICKERS.get(ticker, ticker)
        bar = "#" * int(w * 100 / 2)
        print(f"    {ticker:<12} {name:<30}  {w:6.2%}  {bar}")

    if len(top_weights) > display_n:
        remainder = top_weights.iloc[display_n:].sum()
        print(f"    {'...':<12} {'(others)':<30}  {remainder:6.2%}")

    print()
    print(f"  Efficient frontier: {len(frontier)} points computed.")
    print(f"    Risk range  : {min(p.risk for p in frontier):.2%} – {max(p.risk for p in frontier):.2%}")
    print(f"    Return range: {min(p.ret for p in frontier):.2%} – {max(p.ret for p in frontier):.2%}")


if __name__ == "__main__":
    main()
