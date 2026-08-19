import asyncio
import time
from collections import deque


class TokenBucketLimiter:
    """Caps outgoing requests to at most `max_per_minute` in any rolling
    60s window, so we stay under Avatoris' 30 req/min limit."""

    def __init__(self, max_per_minute: int):
        self._max = max_per_minute
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] > 60:
                    self._timestamps.popleft()
                if len(self._timestamps) < self._max:
                    self._timestamps.append(now)
                    return
                wait_for = 60 - (now - self._timestamps[0])
            await asyncio.sleep(max(wait_for, 0.05))
