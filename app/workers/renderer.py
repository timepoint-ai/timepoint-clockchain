import logging

import httpx

logger = logging.getLogger("clockchain.renderer")


class FlashClient:
    def __init__(self, base_url: str, service_key: str):
        self.base_url = base_url.rstrip("/")
        self.service_key = service_key
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-Service-Key": self.service_key},
            timeout=180.0,
        )

    async def generate_sync(self, query: str, preset: str = "balanced") -> dict:
        logger.info("Flash generate: query=%r preset=%s", query, preset)
        resp = await self._client.post(
            "/api/v1/timepoints/generate/sync",
            json={"query": query, "preset": preset},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_timepoint(self, timepoint_id: str) -> dict:
        resp = await self._client.get(f"/api/v1/timepoints/{timepoint_id}")
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self._client.aclose()
