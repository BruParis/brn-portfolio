"""Markowitz portfolio optimization: efficient frontier, max Sharpe, min variance."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

TRADING_DAYS = 252


@dataclass
class PortfolioPoint:
    risk: float
    ret: float
    weights: pd.Series


def _portfolio_stats(
    weights: np.ndarray,
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
) -> tuple[float, float]:
    """Return (annualized_volatility, annualized_return) for a weight vector."""
    ret = float(np.dot(weights, mean_returns) * TRADING_DAYS)
    var = float(weights @ cov_matrix @ weights * TRADING_DAYS)
    return np.sqrt(var), ret


def _base_constraints(n: int) -> list[dict]:
    return [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]


def _bounds(n: int, min_weight: float = 0.0, max_weight: float = 1.0):
    return [(min_weight, max_weight)] * n


def max_sharpe_portfolio(
    returns: pd.DataFrame,
    risk_free_rate: float = 0.03,
    min_weight: float = 0.0,
    max_weight: float = 1.0,
) -> PortfolioPoint:
    """Find the portfolio that maximises the Sharpe ratio."""
    mean_ret = returns.mean().values
    cov = returns.cov().values
    n = len(mean_ret)

    def neg_sharpe(w: np.ndarray) -> float:
        vol, ret = _portfolio_stats(w, mean_ret, cov)
        if vol == 0:
            return 0.0
        return -(ret - risk_free_rate) / vol

    w0 = np.ones(n) / n
    result = minimize(
        neg_sharpe,
        w0,
        method="SLSQP",
        bounds=_bounds(n, min_weight, max_weight),
        constraints=_base_constraints(n),
        options={"ftol": 1e-7, "maxiter": 1000},
    )
    w = result.x
    vol, ret = _portfolio_stats(w, mean_ret, cov)
    return PortfolioPoint(risk=vol, ret=ret, weights=pd.Series(w, index=returns.columns))


def min_variance_portfolio(
    returns: pd.DataFrame,
    min_weight: float = 0.0,
    max_weight: float = 1.0,
) -> PortfolioPoint:
    """Find the minimum variance portfolio."""
    mean_ret = returns.mean().values
    cov = returns.cov().values
    n = len(mean_ret)

    def portfolio_variance(w: np.ndarray) -> float:
        return float(w @ cov @ w)

    w0 = np.ones(n) / n
    result = minimize(
        portfolio_variance,
        w0,
        method="SLSQP",
        bounds=_bounds(n, min_weight, max_weight),
        constraints=_base_constraints(n),
        options={"ftol": 1e-7, "maxiter": 1000},
    )
    w = result.x
    vol, ret = _portfolio_stats(w, mean_ret, cov)
    return PortfolioPoint(risk=vol, ret=ret, weights=pd.Series(w, index=returns.columns))


def compute_efficient_frontier(
    returns: pd.DataFrame,
    n_points: int = 30,
    min_weight: float = 0.0,
    max_weight: float = 1.0,
) -> list[PortfolioPoint]:
    """Compute the efficient frontier as a list of PortfolioPoints.

    Sweeps target returns from the min-variance portfolio return to the
    maximum single-asset return.
    """
    mean_ret = returns.mean().values
    cov = returns.cov().values
    n = len(mean_ret)

    min_var = min_variance_portfolio(returns, min_weight, max_weight)
    ret_min = min_var.ret
    ret_max = float(mean_ret.max() * TRADING_DAYS)

    target_returns = np.linspace(ret_min, ret_max, n_points)
    frontier: list[PortfolioPoint] = []

    for target in target_returns:
        constraints = _base_constraints(n) + [
            {"type": "eq", "fun": lambda w, t=target: np.dot(w, mean_ret) * TRADING_DAYS - t}
        ]

        def portfolio_variance(w: np.ndarray) -> float:
            return float(w @ cov @ w)

        w0 = np.ones(n) / n
        result = minimize(
            portfolio_variance,
            w0,
            method="SLSQP",
            bounds=_bounds(n, min_weight, max_weight),
            constraints=constraints,
            options={"ftol": 1e-7, "maxiter": 1000},
        )
        if result.success:
            w = result.x
            vol, ret = _portfolio_stats(w, mean_ret, cov)
            frontier.append(PortfolioPoint(risk=vol, ret=ret, weights=pd.Series(w, index=returns.columns)))

    return frontier
