import asyncio

from app.notifications.telegram import send_telegram_message


async def main() -> None:
    await send_telegram_message("Polymarket Smart Money test notification.")
    print("sent=true")


if __name__ == "__main__":
    asyncio.run(main())

