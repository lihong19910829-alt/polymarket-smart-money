import asyncio

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.ingestion.scheduler import build_scheduler


async def main() -> None:
    configure_logging()
    scheduler = build_scheduler()
    scheduler.start()
    while get_settings().enable_scheduler:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())

