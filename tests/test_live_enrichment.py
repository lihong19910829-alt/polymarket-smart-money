from decimal import Decimal

from app.api.live import (
    live_advanced_alerts,
    live_alerts,
    normalize_live_leader,
    normalize_live_position,
    wallet_live_profile,
)


def test_wallet_live_profile_rates_top_profitable_wallet() -> None:
    profile = wallet_live_profile(
        {"rank": 3, "pnl": "25000", "volume": "1500000"},
        [{"market_id": "market-1"}, {"market_id": "market-2"}],
    )

    assert profile["rating"] == "S"
    assert profile["label"] == "HIGH_VOLUME_WINNER"
    assert profile["evidence"]["open_project_count"] == 2


def test_wallet_live_profile_infers_expertise_from_positions() -> None:
    profile = wallet_live_profile(
        {"rank": 12, "pnl": "4000", "volume": "90000"},
        [
            {"market_id": "m1", "question": "Will Bitcoin hit 150k this year?", "category": "Crypto"},
            {"market_id": "m2", "question": "Will Ethereum ETF flows rise?", "category": "Crypto"},
            {"market_id": "m3", "question": "Will the Fed cut rates?", "category": "Macro"},
        ],
    )

    assert profile["expertise"]["primary"] == "Crypto"
    assert profile["expertise"]["secondary"] == ["Macro"]
    assert profile["expertise"]["distribution"] == {"Crypto": 2, "Macro": 1}


def test_wallet_live_profile_scores_hold_quality_and_copyability() -> None:
    profile = wallet_live_profile(
        {"rank": 8, "pnl": "18000", "volume": "300000"},
        [
            {
                "market_id": "btc-150k",
                "question": "Will Bitcoin hit 150k this year?",
                "category": "Crypto",
                "outcome": "Yes",
                "size": "25",
                "avg_price": "0.38",
                "current_price": "0.55",
                "entry_time": "2026-06-20T00:00:00Z",
                "end_date": "2026-12-31T00:00:00Z",
            }
        ],
    )

    assert Decimal(profile["performance_score"]) >= Decimal("80")
    assert Decimal(profile["hold_quality_score"]) >= Decimal("70")
    assert Decimal(profile["copyability_score"]) >= Decimal("65")
    assert profile["copyability_label"] in {"good", "strong"}


def test_normalize_live_leader_discards_address_like_names() -> None:
    row = {
        "proxyWallet": "0x1234567890abcdef",
        "name": "0x1234567890abcdef",
        "profileName": "0x1234...cdef",
        "pnl": "10",
    }

    leader = normalize_live_leader(row, 1)

    assert leader["name"] is None


def test_normalize_live_position_keeps_project_identifiers() -> None:
    position = normalize_live_position(
        {
            "conditionId": "condition-1",
            "eventSlug": "sample-event",
            "title": "Will this test pass?",
            "outcome": "Yes",
            "size": "12.5",
            "avgPrice": "0.41",
            "createdAt": "2026-07-13T12:00:00Z",
            "endDate": "2026-12-31T00:00:00Z",
        }
    )

    assert position["market_id"] == "condition-1"
    assert position["slug"] == "sample-event"
    assert position["question"] == "Will this test pass?"
    assert position["url"] == "https://polymarket.com/event/sample-event"
    assert position["entry_time"] == "2026-07-13T12:00:00Z"
    assert position["size"] == "12.5"
    assert position["avg_price"] == "0.41"
    assert position["end_date"] == "2026-12-31T00:00:00Z"


def test_normalize_live_position_derives_current_price_from_outcome_prices() -> None:
    position = normalize_live_position(
        {
            "conditionId": "world-cup-winner",
            "eventSlug": "team-win-world-cup",
            "title": "Will Example FC win the FIFA World Cup?",
            "outcome": "Yes",
            "outcomes": '["Yes","No"]',
            "outcomePrices": '["0.01","0.99"]',
            "size": "100",
        }
    )

    assert position["current_price"] == "0.01"


def test_live_alerts_detect_expertise_and_same_direction_clusters() -> None:
    wallets = [
        {
            "address": "0xaaa",
            "profile_url": "https://polymarket.com/profile/0xaaa",
            "classification": {
                "rating": "A",
                "quality_score": "76.00",
                "performance_score": "80.00",
                "hold_quality_score": "70.00",
                "copyability_score": "72.00",
                "copyability_label": "good",
                "expertise": {"primary": "Crypto", "secondary": [], "distribution": {"Crypto": 1}},
            },
            "positions": [
                {
                    "market_id": "btc-150k",
                    "question": "Will Bitcoin hit 150k this year?",
                    "category": "Crypto",
                    "outcome": "Yes",
                    "entry_time": "2026-07-13T12:00:00Z",
                    "size": "10",
                    "avg_price": "0.40",
                    "url": "https://polymarket.com/event/btc-150k",
                }
            ],
        },
        {
            "address": "0xbbb",
            "profile_url": "https://polymarket.com/profile/0xbbb",
            "classification": {
                "rating": "S",
                "expertise": {"primary": "Macro", "secondary": [], "distribution": {"Macro": 1}},
            },
            "positions": [
                {
                    "market_id": "btc-150k",
                    "question": "Will Bitcoin hit 150k this year?",
                    "category": "Crypto",
                    "outcome": "Yes",
                    "url": "https://polymarket.com/event/btc-150k",
                }
            ],
        },
    ]

    alerts = live_alerts(wallets)
    expertise_alert = next(alert for alert in alerts if alert["alert_type"] == "EXPERTISE_OPEN_POSITION")
    cluster_alert = next(alert for alert in alerts if alert["alert_type"] == "SAME_DIRECTION_CLUSTER")

    assert expertise_alert["wallet"] == "0xaaa"
    assert expertise_alert["expertise"] == "Crypto"
    assert expertise_alert["entry_time"] == "2026-07-13T12:00:00Z"
    assert expertise_alert["size"] == "10"
    assert expertise_alert["avg_price"] == "0.40"
    assert expertise_alert["copyability_score"] == "72.00"
    assert cluster_alert["market_id"] == "btc-150k"
    assert cluster_alert["direction"] == "Yes"
    assert cluster_alert["wallet_count"] == 2
    assert cluster_alert["wallets"][0]["hold_quality_score"] == "70.00"


