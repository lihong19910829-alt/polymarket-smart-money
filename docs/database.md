# Database

The schema uses ordinary PostgreSQL tables and `NUMERIC` for money, prices, shares, and scores.

Implemented groups:

- Source governance: `data_sources`, `ingestion_runs`, `ingestion_cursors`, `raw_payloads`.
- Market catalog: `events`, `markets`, `market_outcomes`.
- Wallet discovery and retention: `wallets`, `wallet_discovery_events`.
- Trading state: `trades`, `positions_current`, `position_deltas`.
- Raw and activity state: `trades_raw`, `wallet_activities`.
- Market microstructure: `market_state_snapshots`, `orderbook_levels`.
- Identity evidence: `identity_clusters`, `identity_cluster_members`.
- Analytics: `wallet_metrics`, `wallet_classifications`, `inferred_rules`.
- Signals and notifications: `signals`, `notifications`.
- Quality and validation: `data_quality_issues`.
- Backtesting: `backtest_runs`, `backtest_trades`.

High-frequency tables are present in pure PostgreSQL form. Monthly partition automation and retention rollups should be added once live capture volume is known.
