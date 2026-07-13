from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.utils.time import utc_now


@dataclass(frozen=True)
class QualityIssue:
    issue_type: str
    severity: str
    entity_type: str
    entity_key: str
    details: dict[str, Any]


def validate_price(value: Decimal | None, *, entity_type: str, entity_key: str) -> list[QualityIssue]:
    if value is None:
        return [
            QualityIssue("MISSING_PRICE", "WARN", entity_type, entity_key, {"message": "price is null"})
        ]
    if value < 0 or value > 1:
        return [
            QualityIssue(
                "PRICE_OUT_OF_RANGE",
                "ERROR",
                entity_type,
                entity_key,
                {"price": str(value), "expected": "0 <= price <= 1"},
            )
        ]
    return []


def validate_non_negative(
    value: Decimal | None,
    *,
    field_name: str,
    entity_type: str,
    entity_key: str,
) -> list[QualityIssue]:
    if value is not None and value < 0:
        return [
            QualityIssue(
                "NEGATIVE_VALUE",
                "ERROR",
                entity_type,
                entity_key,
                {"field": field_name, "value": str(value)},
            )
        ]
    return []


def validate_timestamp_not_future(
    value: datetime | None,
    *,
    entity_type: str,
    entity_key: str,
) -> list[QualityIssue]:
    if value is not None and value > utc_now():
        return [
            QualityIssue(
                "FUTURE_TIMESTAMP",
                "ERROR",
                entity_type,
                entity_key,
                {"timestamp": value.isoformat()},
            )
        ]
    return []


def validate_trade_record(row: dict[str, Any]) -> list[QualityIssue]:
    key = str(row.get("trade_uid") or row.get("source_trade_key") or "unknown")
    issues: list[QualityIssue] = []
    if not row.get("token_id"):
        issues.append(QualityIssue("MISSING_TOKEN", "ERROR", "trade", key, {}))
    if not row.get("wallet_address"):
        issues.append(QualityIssue("MISSING_WALLET", "ERROR", "trade", key, {}))
    issues.extend(validate_price(row.get("price"), entity_type="trade", entity_key=key))
    issues.extend(
        validate_non_negative(
            row.get("size"),
            field_name="size",
            entity_type="trade",
            entity_key=key,
        )
    )
    issues.extend(
        validate_non_negative(
            row.get("notional_usdc") or row.get("usdc_size"),
            field_name="notional_usdc",
            entity_type="trade",
            entity_key=key,
        )
    )
    issues.extend(
        validate_timestamp_not_future(row.get("trade_at"), entity_type="trade", entity_key=key)
    )
    return issues


def completeness_score(total_fields: int, missing_fields: int) -> Decimal:
    if total_fields <= 0:
        return Decimal("0")
    present = max(total_fields - missing_fields, 0)
    return (Decimal(present) / Decimal(total_fields)).quantize(Decimal("0.0001"))

