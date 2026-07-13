from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.utils.ids import normalize_address, stable_hash, trade_uid_from_parts
from app.utils.time import parse_datetime


def decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def decimal_or_zero(value: Any) -> Decimal:
    return decimal_or_none(value) or Decimal("0")


def normalize_market(row: dict[str, Any]) -> dict[str, Any]:
    market_id = str(row.get("id") or row.get("marketId") or row.get("conditionId"))
    condition_id = str(row.get("conditionId") or row.get("condition_id") or market_id)
    return {
        "market_id": market_id,
        "condition_id": condition_id,
        "event_id": str(row.get("eventId") or row.get("event_id") or "") or None,
        "slug": row.get("slug"),
        "question": row.get("question"),
        "description": row.get("description"),
        "resolution_source": row.get("resolutionSource"),
        "category": row.get("category"),
        "market_type": row.get("marketType"),
        "start_at": parse_datetime(row.get("startDate") or row.get("startDateIso")),
        "end_at": parse_datetime(row.get("endDate") or row.get("endDateIso")),
        "closed_at": parse_datetime(row.get("closedTime")),
        "active": row.get("active"),
        "closed": row.get("closed"),
        "archived": row.get("archived"),
        "restricted": row.get("restricted"),
        "negative_risk": row.get("negRisk"),
        "enable_order_book": row.get("enableOrderBook"),
        "resolution_status": row.get("resolutionStatus"),
        "market_maker_address": normalize_address(row.get("marketMakerAddress")),
        "min_tick_size": decimal_or_none(row.get("minimumTickSize") or row.get("minTickSize")),
        "min_order_size": decimal_or_none(row.get("minimumOrderSize") or row.get("minOrderSize")),
        "fee_rate": decimal_or_none(row.get("fee") or row.get("feeRate")),
        "volume_total": decimal_or_none(row.get("volume")),
        "volume_24h": decimal_or_none(row.get("volume24hr") or row.get("volume24h")),
        "volume_7d": decimal_or_none(row.get("volume7d")),
        "volume_30d": decimal_or_none(row.get("volume30d")),
        "liquidity": decimal_or_none(row.get("liquidity")),
        "open_interest": decimal_or_none(row.get("openInterest")),
        "raw_data": row,
        "source_created_at": parse_datetime(row.get("createdAt")),
        "source_updated_at": parse_datetime(row.get("updatedAt")),
    }


def normalize_outcomes(row: dict[str, Any]) -> list[dict[str, Any]]:
    market_id = str(row.get("id") or row.get("marketId") or row.get("conditionId"))
    condition_id = str(row.get("conditionId") or row.get("condition_id") or market_id)
    tokens = row.get("clobTokenIds") or row.get("tokens") or []
    outcomes = row.get("outcomes") or []
    prices = row.get("outcomePrices") or []
    if isinstance(tokens, str):
        tokens = [item.strip().strip('"') for item in tokens.strip("[]").split(",") if item.strip()]
    if isinstance(outcomes, str):
        outcomes = [item.strip().strip('"') for item in outcomes.strip("[]").split(",") if item.strip()]
    if isinstance(prices, str):
        prices = [item.strip().strip('"') for item in prices.strip("[]").split(",") if item.strip()]
    normalized = []
    for idx, token in enumerate(tokens):
        normalized.append(
            {
                "token_id": str(token),
                "market_id": market_id,
                "condition_id": condition_id,
                "outcome_index": idx,
                "outcome_name": str(outcomes[idx]) if idx < len(outcomes) else str(idx),
                "current_price": decimal_or_none(prices[idx]) if idx < len(prices) else None,
                "opposite_token_id": str(tokens[1 - idx]) if len(tokens) == 2 else None,
            }
        )
    return normalized


def normalize_trade(row: dict[str, Any], source: str = "data_api") -> dict[str, Any] | None:
    wallet = normalize_address(row.get("proxyWallet") or row.get("user") or row.get("wallet"))
    condition_id = str(row.get("conditionId") or row.get("condition_id") or "")
    token_id = str(row.get("asset") or row.get("tokenId") or row.get("token_id") or "")
    if not wallet or not condition_id or not token_id:
        return None
    price = decimal_or_zero(row.get("price"))
    size = decimal_or_zero(row.get("size") or row.get("amount"))
    side = str(row.get("side") or row.get("type") or "UNKNOWN").upper()
    trade_at_value = row.get("timestamp") or row.get("time") or row.get("createdAt")
    trade_at_dt = parse_datetime(trade_at_value) or datetime.utcnow()
    tx_hash = row.get("transactionHash") or row.get("transaction_hash")
    log_index_raw = row.get("logIndex") or row.get("log_index")
    log_index = int(log_index_raw) if log_index_raw is not None else None
    uid = trade_uid_from_parts(
        source=source,
        wallet_address=wallet,
        condition_id=condition_id,
        token_id=token_id,
        side=side,
        price=price,
        size=size,
        trade_at=trade_at_dt.isoformat(),
        transaction_hash=tx_hash,
        log_index=log_index,
    )
    return {
        "trade_uid": uid,
        "wallet_address": wallet,
        "market_id": str(row.get("market") or row.get("marketId") or "") or None,
        "condition_id": condition_id,
        "token_id": token_id,
        "outcome_index": row.get("outcomeIndex"),
        "side": side,
        "liquidity_role": row.get("role"),
        "price": price,
        "size": size,
        "notional_usdc": decimal_or_none(row.get("usdcSize")) or price * size,
        "fee_usdc": decimal_or_none(row.get("fee")),
        "trade_at": trade_at_dt,
        "transaction_hash": tx_hash,
        "log_index": log_index,
        "block_number": row.get("blockNumber"),
        "source_priority": 2,
        "source_confidence": Decimal("0.8500"),
        "is_reconciled": False,
    }


def normalize_activity(row: dict[str, Any], source: str = "data_api") -> dict[str, Any] | None:
    wallet = normalize_address(row.get("proxyWallet") or row.get("user") or row.get("wallet"))
    activity_type = str(row.get("type") or row.get("activityType") or "").upper()
    activity_at = parse_datetime(row.get("timestamp") or row.get("time") or row.get("createdAt"))
    if not wallet or not activity_type or activity_at is None:
        return None
    tx_hash = row.get("transactionHash") or row.get("transaction_hash")
    log_index = row.get("logIndex") or row.get("log_index")
    uid_parts = [
        source,
        wallet,
        activity_type,
        tx_hash,
        log_index,
        row.get("asset") or row.get("tokenId"),
        activity_at.isoformat(),
    ]
    return {
        "activity_uid": stable_hash(uid_parts),
        "wallet_address": wallet,
        "activity_type": activity_type,
        "market_id": str(row.get("market") or row.get("marketId") or "") or None,
        "condition_id": str(row.get("conditionId") or "") or None,
        "token_id": str(row.get("asset") or row.get("tokenId") or "") or None,
        "side": str(row.get("side")).upper() if row.get("side") else None,
        "price": decimal_or_none(row.get("price")),
        "size": decimal_or_none(row.get("size") or row.get("amount")),
        "usdc_size": decimal_or_none(row.get("usdcSize") or row.get("value")),
        "activity_at": activity_at,
        "transaction_hash": tx_hash,
        "log_index": int(log_index) if log_index is not None else None,
        "metadata_json": row,
    }
