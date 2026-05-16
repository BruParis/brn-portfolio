"""Markowitz and Mean-CVaR portfolio optimization."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import linprog, minimize

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


# ── Mean-CVaR optimization ─────────────────────────────────────────────────────


def _portfolio_cvar(weights: np.ndarray, returns_matrix: np.ndarray, alpha: float) -> float:
    """Daily CVaR (positive = loss) at confidence level alpha."""
    pf_returns = returns_matrix @ weights
    threshold = np.percentile(pf_returns, (1 - alpha) * 100)
    tail = pf_returns[pf_returns <= threshold]
    return float(-tail.mean()) if len(tail) > 0 else 0.0


def _solve_min_cvar_lp(
    returns_matrix: np.ndarray,
    mean_ret: np.ndarray,
    alpha: float,
    min_weight: float,
    max_weight: float,
    target_daily_return: float | None = None,
):
    """Solve min-CVaR LP via Rockafellar-Uryasev formulation.

    Variables: [w(n), zeta(1), u(T)]
    """
    T, n = returns_matrix.shape
    scale = 1.0 / ((1 - alpha) * T)

    c = np.concatenate([np.zeros(n), [1.0], np.full(T, scale)])

    # u_t >= -r_t @ w - zeta  =>  -r_t @ w - zeta - u_t <= 0
    A_ub = np.zeros((T, n + 1 + T))
    A_ub[:, :n] = -returns_matrix
    A_ub[:, n] = -1.0
    np.fill_diagonal(A_ub[:, n + 1 :], -1.0)
    b_ub = np.zeros(T)

    if target_daily_return is not None:
        # E[r_p] >= target  =>  -mean_ret @ w <= -target
        row = np.zeros(n + 1 + T)
        row[:n] = -mean_ret
        A_ub = np.vstack([A_ub, row])
        b_ub = np.append(b_ub, -target_daily_return)

    A_eq = np.zeros((1, n + 1 + T))
    A_eq[0, :n] = 1.0
    b_eq = [1.0]

    bounds = [(min_weight, max_weight)] * n + [(None, None)] + [(0.0, None)] * T

    return linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")


def min_cvar_portfolio(
    returns: pd.DataFrame,
    alpha: float = 0.95,
    min_weight: float = 0.0,
    max_weight: float = 1.0,
) -> PortfolioPoint:
    """Find the portfolio that minimises CVaR at confidence level alpha."""
    R = returns.values
    mean_ret = R.mean(axis=0)
    result = _solve_min_cvar_lp(R, mean_ret, alpha, min_weight, max_weight)
    w = result.x[: returns.shape[1]]
    cvar_daily = _portfolio_cvar(w, R, alpha)
    ann_ret = float(mean_ret @ w * TRADING_DAYS)
    return PortfolioPoint(
        risk=cvar_daily * TRADING_DAYS,
        ret=ann_ret,
        weights=pd.Series(w, index=returns.columns),
    )


def max_return_cvar_portfolio(
    returns: pd.DataFrame,
    alpha: float = 0.95,
    min_weight: float = 0.0,
    max_weight: float = 1.0,
) -> PortfolioPoint:
    """Find the portfolio that maximises annualised return / annualised CVaR (STARR ratio)."""
    R = returns.values
    mean_ret = R.mean(axis=0)
    n = len(mean_ret)

    def neg_starr(w: np.ndarray) -> float:
        cvar = _portfolio_cvar(w, R, alpha) * TRADING_DAYS
        ann_ret = float(mean_ret @ w * TRADING_DAYS)
        return -ann_ret / cvar if cvar > 0 else 0.0

    w0 = np.ones(n) / n
    result = minimize(
        neg_starr,
        w0,
        method="SLSQP",
        bounds=_bounds(n, min_weight, max_weight),
        constraints=_base_constraints(n),
        options={"ftol": 1e-7, "maxiter": 1000},
    )
    w = result.x
    cvar_daily = _portfolio_cvar(w, R, alpha)
    ann_ret = float(mean_ret @ w * TRADING_DAYS)
    return PortfolioPoint(
        risk=cvar_daily * TRADING_DAYS,
        ret=ann_ret,
        weights=pd.Series(w, index=returns.columns),
    )


def compute_cvar_frontier(
    returns: pd.DataFrame,
    n_points: int = 30,
    alpha: float = 0.95,
    min_weight: float = 0.0,
    max_weight: float = 1.0,
) -> list[PortfolioPoint]:
    """Mean-CVaR efficient frontier: sweep target returns, minimise CVaR at each level."""
    R = returns.values
    mean_ret = R.mean(axis=0)

    min_pt = min_cvar_portfolio(returns, alpha, min_weight, max_weight)
    ret_min_daily = min_pt.ret / TRADING_DAYS
    ret_max_daily = float(mean_ret.max())

    target_returns = np.linspace(ret_min_daily, ret_max_daily, n_points)
    frontier: list[PortfolioPoint] = []

    for target in target_returns:
        result = _solve_min_cvar_lp(R, mean_ret, alpha, min_weight, max_weight, target)
        if result.success:
            w = result.x[:returns.shape[1]]
            cvar_daily = _portfolio_cvar(w, R, alpha)
            ann_ret = float(mean_ret @ w * TRADING_DAYS)
            frontier.append(
                PortfolioPoint(
                    risk=cvar_daily * TRADING_DAYS,
                    ret=ann_ret,
                    weights=pd.Series(w, index=returns.columns),
                )
            )

    return frontier


# ── Markowitz efficient frontier ───────────────────────────────────────────────


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
