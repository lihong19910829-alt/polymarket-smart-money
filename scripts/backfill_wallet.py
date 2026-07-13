import argparse
import asyncio

from app.db.session import SessionLocal
from app.ingestion.jobs import refresh_wallet_positions


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("address")
    args = parser.parse_args()
    with SessionLocal() as session:
        count = await refresh_wallet_positions(session, args.address)
    print(f"positions={count}")


if __name__ == "__main__":
    asyncio.run(main())

