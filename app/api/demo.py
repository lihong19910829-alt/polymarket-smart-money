from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

DEMO_WALLETS = [
    {
        "address": "0xdemo_smart_money_alpha",
        "current_status": "HIGH_QUALITY",
        "current_tier": "A",
        "first_seen_at": datetime(2026, 7, 13, tzinfo=UTC),
        "last_seen_at": datetime(2026, 7, 13, tzinfo=UTC),
        "data_completeness": Decimal("0.7200"),
    },
    {
        "address": "0xdemo_observation_beta",
        "current_status": "OBSERVATION",
        "current_tier": "OBSERVATION",
        "first_seen_at": datetime(2026, 7, 13, tzinfo=UTC),
        "last_seen_at": datetime(2026, 7, 13, tzinfo=UTC),
        "data_completeness": Decimal("0.4100"),
    },
]

DEMO_MARKETS = [
    {
        "market_id": "demo-market-2026-election",
        "condition_id": "demo-condition-001",
        "question": "Demo: Will the sample market resolve YES?",
        "category": "POLITICS",
        "active": True,
        "closed": False,
        "volume_24h": Decimal("125000.000000000000"),
        "liquidity": Decimal("42000.000000000000"),
    }
]

DEMO_SIGNALS = [
    {
        "signal_id": UUID("00000000-0000-0000-0000-000000000001"),
        "market_id": "demo-market-2026-election",
        "token_id": "demo-token-yes",
        "signal_type": "CONSENSUS",
        "direction": "YES",
        "score": Decimal("72.5000"),
        "copyability_score": Decimal("68.0000"),
        "risk_flags": ["demo_data", "database_not_connected"],
        "evidence": {
            "message": "Demo signal shown because the database is not connected in this local session.",
            "participants": ["0xdemo_smart_money_alpha", "0xdemo_observation_beta"],
        },
        "status": "DEMO",
    }
]


def demo_status() -> dict:
    return {
        "api_status": "ok",
        "data_status": "demo_mode",
        "message": "API is running. Database-backed endpoints fall back to demo data until DATABASE_URL is available and migrations are applied.",
        "timestamp": datetime.now(UTC).isoformat(),
    }

