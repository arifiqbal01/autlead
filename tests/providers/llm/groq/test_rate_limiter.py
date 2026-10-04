from __future__ import annotations

import pytest

from app.providers.llm.groq.rate_limiter import GroqRateLimiter


@pytest.mark.asyncio
async def test_cooldown_accepts_short_wait() -> None:
    limiter = GroqRateLimiter(
        requests_per_minute=25,
        requests_per_day=900,
        max_cooldown_seconds=30.0,
    )

    accepted = await limiter.cooldown(5.0)

    assert accepted is True


@pytest.mark.asyncio
async def test_cooldown_rejects_long_wait() -> None:
    limiter = GroqRateLimiter(
        requests_per_minute=25,
        requests_per_day=900,
        max_cooldown_seconds=30.0,
    )

    accepted = await limiter.cooldown(
        2_500.0
    )

    assert accepted is False


@pytest.mark.asyncio
async def test_rejected_cooldown_does_not_block_acquire() -> None:
    limiter = GroqRateLimiter(
        requests_per_minute=60_000,
        requests_per_day=900,
        max_cooldown_seconds=30.0,
    )

    accepted = await limiter.cooldown(
        2_500.0
    )

    assert accepted is False

    # This should return immediately rather than inheriting the
    # rejected 2,500-second cooldown.
    await limiter.acquire()


def test_rate_limiter_rejects_invalid_max_cooldown() -> None:
    with pytest.raises(
        ValueError,
        match="max_cooldown_seconds",
    ):
        GroqRateLimiter(
            requests_per_minute=25,
            requests_per_day=900,
            max_cooldown_seconds=0,
        )