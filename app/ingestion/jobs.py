from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MarketOutcome
from app.ingestion.normalizers import (
    decimal_or_none,
    normalize_activity,
    normalize_market,
    normalize_outcomes,
    normalize_trade,
)
from app.ingestion.repository import (
    insert_market_snapshot,
    insert_orderbook_levels,
    record_discovery,
    upsert_activities,
    upsert_markets,
    upsert_outcomes,
    upsert_positions,
    upsert_trades,
)
from app.sources.clob import ClobClient
from app.sources.data_api import (
    LEADERBOARD_CATEGORIES,
    LEADERBOARD_ORDER_BY,
    LEADERBOARD_PERIODS,
    DataApiClient,
)
from app.sources.gamma import GammaClient


async def sync_gamma_markets(session: Session, *, active: bool | None = True, max_pages: int = 5) -> int:
    client = GammaClient()
    total = 0
    for page in range(max_pages):
        rows = await client.markets(limit=500, offset=page * 500, active=active)
        if not rows:
            break
        markets = [normalize_market(row) for row in rows]
        outcomes = [outcome for row in rows for outcome in normalize_outcomes(row)]
        total += upsert_markets(session, markets)
        upsert_outcomes(session, outcomes)
        session.commit()
        if len(rows) < 500:
            break
    return total


async def discover_leaderboard_wallets(session: Session, *, max_pages: int = 1) -> int:
    client = DataApiClient()
    total = 0
    for category in LEADERBOARD_CATEGORIES:
        for period in LEADERBOARD_PERIODS:
            for order_by in LEADERBOARD_ORDER_BY:
                for page in range(max_pages):
                    rows = await client.leaderboard(
                        category=category, time_period=period, order_by=order_by, limit=100, offset=page * 100
                    )
                    if not rows:
                        break
                    for idx, row in enumerate(rows, start=page * 100 + 1):
                        wallet = row.get("proxyWallet") or row.get("wallet") or row.get("address") or row.get("user")
                        if not wallet:
                            continue
                        record_discovery(
                            session,
                            wallet,
                            "LEADERBOARD",
                            source_id=2,
                            category=category,
                            time_period=period,
                            order_by=order_by,
                            rank=row.get("rank") or idx,
                            reported_pnl=row.get("pnl"),
                            reported_volume=row.get("volume"),
                            metadata_json=row,
                        )
                        total += 1
                    session.commit()
    return total


async def discover_holder_wallets(session: Session, *, max_tokens: int = 250) -> int:
    client = DataApiClient()
    tokens = session.scalars(select(MarketOutcome.token_id).limit(max_tokens)).all()
    total = 0
    for token_id in tokens:
        rows = await client.holders(token_id)
        for idx, row in enumerate(rows, start=1):
            wallet = row.get("proxyWallet") or row.get("wallet") or row.get("address") or row.get("user")
            if not wallet:
                continue
            record_discovery(
                session,
                wallet,
                "HOLDER",
                source_id=2,
                token_id=token_id,
                rank=row.get("rank") or idx,
                holder_amount=row.get("amount") or row.get("balance"),
                metadata_json=row,
            )
            total += 1
        session.commit()
    return total


async def backfill_market_trades(session: Session, market_id: str | None, *, days: int = 1) -> int:
    client = DataApiClient()
    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    total = 0
    async for _, _, rows, _complete in client.recursive_trades(market=market_id, start=start, end=end):
        trades = [trade for row in rows if (trade := normalize_trade(row))]
        total += upsert_trades(session, trades)
        session.commit()
    return total


async def refresh_wallet_positions(session: Session, wallet: str) -> int:
    client = DataApiClient()
    rows = await client.positions(wallet)
    inserted = upsert_positions(session, wallet, rows)
    session.commit()
    return inserted


async def refresh_wallet_activity(session: Session, wallet: str) -> int:
    client = DataApiClient()
    rows = await client.activity(wallet)
    activities = [activity for row in rows if (activity := normalize_activity(row))]
    inserted = upsert_activities(session, activities)
    session.commit()
    return inserted


async def capture_orderbook_snapshot(session: Session, token_id: str, market_id: str) -> int:
    client = ClobClient()
    book = await client.orderbook(token_id)
    snapshot_at = datetime.now(UTC)
    bids = book.get("bids") or book.get("buy") or []
    asks = book.get("asks") or book.get("sell") or []

    def level_price(level: dict) -> Decimal | None:
        return decimal_or_none(level.get("price") or level.get("p"))

    def level_size(level: dict) -> Decimal | None:
        return decimal_or_none(level.get("size") or level.get("s"))

    best_bid = level_price(bids[0]) if bids else None
    best_ask = level_price(asks[0]) if asks else None
    spread_abs = best_ask - best_bid if best_bid is not None and best_ask is not None else None
    mid_price = (best_bid + best_ask) / Decimal("2") if best_bid is not None and best_ask is not None else None
    spread_bps = (spread_abs / mid_price * Decimal("10000")) if spread_abs is not None and mid_price else None
    insert_market_snapshot(
        session,
        {
            "snapshot_at": snapshot_at,
            "token_id": token_id,
            "market_id": market_id,
            "mid_price": mid_price,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread_abs": spread_abs,
            "spread_bps": spread_bps,
            "data_quality_score": Decimal("1.0000") if best_bid is not None and best_ask is not None else Decimal("0.5000"),
            "source_id": 3,
        },
    )
    levels = []
    for side, rows in [("BID", bids), ("ASK", asks)]:
        for idx, level in enumerate(rows[:20], start=1):
            price = level_price(level)
            size = level_size(level)
            if price is None or size is None:
                continue
            levels.append(
                {
                    "snapshot_at": snapshot_at,
                    "token_id": token_id,
                    "side": side,
                    "level_no": idx,
                    "price": price,
                    "size": size,
                    "source_sequence": str(book.get("hash") or book.get("timestamp") or ""),
                }
            )
    inserted = insert_orderbook_levels(session, levels)
    session.commit()
    return inserted
