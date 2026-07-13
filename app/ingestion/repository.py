from collections.abc import Iterable
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import (
    Market,
    MarketOutcome,
    MarketStateSnapshot,
    OrderbookLevel,
    PositionCurrent,
    Trade,
    Wallet,
    WalletActivity,
    WalletDiscoveryEvent,
)
from app.ingestion.normalizers import decimal_or_zero
from app.utils.ids import normalize_address
from app.utils.time import utc_now


def upsert_wallet(session: Session, address: str, metadata: dict[str, Any] | None = None) -> None:
    normalized = normalize_address(address)
    if not normalized:
        return
    stmt = insert(Wallet).values(
        address=normalized,
        normalized_address=normalized,
        first_seen_at=utc_now(),
        last_seen_at=utc_now(),
        metadata_json=metadata or {},
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[Wallet.address],
        set_={"last_seen_at": utc_now(), "updated_at": utc_now()},
    )
    session.execute(stmt)


def upsert_markets(session: Session, markets: Iterable[dict[str, Any]]) -> int:
    count = 0
    for values in markets:
        stmt = insert(Market).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Market.market_id],
            set_={key: value for key, value in values.items() if key != "market_id"} | {"updated_at": utc_now()},
        )
        session.execute(stmt)
        count += 1
    return count


def upsert_outcomes(session: Session, outcomes: Iterable[dict[str, Any]]) -> int:
    count = 0
    for values in outcomes:
        stmt = insert(MarketOutcome).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[MarketOutcome.token_id],
            set_={key: value for key, value in values.items() if key != "token_id"} | {"updated_at": utc_now()},
        )
        session.execute(stmt)
        count += 1
    return count


def record_discovery(session: Session, address: str, discovery_type: str, **values: Any) -> None:
    normalized = normalize_address(address)
    if not normalized:
        return
    upsert_wallet(session, normalized)
    session.add(WalletDiscoveryEvent(wallet_address=normalized, discovery_type=discovery_type, **values))


def upsert_trades(session: Session, trades: Iterable[dict[str, Any]]) -> int:
    count = 0
    for values in trades:
        upsert_wallet(session, values["wallet_address"])
        stmt = insert(Trade).values(**values)
        stmt = stmt.on_conflict_do_nothing(index_elements=[Trade.trade_uid])
        result = session.execute(stmt)
        count += result.rowcount or 0
    return count


def upsert_activities(session: Session, activities: Iterable[dict[str, Any]]) -> int:
    count = 0
    for values in activities:
        upsert_wallet(session, values["wallet_address"])
        stmt = insert(WalletActivity).values(**values)
        stmt = stmt.on_conflict_do_nothing(index_elements=[WalletActivity.activity_uid])
        result = session.execute(stmt)
        count += result.rowcount or 0
    return count


def upsert_positions(session: Session, wallet: str, rows: Iterable[dict[str, Any]], source_id: int = 2) -> int:
    count = 0
    normalized = normalize_address(wallet)
    if not normalized:
        return 0
    upsert_wallet(session, normalized)
    for row in rows:
        token_id = str(row.get("asset") or row.get("tokenId") or row.get("token_id") or "")
        market_id = str(row.get("market") or row.get("marketId") or "")
        if not token_id or not market_id:
            continue
        size = decimal_or_zero(row.get("size") or row.get("amount"))
        values = {
            "wallet_address": normalized,
            "token_id": token_id,
            "market_id": market_id,
            "outcome_index": row.get("outcomeIndex"),
            "size": size,
            "avg_price": decimal_or_zero(row.get("avgPrice")) if row.get("avgPrice") is not None else None,
            "current_price": decimal_or_zero(row.get("curPrice")) if row.get("curPrice") is not None else None,
            "notional_usdc": decimal_or_zero(row.get("currentValue") or row.get("value")),
            "unrealized_pnl": decimal_or_zero(row.get("cashPnl") or row.get("unrealizedPnl")),
            "source_id": source_id,
            "fetched_at": utc_now(),
            "raw_data": row,
        }
        stmt = insert(PositionCurrent).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[PositionCurrent.wallet_address, PositionCurrent.token_id],
            set_={key: value for key, value in values.items() if key not in {"wallet_address", "token_id"}}
            | {"updated_at": utc_now()},
        )
        session.execute(stmt)
        count += 1
    return count


def insert_market_snapshot(session: Session, values: dict[str, Any]) -> None:
    stmt = insert(MarketStateSnapshot).values(**values)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=[MarketStateSnapshot.snapshot_at, MarketStateSnapshot.token_id]
    )
    session.execute(stmt)


def insert_orderbook_levels(session: Session, rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    for values in rows:
        stmt = insert(OrderbookLevel).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                OrderbookLevel.snapshot_at,
                OrderbookLevel.token_id,
                OrderbookLevel.side,
                OrderbookLevel.level_no,
            ],
            set_={"price": values["price"], "size": values["size"], "source_sequence": values.get("source_sequence")},
        )
        session.execute(stmt)
        count += 1
    return count
