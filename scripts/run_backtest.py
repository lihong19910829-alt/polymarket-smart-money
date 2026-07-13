from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.analytics.backtesting import ExecutableQuote, simulate_binary_trade, summarize_backtest


def main() -> None:
    now = datetime.now(UTC)
    trades = [
        simulate_binary_trade(
            [
                ExecutableQuote(
                    at=now + timedelta(minutes=2),
                    bid=Decimal("0.41"),
                    ask=Decimal("0.43"),
                    bid_size=Decimal("500"),
                    ask_size=Decimal("500"),
                )
            ],
            signal_at=now,
            direction="YES",
            desired_notional=Decimal("100"),
            resolved_payout=Decimal("1"),
            fee_bps=Decimal("0"),
            slippage_bps=Decimal("5"),
        )
    ]
    print(summarize_backtest(trades))


if __name__ == "__main__":
    main()

