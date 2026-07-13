from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.analytics.backtesting import (
    ExecutableQuote,
    executable_entry,
    simulate_binary_trade,
    summarize_backtest,
)


def test_executable_entry_waits_until_after_delay() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    quotes = [
        ExecutableQuote(now, Decimal("0.4"), Decimal("0.42"), Decimal("10"), Decimal("10")),
        ExecutableQuote(
            now + timedelta(minutes=2),
            Decimal("0.41"),
            Decimal("0.43"),
            Decimal("10"),
            Decimal("10"),
        ),
    ]
    quote, size, _ = executable_entry(
        quotes,
        signal_at=now,
        direction="YES",
        delay=timedelta(minutes=1),
        desired_notional=Decimal("4.30"),
    )
    assert quote == quotes[1]
    assert size == Decimal("10")


def test_simulate_binary_trade_uses_ask_after_signal() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    trade = simulate_binary_trade(
        [
            ExecutableQuote(
                now + timedelta(minutes=1),
                Decimal("0.40"),
                Decimal("0.50"),
                Decimal("100"),
                Decimal("100"),
            )
        ],
        signal_at=now,
        direction="YES",
        desired_notional=Decimal("50"),
        resolved_payout=Decimal("1"),
    )
    assert trade.entry_price == Decimal("0.50")
    assert trade.pnl == Decimal("50.00")


def test_summarize_backtest() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    trade = simulate_binary_trade(
        [
            ExecutableQuote(
                now + timedelta(minutes=1),
                Decimal("0.40"),
                Decimal("0.50"),
                Decimal("100"),
                Decimal("100"),
            )
        ],
        signal_at=now,
        direction="YES",
        desired_notional=Decimal("50"),
        resolved_payout=Decimal("1"),
    )
    summary = summarize_backtest([trade])
    assert summary["trade_count"] == 1
    assert summary["win_rate"] == Decimal("1.0000")
