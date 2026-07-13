# Architecture

The system is a FastAPI service with separate adapters for Gamma, Data API, CLOB, and future chain/subgraph data.

Core paths:

- `app/sources`: external API clients and retry behavior.
- `app/ingestion`: normalization, idempotent writes, discovery, trade backfill, and position refresh.
- `app/analytics`: wallet scoring, strategy classification, consensus scoring, and metric helpers.
- `app/api`: read/admin endpoints and the minimal operations console.
- `app/notifications`: Telegram rendering and sending.
- `alembic`: database migrations.

The first production rule is data retention: discovered wallets are never deleted because they later score poorly. They move through statuses and tiers while preserving history and evidence.

