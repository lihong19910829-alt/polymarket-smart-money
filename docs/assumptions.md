# Assumptions

- The repository was empty at implementation time, so the first version uses a new FastAPI/Python service layout.
- Python 3.12 is the target runtime. The local sandbox reported Python 3.11, so full local runtime validation may require the Docker image or a 3.12 environment.
- PostgreSQL 16 is the primary database. TimescaleDB is not required.
- Redis is used for future distributed locks, cache, rate limits, and notification dedupe; v1 database unique keys also protect dedupe.
- Polymarket authenticated trading is intentionally excluded.
- Chain/subgraph backfill is configurable but not hardcoded because public subgraph endpoints can change.
- The v1 strategy classifier is deterministic and evidence-first. Statistical model training is represented by explicit extension points and must be promoted only after enough historical samples exist.
- PnL and rule inference are conservative when only public API data is available; current positions are not treated as new trades.

