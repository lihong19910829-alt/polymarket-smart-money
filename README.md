# Polymarket Smart Money Reverse Engineering System

Production-shaped v1 for discovering Polymarket wallets, preserving them permanently, scoring quality, classifying strategies, inferring explainable rules, generating consensus signals, and sending Telegram notifications.

## Start

```bash
cp .env.example .env
docker compose up --build
docker compose exec api alembic upgrade head
```

Open `http://localhost:8000`.

## Windows Quick View

Open the live public-data dashboard without starting the backend:

```powershell
scripts\open_live_dashboard.cmd
```

Start the FastAPI backend and open the dashboard:

```powershell
scripts\start_api_and_open.cmd
```

The backend also exposes live public-data endpoints:

```text
http://127.0.0.1:8000/live/overview
http://127.0.0.1:8000/live/markets
http://127.0.0.1:8000/live/leaderboard
```

## Backfill

```bash
python scripts/backfill_markets.py
python scripts/backfill_wallet.py 0x...
python scripts/run_data_quality_checks.py
python scripts/run_backtest.py
```

## Worker

```bash
ENABLE_SCHEDULER=true python -m app.worker
```

## Tests

```bash
pytest
ruff check .
mypy app
```

## Implemented

- PostgreSQL/Alembic schema for sources, ingestion runs, markets, wallets, trades, positions, metrics, classifications, rules, signals, and notifications.
- Gamma, Data API, and CLOB adapter layer.
- Leaderboard, holder, market, trade, and position ingestion workflows.
- Recursive time-window trade fetching.
- Wallet tier scoring and deterministic strategy classification with evidence.
- Consensus weighting with tier, quality, confidence, copyability, freshness, and size significance.
- Market state snapshot and orderbook level tables, plus an admin endpoint for CLOB orderbook capture.
- Data-quality checks for missing token/wallet, out-of-range prices, negative values, and future timestamps.
- Conservative backtest helpers that use post-signal executable orderbook quotes, delay, fees, slippage, and capacity.
- Live public-data dashboard and API endpoints backed by Polymarket Gamma API and Data API.
- FastAPI read/admin endpoints and a minimal admin page.
- Telegram test notification support.

## Not Yet Complete

- Full chain/subgraph backfill implementation.
- Monthly PostgreSQL partition management and retention rollups.
- Statistical rule training with walk-forward validation.
- Complete historical PnL reconciliation across all market resolution cases.
