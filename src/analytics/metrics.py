"""Portfolio analytics: returns, volatility, Sharpe ratio, drawdown."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def daily_returns(prices: pd.DataFrame, method: str = "simple") -> pd.DataFrame:
    """Compute daily returns from a price DataFrame.

    Args:
        prices: DataFrame of adjusted close prices (rows=dates, cols=tickers).
        method: "simple" (pct_change) or "log" (log returns).
    """
    if method == "log":
        return np.log(prices / prices.shift(1)).dropna()
    return prices.pct_change().dropna()


def annualized_return(returns: pd.Series | pd.DataFrame) -> float | pd.Series:
    """Geometric annualized return."""
    if isinstance(returns, pd.DataFrame):
        return returns.apply(annualized_return)
    total = (1 + returns).prod()
    n = len(returns)
    return float(total ** (TRADING_DAYS / n) - 1)


def annualized_volatility(returns: pd.Series | pd.DataFrame) -> float | pd.Series:
    """Annualized volatility (std × sqrt(252))."""
    if isinstance(returns, pd.DataFrame):
        return returns.apply(annualized_volatility)
    return float(returns.std() * np.sqrt(TRADING_DAYS))


def sharpe_ratio(
    returns: pd.Series | pd.DataFrame,
    risk_free_rate: float = 0.03,
) -> float | pd.Series:
    """Annualized Sharpe ratio."""
    if isinstance(returns, pd.DataFrame):
        return returns.apply(lambda col: sharpe_ratio(col, risk_free_rate))
    ann_ret = annualized_return(returns)
    ann_vol = annualized_volatility(returns)
    if ann_vol == 0:
        return 0.0
    return float((ann_ret - risk_free_rate) / ann_vol)


def max_drawdown(prices: pd.Series | pd.DataFrame) -> float | pd.Series:
    """Maximum peak-to-trough drawdown."""
    if isinstance(prices, pd.DataFrame):
        return prices.apply(max_drawdown)
    roll_max = prices.cummax()
    drawdown = prices / roll_max - 1
    return float(drawdown.min())


def portfolio_returns(
    prices: pd.DataFrame,
    weights: dict[str, float] | pd.Series,
) -> pd.Series:
    """Compute daily portfolio returns given a weight allocation."""
    if isinstance(weights, dict):
        weights = pd.Series(weights)
    weights = weights.reindex(prices.columns).fillna(0)
    weights = weights / weights.sum()
    rets = daily_returns(prices)
    return (rets * weights).sum(axis=1)


def summary_table(
    prices: pd.DataFrame,
    risk_free_rate: float = 0.03,
) -> pd.DataFrame:
    """Return a summary DataFrame with annualized return, volatility, Sharpe for each ticker."""
    rets = daily_returns(prices)
    ytd_start = pd.Timestamp(prices.index[-1].year, 1, 1)
    ytd_prices = prices[prices.index >= ytd_start]
    ytd_ret = (ytd_prices.iloc[-1] / ytd_prices.iloc[0] - 1) if len(ytd_prices) > 1 else pd.Series(0, index=prices.columns)
    return pd.DataFrame(
        {
            "YTD Return": ytd_ret,
            "Ann. Return": annualized_return(rets),
            "Volatility": annualized_volatility(rets),
            "Sharpe": sharpe_ratio(rets, risk_free_rate),
            "Max Drawdown": max_drawdown(prices),
        }
    )
