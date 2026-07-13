from typing import Any

from app.core.config import get_settings
from app.sources.http import PolymarketHttpClient


class ClobClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.http = PolymarketHttpClient(
            settings.clob_base_url, settings.http_timeout_seconds, settings.http_max_retries
        )

    async def orderbook(self, token_id: str) -> dict[str, Any]:
        payload = (await self.http.get("/book", params={"token_id": token_id})).json_data
        return payload if isinstance(payload, dict) else {}

    async def midpoint(self, token_id: str) -> dict[str, Any]:
        payload = (await self.http.get("/midpoint", params={"token_id": token_id})).json_data
        return payload if isinstance(payload, dict) else {}

