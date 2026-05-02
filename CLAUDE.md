# brn-portfolio

## Purpose

A personal stock portfolio management tool focused on the **CAC 40** (French stock index). The goal is to:

1. Pull and visualize historical CAC 40 stock price data
2. Run **Markowitz portfolio optimization** to compute efficient frontiers and optimal allocations
3. Accept the user's current portfolio distribution as input
4. Produce concrete **rebalancing recommendations** based on the optimization results

This is a local tool — not a web service — designed for personal use and run via `streamlit run`.

---

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python 3.11+ | Best ecosystem for data science |
| UI | Streamlit | Reactive, Python-native, no frontend code needed |
| Data fetching | `yfinance` | Pulls Yahoo Finance data; CAC 40 stocks use `.PA` suffix (e.g. `MC.PA`) |
| Data storage | Parquet files (local cache) | Avoid redundant API calls; fast read/write with pandas |
| Numerics | `numpy`, `pandas` | Standard data manipulation |
| Optimizer | `scipy.optimize` (SLSQP) | Constrained quadratic optimization for Markowitz |
| Charts | `plotly` | Interactive charts, native Streamlit support |

---

## Project Structure

```
brn-portfolio/
├── CLAUDE.md
├── pyproject.toml
├── data/
│   └── cache/                  # parquet files with cached historical prices
├── src/
│   ├── data/
│   │   ├── cac40.py            # CAC 40 ticker list with company names
│   │   └── fetcher.py          # yfinance wrapper: fetch, cache, refresh logic
│   ├── analytics/
│   │   ├── metrics.py          # returns, volatility, Sharpe ratio, drawdown
│   │   └── markowitz.py        # efficient frontier, min-variance, max-Sharpe
│   └── app/
│       ├── main.py             # Streamlit entry point (sidebar nav)
│       └── pages/
│           ├── 1_market.py     # CAC 40 overview + per-stock drill-down
│           ├── 2_portfolio.py  # user portfolio input + current performance
│           ├── 3_optimizer.py  # Markowitz params + efficient frontier chart
│           └── 4_advice.py     # current vs optimal allocation + rebalancing trades
```

---

## Pages

### 1 — Market
- Date range selector (default: last 3 years)
- CAC 40 index-level price chart
- Stock selector: per-stock price history, returns, rolling volatility
- Sortable summary table: YTD return, volatility, Sharpe

### 2 — Portfolio
- Input table: ticker + % allocation (must sum to 100)
- Portfolio historical performance vs CAC 40 benchmark
- Current metrics: expected return, volatility, Sharpe ratio, max drawdown

### 3 — Optimizer
- Parameters (all adjustable via sliders/inputs):
  - Historical lookback window (1y / 3y / 5y)
  - Risk-free rate
  - Objective: Max Sharpe or Min Variance
  - Per-stock weight bounds (e.g. min 0%, max 20%)
- Outputs:
  - Efficient frontier chart (risk vs return, hover shows weights)
  - Optimal portfolio weights table
  - Key metrics for the optimal portfolio

### 4 — Advice
- Side-by-side comparison: current allocation vs optimal
- Delta table: which stocks to buy/sell and by how much
- Optional: input total portfolio value (€) to get trade amounts in euros

---

## Analytics

### Data (`src/data/`)

- `cac40.py`: static list of 40 tickers with display names
- `fetcher.py`:
  - `fetch_prices(tickers, start, end)` — returns a `pd.DataFrame` of adjusted close prices
  - Caches per-ticker in `data/cache/{ticker}.parquet`
  - Refreshes only if cache is stale (last date < today)

### Metrics (`src/analytics/metrics.py`)

- `daily_returns(prices)` — log or simple returns
- `annualized_return(returns)` — geometric mean × 252
- `annualized_volatility(returns)` — std × sqrt(252)
- `sharpe_ratio(returns, risk_free_rate)` — excess return / volatility
- `max_drawdown(prices)` — peak-to-trough

### Markowitz (`src/analytics/markowitz.py`)

- `compute_efficient_frontier(returns, n_points, constraints)` — array of (risk, return, weights) tuples
- `max_sharpe_portfolio(returns, risk_free_rate, constraints)` — optimal weights maximizing Sharpe
- `min_variance_portfolio(returns, constraints)` — minimum volatility point
- Constraints: long-only (`w >= 0`), fully invested (`sum(w) = 1`), optional per-asset max weight

---

## Key Design Decisions

- **Universe**: all 40 CAC 40 constituents; user can restrict to a subset in the optimizer
- **Default lookback**: 3 years for covariance estimation (configurable)
- **Long-only**: no short positions; weights bounded `[0, 1]`
- **No live prices**: data is end-of-day adjusted close; no real-time feed
- **Local only**: no database, no authentication, no deployment target — runs on localhost

---

## Providing Your Portfolio Distribution

Portfolio input is done interactively on **Page 2 — Portfolio** via a Streamlit `data_editor` table. There is no file to edit manually.

### How it works

1. Navigate to the **My Portfolio** page in the sidebar.
2. The table pre-fills with a default allocation across 7 CAC 40 stocks.
3. Edit, add, or delete rows directly in the table:
   - **Ticker**: choose from the CAC 40 dropdown (`.PA`-suffixed tickers, e.g. `MC.PA`)
   - **Allocation (%)**: numeric weight for that stock
4. Allocations **must sum to exactly 100%** — the app shows a warning and stops rendering if they don't.
5. The parsed weights are stored in `st.session_state["weights"]` and automatically carried forward to **Page 3 — Optimizer** and **Page 4 — Advice**.

### Persistence across pages

- `st.session_state["weights"]` — `{ticker: float}` dict with decimal weights (e.g. `0.20` for 20%)
- `st.session_state["portfolio_tickers"]` — ordered list of tickers
- These session-state keys must be populated (by visiting Page 2 first) before Pages 3 and 4 will work correctly.

---

## Running the App

```bash
source .venv/bin/activate
streamlit run src/app/main.py
```

---

## Scripts (`scripts/`)

Standalone utility scripts for offline operations.

### `scripts/fetch_prices.py`

Fetches and caches historical prices for all 40 CAC 40 tickers into `data/cache/`.

```bash
source .venv/bin/activate
python scripts/fetch_prices.py           # default: 5-year lookback
python scripts/fetch_prices.py --years 3
```

Run this to warm the cache before using the app, or to refresh stale data.

---

## Dependencies (requirements.txt)

```
streamlit
yfinance
pandas
numpy
scipy
plotly
pyarrow        # parquet support
```
