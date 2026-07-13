from decimal import Decimal

from sqlalchemy import func, select

from app.analytics.scoring import score_wallet
from app.db.models import Trade, Wallet, WalletMetric
from app.db.session import SessionLocal


def main() -> None:
    updated = 0
    with SessionLocal() as session:
        wallets = session.scalars(select(Wallet.address)).all()
        for address in wallets:
            trade_count = session.scalar(select(func.count()).select_from(Trade).where(Trade.wallet_address == address)) or 0
            volume = session.scalar(select(func.coalesce(func.sum(Trade.notional_usdc), 0)).where(Trade.wallet_address == address)) or Decimal("0")
            score = score_wallet(
                trade_count=int(trade_count),
                profit_factor=None,
                win_rate=None,
                positive_month_ratio=None,
                max_drawdown=None,
                volume=Decimal(volume),
            )
            wallet = session.get(Wallet, address)
            if wallet:
                wallet.current_tier = score.tier
            session.merge(
                WalletMetric(
                    wallet_address=address,
                    window_days=365,
                    trade_count=int(trade_count),
                    volume=Decimal(volume),
                    quality_score=score.quality_score,
                    risk_score=score.risk_score,
                    copyability_score=score.copyability_score,
                    evidence=score.evidence,
                )
            )
            updated += 1
        session.commit()
    print(f"reclassified_wallets={updated}")


if __name__ == "__main__":
    main()

