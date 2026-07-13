from app.analytics.classification import classify_strategy


def test_classify_momentum() -> None:
    result = classify_strategy([{"holding_minutes": 10}, {"holding_minutes": 80}, {"holding_minutes": 1200}])
    assert result.primary_label == "MOMENTUM"
    assert result.confidence > 0

