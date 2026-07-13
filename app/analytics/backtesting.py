from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from app.analytics.metrics import max_drawdown, profit_factor


@dataclass(frozen=True)
class ExecutableQuote:
    at: datetime
    bid: Decimal
    ask: Decimal
    bid_size: Decimal
    ask_size: Decimal


@dataclass(frozen=True)
class SimulatedTrade:
    signal_at: datetime
    entry_at: datetime | None
    exit_at: datetime | None
    entry_price: Decimal | None
    exit_price: Decimal | None
    size: Decimal
    pnl: Decimal
    fees: Decimal
    slippage: Decimal
    capacity_used: Decimal
    evidence: dict


def executable_entry(
    quotes: list[ExecutableQuote],
    *,
    signal_at: datetime,
    direction: str,
    delay: timedelta,
    desired_notional: Decimal,
) -> tuple[ExecutableQuote | None, Decimal, dict]:
    earliest = signal_at + delay
    quote = next((item for item in quotes if item.at >= earliest), None)
    if quote is None:
        return None, Decimal("0"), {"reason": "no executable quote after delay"}
    price = quote.ask if direction.upper() in {"YES", "BUY", "LONG"} else Decimal("1") - quote.bid
    available_size = quote.ask_size if direction.upper() in {"YES", "BUY", "LONG"} else quote.bid_size
    desired_size = desired_notional / price if price > 0 else Decimal("0")
    size = min(desired_size, available_size)
    return quote, size, {
        "delay_seconds": delay.total_seconds(),
        "desired_notional": str(desired_notional),
        "available_size": str(available_size),
    }


def simulate_binary_trade(
    quotes: list[ExecutableQuote],
    *,
    signal_at: datetime,
    direction: str,
    desired_notional: Decimal,
    resolved_payout: Decimal,
    delay: timedelta = timedelta(minutes=1),
    fee_bps: Decimal = Decimal("0"),
    slippage_bps: Decimal = Decimal("0"),
) -> SimulatedTrade:
    quote, size, evidence = executable_entry(
        quotes,
        signal_at=signal_at,
        direction=direction,
        delay=delay,
        desired_notional=desired_notional,
    )
    if quote is None or size <= 0:
        return SimulatedTrade(
            signal_at=signal_at,
            entry_at=None,
            exit_at=None,
            entry_price=None,
            exit_price=None,
            size=Decimal("0"),
            pnl=Decimal("0"),
            fees=Decimal("0"),
            slippage=Decimal("0"),
            capacity_used=Decimal("0"),
            evidence=evidence,
        )
    entry_price = quote.ask if direction.upper() in {"YES", "BUY", "LONG"} else Decimal("1") - quote.bid
    gross_cost = entry_price * size
    fees = gross_cost * fee_bps / Decimal("10000")
    slippage = gross_cost * slippage_bps / Decimal("10000")
    pnl = (resolved_payout - entry_price) * size - fees - slippage
    return SimulatedTrade(
        signal_at=signal_at,
        entry_at=quote.at,
        exit_at=None,
        entry_price=entry_price,
        exit_price=resolved_payout,
        size=size,
        pnl=pnl,
        fees=fees,
        slippage=slippage,
        capacity_used=gross_cost,
        evidence=evidence | {"entry_source": "post_signal_orderbook"},
    )


def summarize_backtest(trades: list[SimulatedTrade]) -> dict[str, Decimal | int | None]:
    pnls = [trade.pnl for trade in trades]
    wins = sum(1 for pnl in pnls if pnl > 0)
    deployed = sum((trade.capacity_used for trade in trades), Decimal("0"))
    equity = []
    running = Decimal("0")
    for pnl in pnls:
        running += pnl
        equity.append(running)
    return {
        "trade_count": len(trades),
        "win_rate": (Decimal(wins) / Decimal(len(trades))).quantize(Decimal("0.0001")) if trades else None,
        "profit_factor": profit_factor(pnls),
        "total_return": sum(pnls, Decimal("0")),
        "roi_on_deployed_capital": (sum(pnls, Decimal("0")) / deployed).quantize(Decimal("0.0001"))
        if deployed
        else None,
        "max_drawdown": max_drawdown(equity),
        "average_slippage": (sum((trade.slippage for trade in trades), Decimal("0")) / Decimal(len(trades)))
        if trades
        else None,
    }
