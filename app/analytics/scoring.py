from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class WalletScore:
    tier: str
    quality_score: Decimal
    risk_score: Decimal
    copyability_score: Decimal
    evidence: dict


def clamp(value: Decimal, low: Decimal = Decimal("0"), high: Decimal = Decimal("100")) -> Decimal:
    return max(low, min(high, value))


def score_wallet(
    *,
    trade_count: int,
    profit_factor: Decimal | None,
    win_rate: Decimal | None,
    positive_month_ratio: Decimal | None,
    max_drawdown: Decimal | None,
    volume: Decimal,
    data_completeness: Decimal = Decimal("1"),
) -> WalletScore:
    pf_component = Decimal("0") if profit_factor is None else min(profit_factor, Decimal("3")) / Decimal("3") * 30
    win_component = (win_rate or Decimal("0")) * 20
    month_component = (positive_month_ratio or Decimal("0")) * 20
    sample_component = min(Decimal(trade_count) / Decimal("100"), Decimal("1")) * 15
    volume_component = min(volume / Decimal("100000"), Decimal("1")) * 10
    completeness_component = data_completeness * 5
    quality = clamp(pf_component + win_component + month_component + sample_component + volume_component + completeness_component)

    drawdown_penalty = Decimal("0")
    if max_drawdown is not None and volume > 0:
        drawdown_penalty = min(max_drawdown / volume, Decimal("1")) * 70
    risk = clamp(drawdown_penalty + (Decimal("1") - data_completeness) * 30)
    copyability = clamp(quality - risk * Decimal("0.35"))

    if trade_count < 10:
        tier = "INSUFFICIENT_DATA"
    elif quality >= 90 and risk <= 35:
        tier = "S"
    elif quality >= 75 and risk <= 45:
        tier = "A"
    elif quality >= 60:
        tier = "B"
    elif quality >= 40:
        tier = "C"
    elif quality >= 20:
        tier = "OBSERVATION"
    else:
        tier = "LOW_QUALITY"

    return WalletScore(
        tier=tier,
        quality_score=quality.quantize(Decimal("0.0001")),
        risk_score=risk.quantize(Decimal("0.0001")),
        copyability_score=copyability.quantize(Decimal("0.0001")),
        evidence={
            "trade_count": trade_count,
            "profit_factor": str(profit_factor) if profit_factor is not None else None,
            "win_rate": str(win_rate) if win_rate is not None else None,
            "positive_month_ratio": str(positive_month_ratio) if positive_month_ratio is not None else None,
            "max_drawdown": str(max_drawdown) if max_drawdown is not None else None,
            "volume": str(volume),
            "components": {
                "profit_factor": str(pf_component),
                "win_rate": str(win_component),
                "positive_month_ratio": str(month_component),
                "sample_size": str(sample_component),
                "volume": str(volume_component),
                "data_completeness": str(completeness_component),
            },
        },
    )

