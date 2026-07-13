from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WalletOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    address: str
    current_status: str
    current_tier: str
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    data_completeness: Decimal | None


class MarketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    market_id: str
    condition_id: str
    question: str | None
    category: str | None
    active: bool | None
    closed: bool | None
    volume_24h: Decimal | None
    liquidity: Decimal | None


class SignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    signal_id: UUID
    market_id: str
    token_id: str
    signal_type: str
    direction: str
    score: Decimal
    copyability_score: Decimal
    risk_flags: list
    evidence: dict
    status: str

