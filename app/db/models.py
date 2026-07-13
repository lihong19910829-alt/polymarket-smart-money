import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import Money, Price, Score


class WalletStatus(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    DATA_PENDING = "DATA_PENDING"
    OBSERVATION = "OBSERVATION"
    QUALIFIED = "QUALIFIED"
    HIGH_QUALITY = "HIGH_QUALITY"
    DORMANT = "DORMANT"
    LOW_QUALITY = "LOW_QUALITY"
    EXCLUDED = "EXCLUDED"
    DATA_ERROR = "DATA_ERROR"


class Tier(str, enum.Enum):
    S = "S"
    A = "A"
    B = "B"
    C = "C"
    OBSERVATION = "OBSERVATION"
    LOW_QUALITY = "LOW_QUALITY"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DataSource(Base, TimestampMixin):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    source_kind: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_health_status: Mapped[str | None] = mapped_column(Text)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"))
    scope_type: Mapped[str | None] = mapped_column(Text)
    scope_key: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="RUNNING")
    cursor_before: Mapped[dict | None] = mapped_column(JSONB)
    cursor_after: Mapped[dict | None] = mapped_column(JSONB)
    rows_read: Mapped[int] = mapped_column(BigInteger, default=0)
    rows_inserted: Mapped[int] = mapped_column(BigInteger, default=0)
    rows_updated: Mapped[int] = mapped_column(BigInteger, default=0)
    rows_rejected: Mapped[int] = mapped_column(BigInteger, default=0)
    http_requests: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_class: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)


Index("ix_ingestion_runs_job_started", IngestionRun.job_name, IngestionRun.started_at.desc())
Index("ix_ingestion_runs_status_started", IngestionRun.status, IngestionRun.started_at.desc())
Index("ix_ingestion_runs_scope_started", IngestionRun.scope_type, IngestionRun.scope_key, IngestionRun.started_at.desc())


class IngestionCursor(Base):
    __tablename__ = "ingestion_cursors"

    job_name: Mapped[str] = mapped_column(Text, primary_key=True)
    source_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    scope_key: Mapped[str] = mapped_column(Text, primary_key=True)
    cursor: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class RawPayload(Base):
    __tablename__ = "raw_payloads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"))
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    request_params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | list] = mapped_column(JSONB, nullable=False)
    object_storage_uri: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


Index("ix_raw_payloads_content_hash", RawPayload.content_hash)
Index("ix_raw_payloads_request_fingerprint", RawPayload.request_fingerprint)


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_key: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


Index("ix_data_quality_entity", DataQualityIssue.entity_type, DataQualityIssue.entity_key)
Index("ix_data_quality_open", DataQualityIssue.severity, DataQualityIssue.detected_at.desc())


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    slug: Mapped[str | None] = mapped_column(Text, unique=True)
    title: Mapped[str | None] = mapped_column(Text)
    subtitle: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    series_id: Mapped[str | None] = mapped_column(Text)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool | None] = mapped_column(Boolean)
    closed: Mapped[bool | None] = mapped_column(Boolean)
    archived: Mapped[bool | None] = mapped_column(Boolean)
    restricted: Mapped[bool | None] = mapped_column(Boolean)
    volume: Mapped[Decimal | None] = mapped_column(Money)
    liquidity: Mapped[Decimal | None] = mapped_column(Money)
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Market(Base, TimestampMixin):
    __tablename__ = "markets"

    market_id: Mapped[str] = mapped_column(Text, primary_key=True)
    condition_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.event_id"))
    slug: Mapped[str | None] = mapped_column(Text)
    question: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    resolution_source: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    market_type: Mapped[str | None] = mapped_column(Text)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool | None] = mapped_column(Boolean)
    closed: Mapped[bool | None] = mapped_column(Boolean)
    archived: Mapped[bool | None] = mapped_column(Boolean)
    restricted: Mapped[bool | None] = mapped_column(Boolean)
    negative_risk: Mapped[bool | None] = mapped_column(Boolean)
    enable_order_book: Mapped[bool | None] = mapped_column(Boolean)
    resolution_status: Mapped[str | None] = mapped_column(Text)
    resolved_outcome_index: Mapped[int | None] = mapped_column(Integer)
    market_maker_address: Mapped[str | None] = mapped_column(Text)
    min_tick_size: Mapped[Decimal | None] = mapped_column(Price)
    min_order_size: Mapped[Decimal | None] = mapped_column(Money)
    fee_rate: Mapped[Decimal | None] = mapped_column(Price)
    volume_total: Mapped[Decimal | None] = mapped_column(Money)
    volume_24h: Mapped[Decimal | None] = mapped_column(Money)
    volume_7d: Mapped[Decimal | None] = mapped_column(Money)
    volume_30d: Mapped[Decimal | None] = mapped_column(Money)
    liquidity: Mapped[Decimal | None] = mapped_column(Money)
    open_interest: Mapped[Decimal | None] = mapped_column(Money)
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    source_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcomes: Mapped[list["MarketOutcome"]] = relationship(back_populates="market")


