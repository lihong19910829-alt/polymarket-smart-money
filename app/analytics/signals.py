from dataclasses import dataclass
from decimal import Decimal

TIER_WEIGHT = {
    "S": Decimal("1.50"),
    "A": Decimal("1.00"),
    "B": Decimal("0.60"),
    "C": Decimal("0.25"),
    "OBSERVATION": Decimal("0.10"),
}


@dataclass(frozen=True)
class Participant:
    wallet: str
    tier: str
    quality_score: Decimal
    classification_confidence: Decimal
    category_expertise: Decimal
    copyability: Decimal
    freshness: Decimal
    size_significance: Decimal
    cluster_id: str | None = None


def wallet_weight(participant: Participant) -> Decimal:
    tier_weight = TIER_WEIGHT.get(participant.tier, Decimal("0"))
    weight = (
        tier_weight
        * (participant.quality_score / Decimal("100"))
        * participant.classification_confidence
        * participant.category_expertise
        * participant.copyability
        * participant.freshness
        * participant.size_significance
    )
    return min(weight, Decimal("1.50"))


def consensus_score(participants: list[Participant], *, independent_clusters: int, drift_penalty: Decimal = Decimal("0")) -> dict:
    if not participants:
        return {"score": Decimal("0"), "eligible": False, "reasons": ["no participants"]}
    weights = [wallet_weight(item) for item in participants]
    raw = sum(weights, Decimal("0"))
    cluster_bonus = min(Decimal(independent_clusters) / Decimal("3"), Decimal("1")) * Decimal("15")
    tier_bonus = Decimal("10") if any(item.tier in {"S", "A"} for item in participants) else Decimal("0")
    score = max(Decimal("0"), min(Decimal("100"), raw * Decimal("35") + cluster_bonus + tier_bonus - drift_penalty))
    reasons = []
    if len(participants) < 3:
        reasons.append("fewer than 3 qualified wallets")
    if independent_clusters < 2:
        reasons.append("fewer than 2 independent clusters")
    if not any(item.tier in {"S", "A"} for item in participants):
        reasons.append("no S/A wallet")
    if score < Decimal("65"):
        reasons.append("score below trigger threshold")
    return {
        "score": score.quantize(Decimal("0.0001")),
        "eligible": not reasons,
        "reasons": reasons,
        "weights": [str(weight.quantize(Decimal("0.0001"))) for weight in weights],
    }


def signal_dedupe_key(market_id: str, token_id: str, signal_type: str, direction: str) -> str:
    return f"{market_id}:{token_id}:{signal_type}:{direction}".lower()

