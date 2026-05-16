"""Holdings analytics — derive positions and portfolio value from transaction history."""

from __future__ import annotations

import pandas as pd

from src.market.history import Transaction


def compute_positions(transactions: list[Transaction]) -> dict[str, int]:
    """Aggregate net shares held per ticker (excludes positions reduced to zero)."""
    pos: dict[str, int] = {}
    for t in transactions:
        delta = t.quantity if t.operation == "Buy" else -t.quantity
        pos[t.ticker] = pos.get(t.ticker, 0) + delta
    return {k: v for k, v in pos.items() if v > 0}


def compute_cost_basis(transactions: list[Transaction]) -> dict[str, float]:
    """Total EUR invested per ticker (buys minus sell proceeds)."""
    basis: dict[str, float] = {}
    for t in transactions:
        delta = t.amount_eur if t.operation == "Buy" else -t.amount_eur
        basis[t.ticker] = basis.get(t.ticker, 0.0) + delta
    return basis


def portfolio_value_series(
    transactions: list[Transaction],
    prices: pd.DataFrame,
) -> pd.Series:
    """Daily portfolio market value (EUR) reconstructed from transactions.

    For each date in *prices.index*, computes sum(shares_held × price) based
    on all transactions up to and including that date.
    Transactions are assumed to be sorted ascending by date.
    """
    dates = prices.index
    tickers = [t for t in {txn.ticker for txn in transactions} if t in prices.columns]

    shares = pd.DataFrame(0.0, index=dates, columns=tickers)
    for txn in transactions:
        if txn.ticker not in tickers:
            continue
        delta = txn.quantity if txn.operation == "Buy" else -txn.quantity
        shares.loc[shares.index >= pd.Timestamp(txn.date), txn.ticker] += delta

    return (shares * prices[tickers]).sum(axis=1)


def cumulative_invested(transactions: list[Transaction], index: pd.DatetimeIndex) -> pd.Series:
    """Cumulative EUR invested (buys minus sell proceeds) at each date in *index*."""
    invested = pd.Series(0.0, index=index)
    for txn in transactions:
        delta = txn.amount_eur if txn.operation == "Buy" else -txn.amount_eur
        invested[invested.index >= pd.Timestamp(txn.date)] += delta
    return invested
