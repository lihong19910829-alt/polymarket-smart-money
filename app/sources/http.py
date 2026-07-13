import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    json_data: Any
    headers: Mapping[str, str]


class PolymarketHttpClient:
    def __init__(self, base_url: str, timeout: float, max_retries: int = 4) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    async def get(self, path: str, params: dict[str, Any] | None = None) -> ApiResponse:
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.get(url, params=params)
                    if response.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                        await asyncio.sleep(min(2**attempt, 30) + attempt * 0.1)
                        continue
                    response.raise_for_status()
                    return ApiResponse(response.status_code, response.json(), response.headers)
                except (httpx.HTTPError, ValueError) as exc:
                    last_error = exc
                    if attempt >= self.max_retries:
                        raise
                    await asyncio.sleep(min(2**attempt, 30) + attempt * 0.1)
        raise RuntimeError("unreachable") from last_error

