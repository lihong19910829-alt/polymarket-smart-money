import os
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
except ModuleNotFoundError:  # pragma: no cover - only used in minimal local sandboxes
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    def generate_latest() -> bytes:
        return b"# prometheus_client is not installed\n"
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.analytics.scoring import score_wallet
from app.api.demo import DEMO_MARKETS, DEMO_SIGNALS, DEMO_WALLETS, demo_status
from app.api.live import (
    live_leaderboard,
    live_markets,
    live_overview,
    live_project_participants,
    live_wallet_positions,
    live_wallets_enriched,
)
from app.api.schemas import MarketOut, SignalOut, WalletOut
from app.core.security import require_admin_key
from app.db.models import (
    DataQualityIssue,
    InferredRule,
    IngestionRun,
    Market,
    PositionCurrent,
    Signal,
    Trade,
    Wallet,
    WalletClassification,
    WalletMetric,
)
from app.db.session import get_db
from app.ingestion.jobs import (
    capture_orderbook_snapshot,
    discover_leaderboard_wallets,
    refresh_wallet_positions,
    sync_gamma_markets,
)
from app.notifications.telegram import send_telegram_message

router = APIRouter()


def database_configured() -> bool:
    return bool(os.getenv("DATABASE_URL"))


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/system-status")
def system_status() -> dict:
    return demo_status()


@router.get("/live/overview")
async def get_live_overview(limit: int = Query(default=20, le=100)) -> dict:
    return await live_overview(limit)


@router.get("/live/markets")
async def get_live_markets(limit: int = Query(default=20, le=100)) -> dict:
    return await live_markets(limit)


@router.get("/live/leaderboard")
async def get_live_leaderboard(limit: int = Query(default=20, le=100)) -> dict:
    return await live_leaderboard(limit)


@router.get("/live/wallets/enriched")
async def get_live_wallets_enriched(
    limit: int = Query(default=50, le=50),
    positions_per_wallet: int = Query(default=8, le=30),
) -> dict:
    return await live_wallets_enriched(limit, positions_per_wallet)


@router.get("/live/wallets/{address}/positions")
async def get_live_wallet_positions(address: str, limit: int = Query(default=20, le=100)) -> dict:
    return await live_wallet_positions(address, limit)


@router.get("/live/projects/{project_key}/participants")
async def get_live_project_participants(project_key: str, limit: int = Query(default=50, le=50)) -> dict:
    return await live_project_participants(project_key, limit)


@router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/", response_class=HTMLResponse)
def admin_page() -> str:
    dashboard = Path(__file__).resolve().parents[2] / "live-dashboard.html"
    if dashboard.exists():
        return dashboard.read_text(encoding="utf-8")
    return "<!doctype html><title>Polymarket Smart Money</title><p>Dashboard file not found.</p>"


@router.get("/wallets", response_model=list[WalletOut])
def list_wallets(
    db: Session = Depends(get_db),
    tier: str | None = None,
    limit: int = Query(default=100, le=500),
) -> list[Wallet]:
    if not database_configured():
        rows = DEMO_WALLETS if tier is None else [row for row in DEMO_WALLETS if row["current_tier"] == tier]
        return [WalletOut(**row) for row in rows[:limit]]
    try:
        stmt = select(Wallet).order_by(desc(Wallet.last_seen_at)).limit(limit)
        if tier:
            stmt = stmt.where(Wallet.current_tier == tier)
        return list(db.scalars(stmt).all())
    except Exception:
        rows = DEMO_WALLETS if tier is None else [row for row in DEMO_WALLETS if row["current_tier"] == tier]
        return [WalletOut(**row) for row in rows[:limit]]


@router.get("/wallets/{address}", response_model=WalletOut)
def get_wallet(address: str, db: Session = Depends(get_db)) -> Wallet:
    if not database_configured():
        for row in DEMO_WALLETS:
            if row["address"].lower() == address.lower():
                return WalletOut(**row)
        raise HTTPException(404, "wallet not found")
    try:
        wallet = db.get(Wallet, address.lower())
        if wallet:
            return wallet
    except Exception:
        pass
    for row in DEMO_WALLETS:
        if row["address"].lower() == address.lower():
            return WalletOut(**row)
    raise HTTPException(404, "wallet not found")


