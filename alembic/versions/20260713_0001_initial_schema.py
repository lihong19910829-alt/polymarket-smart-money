"""initial production schema

Revision ID: 20260713_0001
Revises:
Create Date: 2026-07-13 00:00:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260713_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_sources",
        sa.Column("id", sa.SmallInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("base_url", sa.Text()),
        sa.Column("priority", sa.SmallInteger(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_health_at", sa.DateTime(timezone=True)),
        sa.Column("last_health_status", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.bulk_insert(
        sa.table(
            "data_sources",
            sa.column("id", sa.SmallInteger()),
            sa.column("name", sa.Text()),
            sa.column("source_kind", sa.Text()),
            sa.column("base_url", sa.Text()),
            sa.column("priority", sa.SmallInteger()),
        ),
        [
            {"id": 1, "name": "gamma", "source_kind": "rest", "base_url": "https://gamma-api.polymarket.com", "priority": 2},
            {"id": 2, "name": "data_api", "source_kind": "rest", "base_url": "https://data-api.polymarket.com", "priority": 2},
            {"id": 3, "name": "clob", "source_kind": "rest_ws", "base_url": "https://clob.polymarket.com", "priority": 2},
            {"id": 4, "name": "chain", "source_kind": "chain", "base_url": None, "priority": 1},
        ],
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_name", sa.Text(), nullable=False),
        sa.Column("source_id", sa.SmallInteger(), sa.ForeignKey("data_sources.id")),
        sa.Column("scope_type", sa.Text()),
        sa.Column("scope_key", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("cursor_before", postgresql.JSONB()),
        sa.Column("cursor_after", postgresql.JSONB()),
        sa.Column("rows_read", sa.BigInteger(), server_default="0"),
        sa.Column("rows_inserted", sa.BigInteger(), server_default="0"),
        sa.Column("rows_updated", sa.BigInteger(), server_default="0"),
        sa.Column("rows_rejected", sa.BigInteger(), server_default="0"),
        sa.Column("http_requests", sa.Integer(), server_default="0"),
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        sa.Column("error_class", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_ingestion_runs_job_started", "ingestion_runs", ["job_name", sa.text("started_at DESC")])
    op.create_index("ix_ingestion_runs_status_started", "ingestion_runs", ["status", sa.text("started_at DESC")])
    op.create_index("ix_ingestion_runs_scope_started", "ingestion_runs", ["scope_type", "scope_key", sa.text("started_at DESC")])

    op.create_table(
        "ingestion_cursors",
        sa.Column("job_name", sa.Text(), primary_key=True),
        sa.Column("source_id", sa.SmallInteger(), primary_key=True),
        sa.Column("scope_key", sa.Text(), primary_key=True),
        sa.Column("cursor", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "raw_payloads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", sa.SmallInteger(), sa.ForeignKey("data_sources.id")),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("request_fingerprint", sa.Text(), nullable=False),
        sa.Column("request_params", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("object_storage_uri", sa.Text()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True)),
    )
    op.create_index("ix_raw_payloads_content_hash", "raw_payloads", ["content_hash"])
    op.create_index("ix_raw_payloads_request_fingerprint", "raw_payloads", ["request_fingerprint"])

    op.create_table(
        "events",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("slug", sa.Text(), unique=True),
        sa.Column("title", sa.Text()),
        sa.Column("subtitle", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.Text()),
        sa.Column("series_id", sa.Text()),
        sa.Column("start_at", sa.DateTime(timezone=True)),
        sa.Column("end_at", sa.DateTime(timezone=True)),
        sa.Column("active", sa.Boolean()),
        sa.Column("closed", sa.Boolean()),
        sa.Column("archived", sa.Boolean()),
        sa.Column("restricted", sa.Boolean()),
        sa.Column("volume", sa.Numeric(38, 12)),
        sa.Column("liquidity", sa.Numeric(38, 12)),
        sa.Column("raw_data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source_updated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "markets",
        sa.Column("market_id", sa.Text(), primary_key=True),
        sa.Column("condition_id", sa.Text(), nullable=False, unique=True),
        sa.Column("event_id", sa.Text(), sa.ForeignKey("events.event_id")),
        sa.Column("slug", sa.Text()),
        sa.Column("question", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("resolution_source", sa.Text()),
        sa.Column("category", sa.Text()),
        sa.Column("market_type", sa.Text()),
        sa.Column("start_at", sa.DateTime(timezone=True)),
        sa.Column("end_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("active", sa.Boolean()),
        sa.Column("closed", sa.Boolean()),
        sa.Column("archived", sa.Boolean()),
        sa.Column("restricted", sa.Boolean()),
        sa.Column("negative_risk", sa.Boolean()),
        sa.Column("enable_order_book", sa.Boolean()),
        sa.Column("resolution_status", sa.Text()),
        sa.Column("resolved_outcome_index", sa.Integer()),
        sa.Column("market_maker_address", sa.Text()),
        sa.Column("min_tick_size", sa.Numeric(20, 12)),
        sa.Column("min_order_size", sa.Numeric(38, 12)),
        sa.Column("fee_rate", sa.Numeric(20, 12)),
        sa.Column("volume_total", sa.Numeric(38, 12)),
        sa.Column("volume_24h", sa.Numeric(38, 12)),
        sa.Column("volume_7d", sa.Numeric(38, 12)),
        sa.Column("volume_30d", sa.Numeric(38, 12)),
        sa.Column("liquidity", sa.Numeric(38, 12)),
        sa.Column("open_interest", sa.Numeric(38, 12)),
        sa.Column("raw_data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source_created_at", sa.DateTime(timezone=True)),
        sa.Column("source_updated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_markets_active_closed_volume", "markets", ["active", "closed", sa.text("volume_24h DESC")])
    op.create_index("ix_markets_event_id", "markets", ["event_id"])
    op.create_index("ix_markets_end_at", "markets", ["end_at"])
    op.create_index("ix_markets_category", "markets", ["category"])
    op.create_index("ix_markets_condition_id", "markets", ["condition_id"])

    op.create_table(
        "market_outcomes",
        sa.Column("token_id", sa.Text(), primary_key=True),
        sa.Column("market_id", sa.Text(), sa.ForeignKey("markets.market_id"), nullable=False),
        sa.Column("condition_id", sa.Text(), nullable=False),
        sa.Column("outcome_index", sa.Integer(), nullable=False),
        sa.Column("outcome_name", sa.Text(), nullable=False),
        sa.Column("opposite_token_id", sa.Text()),
        sa.Column("current_price", sa.Numeric(20, 12)),
        sa.Column("resolved", sa.Boolean()),
        sa.Column("winning", sa.Boolean()),
        sa.Column("payout", sa.Numeric(20, 12)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("market_id", "outcome_index", name="uq_market_outcome_index"),
    )

    op.create_table(
        "wallets",
        sa.Column("address", sa.Text(), primary_key=True),
        sa.Column("normalized_address", sa.Text(), nullable=False, unique=True),
        sa.Column("profile_name", sa.Text()),
        sa.Column("pseudonym", sa.Text()),
        sa.Column("bio", sa.Text()),
        sa.Column("x_username", sa.Text()),
        sa.Column("profile_image", sa.Text()),
        sa.Column("verified_badge", sa.Boolean()),
        sa.Column("profile_created_at", sa.DateTime(timezone=True)),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("first_trade_at", sa.DateTime(timezone=True)),
        sa.Column("last_trade_at", sa.DateTime(timezone=True)),
        sa.Column("active_span_days", sa.Integer()),
        sa.Column("current_status", sa.Text(), nullable=False, server_default="DISCOVERED"),
        sa.Column("current_tier", sa.Text(), nullable=False, server_default="INSUFFICIENT_DATA"),
        sa.Column("identity_cluster_id", postgresql.UUID(as_uuid=True)),
        sa.Column("data_completeness", sa.Numeric(8, 4)),
        sa.Column("excluded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("exclusion_reason", sa.Text()),
        sa.Column("manual_notes", sa.Text()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "wallet_discovery_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("wallet_address", sa.Text(), sa.ForeignKey("wallets.address"), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("discovery_type", sa.Text(), nullable=False),
        sa.Column("source_id", sa.SmallInteger()),
        sa.Column("category", sa.Text()),
        sa.Column("time_period", sa.Text()),
        sa.Column("order_by", sa.Text()),
        sa.Column("rank", sa.Integer()),
        sa.Column("reported_pnl", sa.Numeric(38, 12)),
        sa.Column("reported_volume", sa.Numeric(38, 12)),
        sa.Column("market_id", sa.Text()),
        sa.Column("token_id", sa.Text()),
        sa.Column("holder_amount", sa.Numeric(38, 12)),
        sa.Column("transaction_hash", sa.Text()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_wallet_discovery_address_time", "wallet_discovery_events", ["wallet_address", sa.text("discovered_at DESC")])

    op.create_table(
        "trades",
        sa.Column("trade_uid", sa.Text(), primary_key=True),
        sa.Column("wallet_address", sa.Text(), sa.ForeignKey("wallets.address"), nullable=False),
        sa.Column("market_id", sa.Text()),
        sa.Column("condition_id", sa.Text(), nullable=False),
        sa.Column("token_id", sa.Text(), nullable=False),
        sa.Column("outcome_index", sa.Integer()),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("liquidity_role", sa.Text()),
        sa.Column("price", sa.Numeric(20, 12), nullable=False),
        sa.Column("size", sa.Numeric(38, 12), nullable=False),
        sa.Column("notional_usdc", sa.Numeric(38, 12), nullable=False),
        sa.Column("fee_usdc", sa.Numeric(38, 12)),
        sa.Column("trade_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("transaction_hash", sa.Text()),
        sa.Column("log_index", sa.BigInteger()),
        sa.Column("block_number", sa.BigInteger()),
        sa.Column("source_priority", sa.SmallInteger()),
        sa.Column("source_confidence", sa.Numeric(8, 4)),
        sa.Column("is_reconciled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_trades_wallet_time", "trades", ["wallet_address", sa.text("trade_at DESC")])
    op.create_index("ix_trades_market_time", "trades", ["market_id", sa.text("trade_at DESC")])
    op.create_index("ix_trades_token_time", "trades", ["token_id", sa.text("trade_at DESC")])
    op.create_index("ix_trades_tx", "trades", ["transaction_hash"])
    op.create_index("ix_trades_time", "trades", [sa.text("trade_at DESC")])

    op.create_table(
        "positions_current",
        sa.Column("wallet_address", sa.Text(), sa.ForeignKey("wallets.address"), primary_key=True),
        sa.Column("token_id", sa.Text(), primary_key=True),
        sa.Column("market_id", sa.Text(), nullable=False),
        sa.Column("outcome_index", sa.Integer()),
        sa.Column("size", sa.Numeric(38, 12), nullable=False),
        sa.Column("avg_price", sa.Numeric(20, 12)),
        sa.Column("current_price", sa.Numeric(20, 12)),
        sa.Column("notional_usdc", sa.Numeric(38, 12)),
        sa.Column("unrealized_pnl", sa.Numeric(38, 12)),
        sa.Column("source_id", sa.SmallInteger()),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("raw_data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "position_deltas",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("wallet_address", sa.Text(), nullable=False),
        sa.Column("token_id", sa.Text(), nullable=False),
        sa.Column("market_id", sa.Text(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("size_delta", sa.Numeric(38, 12), nullable=False),
        sa.Column("notional_delta", sa.Numeric(38, 12), nullable=False),
        sa.Column("previous_size", sa.Numeric(38, 12), nullable=False),
        sa.Column("current_size", sa.Numeric(38, 12), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "wallet_metrics",
        sa.Column("wallet_address", sa.Text(), sa.ForeignKey("wallets.address"), primary_key=True),
        sa.Column("window_days", sa.Integer(), primary_key=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("trade_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("realized_pnl", sa.Numeric(38, 12), nullable=False, server_default="0"),
        sa.Column("volume", sa.Numeric(38, 12), nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Numeric(8, 4)),
        sa.Column("profit_factor", sa.Numeric(8, 4)),
        sa.Column("max_drawdown", sa.Numeric(38, 12)),
        sa.Column("positive_month_ratio", sa.Numeric(8, 4)),
        sa.Column("pnl_trend_r2", sa.Numeric(8, 4)),
        sa.Column("quality_score", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("risk_score", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("copyability_score", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("model_version", sa.Text(), nullable=False, server_default="v1"),
    )

    op.create_table(
        "wallet_classifications",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("wallet_address", sa.Text(), sa.ForeignKey("wallets.address"), nullable=False),
        sa.Column("classified_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("primary_label", sa.Text(), nullable=False),
        sa.Column("secondary_labels", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("category_expertise", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("confidence", sa.Numeric(8, 4), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("model_version", sa.Text(), nullable=False, server_default="rules-v1"),
    )

    op.create_table(
        "inferred_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("wallet_address", sa.Text(), sa.ForeignKey("wallets.address"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("rule_type", sa.Text(), nullable=False),
        sa.Column("rule_text", sa.Text(), nullable=False),
        sa.Column("precision", sa.Numeric(8, 4)),
        sa.Column("recall", sa.Numeric(8, 4)),
        sa.Column("profit_factor", sa.Numeric(8, 4)),
        sa.Column("out_of_sample_roi", sa.Numeric(8, 4)),
        sa.Column("confidence", sa.Numeric(8, 4), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "signals",
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("market_id", sa.Text(), nullable=False),
        sa.Column("token_id", sa.Text(), nullable=False),
        sa.Column("signal_type", sa.Text(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("score", sa.Numeric(8, 4), nullable=False),
        sa.Column("copyability_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("weighted_entry_price", sa.Numeric(20, 12)),
        sa.Column("current_price", sa.Numeric(20, 12)),
        sa.Column("price_drift", sa.Numeric(20, 12)),
        sa.Column("liquidity", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("participant_summary", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("risk_flags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("dedupe_key", sa.Text(), nullable=False, unique=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True)),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("dedupe_key", sa.Text(), nullable=False, unique=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in [
        "notifications",
        "signals",
        "inferred_rules",
        "wallet_classifications",
        "wallet_metrics",
        "position_deltas",
        "positions_current",
        "trades",
        "wallet_discovery_events",
        "wallets",
        "market_outcomes",
        "markets",
        "events",
        "raw_payloads",
        "ingestion_cursors",
        "ingestion_runs",
        "data_sources",
    ]:
        op.drop_table(table)

