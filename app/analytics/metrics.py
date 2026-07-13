from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TradePnL:
    pnl: Decimal
    volume: Decimal
    wins: int
    losses: int
    equity_curve: list[Decimal]


def profit_factor(pnls: list[Decimal]) -> Decimal | None:
    gross_profit = sum((p for p in pnls if p > 0), Decimal("0"))
    gross_loss = abs(sum((p for p in pnls if p < 0), Decimal("0")))
    if gross_loss == 0:
        return None if gross_profit == 0 else Decimal("999.0000")
    return gross_profit / gross_loss


def max_drawdown(equity_curve: list[Decimal]) -> Decimal:
    peak = Decimal("0")
    worst = Decimal("0")
    for value in equity_curve:
        peak = max(peak, value)
        worst = min(worst, value - peak)
    return abs(worst)


def positive_ratio(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    positives = sum(1 for value in values if value > 0)
    return Decimal(positives) / Decimal(len(values))


def estimate_position_delta(previous: Decimal, current: Decimal, price: Decimal) -> dict[str, Decimal | str]:
    delta = current - previous
    if delta > 0:
        side = "ADD"
    elif delta < 0 and current > 0:
        side = "REDUCE"
    elif delta < 0 and current <= 0:
        side = "EXIT"
    else:
        side = "UNCHANGED"
    return {
        "side": side,
        "size_delta": delta,
        "notional_delta": abs(delta) * price,
        "previous_size": previous,
        "current_size": current,
    }