@router.get("/wallets/{address}/metrics")
def wallet_metrics(address: str, db: Session = Depends(get_db)) -> list[dict]:
    if not database_configured():
        return [{"window_days": 365, "quality_score": 76.5, "risk_score": 28.0, "copyability_score": 66.7, "evidence": {"mode": "demo"}}]
    try:
        rows = db.scalars(select(WalletMetric).where(WalletMetric.wallet_address == address.lower())).all()
        return [
            {
                "window_days": row.window_days,
                "quality_score": row.quality_score,
                "risk_score": row.risk_score,
                "copyability_score": row.copyability_score,
                "evidence": row.evidence,
            }
            for row in rows
        ]
    except Exception:
        return [{"window_days": 365, "quality_score": 76.5, "risk_score": 28.0, "copyability_score": 66.7, "evidence": {"mode": "demo"}}]


@router.get("/wallets/{address}/positions")
def wallet_positions(address: str, db: Session = Depends(get_db)) -> list[dict]:
    if not database_configured():
        return []
    try:
        rows = db.scalars(select(PositionCurrent).where(PositionCurrent.wallet_address == address.lower())).all()
        return [
            {
                "market_id": row.market_id,
                "token_id": row.token_id,
                "size": row.size,
                "avg_price": row.avg_price,
                "current_price": row.current_price,
                "notional_usdc": row.notional_usdc,
            }
            for row in rows
        ]
    except Exception:
        return []


@router.get("/wallets/{address}/trades")
def wallet_trades(address: str, db: Session = Depends(get_db), limit: int = Query(default=100, le=500)) -> list[dict]:
    if not database_configured():
        return []
    try:
        rows = db.scalars(
            select(Trade).where(Trade.wallet_address == address.lower()).order_by(desc(Trade.trade_at)).limit(limit)
        ).all()
        return [
            {
                "trade_uid": row.trade_uid,
                "market_id": row.market_id,
                "token_id": row.token_id,
                "side": row.side,
                "price": row.price,
                "size": row.size,
                "notional_usdc": row.notional_usdc,
                "trade_at": row.trade_at,
            }
            for row in rows
        ]
    except Exception:
        return []


@router.get("/wallets/{address}/classification")
def wallet_classification(address: str, db: Session = Depends(get_db)) -> dict:
    if not database_configured():
        return {"primary_label": "MOMENTUM", "secondary_labels": ["DEMO"], "confidence": 0.62, "evidence": {"mode": "demo"}}
    try:
        row = db.scalars(
            select(WalletClassification)
            .where(WalletClassification.wallet_address == address.lower())
            .order_by(desc(WalletClassification.classified_at))
            .limit(1)
        ).first()
        if row:
            return {
                "primary_label": row.primary_label,
                "secondary_labels": row.secondary_labels,
                "confidence": row.confidence,
                "evidence": row.evidence,
            }
    except Exception:
        pass
    return {"primary_label": "MOMENTUM", "secondary_labels": ["DEMO"], "confidence": 0.62, "evidence": {"mode": "demo"}}


@router.get("/wallets/{address}/inferred-rules")
def wallet_rules(address: str, db: Session = Depends(get_db)) -> list[dict]:
    if not database_configured():
        return [{"rule_type": "DEMO", "rule_text": "Demo rule until database-backed inference is available.", "confidence": 0.3, "evidence": {"mode": "demo"}}]
    try:
        rows = db.scalars(select(InferredRule).where(InferredRule.wallet_address == address.lower())).all()
        return [{"rule_type": row.rule_type, "rule_text": row.rule_text, "confidence": row.confidence, "evidence": row.evidence} for row in rows]
    except Exception:
        return [{"rule_type": "DEMO", "rule_text": "Demo rule until database-backed inference is available.", "confidence": 0.3, "evidence": {"mode": "demo"}}]


