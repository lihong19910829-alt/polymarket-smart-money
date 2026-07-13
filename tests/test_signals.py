from decimal import Decimal

from app.analytics.signals import Participant, consensus_score, signal_dedupe_key, wallet_weight


def test_wallet_weight_is_capped() -> None:
    participant = Participant("w", "S", Decimal("100"), Decimal("1"), Decimal("1"), Decimal("1"), Decimal("1"), Decimal("5"))
    assert wallet_weight(participant) == Decimal("1.50")


def test_consensus_requires_cluster_independence() -> None:
    participants = [
        Participant("a", "A", Decimal("90"), Decimal("0.9"), Decimal("1"), Decimal("1"), Decimal("1"), Decimal("1")),
        Participant("b", "B", Decimal("80"), Decimal("0.9"), Decimal("1"), Decimal("1"), Decimal("1"), Decimal("1")),
        Participant("c", "B", Decimal("80"), Decimal("0.9"), Decimal("1"), Decimal("1"), Decimal("1"), Decimal("1")),
    ]
    result = consensus_score(participants, independent_clusters=1)
    assert result["eligible"] is False
    assert "fewer than 2 independent clusters" in result["reasons"]


def test_signal_dedupe_key_is_stable_lowercase() -> None:
    assert signal_dedupe_key("M1", "T1", "CONSENSUS", "YES") == "m1:t1:consensus:yes"