Index("ix_markets_active_closed_volume", Market.active, Market.closed, Market.volume_24h.desc())
Index("ix_markets_event_id", Market.event_id)
Index("ix_markets_end_at", Market.end_at)
Index("ix_markets_category", Market.category)
Index("ix_markets_condition_id", Market.condition_id)


class MarketOutcome(Base, TimestampMixin):
    __tablename__ = "market_outcomes"
    __table_args__ = (UniqueConstraint("market_id", "outcome_index", name="uq_market_outcome_index"),)

    token_id: Mapped[str] = mapped_column(Text, primary_key=True)
    market_id: Mapped[str] = mapped_column(ForeignKey("markets.market_id"), nullable=False)
    condition_id: Mapped[str] = mapped_column(Text, nullable=False)
    outcome_index: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome_name: Mapped[str] = mapped_column(Text, nullable=False)
    opposite_token_id: Mapped[str | None] = mapped_column(Text)
    current_price: Mapped[Decimal | None] = mapped_column(Price)
    resolved: Mapped[bool | None] = mapped_column(Boolean)
    winning: Mapped[bool | None] = mapped_column(Boolean)
    payout: Mapped[Decimal | None] = mapped_column(Price)
    market: Mapped[Market] = relationship(back_populates="outcomes")


class MarketStateSnapshot(Base):
    __tablename__ = "market_state_snapshots"

    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    token_id: Mapped[str] = mapped_column(Text, primary_key=True)
    market_id: Mapped[str] = mapped_column(Text, nullable=False)
    last_price: Mapped[Decimal | None] = mapped_column(Price)
    mid_price: Mapped[Decimal | None] = mapped_column(Price)
    best_bid: Mapped[Decimal | None] = mapped_column(Price)
    best_ask: Mapped[Decimal | None] = mapped_column(Price)
    spread_abs: Mapped[Decimal | None] = mapped_column(Price)
    spread_bps: Mapped[Decimal | None] = mapped_column(Score)
    bid_depth_1c: Mapped[Decimal | None] = mapped_column(Money)
    ask_depth_1c: Mapped[Decimal | None] = mapped_column(Money)
    bid_depth_5c: Mapped[Decimal | None] = mapped_column(Money)
    ask_depth_5c: Mapped[Decimal | None] = mapped_column(Money)
    bid_depth_10c: Mapped[Decimal | None] = mapped_column(Money)
    ask_depth_10c: Mapped[Decimal | None] = mapped_column(Money)
    volume_5m: Mapped[Decimal | None] = mapped_column(Money)
    volume_1h: Mapped[Decimal | None] = mapped_column(Money)
    volume_24h: Mapped[Decimal | None] = mapped_column(Money)
    open_interest: Mapped[Decimal | None] = mapped_column(Money)
    return_5m: Mapped[Decimal | None] = mapped_column(Price)
    return_15m: Mapped[Decimal | None] = mapped_column(Price)
    return_1h: Mapped[Decimal | None] = mapped_column(Price)
    return_24h: Mapped[Decimal | None] = mapped_column(Price)
    realized_vol_1h: Mapped[Decimal | None] = mapped_column(Price)
    realized_vol_24h: Mapped[Decimal | None] = mapped_column(Price)
    seconds_to_resolution: Mapped[int | None] = mapped_column(BigInteger)
    data_quality_score: Mapped[Decimal | None] = mapped_column(Score)
    source_id: Mapped[int | None] = mapped_column(SmallInteger)