@router.get("/markets", response_model=list[MarketOut])
def list_markets(db: Session = Depends(get_db), limit: int = Query(default=100, le=500)) -> list[Market]:
    if not database_configured():
        return [MarketOut(**row) for row in DEMO_MARKETS[:limit]]
    try:
        return list(db.scalars(select(Market).order_by(desc(Market.volume_24h)).limit(limit)).all())
    except Exception:
        return [MarketOut(**row) for row in DEMO_MARKETS[:limit]]


@router.get("/markets/{market_id}", response_model=MarketOut)
def get_market(market_id: str, db: Session = Depends(get_db)) -> Market:
    if not database_configured():
        for row in DEMO_MARKETS:
            if row["market_id"] == market_id:
                return MarketOut(**row)
        raise HTTPException(404, "market not found")
    try:
        market = db.get(Market, market_id)
        if market:
            return market
    except Exception:
        pass
    for row in DEMO_MARKETS:
        if row["market_id"] == market_id:
            return MarketOut(**row)
    raise HTTPException(404, "market not found")


@router.get("/markets/{market_id}/smart-money")
def market_smart_money(market_id: str, db: Session = Depends(get_db)) -> dict:
    if not database_configured():
        return {"market_id": market_id, "wallets": [{"address": "0xdemo_smart_money_alpha", "notional": "12500.00"}], "mode": "demo"}
    try:
        rows = db.execute(
            select(Trade.wallet_address, func.sum(Trade.notional_usdc).label("notional"))
            .where(Trade.market_id == market_id)
            .group_by(Trade.wallet_address)
            .order_by(desc("notional"))
            .limit(20)
        ).all()
        return {"market_id": market_id, "wallets": [{"address": row[0], "notional": row[1]} for row in rows]}
    except Exception:
        return {"market_id": market_id, "wallets": [{"address": "0xdemo_smart_money_alpha", "notional": "12500.00"}], "mode": "demo"}


@router.get("/signals", response_model=list[SignalOut])
def list_signals(db: Session = Depends(get_db), limit: int = Query(default=100, le=500)) -> list[Signal]:
    if not database_configured():
        return [SignalOut(**row) for row in DEMO_SIGNALS[:limit]]
    try:
        return list(db.scalars(select(Signal).order_by(desc(Signal.created_at)).limit(limit)).all())
    except Exception:
        return [SignalOut(**row) for row in DEMO_SIGNALS[:limit]]


@router.get("/signals/{signal_id}", response_model=SignalOut)
def get_signal(signal_id: UUID, db: Session = Depends(get_db)) -> Signal:
    if not database_configured():
        for row in DEMO_SIGNALS:
            if row["signal_id"] == signal_id:
                return SignalOut(**row)
        raise HTTPException(404, "signal not found")
    try:
        signal = db.get(Signal, signal_id)
        if signal:
            return signal
    except Exception:
        pass
    for row in DEMO_SIGNALS:
        if row["signal_id"] == signal_id:
            return SignalOut(**row)
    raise HTTPException(404, "signal not found")


@router.get("/consensus", response_model=list[SignalOut])
def consensus(db: Session = Depends(get_db), limit: int = Query(default=25, le=100)) -> list[Signal]:
    if not database_configured():
        return [SignalOut(**row) for row in DEMO_SIGNALS[:limit]]
    try:
        return list(
            db.scalars(
                select(Signal)
                .where(Signal.signal_type.in_(["CONSENSUS", "REVERSAL", "SINGLE_WHALE"]))
                .order_by(desc(Signal.created_at))
                .limit(limit)
            ).all()
        )
    except Exception:
        return [SignalOut(**row) for row in DEMO_SIGNALS[:limit]]


