"""Page 1 — CAC 40 market overview and per-stock drill-down."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.analytics.metrics import annualized_volatility, daily_returns, summary_table
from src.market.cac40 import CAC40_TICKERS, TICKERS
from src.market.fetcher import fetch_prices

st.set_page_config(page_title="Market — BRN Portfolio", layout="wide")
st.title("CAC 40 — Market Overview")

# ── Date range ────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
default_end = pd.Timestamp.today().normalize()
default_start = default_end - pd.DateOffset(years=3)

with col1:
    start_date = st.date_input("Start date", value=default_start.date())
with col2:
    end_date = st.date_input("End date", value=default_end.date())

if start_date >= end_date:
    st.error("Start date must be before end date.")
    st.stop()

# ── Fetch data ────────────────────────────────────────────────────────────────
with st.spinner("Fetching price data…"):
    prices = fetch_prices(TICKERS, start=str(start_date), end=str(end_date))

if prices.empty:
    st.error("No data returned. Check your internet connection.")
    st.stop()

available_tickers = list(prices.columns)

# ── CAC 40 index proxy (equal-weight) ─────────────────────────────────────────
st.subheader("CAC 40 Equal-Weight Index")
index_prices = prices.div(prices.iloc[0]).mean(axis=1) * 100
fig_index = px.line(
    index_prices,
    labels={"value": "Indexed price (base 100)", "Date": "Date"},
    title="CAC 40 Equal-Weight Index (base 100)",
)
fig_index.update_layout(showlegend=False)
st.plotly_chart(fig_index, width="stretch")

# ── Summary table ─────────────────────────────────────────────────────────────
st.subheader("Stock Summary")
risk_free = st.number_input("Risk-free rate (%)", value=3.0, step=0.1) / 100
summary = summary_table(prices, risk_free_rate=risk_free)
summary.index = [f"{t} — {CAC40_TICKERS.get(t, t)}" for t in summary.index]

fmt = {
    "YTD Return": "{:.1%}",
    "Ann. Return": "{:.1%}",
    "Volatility": "{:.1%}",
    "Sharpe": "{:.2f}",
    "Max Drawdown": "{:.1%}",
}
st.dataframe(summary.style.format(fmt), width="stretch")

# ── Per-stock drill-down ──────────────────────────────────────────────────────
st.subheader("Per-Stock Drill-Down")
selected_ticker = st.selectbox(
    "Select a stock",
    options=available_tickers,
    format_func=lambda t: f"{t} — {CAC40_TICKERS.get(t, t)}",
)

stock_prices = prices[selected_ticker].dropna()
rets = daily_returns(stock_prices.to_frame())

tab1, tab2, tab3 = st.tabs(["Price History", "Returns", "Rolling Volatility"])

with tab1:
    fig_price = px.line(
        stock_prices,
        title=f"{selected_ticker} — Price History",
        labels={"value": "Price (€)", "Date": "Date"},
    )
    fig_price.update_layout(showlegend=False)
    st.plotly_chart(fig_price, width="stretch")

with tab2:
    col_ret = rets[selected_ticker]
    fig_ret = px.bar(
        col_ret,
        title=f"{selected_ticker} — Daily Returns",
        labels={"value": "Return", "Date": "Date"},
        color=col_ret,
        color_continuous_scale=["red", "white", "green"],
        color_continuous_midpoint=0,
    )
    fig_ret.update_layout(showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig_ret, width="stretch")

with tab3:
    window = st.slider("Rolling window (days)", min_value=10, max_value=90, value=21)
    rolling_vol = col_ret.rolling(window).std() * (252 ** 0.5)
    fig_vol = px.line(
        rolling_vol,
        title=f"{selected_ticker} — Rolling Volatility ({window}d)",
        labels={"value": "Ann. Volatility", "Date": "Date"},
    )
    fig_vol.update_layout(showlegend=False)
    st.plotly_chart(fig_vol, width="stretch")
