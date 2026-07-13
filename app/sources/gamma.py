from typing import Any

from app.core.config import get_settings
from app.sources.http import PolymarketHttpClient


class GammaClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.http = PolymarketHttpClient(
            settings.gamma_base_url, settings.http_timeout_seconds, settings.http_max_retries
        )

    async def markets(self, *, limit: int = 500, offset: int = 0, active: bool | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if active is not None:
            params["active"] = str(active).lower()
        data = (await self.http.get("/markets", params=params)).json_data
        return data if isinstance(data, list) else data.get("markets", [])

    async def events(self, *, limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
        data = (await self.http.get("/events", params={"limit": limit, "offset": offset})).json_data
        return data if isinstance(data, list) else data.get("events", [])

