# Operations

Local start:

```bash
cp .env.example .env
docker compose up --build
docker compose exec api alembic upgrade head
```

Useful commands:

```bash
python scripts/backfill_markets.py
python scripts/backfill_wallet.py 0x...
python scripts/run_monthly_reclassification.py
python scripts/run_data_quality_checks.py
python scripts/run_backtest.py
python scripts/send_test_notification.py
pytest
ruff check .
mypy app
```

Admin endpoints require `X-API-Key` with `ADMIN_API_KEY`.

Useful admin endpoints:

- `POST /admin/run-discovery`
- `POST /admin/recompute-wallet/{address}`
- `POST /admin/refresh-wallet/{address}`
- `POST /admin/capture-orderbook/{market_id}/{token_id}`
- `POST /admin/test-notification`
- `GET /data-quality`