@router.get("/jobs")
def jobs(db: Session = Depends(get_db), limit: int = Query(default=100, le=500)) -> list[dict]:
    if not database_configured():
        return [{"job_name": "demo_mode", "status": "DATABASE_NOT_CONNECTED", "rows_read": 0, "rows_inserted": 0}]
    try:
        rows = db.scalars(select(IngestionRun).order_by(desc(IngestionRun.started_at)).limit(limit)).all()
        return [
            {
                "id": str(row.id),
                "job_name": row.job_name,
                "status": row.status,
                "started_at": row.started_at,
                "finished_at": row.finished_at,
                "rows_read": row.rows_read,
                "rows_inserted": row.rows_inserted,
                "error": row.error_message,
            }
            for row in rows
        ]
    except Exception:
        return [{"job_name": "demo_mode", "status": "DATABASE_NOT_CONNECTED", "rows_read": 0, "rows_inserted": 0}]


@router.get("/data-quality")
def data_quality_issues(db: Session = Depends(get_db), limit: int = Query(default=100, le=500)) -> list[dict]:
    if not database_configured():
        return [{"issue_type": "DATABASE_NOT_CONNECTED", "severity": "WARN", "entity_type": "system", "entity_key": "database", "details": {"mode": "demo"}}]
    try:
        rows = db.scalars(
            select(DataQualityIssue).order_by(desc(DataQualityIssue.detected_at)).limit(limit)
        ).all()
        return [
            {
                "issue_type": row.issue_type,
                "severity": row.severity,
                "entity_type": row.entity_type,
                "entity_key": row.entity_key,
                "detected_at": row.detected_at,
                "resolved_at": row.resolved_at,
                "details": row.details,
            }
            for row in rows
        ]
    except Exception:
        return [{"issue_type": "DATABASE_NOT_CONNECTED", "severity": "WARN", "entity_type": "system", "entity_key": "database", "details": {"mode": "demo"}}]


@router.post("/admin/recompute-wallet/{address}", dependencies=[Depends(require_admin_key)])
def recompute_wallet(address: str, db: Session = Depends(get_db)) -> dict:
    trade_count = db.scalar(select(func.count()).select_from(Trade).where(Trade.wallet_address == address.lower())) or 0
    volume = db.scalar(select(func.coalesce(func.sum(Trade.notional_usdc), 0)).where(Trade.wallet_address == address.lower())) or Decimal("0")
    scored = score_wallet(
        trade_count=int(trade_count),
        profit_factor=None,
        win_rate=None,
        positive_month_ratio=None,
        max_drawdown=None,
        volume=Decimal(volume),
    )
    wallet = db.get(Wallet, address.lower())
    if wallet:
        wallet.current_tier = scored.tier
    db.merge(
        WalletMetric(
            wallet_address=address.lower(),
            window_days=365,
            trade_count=int(trade_count),
            volume=Decimal(volume),
            quality_score=scored.quality_score,
            risk_score=scored.risk_score,
            copyability_score=scored.copyability_score,
            evidence=scored.evidence,
        )
    )
    db.commit()
    return {"wallet": address.lower(), "tier": scored.tier, "quality_score": scored.quality_score}


@router.post("/admin/run-discovery", dependencies=[Depends(require_admin_key)])
async def run_discovery(db: Session = Depends(get_db)) -> dict:
    markets = await sync_gamma_markets(db)
    wallets = await discover_leaderboard_wallets(db)
    return {"markets": markets, "leaderboard_wallet_observations": wallets}


@router.post("/admin/refresh-wallet/{address}", dependencies=[Depends(require_admin_key)])
async def refresh_wallet(address: str, db: Session = Depends(get_db)) -> dict:
    positions = await refresh_wallet_positions(db, address)
    return {"wallet": address.lower(), "positions": positions}


@router.post("/admin/capture-orderbook/{market_id}/{token_id}", dependencies=[Depends(require_admin_key)])
async def capture_orderbook(market_id: str, token_id: str, db: Session = Depends(get_db)) -> dict:
    levels = await capture_orderbook_snapshot(db, token_id, market_id)
    return {"market_id": market_id, "token_id": token_id, "levels": levels}


@router.post("/admin/test-notification", dependencies=[Depends(require_admin_key)])
async def test_notification() -> dict:
    await send_telegram_message("Polymarket Smart Money test notification.")
    return {"sent": True}
