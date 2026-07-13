from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from typing import Any

from app.core.config import get_settings
from app.sources.http import PolymarketHttpClient

LEADERBOARD_CATEGORIES = [
    "OVERALL",
    "POLITICS",
    "SPORTS",
    "ESPORTS",
    "CRYPTO",
    "CULTURE",
    "MENTIONS",
    "WEATHER",
    "ECONOMICS",
    "TECH",
    "FINANCE",
]
LEADERBOARD_PERIODS = ["DAY", "WEEK", "MONTH", "ALL"]
LEADERBOARD_ORDER_BY = ["PNL", "VOL"]


class DataApiClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.http = PolymarketHttpClient(
            settings.data_api_base_url, settings.http_timeout_seconds, settings.http_max_retries
        )

    async def leaderboard(
        self,
        *,
        category: str,
        time_period: str,
        order_by: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        payload = (
            await self.http.get(
                "/v1/leaderboard",
                params={
                    "category": category,
                    "timePeriod": time_period,
                    "orderBy": order_by,
                    "limit": limit,
                    "offset": offset,
                },
            )
        ).json_data
        return payload if isinstance(payload, list) else payload.get("data", payload.get("leaderboard", []))

    async def holders(self, token_id: str, *, limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
        payload = (await self.http.get("/holders", params={"token": token_id, "limit": limit, "offset": offset})).json_data
        return payload if isinstance(payload, list) else payload.get("holders", payload.get("data", []))

    async def positions(self, wallet: str, *, limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
        payload = (await self.http.get("/positions", params={"user": wallet, "limit": limit, "offset": offset})).json_data
        return payload if isinstance(payload, list) else payload.get("data", payload.get("positions", []))

    async def closed_positions(self, wallet: str, *, limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
        payload = (await self.http.get("/closed-positions", params={"user": wallet, "limit": limit, "offset": offset})).json_data
        return payload if isinstance(payload, list) else payload.get("data", payload.get("positions", []))

    async def activity(self, wallet: str, *, limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
        payload = (
            await self.http.get(
                "/activity",
                params={"user": wallet, "limit": limit, "offset": offset},
            )
        ).json_data
        return payload if isinstance(payload, list) else payload.get("data", payload.get("activity", []))

    async def trades_window(
        self,
        *,
        market: str | None,
        start: datetime,
        end: datetime,
        limit: int = 500,
        taker_only: bool = False,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "limit": limit,
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
            "takerOnly": str(taker_only).lower(),
        }
        if market:
            params["market"] = market
        payload = (await self.http.get("/trades", params=params)).json_data
        return payload if isinstance(payload, list) else payload.get("data", payload.get("trades", []))

    async def recursive_trades(
        self,
        *,
        market: str | None,
        start: datetime,
        end: datetime,
        limit: int = 500,
        min_window: timedelta = timedelta(minutes=5),
    ) -> AsyncIterator[tuple[datetime, datetime, list[dict[str, Any]], bool]]:
        rows = await self.trades_window(market=market, start=start, end=end, limit=limit)
        near_limit = len(rows) >= int(limit * 0.9)
        if near_limit and end - start > min_window:
            midpoint = start + (end - start) / 2
            async for item in self.recursive_trades(market=market, start=start, end=midpoint, limit=limit, min_window=min_window):
                yield item
            async for item in self.recursive_trades(market=market, start=midpoint, end=end, limit=limit, min_window=min_window):
                yield item
        else:
            yield start, end, rows, not near_limit
