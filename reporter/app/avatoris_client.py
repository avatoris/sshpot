import asyncio
import logging

import httpx

from .config import API_BASE

logger = logging.getLogger("reporter.avatoris")


class AvatorisClient:
    def __init__(self, api_key: str, limiter):
        self._base = API_BASE
        self._limiter = limiter
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=10.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def report(self, ip: str, categories: list[str], comment: str, max_attempts: int = 5) -> bool:
        attempt = 0
        backoff = 2.0
        while attempt < max_attempts:
            attempt += 1
            await self._limiter.acquire()
            try:
                resp = await self._client.post(
                    f"{self._base}/report",
                    json={"ip": ip, "categories": categories, "comment": comment},
                )
            except httpx.HTTPError as exc:
                logger.warning("network error reporting %s (attempt %d): %s", ip, attempt, exc)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue

            if resp.status_code in (200, 201):
                logger.info("reported %s categories=%s", ip, categories)
                return True
            if resp.status_code == 409:
                # Avatoris already has a recent report for this target
                # (e.g. our local state was lost on restart) - not an error.
                logger.info("report for %s already recent (409), treating as delivered", ip)
                return True
            if resp.status_code == 401:
                logger.error("AVATORIS_API_KEY rejected (401) - check credentials")
                return False
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", backoff))
                logger.warning("rate limited by Avatoris, retrying %s in %.1fs", ip, retry_after)
                await asyncio.sleep(retry_after)
                continue
            logger.warning(
                "unexpected status %d reporting %s: %s", resp.status_code, ip, resp.text[:200]
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

        logger.error("giving up reporting %s after %d attempts", ip, attempt)
        return False
