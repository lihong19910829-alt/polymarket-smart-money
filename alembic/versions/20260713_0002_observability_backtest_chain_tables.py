"""observability, snapshots, raw activity, and backtest tables

Revision ID: 20260713_0002
Revises: 20260713_0001
Create Date: 2026-07-13 01:00:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260713_0002"
down_revision = "20260713_0001"
branch_labels = None
depends_on = None


def jsonb_default(value: str = "{}") -> sa.TextClause:
    return sa.text(f"'{value}'::jsonb")


def upgrade() -> None:
    op.create_table(
        "data_quality_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("issue_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_key", sa.Text(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default=jsonb_default()),
    )
    op.create_index("ix_data_quality_entity", "data_quality_issues", ["entity_type", "entity_key"])
    op.create_index(
        "ix_data_quality_open",
        "data_quality_issues",
        ["severity", sa.text("detected_at DESC")],
    )

    op.create_table(
        "market_state_snapshots",
        sa.Column("snapshot_at", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("token_id", sa.Text(), primary_key=True),
        sa.Column("market_id", sa.Text(), nullable=False),
        sa.Column("last_price", sa.Numeric(20, 12)),
        sa.Column("mid_price", sa.Numeric(20, 12)),
        sa.Column("best_bid", sa.Numeric(20, 12)),
        sa.Column("best_ask", sa.Numeric(20, 12)),
        sa.Column("spread_abs", sa.Numeric(20, 12)),
        sa.Column("spread_bps", sa.Numeric(8, 4)),
        sa.Column("bid_depth_1c", sa.Numeric(38, 12)),
        sa.Column("ask_depth_1c", sa.Numeric(38, 12)),
        sa.Column("bid_depth_5c", sa.Numeric(38, 12)),
        sa.Column("ask_depth_5c", sa.Numeric(38, 12)),
        sa.Column("bid_depth_10c", sa.Numeric(38, 12)),
        sa.Column("ask_depth_10c", sa.Numeric(38, 12)),
        sa.Column("volume_5m", sa.Numeric(38, 12)),
        sa.Column("volume_1h", sa.Numeric(38, 12)),
        sa.Column("volume_24h", sa.Numeric(38, 12)),
        sa.Column("open_interest", sa.Numeric(38, 12)),
        sa.Column("return_5m", sa.Numeric(20, 12)),
        sa.Column("return_15m", sa.Numeric(20, 12)),
        sa.Column("return_1h", sa.Numeric(20, 12)),
        sa.Column("return_24h", sa.Numeric(20, 12)),
        sa.Column("realized_vol_1h", sa.Numeric(20, 12)),
        sa.Column("realized_vol_24h", sa.Numeric(20, 12)),
        sa.Column("seconds_to_resolution", sa.BigInteger()),
        sa.Column("data_quality_score", sa.Numeric(8, 4)),
        sa.Column("source_id", sa.SmallInteger()),
    )
    op.create_index(
        "ix_market_snapshots_market_time",
        "market_state_snapshots",
        ["market_id", sa.text("snapshot_at DESC")],
    )

    op.create_table(
        "orderbook_levels",
        sa.Column("snapshot_at", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("token_id", sa.Text(), primary_key=True),
        sa.Column("side", sa.Text(), primary_key=True),
        sa.Column("level_no", sa.SmallInteger(), primary_key=True),
        sa.Column("price", sa.Numeric(20, 12), nullable=False),
        sa.Column("size", sa.Numeric(38, 12), nullable=False),
        sa.Column("source_sequence", sa.Text()),
    )
    op.create_index(
        "ix_orderbook_token_time",
        "orderbook_levels",
        ["token_id", sa.text("snapshot_at DESC")],
    )

    op.create_table(
        "identity_clusters",
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cluster_label", sa.Text()),
        sa.Column("cluster_confidence", sa.Numeric(8, 4), nullable=False),
        sa.Column("cluster_method", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default=jsonb_default()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "identity_cluster_members",
        sa.Column(
            "cluster_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_clusters.cluster_id"),
            primary_key=True,
        ),
        sa.Column("wallet_address", sa.Text(), sa.ForeignKey("wallets.address"), primary_key=True),
        sa.Column("confidence", sa.Numeric(8, 4), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default=jsonb_default()),
    )

    op.create_table(
        "trades_raw",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.SmallInteger()),
        sa.Column("source_trade_key", sa.Text()),
        sa.Column("wallet_address", sa.Text()),
        sa.Column("condition_id", sa.Text()),
        sa.Column("market_id", sa.Text()),
        sa.Column("token_id", sa.Text()),
        sa.Column("outcome_index", sa.Integer()),
        sa.Column("side", sa.Text()),
        sa.Column("role", sa.Text()),
        sa.Column("price", sa.Numeric(20, 12)),
        sa.Column("size", sa.Numeric(38, 12)),
        sa.Column("usdc_size", sa.Numeric(38, 12)),
        sa.Column("fee", sa.Numeric(38, 12)),
        sa.Column("trade_at", sa.DateTime(timezone=True)),
        sa.Column("transaction_hash", sa.Text()),
        sa.Column("log_index", sa.BigInteger()),
        sa.Column("block_number", sa.BigInteger()),
        sa.Column("raw_data", postgresql.JSONB(), nullable=False, server_default=jsonb_default()),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_trades_raw_source_key", "trades_raw", ["source_id", "source_trade_key"])
    op.create_index("ix_trades_raw_tx_log", "trades_raw", ["transaction_hash", "log_index"])

    op.create_table(
        "wallet_activities",
        sa.Column("activity_uid", sa.Text(), primary_key=True),
        sa.Column("wallet_address", sa.Text(), nullable=False),
        sa.Column("activity_type", sa.Text(), nullable=False),
        sa.Column("market_id", sa.Text()),
        sa.Column("condition_id", sa.Text()),
        sa.Column("token_id", sa.Text()),
        sa.Column("side", sa.Text()),
        sa.Column("price", sa.Numeric(20, 12)),
        sa.Column("size", sa.Numeric(38, 12)),
        sa.Column("usdc_size", sa.Numeric(38, 12)),
        sa.Column("activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("transaction_hash", sa.Text()),
        sa.Column("log_index", sa.BigInteger()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=jsonb_default()),
    )
    op.create_index(
        "ix_wallet_activities_wallet_time",
        "wallet_activities",
        ["wallet_address", sa.text("activity_at DESC")],
    )
    op.create_index(
        "ix_wallet_activities_market_time",
        "wallet_activities",
        ["market_id", sa.text("activity_at DESC")],
    )

    op.create_table(
        "backtest_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("strategy_name", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("train_start", sa.DateTime(timezone=True)),
        sa.Column("train_end", sa.DateTime(timezone=True)),
        sa.Column("test_start", sa.DateTime(timezone=True)),
        sa.Column("test_end", sa.DateTime(timezone=True)),
        sa.Column("assumptions", postgresql.JSONB(), nullable=False, server_default=jsonb_default()),
        sa.Column("metrics", postgresql.JSONB(), nullable=False, server_default=jsonb_default()),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
    )
    op.create_table(
        "backtest_trades",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "backtest_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("backtest_runs.id"),
        ),
        sa.Column("market_id", sa.Text(), nullable=False),
        sa.Column("token_id", sa.Text(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("signal_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entry_at", sa.DateTime(timezone=True)),
        sa.Column("exit_at", sa.DateTime(timezone=True)),
        sa.Column("entry_price", sa.Numeric(20, 12)),
        sa.Column("exit_price", sa.Numeric(20, 12)),
        sa.Column("size", sa.Numeric(38, 12)),
        sa.Column("pnl", sa.Numeric(38, 12)),
        sa.Column("fees", sa.Numeric(38, 12)),
        sa.Column("slippage", sa.Numeric(38, 12)),
        sa.Column("capacity_used", sa.Numeric(38, 12)),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default=jsonb_default()),
    )


def downgrade() -> None:
    for table in [
        "backtest_trades",
        "backtest_runs",
        "wallet_activities",
        "trades_raw",
        "identity_cluster_members",
        "identity_clusters",
        "orderbook_levels",
        "market_state_snapshots",
        "data_quality_issues",
    ]:
        op.drop_table(table)