Index("ix_market_snapshots_market_time", MarketStateSnapshot.market_id, MarketStateSnapshot.snapshot_at.desc())


class OrderbookLevel(Base):
    __tablename__ = "orderbook_levels"

    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    token_id: Mapped[str] = mapped_column(Text, primary_key=True)
    side: Mapped[str] = mapped_column(Text, primary_key=True)
    level_no: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    price: Mapped[Decimal] = mapped_column(Price, nullable=False)
    size: Mapped[Decimal] = mapped_column(Money, nullable=False)
    source_sequence: Mapped[str | None] = mapped_column(Text)


Index("ix_orderbook_token_time", OrderbookLevel.token_id, OrderbookLevel.snapshot_at.desc())


class Wallet(Base, TimestampMixin):
    __tablename__ = "wallets"

    address: Mapped[str] = mapped_column(Text, primary_key=True)
    normalized_address: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    profile_name: Mapped[str | None] = mapped_column(Text)
    pseudonym: Mapped[str | None] = mapped_column(Text)
    bio: Mapped[str | None] = mapped_column(Text)
    x_username: Mapped[str | None] = mapped_column(Text)
    profile_image: Mapped[str | None] = mapped_column(Text)
    verified_badge: Mapped[bool | None] = mapped_column(Boolean)
    profile_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    first_trade_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_trade_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active_span_days: Mapped[int | None] = mapped_column(Integer)
    current_status: Mapped[str] = mapped_column(Text, nullable=False, default=WalletStatus.DISCOVERED.value)
    current_tier: Mapped[str] = mapped_column(Text, nullable=False, default=Tier.INSUFFICIENT_DATA.value)
    identity_cluster_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    data_completeness: Mapped[Decimal | None] = mapped_column(Score)
    excluded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    exclusion_reason: Mapped[str | None] = mapped_column(Text)
    manual_notes: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class WalletDiscoveryEvent(Base):
    __tablename__ = "wallet_discovery_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    wallet_address: Mapped[str] = mapped_column(ForeignKey("wallets.address"), nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    discovery_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[int | None] = mapped_column(SmallInteger)
    category: Mapped[str | None] = mapped_column(Text)
    time_period: Mapped[str | None] = mapped_column(Text)
    order_by: Mapped[str | None] = mapped_column(Text)
    rank: Mapped[int | None] = mapped_column(Integer)
    reported_pnl: Mapped[Decimal | None] = mapped_column(Money)
    reported_volume: Mapped[Decimal | None] = mapped_column(Money)
    market_id: Mapped[str | None] = mapped_column(Text)
    token_id: Mapped[str | None] = mapped_column(Text)
    holder_amount: Mapped[Decimal | None] = mapped_column(Money)
    transaction_hash: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)


Index("ix_wallet_discovery_address_time", WalletDiscoveryEvent.wallet_address, WalletDiscoveryEvent.discovered_at.desc())
Index(
    "uq_wallet_discovery_observation",
    WalletDiscoveryEvent.wallet_address,
    WalletDiscoveryEvent.discovery_type,
    WalletDiscoveryEvent.category,
    WalletDiscoveryEvent.time_period,
    WalletDiscoveryEvent.order_by,
    WalletDiscoveryEvent.market_id,
    WalletDiscoveryEvent.token_id,
    WalletDiscoveryEvent.discovered_at,
    unique=True,
)


class IdentityCluster(Base, TimestampMixin):
    __tablename__ = "identity_clusters"

    cluster_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_label: Mapped[str | None] = mapped_column(Text)
    cluster_confidence: Mapped[Decimal] = mapped_column(Score, nullable=False)
    cluster_method: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class IdentityClusterMember(Base):
    __tablename__ = "identity_cluster_members"

    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_clusters.cluster_id"), primary_key=True
    )
    wallet_address: Mapped[str] = mapped_column(ForeignKey("wallets.address"), primary_key=True)
    confidence: Mapped[Decimal] = mapped_column(Score, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class TradeRaw(Base):
    __tablename__ = "trades_raw"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[int | None] = mapped_column(SmallInteger)
    source_trade_key: Mapped[str | None] = mapped_column(Text)
    wallet_address: Mapped[str | None] = mapped_column(Text)
    condition_id: Mapped[str | None] = mapped_column(Text)
    market_id: Mapped[str | None] = mapped_column(Text)
    token_id: Mapped[str | None] = mapped_column(Text)
    outcome_index: Mapped[int | None] = mapped_column(Integer)
    side: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal | None] = mapped_column(Price)
    size: Mapped[Decimal | None] = mapped_column(Money)
    usdc_size: Mapped[Decimal | None] = mapped_column(Money)
    fee: Mapped[Decimal | None] = mapped_column(Money)
    trade_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transaction_hash: Mapped[str | None] = mapped_column(Text)
    log_index: Mapped[int | None] = mapped_column(BigInteger)
    block_number: Mapped[int | None] = mapped_column(BigInteger)
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