def test_live_advanced_alerts_detect_four_wallet_same_direction() -> None:
    wallets = [
        {
            "address": f"0x{i}",
            "name": f"wallet-{i}",
            "profile_url": f"https://polymarket.com/profile/0x{i}",
            "rank": i,
            "classification": {
                "rating": "A" if i <= 2 else "B",
                "expertise": {"primary": "Crypto", "secondary": [], "distribution": {"Crypto": 1}},
            },
            "positions": [
                {
                    "market_id": "btc-150k",
                    "question": "Will Bitcoin hit 150k this year?",
                    "category": "Crypto",
                    "outcome": "Yes",
                    "url": "https://polymarket.com/event/btc-150k",
                }
            ],
        }
        for i in range(1, 5)
    ]

    alerts = live_advanced_alerts(wallets)
    alert = next(alert for alert in alerts if alert["alert_type"] == "ADVANCED_SAME_DIRECTION_CONSENSUS")

    assert alert["severity"] == "HIGH"
    assert alert["wallet_count"] == 4
    assert alert["strong_wallet_count"] == 2
    assert alert["expertise_distribution"] == {"Crypto": 4}
    assert alert["wallets"][0]["name"] == "wallet-1"
    assert "size" in alert["wallets"][0]


def test_live_advanced_alerts_detect_same_expertise_wallets() -> None:
    wallets = [
        {
            "address": "0xmacro1",
            "classification": {
                "rating": "S",
                "expertise": {"primary": "Macro", "secondary": [], "distribution": {"Macro": 1}},
            },
            "positions": [
                {
                    "market_id": "fed-cuts",
                    "question": "Will the Fed cut rates?",
                    "category": "Macro",
                    "outcome": "Yes",
                }
            ],
        },
        {
            "address": "0xmacro2",
            "classification": {
                "rating": "A",
                "expertise": {"primary": "Macro", "secondary": [], "distribution": {"Macro": 1}},
            },
            "positions": [
                {
                    "market_id": "fed-cuts",
                    "question": "Will the Fed cut rates?",
                    "category": "Macro",
                    "outcome": "Yes",
                }
            ],
        },
    ]

    alerts = live_advanced_alerts(wallets)
    alert = next(alert for alert in alerts if alert["alert_type"] == "ADVANCED_SAME_EXPERTISE_CONSENSUS")

    assert alert["severity"] == "CRITICAL"
    assert alert["expertise"] == "Macro"
    assert alert["wallet_count"] == 2
    assert alert["direction_distribution"] == {"Yes": 2}


def test_alerts_ignore_expired_positions() -> None:
    wallets = [
        {
            "address": "0xexpired",
            "classification": {
                "rating": "S",
                "expertise": {"primary": "Crypto", "secondary": [], "distribution": {"Crypto": 1}},
            },
            "positions": [
                {
                    "market_id": "old-btc",
                    "question": "Will Bitcoin hit 100k in 2025?",
                    "category": "Crypto",
                    "outcome": "Yes",
                    "end_date": "2025-01-01T00:00:00Z",
                }
            ],
        }
    ]

    assert live_alerts(wallets) == []
    assert live_advanced_alerts(wallets) == []


def test_alerts_ignore_near_zero_live_positions() -> None:
    wallets = [
        {
            "address": "0xeliminated",
            "classification": {
                "rating": "S",
                "expertise": {"primary": "Sports", "secondary": [], "distribution": {"Sports": 1}},
            },
            "positions": [
                {
                    "market_id": "world-cup-winner",
                    "question": "Will Example FC win the FIFA World Cup?",
                    "category": "Sports",
                    "outcome": "Yes",
                    "active": True,
                    "closed": False,
                    "end_date": "2026-12-31T00:00:00Z",
                    "size": "100",
                    "current_price": "0.01",
                }
            ],
        }
    ]

    assert live_alerts(wallets) == []
    assert live_advanced_alerts(wallets) == []


def test_alerts_ignore_low_price_world_cup_outrights() -> None:
    wallets = [
        {
            "address": "0xlongshot",
            "classification": {
                "rating": "S",
                "expertise": {"primary": "Sports", "secondary": [], "distribution": {"Sports": 1}},
            },
            "positions": [
                {
                    "market_id": "world-cup-winner",
                    "question": "Will Example FC win the FIFA World Cup?",
                    "category": "Sports",
                    "outcome": "Yes",
                    "active": True,
                    "closed": False,
                    "end_date": "2026-12-31T00:00:00Z",
                    "size": "100",
                    "current_price": "0.04",
                }
            ],
        }
    ]

    assert live_alerts(wallets) == []
    assert live_advanced_alerts(wallets) == []
