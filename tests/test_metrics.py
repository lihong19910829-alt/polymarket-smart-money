from decimal import Decimal

from app.analytics.metrics import (
    estimate_position_delta,
    max_drawdown,
    positive_ratio,
    profit_factor,
)


def test_profit_factor() -> None:
    assert profit_factor([Decimal("10"), Decimal("-5"), Decimal("15")]) == Decimal("5")


def test_max_drawdown() -> None:
    assert max_drawdown([Decimal("0"), Decimal("10"), Decimal("7"), Decimal("15"), Decimal("2")]) == Decimal("13")


def test_positive_ratio() -> None:
    assert positive_ratio([Decimal("1"), Decimal("-1"), Decimal("2")]) == Decimal("0.6666666666666666666666666667")


def test_position_delta_exit() -> None:
    delta = estimate_position_delta(Decimal("5"), Decimal("0"), Decimal("0.25"))
    assert delta["side"] == "EXIT"
    assert delta["notional_delta"] == Decimal("1.25")

