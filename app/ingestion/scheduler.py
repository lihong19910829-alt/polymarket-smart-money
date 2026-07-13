from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.db.session import SessionLocal
from app.ingestion.jobs import (
    discover_holder_wallets,
    discover_leaderboard_wallets,
    sync_gamma_markets,
)


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    async def run_with_session(job):
        with SessionLocal() as session:
            return await job(session)

    scheduler.add_job(lambda: run_with_session(sync_gamma_markets), IntervalTrigger(minutes=5), id="gamma_markets")
    scheduler.add_job(
        lambda: run_with_session(discover_leaderboard_wallets),
        CronTrigger(hour=2, minute=0),
        id="leaderboard_discovery",
    )
    scheduler.add_job(lambda: run_with_session(discover_holder_wallets), IntervalTrigger(hours=6), id="holder_discovery")
    return scheduler

