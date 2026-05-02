"""Page 3 — Markowitz optimizer: efficient frontier and optimal weights."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analytics.markowitz import (
    compute_efficient_frontier,
    max_sharpe_portfolio,
    min_variance_portfolio,
)
from src.analytics.metrics import daily_returns
from src.data.cac40 import CAC40_TICKERS, TICKERS
from src.data.fetcher import fetch_prices

st.set_page_config(page_title="Optimizer — BRN Portfolio", layout="wide")
st.title("Markowitz Optimizer")

# ── Sidebar parameters ─────────────────────────────────────────────────────────
st.sidebar.header("Optimizer Parameters")

lookback = st.sidebar.selectbox("Lookback window", options=["1y", "3y", "5y"], index=1)
lookback_years = {"1y": 1, "3y": 3, "5y": 5}[lookback]

risk_free = st.sidebar.number_input("Risk-free rate (%)", value=3.0, step=0.1) / 100

objective = st.sidebar.radio("Objective", options=["Max Sharpe", "Min Variance"])

min_w = st.sidebar.slider("Min weight per stock (%)", 0, 20, 0) / 100
max_w = st.sidebar.slider("Max weight per stock (%)", 5, 100, 20) / 100

n_frontier = st.sidebar.slider("Frontier points", 20, 100, 50)

# ── Stock universe selection ────────────────────────────────────────────────────
st.subheader("Universe Selection")

col_select, col_deselect = st.columns([1, 1], gap="small")
if col_select.button("Select all"):
    for t in TICKERS:
        st.session_state[f"universe_{t}"] = True
if col_deselect.button("Deselect all"):
    for t in TICKERS:
        st.session_state[f"universe_{t}"] = False

grid_cols = st.columns(5)
selected_tickers = []
for i, t in enumerate(TICKERS):
    checked = grid_cols[i % 5].checkbox(
        f"{t}  \n{CAC40_TICKERS.get(t, t)}",
        value=st.session_state.get(f"universe_{t}", True),
        key=f"universe_{t}",
    )
    if checked:
        selected_tickers.append(t)

if len(selected_tickers) < 2:
    st.warning("Select at least 2 stocks.")
    st.stop()

# ── Run button ─────────────────────────────────────────────────────────────────
st.divider()
if st.button("Run Optimizer", type="primary", use_container_width=True):
    end_date = pd.Timestamp.today().normalize()
    start_date = end_date - pd.DateOffset(years=lookback_years)

    with st.spinner("Fetching price data…"):
        prices = fetch_prices(
            selected_tickers,
            start=str(start_date.date()),
            end=str(end_date.date()),
        )

    if prices.empty or prices.shape[1] < 2:
        st.error("Not enough data for optimization.")
        st.stop()

    prices = prices.dropna(axis=1, thresh=int(len(prices) * 0.8))
    prices = prices.dropna()

    if prices.shape[1] < 2:
        st.error("Not enough valid price data after cleaning.")
        st.stop()

    returns = daily_returns(prices)

    with st.spinner("Computing efficient frontier…"):
        frontier = compute_efficient_frontier(
            returns, n_points=n_frontier, min_weight=min_w, max_weight=max_w
        )
        if objective == "Max Sharpe":
            optimal = max_sharpe_portfolio(
                returns, risk_free_rate=risk_free, min_weight=min_w, max_weight=max_w
            )
        else:
            optimal = min_variance_portfolio(returns, min_weight=min_w, max_weight=max_w)

    st.session_state["optimizer_results"] = {
        "frontier": frontier,
        "optimal": optimal,
        "risk_free": risk_free,
        "objective": objective,
        "tickers": list(prices.columns),
        "optimal_weights": optimal.weights.to_dict(),
    }
    # Also persist for advice page
    st.session_state["optimal_weights"] = optimal.weights.to_dict()
    st.session_state["optimizer_tickers"] = list(prices.columns)

# ── Display cached results ─────────────────────────────────────────────────────
results = st.session_state.get("optimizer_results")

if results is None:
    st.info("Configure parameters above and click **Run Optimizer** to compute the efficient frontier.")
    st.stop()

frontier = results["frontier"]
optimal = results["optimal"]
stored_risk_free = results["risk_free"]
stored_objective = results["objective"]

# ── Efficient frontier chart ────────────────────────────────────────────────────
st.subheader("Efficient Frontier")

risks = [p.risk for p in frontier]
rets = [p.ret for p in frontier]

hover_texts = []
for p in frontier:
    top5 = p.weights.nlargest(5)
    text = "<br>".join(
        f"{CAC40_TICKERS.get(t, t)}: {w:.1%}" for t, w in top5.items()
    )
    hover_texts.append(text)

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=risks,
        y=rets,
        mode="lines+markers",
        name="Efficient Frontier",
        marker=dict(size=4, color="steelblue"),
        line=dict(color="steelblue"),
        text=hover_texts,
        hovertemplate="<b>Risk:</b> %{x:.1%}<br><b>Return:</b> %{y:.1%}<br>%{text}<extra></extra>",
    )
)

fig.add_trace(
    go.Scatter(
        x=[optimal.risk],
        y=[optimal.ret],
        mode="markers",
        name=f"Optimal ({stored_objective})",
        marker=dict(size=14, color="crimson", symbol="star"),
        hovertemplate=f"<b>{stored_objective}</b><br>Risk: %{{x:.1%}}<br>Return: %{{y:.1%}}<extra></extra>",
    )
)

fig.update_layout(
    xaxis_title="Annualised Volatility",
    yaxis_title="Annualised Return",
    xaxis_tickformat=".0%",
    yaxis_tickformat=".0%",
    hovermode="closest",
    legend=dict(x=0.01, y=0.99),
)

st.plotly_chart(fig, width="stretch")

# ── Optimal weights table ──────────────────────────────────────────────────────
st.subheader(f"Optimal Weights — {stored_objective}")

weights_df = optimal.weights[optimal.weights > 0.001].sort_values(ascending=False).reset_index()
weights_df.columns = ["Ticker", "Weight"]
weights_df["Company"] = weights_df["Ticker"].map(lambda t: CAC40_TICKERS.get(t, t))
weights_df["Weight (%)"] = weights_df["Weight"] * 100

st.dataframe(
    weights_df[["Ticker", "Company", "Weight (%)"]].style.format({"Weight (%)": "{:.2f}%"}),
    width="stretch",
)

# ── Key metrics ────────────────────────────────────────────────────────────────
st.subheader("Optimal Portfolio Metrics")
sharpe_opt = (optimal.ret - stored_risk_free) / optimal.risk if optimal.risk > 0 else 0

m1, m2, m3 = st.columns(3)
m1.metric("Expected Return (ann.)", f"{optimal.ret:.1%}")
m2.metric("Volatility (ann.)", f"{optimal.risk:.1%}")
m3.metric("Sharpe Ratio", f"{sharpe_opt:.2f}")
