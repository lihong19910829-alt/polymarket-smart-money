from sqlalchemy import select

from app.analytics.data_quality import validate_trade_record
from app.db.models import DataQualityIssue, Trade
from app.db.session import SessionLocal


def main() -> None:
    inserted = 0
    with SessionLocal() as session:
        trades = session.scalars(select(Trade).limit(10000)).all()
        for trade in trades:
            issues = validate_trade_record(
                {
                    "trade_uid": trade.trade_uid,
                    "wallet_address": trade.wallet_address,
                    "token_id": trade.token_id,
                    "price": trade.price,
                    "size": trade.size,
                    "notional_usdc": trade.notional_usdc,
                    "trade_at": trade.trade_at,
                }
            )
            for issue in issues:
                session.add(
                    DataQualityIssue(
                        issue_type=issue.issue_type,
                        severity=issue.severity,
                        entity_type=issue.entity_type,
                        entity_key=issue.entity_key,
                        details=issue.details,
                    )
                )
                inserted += 1
        session.commit()
    print(f"data_quality_issues={inserted}")


if __name__ == "__main__":
    main()