Index("ix_trades_raw_source_key", TradeRaw.source_id, TradeRaw.source_trade_key)
Index("ix_trades_raw_tx_log", TradeRaw.transaction_hash, TradeRaw.log_index)


class Trade(Base):
    __tablename__ = "trades"

    trade_uid: Mapped[str] = mapped_column(Text, primary_key=True)
    wallet_address: Mapped[str] = mapped_column(ForeignKey("wallets.address"), nullable=False)
    market_id: Mapped[str | None] = mapped_column(Text)
    condition_id: Mapped[str] = mapped_column(Text, nullable=False)
    token_id: Mapped[str] = mapped_column(Text, nullable=False)
    outcome_index: Mapped[int | None] = mapped_column(Integer)
    side: Mapped[str] = mapped_column(Text, nullable=False)
    liquidity_role: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Price, nullable=False)
    size: Mapped[Decimal] = mapped_column(Money, nullable=False)
    notional_usdc: Mapped[Decimal] = mapped_column(Money, nullable=False)
    fee_usdc: Mapped[Decimal | None] = mapped_column(Money)
    trade_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    transaction_hash: Mapped[str | None] = mapped_column(Text)
    log_index: Mapped[int | None] = mapped_column(BigInteger)
    block_number: Mapped[int | None] = mapped_column(BigInteger)
    source_priority: Mapped[int | None] = mapped_column(SmallInteger)
    source_confidence: Mapped[Decimal | None] = mapped_column(Score)
    is_reconciled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


Index("ix_trades_wallet_time", Trade.wallet_address, Trade.trade_at.desc())
Index("ix_trades_market_time", Trade.market_id, Trade.trade_at.desc())
Index("ix_trades_token_time", Trade.token_id, Trade.trade_at.desc())
Index("ix_trades_tx", Trade.transaction_hash)
Index("ix_trades_time", Trade.trade_at.desc())


class WalletActivity(Base):
    __tablename__ = "wallet_activities"

    activity_uid: Mapped[str] = mapped_column(Text, primary_key=True)
    wallet_address: Mapped[str] = mapped_column(Text, nullable=False)
    activity_type: Mapped[str] = mapped_column(Text, nullable=False)
    market_id: Mapped[str | None] = mapped_column(Text)
    condition_id: Mapped[str | None] = mapped_column(Text)
    token_id: Mapped[str | None] = mapped_column(Text)
    side: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal | None] = mapped_column(Price)
    size: Mapped[Decimal | None] = mapped_column(Money)
    usdc_size: Mapped[Decimal | None] = mapped_column(Money)
    activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    transaction_hash: Mapped[str | None] = mapped_column(Text)
    log_index: Mapped[int | None] = mapped_column(BigInteger)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)


Index("ix_wallet_activities_wallet_time", WalletActivity.wallet_address, WalletActivity.activity_at.desc())
Index("ix_wallet_activities_market_time", WalletActivity.market_id, WalletActivity.activity_at.desc())


