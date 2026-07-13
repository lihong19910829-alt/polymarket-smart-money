import asyncio

from app.db.session import SessionLocal
from app.ingestion.jobs import sync_gamma_markets


async def main() -> None:
    with SessionLocal() as session:
        count = await sync_gamma_markets(session, active=True, max_pages=20)
    print(f"synced_markets={count}")


if __name__ == "__main__":
    asyncio.run(main())

