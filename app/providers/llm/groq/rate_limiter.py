from __future__ import annotations

import asyncio
import time
from collections import deque


class GroqRateLimiter:
    def __init__(
        self,
        *,
        requests_per_minute: int,
        requests_per_day: int,
        max_cooldown_seconds: float = 30.0,
    ) -> None:
        if requests_per_minute < 1:
            raise ValueError(
                "requests_per_minute must be >= 1"
            )

        if requests_per_day < 1:
            raise ValueError(
                "requests_per_day must be >= 1"
            )

        if max_cooldown_seconds <= 0:
            raise ValueError(
                "max_cooldown_seconds must be > 0"
            )

        self._rpm = requests_per_minute
        self._rpd = requests_per_day
        self._max_cooldown_seconds = (
            max_cooldown_seconds
        )

        self._lock = asyncio.Lock()

        self._minute_requests: deque[
            float
        ] = deque()

        self._daily_count = 0
        self._daily_date = time.strftime(
            "%Y-%m-%d",
            time.gmtime(),
        )

        self._min_interval = (
            60.0 / requests_per_minute
        )

        self._last_request_at: (
            float | None
        ) = None

        self._blocked_until = 0.0

    async def acquire(
        self,
    ) -> None:
        while True:
            async with self._lock:
                self._reset_day_if_needed()

                if (
                    self._daily_count
                    >= self._rpd
                ):
                    raise RuntimeError(
                        "Groq daily request limit reached"
                    )

                now = time.monotonic()

                cooldown_wait = max(
                    0.0,
                    self._blocked_until - now,
                )

                # Rolling 60-second request window.
                while (
                    self._minute_requests
                    and (
                        now
                        - self._minute_requests[0]
                        >= 60.0
                    )
                ):
                    self._minute_requests.popleft()

                interval_wait = 0.0

                if (
                    self._last_request_at
                    is not None
                ):
                    interval_wait = max(
                        0.0,
                        self._min_interval
                        - (
                            now
                            - self._last_request_at
                        ),
                    )

                window_wait = 0.0

                if (
                    len(
                        self._minute_requests
                    )
                    >= self._rpm
                ):
                    oldest = (
                        self._minute_requests[0]
                    )

                    window_wait = max(
                        0.0,
                        60.0
                        - (
                            now
                            - oldest
                        ),
                    )

                wait_seconds = max(
                    cooldown_wait,
                    interval_wait,
                    window_wait,
                )

                if wait_seconds <= 0:
                    now = time.monotonic()

                    self._minute_requests.append(
                        now
                    )

                    self._last_request_at = now
                    self._daily_count += 1

                    return

            # Do not hold the lock while sleeping.
            await asyncio.sleep(
                max(
                    0.1,
                    wait_seconds,
                )
            )

    async def cooldown(
        self,
        seconds: float,
    ) -> bool:
        """
        Apply a short provider-directed cooldown.

        Returns False when the requested cooldown exceeds the
        configured maximum. The caller should fail fast and use
        its fallback instead of blocking a worker for a long time.
        """
        if seconds <= 0:
            return True

        if seconds > self._max_cooldown_seconds:
            return False

        async with self._lock:
            self._blocked_until = max(
                self._blocked_until,
                time.monotonic()
                + seconds,
            )

        return True

    def _reset_day_if_needed(
        self,
    ) -> None:
        current_date = time.strftime(
            "%Y-%m-%d",
            time.gmtime(),
        )

        if current_date != self._daily_date:
            self._daily_date = current_date
            self._daily_count = 0