class PositionCurrent(Base, TimestampMixin):
    __tablename__ = "positions_current"

    wallet_address: Mapped[str] = mapped_column(ForeignKey("wallets.address"), primary_key=True)
    token_id: Mapped[str] = mapped_column(Text, primary_key=True)
    market_id: Mapped[str] = mapped_column(Text, nullable=False)
    outcome_index: Mapped[int | None] = mapped_column(Integer)
    size: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)
    avg_price: Mapped[Decimal | None] = mapped_column(Price)
    current_price: Mapped[Decimal | None] = mapped_column(Price)
    notional_usdc: Mapped[Decimal | None] = mapped_column(Money)
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(Money)
    source_id: Mapped[int | None] = mapped_column(SmallInteger)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class PositionDelta(Base):
    __tablename__ = "position_deltas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    wallet_address: Mapped[str] = mapped_column(Text, nullable=False)
    token_id: Mapped[str] = mapped_column(Text, nullable=False)
    market_id: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    side: Mapped[str] = mapped_column(Text, nullable=False)
    size_delta: Mapped[Decimal] = mapped_column(Money, nullable=False)
    notional_delta: Mapped[Decimal] = mapped_column(Money, nullable=False)
    previous_size: Mapped[Decimal] = mapped_column(Money, nullable=False)
    current_size: Mapped[Decimal] = mapped_column(Money, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class WalletMetric(Base):
    __tablename__ = "wallet_metrics"

    wallet_address: Mapped[str] = mapped_column(ForeignKey("wallets.address"), primary_key=True)
    window_days: Mapped[int] = mapped_column(Integer, primary_key=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    trade_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    realized_pnl: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)
    volume: Mapped[Decimal] = mapped_column(Money, nullable=False, default=0)
    win_rate: Mapped[Decimal | None] = mapped_column(Score)
    profit_factor: Mapped[Decimal | None] = mapped_column(Score)
    max_drawdown: Mapped[Decimal | None] = mapped_column(Money)
    positive_month_ratio: Mapped[Decimal | None] = mapped_column(Score)
    pnl_trend_r2: Mapped[Decimal | None] = mapped_column(Score)
    quality_score: Mapped[Decimal] = mapped_column(Score, nullable=False, default=0)
    risk_score: Mapped[Decimal] = mapped_column(Score, nullable=False, default=0)
    copyability_score: Mapped[Decimal] = mapped_column(Score, nullable=False, default=0)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    model_version: Mapped[str] = mapped_column(Text, nullable=False, default="v1")


class WalletClassification(Base):
    __tablename__ = "wallet_classifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    wallet_address: Mapped[str] = mapped_column(ForeignKey("wallets.address"), nullable=False)
    classified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    primary_label: Mapped[str] = mapped_column(Text, nullable=False)
    secondary_labels: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    category_expertise: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    confidence: Mapped[Decimal] = mapped_column(Score, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    model_version: Mapped[str] = mapped_column(Text, nullable=False, default="rules-v1")


class InferredRule(Base):
    __tablename__ = "inferred_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_address: Mapped[str] = mapped_column(ForeignKey("wallets.address"), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    rule_type: Mapped[str] = mapped_column(Text, nullable=False)
    rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    precision: Mapped[Decimal | None] = mapped_column(Score)
    recall: Mapped[Decimal | None] = mapped_column(Score)
    profit_factor: Mapped[Decimal | None] = mapped_column(Score)
    out_of_sample_roi: Mapped[Decimal | None] = mapped_column(Score)
    confidence: Mapped[Decimal] = mapped_column(Score, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class Signal(Base, TimestampMixin):
    __tablename__ = "signals"

    signal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_id: Mapped[str] = mapped_column(Text, nullable=False)
    token_id: Mapped[str] = mapped_column(Text, nullable=False)
    signal_type: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[Decimal] = mapped_column(Score, nullable=False)
    copyability_score: Mapped[Decimal] = mapped_column(Score, nullable=False)
    weighted_entry_price: Mapped[Decimal | None] = mapped_column(Price)
    current_price: Mapped[Decimal | None] = mapped_column(Price)
    price_drift: Mapped[Decimal | None] = mapped_column(Price)
    liquidity: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    participant_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    risk_flags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    dedupe_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="OPEN")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING")
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_name: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    train_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    train_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    test_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    test_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assumptions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING")


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    backtest_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("backtest_runs.id"))
    market_id: Mapped[str] = mapped_column(Text, nullable=False)
    token_id: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    signal_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    entry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    entry_price: Mapped[Decimal | None] = mapped_column(Price)
    exit_price: Mapped[Decimal | None] = mapped_column(Price)
    size: Mapped[Decimal | None] = mapped_column(Money)
    pnl: Mapped[Decimal | None] = mapped_column(Money)
    fees: Mapped[Decimal | None] = mapped_column(Money)
    slippage: Mapped[Decimal | None] = mapped_column(Money)
    capacity_used: Mapped[Decimal | None] = mapped_column(Money)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
