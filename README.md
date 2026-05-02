# brn-portfolio

A personal stock portfolio management tool for the **CAC 40**. It fetches historical price data, runs Markowitz portfolio optimization, and produces concrete rebalancing recommendations based on your current holdings.

Runs entirely on localhost — no database, no authentication, no deployment needed.

---

## Features

- **Market overview** — CAC 40 index chart, per-stock price history, rolling volatility, and a sortable summary table (YTD return, volatility, Sharpe)
- **Portfolio input** — interactive allocation table; tracks performance vs. CAC 40 benchmark with annualized return, volatility, Sharpe ratio, and max drawdown
- **Markowitz optimizer** — efficient frontier chart, max-Sharpe and min-variance portfolios, configurable lookback window and per-asset weight bounds
- **Rebalancing advice** — side-by-side current vs. optimal allocation, delta table of trades to execute, optional euro amounts given total portfolio value

---

## Setup

**Requirements:** Python 3.11+

```bash
python -m venv .venv
source .venv/bin/activate
pip install streamlit yfinance pandas numpy scipy plotly pyarrow
```

---

## Usage

### Run the app

```bash
source .venv/bin/activate
streamlit run src/app/main.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

### Pre-fetch price data (optional)

Warms the local cache before opening the app, or refreshes stale data:

```bash
source .venv/bin/activate
python scripts/fetch_prices.py           # default: 5-year lookback
python scripts/fetch_prices.py --years 3
```

Data is cached per-ticker as Parquet files in `data/cache/` and only re-fetched when stale.

### Run the optimizer from the command line

Runs the exact same Markowitz computation as Page 3 of the app and prints results to stdout:

```bash
source .venv/bin/activate
python scripts/run_optimizer.py                              # defaults: 3y, max-Sharpe, weights [0%, 20%]
python scripts/run_optimizer.py --lookback 1y
python scripts/run_optimizer.py --objective min-variance
python scripts/run_optimizer.py --risk-free 3.5 --max-weight 15
python scripts/run_optimizer.py --tickers MC.PA OR.PA SAN.PA TTE.PA
```

| Option | Default | Description |
|---|---|---|
| `--lookback` | `3y` | Historical window: `1y`, `3y`, or `5y` |
| `--objective` | `max-sharpe` | `max-sharpe` or `min-variance` |
| `--risk-free` | `3.0` | Risk-free rate in % |
| `--min-weight` | `0` | Minimum weight per stock in % |
| `--max-weight` | `20` | Maximum weight per stock in % |
| `--frontier-points` | `50` | Number of points on the efficient frontier |
| `--tickers` | *(all 40)* | Restrict the universe to specific tickers |
| `--top` | `10` | Number of top holdings to display |

---

## Workflow

1. **Market** — explore CAC 40 stocks and pick your universe
2. **Portfolio** — enter your current holdings (allocations must sum to 100%)
3. **Optimizer** — tune parameters and inspect the efficient frontier
4. **Advice** — see what to buy/sell to reach the optimal allocation

Pages 3 and 4 require visiting Page 2 first to populate the portfolio in session state.

---

## Project Structure

```
brn-portfolio/
├── scripts/
│   ├── fetch_prices.py         # offline price cache refresh
│   └── run_optimizer.py        # CLI optimizer (same computation as Page 3)
├── data/
│   └── cache/                  # per-ticker Parquet files
├── src/
│   ├── data/
│   │   ├── cac40.py            # CAC 40 ticker list with display names
│   │   └── fetcher.py          # yfinance wrapper with cache logic
│   ├── analytics/
│   │   ├── metrics.py          # returns, volatility, Sharpe, drawdown
│   │   └── markowitz.py        # efficient frontier, max-Sharpe, min-variance
│   └── app/
│       ├── main.py             # Streamlit entry point
│       └── pages/
│           ├── 1_market.py
│           ├── 2_portfolio.py
│           ├── 3_optimizer.py
│           └── 4_advice.py
```

---

## Design Notes

- **Universe**: all 40 CAC 40 constituents; can be restricted to a subset in the optimizer
- **Long-only**: no short positions; weights bounded `[0, 1]`
- **End-of-day data**: adjusted close prices via Yahoo Finance — no real-time feed
- **Optimizer**: SLSQP via `scipy.optimize`, constrained to fully-invested long-only portfolios
