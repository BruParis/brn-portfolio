"""Page 2 — User portfolio input and current performance."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

_PORTFOLIO_FILE = Path(__file__).resolve().parents[3] / "data" / "portfolio.json"


def _load_portfolio() -> list[dict] | None:
    if _PORTFOLIO_FILE.exists():
        try:
            return json.loads(_PORTFOLIO_FILE.read_text())
        except Exception:
            return None
    return None


def _save_portfolio(data: list[dict]) -> None:
    _PORTFOLIO_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PORTFOLIO_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.analytics.metrics import (
    annualized_return,
    annualized_volatility,
    daily_returns,
    max_drawdown,
    portfolio_returns,
    sharpe_ratio,
)
from src.data.cac40 import CAC40_TICKERS, DISPLAY_OPTIONS, DISPLAY_TO_TICKER, TICKER_TO_DISPLAY
from src.data.fetcher import fetch_prices

st.set_page_config(page_title="Portfolio — BRN Portfolio", layout="wide")
st.title("My Portfolio")

# ── Portfolio input ────────────────────────────────────────────────────────────
st.subheader("Portfolio Allocation")
st.caption("Enter your current holdings. Allocations must sum to 100%.")

DEFAULT_PORTFOLIO = [
    {"Stock": TICKER_TO_DISPLAY["MC.PA"], "Allocation (%)": 20.0},
    {"Stock": TICKER_TO_DISPLAY["OR.PA"], "Allocation (%)": 15.0},
    {"Stock": TICKER_TO_DISPLAY["SAN.PA"], "Allocation (%)": 15.0},
    {"Stock": TICKER_TO_DISPLAY["TTE.PA"], "Allocation (%)": 15.0},
    {"Stock": TICKER_TO_DISPLAY["AIR.PA"], "Allocation (%)": 10.0},
    {"Stock": TICKER_TO_DISPLAY["SU.PA"], "Allocation (%)": 10.0},
    {"Stock": TICKER_TO_DISPLAY["BNP.PA"], "Allocation (%)": 15.0},
]

if "portfolio_data" not in st.session_state:
    st.session_state["portfolio_data"] = _load_portfolio() or DEFAULT_PORTFOLIO

st.caption("Select rows with the checkbox then press **Delete** to remove them. Use the **+** button at the bottom to add new holdings.")

edited = st.data_editor(
    pd.DataFrame(st.session_state["portfolio_data"]),
    num_rows="dynamic",
    column_config={
        "Stock": st.column_config.SelectboxColumn(
            "Stock", options=DISPLAY_OPTIONS, required=True
        ),
        "Allocation (%)": st.column_config.NumberColumn(
            "Allocation (%)", min_value=0.0, max_value=100.0, step=0.01, format="%.2f", required=True
        ),
    },
    width="stretch",
    key="portfolio_editor",
)

# Persist whenever the table changes, without recreating the widget.
current_records = edited.to_dict(orient="records")
if current_records != st.session_state["portfolio_data"]:
    _save_portfolio(current_records)
    st.session_state["portfolio_data"] = current_records

total_alloc = edited["Allocation (%)"].sum()
if abs(total_alloc - 100) > 0.01:
    st.warning(f"Allocations sum to {total_alloc:.1f}% — must equal 100%.")
    st.stop()

weights = {
    DISPLAY_TO_TICKER[row["Stock"]]: row["Allocation (%)"] / 100
    for _, row in edited.iterrows()
    if row["Stock"] in DISPLAY_TO_TICKER
}

# ── Date range ────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
default_end = pd.Timestamp.today().normalize()
default_start = default_end - pd.DateOffset(years=3)
with col1:
    start_date = st.date_input("Start date", value=default_start.date())
with col2:
    end_date = st.date_input("End date", value=default_end.date())

# ── Fetch data ────────────────────────────────────────────────────────────────
portfolio_tickers = list(weights.keys())
benchmark_ticker = ["^FCHI"]  # CAC 40 index

with st.spinner("Fetching data…"):
    prices = fetch_prices(portfolio_tickers, start=str(start_date), end=str(end_date))
    bench_prices = fetch_prices(benchmark_ticker, start=str(start_date), end=str(end_date))

if prices.empty:
    st.error("No price data available for the selected tickers.")
    st.stop()

# ── Portfolio performance ──────────────────────────────────────────────────────
port_rets = portfolio_returns(prices, weights)
port_cumret = (1 + port_rets).cumprod()

fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=port_cumret.index,
        y=port_cumret.values,
        name="My Portfolio",
        line=dict(color="royalblue", width=2),
    )
)

if not bench_prices.empty:
    bench_col = bench_prices.columns[0]
    bench_norm = bench_prices[bench_col] / bench_prices[bench_col].iloc[0]
    fig.add_trace(
        go.Scatter(
            x=bench_norm.index,
            y=bench_norm.values,
            name="CAC 40",
            line=dict(color="orange", width=1.5, dash="dash"),
        )
    )

fig.update_layout(
    title="Portfolio vs CAC 40 (normalised)",
    yaxis_title="Cumulative Return (base 1)",
    xaxis_title="Date",
    hovermode="x unified",
)
st.plotly_chart(fig, width="stretch")

# ── Current metrics ────────────────────────────────────────────────────────────
st.subheader("Portfolio Metrics")
risk_free = st.number_input("Risk-free rate (%)", value=3.0, step=0.1) / 100

ann_ret = annualized_return(port_rets)
ann_vol = annualized_volatility(port_rets)
sharpe = sharpe_ratio(port_rets, risk_free)

port_prices = (1 + port_rets).cumprod()
mdd = max_drawdown(port_prices)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Expected Return (ann.)", f"{ann_ret:.1%}")
m2.metric("Volatility (ann.)", f"{ann_vol:.1%}")
m3.metric("Sharpe Ratio", f"{sharpe:.2f}")
m4.metric("Max Drawdown", f"{mdd:.1%}")

# ── Allocation pie chart ────────────────────────────────────────────────────────
st.subheader("Current Allocation")
pie_labels = [f"{CAC40_TICKERS.get(t, t)} ({t})" for t in weights]
pie_values = list(weights.values())
fig_pie = px.pie(names=pie_labels, values=pie_values, title="Portfolio Allocation")
st.plotly_chart(fig_pie, width="stretch")

# Persist portfolio for use in other pages
st.session_state["weights"] = weights
st.session_state["portfolio_tickers"] = portfolio_tickers
