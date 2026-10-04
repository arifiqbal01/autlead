from __future__ import annotations

from typing import NoReturn

import pytest

from app.providers.llm.groq.errors import (
    GroqRateLimitedError,
)
from app.providers.llm.groq.provider import (
    GroqLLMProvider,
)


class FakeRateLimitError(Exception):
    status_code = 429


def _provider() -> GroqLLMProvider:
    return GroqLLMProvider(
        api_key="test-key",
        model="openai/gpt-oss-20b",
        requests_per_minute=25,
        requests_per_day=900,
        max_rate_limit_attempts=3,
        timeout=60,
    )


@pytest.mark.asyncio
async def test_long_rate_limit_wait_fails_fast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider()

    async def operation() -> NoReturn:
        raise FakeRateLimitError(
            "Rate limit reached"
        )

    monkeypatch.setattr(
        provider,
        "_extract_retry_seconds",
        lambda _exc: 2_500.0,
    )

    with pytest.raises(
        GroqRateLimitedError,
        match="exceeds the configured maximum",
    ):
        await provider._execute_with_rate_limit(
            operation
        )


@pytest.mark.asyncio
async def test_short_rate_limit_wait_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider()

    calls = 0

    async def operation() -> str:
        nonlocal calls
        calls += 1

        if calls == 1:
            raise FakeRateLimitError(
                "Rate limit reached"
            )

        return "success"

    monkeypatch.setattr(
        provider,
        "_extract_retry_seconds",
        lambda _exc: 0.01,
    )

    monkeypatch.setattr(
        "app.providers.llm.groq.provider.random.uniform",
        lambda _start, _end: 0.0,
    )

    result = await provider._execute_with_rate_limit(
        operation
    )

    assert result == "success"
    assert calls == 2


@pytest.mark.asyncio
async def test_rate_limit_attempts_are_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = GroqLLMProvider(
        api_key="test-key",
        model="openai/gpt-oss-20b",
        requests_per_minute=25,
        requests_per_day=900,
        max_rate_limit_attempts=2,
        timeout=60,
    )

    calls = 0

    async def operation() -> NoReturn:
        nonlocal calls
        calls += 1

        raise FakeRateLimitError(
            "Rate limit reached"
        )

    monkeypatch.setattr(
        provider,
        "_extract_retry_seconds",
        lambda _exc: 0.01,
    )

    monkeypatch.setattr(
        "app.providers.llm.groq.provider.random.uniform",
        lambda _start, _end: 0.0,
    )

    with pytest.raises(
        GroqRateLimitedError
    ):
        await provider._execute_with_rate_limit(
            operation
        )

    assert calls == 2