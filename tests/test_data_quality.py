from datetime import timedelta
from decimal import Decimal

from app.analytics.data_quality import completeness_score, validate_trade_record
from app.utils.time import utc_now


def test_validate_trade_record_flags_bad_trade() -> None:
    issues = validate_trade_record(
        {
            "trade_uid": "t1",
            "wallet_address": "",
            "token_id": "",
            "price": Decimal("1.2"),
            "size": Decimal("-1"),
            "notional_usdc": Decimal("-2"),
            "trade_at": utc_now() + timedelta(minutes=1),
        }
    )
    issue_types = {issue.issue_type for issue in issues}
    assert {
        "MISSING_TOKEN",
        "MISSING_WALLET",
        "PRICE_OUT_OF_RANGE",
        "NEGATIVE_VALUE",
        "FUTURE_TIMESTAMP",
    }.issubset(issue_types)


def test_completeness_score() -> None:
    assert completeness_score(10, 2) == Decimal("0.8000")

