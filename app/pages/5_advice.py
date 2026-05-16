"""Page 4 — Rebalancing advice: current vs optimal allocation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.market.cac40 import CAC40_TICKERS
from src.market.fetcher import fetch_prices

st.set_page_config(page_title="Advice — BRN Portfolio", layout="wide")
st.title("Rebalancing Advice")

# ── Check prerequisites ────────────────────────────────────────────────────────
if "weights" not in st.session_state or "optimal_weights" not in st.session_state:
    st.info(
        "Please configure your portfolio on **page 2** and run the optimizer on **page 3** first."
    )
    st.stop()

current_weights: dict[str, float] = st.session_state["weights"]
optimal_weights_raw: dict[str, float] = st.session_state["optimal_weights"]

# Normalise optimal weights (filter near-zero)
optimal_weights = {k: v for k, v in optimal_weights_raw.items() if v > 0.001}
total_opt = sum(optimal_weights.values())
optimal_weights = {k: v / total_opt for k, v in optimal_weights.items()}

# ── Build comparison DataFrame ─────────────────────────────────────────────────
all_tickers = sorted(set(list(current_weights.keys()) + list(optimal_weights.keys())))

rows = []
for t in all_tickers:
    cur = current_weights.get(t, 0.0)
    opt = optimal_weights.get(t, 0.0)
    delta = opt - cur
    rows.append(
        {
            "Ticker": t,
            "Company": CAC40_TICKERS.get(t, t),
            "Current (%)": cur * 100,
            "Optimal (%)": opt * 100,
            "Delta (%)": delta * 100,
        }
    )

df = pd.DataFrame(rows).sort_values("Delta (%)", ascending=False)

# ── Side-by-side bar chart ─────────────────────────────────────────────────────
st.subheader("Current vs Optimal Allocation")

labels = [f"{r['Ticker']}" for _, r in df.iterrows()]
fig = go.Figure(
    data=[
        go.Bar(name="Current", x=labels, y=df["Current (%)"], marker_color="steelblue"),
        go.Bar(name="Optimal", x=labels, y=df["Optimal (%)"], marker_color="seagreen"),
    ]
)
fig.update_layout(
    barmode="group",
    xaxis_title="Stock",
    yaxis_title="Weight (%)",
    hovermode="x unified",
)
st.plotly_chart(fig, width="stretch")

# ── Delta table ────────────────────────────────────────────────────────────────
st.subheader("Rebalancing Actions")

def color_delta(val: float) -> str:
    if val > 0.5:
        return "color: green"
    if val < -0.5:
        return "color: red"
    return ""

styled = df.style.format(
    {
        "Current (%)": "{:.2f}%",
        "Optimal (%)": "{:.2f}%",
        "Delta (%)": "{:+.2f}%",
    }
).map(color_delta, subset=["Delta (%)"])

st.dataframe(styled, width="stretch")

# ── Euro amounts ───────────────────────────────────────────────────────────────
st.subheader("Trade Amounts")
portfolio_value = st.number_input(
    "Total portfolio value (€)",
    min_value=0.0,
    value=10_000.0,
    step=100.0,
    format="%.2f",
)

if portfolio_value > 0:
    # Fetch latest prices for all tickers
    latest_prices: dict[str, float] = {}
    tickers_to_fetch = all_tickers
    price_data = fetch_prices(
        tickers_to_fetch,
        start=pd.Timestamp.today() - pd.Timedelta(days=10),
    )
    if not price_data.empty:
        for t in tickers_to_fetch:
            if t in price_data.columns:
                series = price_data[t].dropna()
                if not series.empty:
                    latest_prices[t] = float(series.iloc[-1])

    df_trades = df.copy()
    df_trades["Trade Amount (€)"] = df_trades["Delta (%)"] / 100 * portfolio_value
    df_trades["Action"] = df_trades["Trade Amount (€)"].apply(
        lambda x: "BUY" if x > 0 else ("SELL" if x < 0 else "HOLD")
    )
    df_trades["Price (€)"] = df_trades["Ticker"].map(latest_prices)
    df_trades["Shares"] = df_trades.apply(
        lambda r: int(abs(r["Trade Amount (€)"]) / r["Price (€)"]) if pd.notna(r["Price (€)"]) and r["Price (€)"] > 0 else None,
        axis=1,
    )

    trades_only = df_trades[df_trades["Action"] != "HOLD"].copy()
    trades_only["Trade Amount (€)"] = trades_only["Trade Amount (€)"].abs()

    buys = trades_only[trades_only["Action"] == "BUY"].sort_values("Trade Amount (€)", ascending=False)
    sells = trades_only[trades_only["Action"] == "SELL"].sort_values("Trade Amount (€)", ascending=False)

    col_buy, col_sell = st.columns(2)

    with col_buy:
        st.markdown("**Stocks to BUY**")
        if buys.empty:
            st.write("None")
        else:
            st.dataframe(
                buys[["Ticker", "Company", "Trade Amount (€)", "Price (€)", "Shares"]].style.format(
                    {"Trade Amount (€)": "€{:,.2f}", "Price (€)": "€{:,.2f}"},
                    na_rep="N/A",
                ),
                width="stretch",
            )

    with col_sell:
        st.markdown("**Stocks to SELL**")
        if sells.empty:
            st.write("None")
        else:
            st.dataframe(
                sells[["Ticker", "Company", "Trade Amount (€)", "Price (€)", "Shares"]].style.format(
                    {"Trade Amount (€)": "€{:,.2f}", "Price (€)": "€{:,.2f}"},
                    na_rep="N/A",
                ),
                width="stretch",
            )
