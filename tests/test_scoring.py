from decimal import Decimal

from app.analytics.scoring import score_wallet


def test_score_wallet_assigns_s_tier_for_strong_complete_sample() -> None:
    result = score_wallet(
        trade_count=200,
        profit_factor=Decimal("3.0"),
        win_rate=Decimal("0.82"),
        positive_month_ratio=Decimal("0.90"),
        max_drawdown=Decimal("500"),
        volume=Decimal("250000"),
    )
    assert result.tier == "S"
    assert result.quality_score >= Decimal("90")
    assert "components" in result.evidence


def test_score_wallet_marks_small_sample_insufficient() -> None:
    result = score_wallet(
        trade_count=3,
        profit_factor=Decimal("4"),
        win_rate=Decimal("1"),
        positive_month_ratio=Decimal("1"),
        max_drawdown=Decimal("0"),
        volume=Decimal("1000000"),
    )
    assert result.tier == "INSUFFICIENT_DATA"
