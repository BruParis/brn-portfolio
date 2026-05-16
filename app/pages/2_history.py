"""Page 2 — Transaction history, timeline, and cohort analysis."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analytics.holdings import compute_cost_basis, compute_positions
from src.market.cac40 import CAC40_TICKERS, TICKER_TO_DISPLAY
from src.market.fetcher import fetch_prices
from src.market.history import load_history

st.set_page_config(page_title="History — BRN Portfolio", layout="wide")
st.title("Portfolio History")

# ── Load transactions ──────────────────────────────────────────────────────────
try:
    transactions = load_history()
except FileNotFoundError:
    st.error("No transaction history found. Expected `data/historic.csv`.")
    st.stop()
except ValueError as exc:
    st.error(str(exc))
    st.stop()

if not transactions:
    st.info("Transaction history is empty.")
    st.stop()

# ── Build base DataFrame ───────────────────────────────────────────────────────
txn_df = pd.DataFrame(
    [
        {
            "Date": pd.Timestamp(t.date),
            "Operation": t.operation,
            "Company": CAC40_TICKERS.get(t.ticker, t.broker_name),
            "Ticker": t.ticker,
            "Shares": t.quantity,
            "Amount (€)": t.amount_eur,
        }
        for t in transactions  # sorted ascending by load_history
    ]
)

today = pd.Timestamp.today().date()

# ── 1. Transaction Timeline ────────────────────────────────────────────────────
st.subheader("Transaction Timeline")

# Stack events that share the same date: y = rank within that date group
tl = txn_df.sort_values(["Date", "Company"]).copy()
tl["stack"] = tl.groupby("Date").cumcount()
max_stack = tl["stack"].max()

_PALETTE = [
    "#3498db", "#e67e22", "#2ecc71", "#9b59b6", "#e74c3c",
    "#1abc9c", "#f39c12", "#d35400", "#27ae60", "#8e44ad",
    "#2980b9", "#c0392b", "#16a085", "#f1c40f", "#7f8c8d",
    "#2c3e50", "#e91e63", "#00bcd4", "#ff5722", "#607d8b",
]
companies = tl["Company"].unique().tolist()
color_map = {c: _PALETTE[i % len(_PALETTE)] for i, c in enumerate(sorted(companies))}

fig_tl = go.Figure()

# Baseline
fig_tl.add_shape(
    type="line",
    x0=tl["Date"].min(), x1=tl["Date"].max(),
    y0=-0.5, y1=-0.5,
    line=dict(color="gray", width=1),
)

# One trace per company so the legend is meaningful
for company in sorted(companies):
    sub = tl[tl["Company"] == company]
    fig_tl.add_trace(
        go.Scatter(
            x=sub["Date"],
            y=sub["stack"],
            mode="markers",
            name=company,
            marker=dict(
                size=14,
                color=color_map[company],
                opacity=0.9,
                line=dict(width=1, color="white"),
                symbol="circle",
            ),
            customdata=sub[["Ticker", "Shares", "Amount (€)", "Operation"]].values,
            hovertemplate=(
                "<b>%{customdata[3]} %{fullData.name}</b> (%{customdata[0]})<br>"
                "%{x|%d %b %Y}<br>"
                "Shares: %{customdata[1]}<br>"
                "Amount: €%{customdata[2]:,.0f}"
                "<extra></extra>"
            ),
        )
    )

fig_tl.update_layout(
    height=max(160, 50 + 40 * (max_stack + 1)),
    margin=dict(l=0, r=0, t=10, b=10),
    xaxis=dict(title=""),
    yaxis=dict(visible=False, range=[-1, max_stack + 1]),
    hovermode="closest",
    legend=dict(
        orientation="h",
        yanchor="bottom", y=1.02,
        xanchor="left", x=0,
        font=dict(size=11),
    ),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)
fig_tl.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.15)")

st.plotly_chart(fig_tl, use_container_width=True)

# ── 2. Period Analysis ─────────────────────────────────────────────────────────
st.subheader("Period Analysis")
st.caption(
    "Filter by **transaction date** to isolate a cohort. "
    "Useful when recent purchases haven't matured yet and are diluting overall P&L."
)

first_date = transactions[0].date

col1, col2 = st.columns(2)
with col1:
    filter_start = st.date_input("From", value=first_date, min_value=first_date, max_value=today)
with col2:
    filter_end = st.date_input("To", value=today, min_value=first_date, max_value=today)

filtered = [t for t in transactions if filter_start <= t.date <= filter_end]

if not filtered:
    st.warning("No transactions in the selected period.")
else:
    positions = compute_positions(filtered)
    basis = compute_cost_basis(filtered)
    f_tickers = list(positions.keys())

    with st.spinner("Fetching latest prices…"):
        prices = fetch_prices(f_tickers, start="2025-01-01", end=str(today))

    latest_prices: dict[str, float] = {}
    for t in f_tickers:
        if t in prices.columns:
            series = prices[t].dropna()
            if not series.empty:
                latest_prices[t] = series.iloc[-1]

    total_invested = sum(basis.get(t, 0.0) for t in f_tickers)
    total_value = sum(positions[t] * latest_prices[t] for t in f_tickers if t in latest_prices)
    total_pnl = total_value - total_invested
    total_pnl_pct = total_pnl / total_invested * 100 if total_invested > 0 else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Invested", f"€{total_invested:,.0f}")
    m2.metric("Market Value", f"€{total_value:,.0f}")
    m3.metric("Unrealised P&L", f"€{total_pnl:,.0f}", delta=f"{total_pnl_pct:+.1f}%")
    m4.metric("Positions", len(positions))

    # Per-position breakdown table
    pos_rows = []
    for t in f_tickers:
        shares = positions[t]
        cost = basis.get(t, 0.0)
        price = latest_prices.get(t)
        value = shares * price if price is not None else None
        pnl = value - cost if value is not None else None
        pnl_pct = pnl / cost * 100 if (pnl is not None and cost > 0) else None
        pos_rows.append(
            {
                "Company": CAC40_TICKERS.get(t, t),
                "Ticker": t,
                "Shares": shares,
                "Invested (€)": round(cost, 2),
                "Last Price (€)": round(price, 2) if price is not None else None,
                "Value (€)": round(value, 2) if value is not None else None,
                "P&L (€)": round(pnl, 2) if pnl is not None else None,
                "P&L (%)": round(pnl_pct, 2) if pnl_pct is not None else None,
            }
        )

    pos_df = pd.DataFrame(pos_rows).sort_values("P&L (%)", ascending=False, na_position="last")
    st.dataframe(
        pos_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Invested (€)": st.column_config.NumberColumn(format="%.2f €"),
            "Last Price (€)": st.column_config.NumberColumn(format="%.2f €"),
            "Value (€)": st.column_config.NumberColumn(format="%.2f €"),
            "P&L (€)": st.column_config.NumberColumn(format="%.2f €"),
            "P&L (%)": st.column_config.NumberColumn(format="%.2f %%"),
        },
    )

    # P&L bar chart
    chart_data = [
        (r["Company"], r["P&L (€)"])
        for r in pos_rows
        if r["P&L (€)"] is not None
    ]
    if chart_data:
        bar_df = (
            pd.DataFrame(chart_data, columns=["Company", "P&L (€)"])
            .sort_values("P&L (€)", ascending=False)
        )
        fig_bar = go.Figure(
            go.Bar(
                x=bar_df["Company"],
                y=bar_df["P&L (€)"],
                marker_color=["#2ecc71" if v >= 0 else "#e74c3c" for v in bar_df["P&L (€)"]],
                text=[f"€{v:,.0f}" for v in bar_df["P&L (€)"]],
                textposition="outside",
            )
        )
        fig_bar.update_layout(
            yaxis_title="P&L (€)",
            showlegend=False,
            margin=dict(t=10, b=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        fig_bar.update_yaxes(
            showgrid=True,
            gridcolor="rgba(128,128,128,0.15)",
            zeroline=True,
            zerolinecolor="gray",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

# ── 3. Sync to Portfolio ───────────────────────────────────────────────────────
with st.expander("Sync current positions to Portfolio page"):
    st.caption(
        "Derive weights from **all** transactions (current market values) "
        "and populate the Portfolio page so pages 3 – 5 use your actual holdings."
    )
    if st.button("Sync to Portfolio", type="primary"):
        all_positions = compute_positions(transactions)
        all_tickers = list(all_positions.keys())
        with st.spinner("Fetching latest prices…"):
            all_prices = fetch_prices(all_tickers, start="2025-01-01", end=str(today))
        all_latest: dict[str, float] = {}
        for t in all_tickers:
            if t in all_prices.columns:
                s = all_prices[t].dropna()
                if not s.empty:
                    all_latest[t] = s.iloc[-1]
        total_mv = sum(all_positions[t] * all_latest[t] for t in all_tickers if t in all_latest)
        if total_mv > 0:
            raw = {t: all_positions[t] * all_latest[t] for t in all_tickers if t in all_latest}
            weights = {t: v / total_mv for t, v in raw.items()}
            st.session_state["weights"] = weights
            st.session_state["portfolio_tickers"] = list(weights.keys())
            st.session_state["portfolio_data"] = [
                {"Stock": TICKER_TO_DISPLAY.get(t, t), "Allocation (%)": round(w * 100, 2)}
                for t, w in weights.items()
            ]
            st.success("Done — head to **My Portfolio** to review.")
        else:
            st.warning("No price data available.")

# ── 4. Transaction Log ─────────────────────────────────────────────────────────
st.subheader("All Transactions")
log_df = txn_df.copy()
log_df["Date"] = log_df["Date"].dt.date
st.dataframe(
    log_df[["Date", "Operation", "Company", "Ticker", "Shares", "Amount (€)"]]
    .iloc[::-1]
    .reset_index(drop=True),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Amount (€)": st.column_config.NumberColumn(format="%.2f €"),
    },
)
