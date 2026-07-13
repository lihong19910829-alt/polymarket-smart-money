from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class StrategyClassification:
    primary_label: str
    secondary_labels: list[str]
    confidence: Decimal
    evidence: dict


def classify_strategy(trades: Iterable[dict]) -> StrategyClassification:
    rows = list(trades)
    if not rows:
        return StrategyClassification("UNEXPLAINED", [], Decimal("0.0000"), {"reason": "no trades"})

    hold_to_resolution = sum(1 for row in rows if row.get("resolved_position"))
    quick_flips = sum(1 for row in rows if row.get("holding_minutes", 999999) <= 240)
    makers = sum(1 for row in rows if str(row.get("liquidity_role", "")).upper() == "MAKER")
    categories = Counter(str(row.get("category") or "UNKNOWN") for row in rows)

    scores = {
        "HOLD_TO_RESOLUTION": Decimal(hold_to_resolution) / Decimal(len(rows)),
        "MOMENTUM": Decimal(quick_flips) / Decimal(len(rows)),
        "MARKET_MAKING": Decimal(makers) / Decimal(len(rows)),
    }
    primary = max(scores, key=scores.get)
    secondary = [name for name, score in scores.items() if name != primary and score >= Decimal("0.25")]
    confidence = max(scores.values()).quantize(Decimal("0.0001"))
    if confidence < Decimal("0.35"):
        primary = "UNEXPLAINED"

    return StrategyClassification(
        primary_label=primary,
        secondary_labels=secondary,
        confidence=confidence,
        evidence={
            "sample_size": len(rows),
            "scores": {key: str(value.quantize(Decimal("0.0001"))) for key, value in scores.items()},
            "top_categories": categories.most_common(5),
        },
    )


def infer_rule_stub(classification: StrategyClassification) -> dict:
    if classification.primary_label == "UNEXPLAINED":
        return {
            "rule_type": "UNEXPLAINED",
            "rule_text": "No statistically supported repeatable rule was inferred for this wallet.",
            "confidence": Decimal("0.1000"),
            "evidence": classification.evidence,
        }
    return {
        "rule_type": classification.primary_label,
        "rule_text": (
            f"Wallet behavior is most consistent with {classification.primary_label}; "
            "validate with walk-forward samples before using as a live signal."
        ),
        "confidence": classification.confidence,
        "evidence": classification.evidence,
    }

