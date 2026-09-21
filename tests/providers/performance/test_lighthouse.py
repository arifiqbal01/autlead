from __future__ import annotations

import json

import pytest

from app.providers.performance.lighthouse import LighthouseProvider


@pytest.mark.asyncio
async def test_lighthouse_analyze_performance(monkeypatch) -> None:
    """Lighthouse performance score is mapped correctly."""

    provider = LighthouseProvider()

    report = {
        "categories": {
            "performance": {
                "score": 0.87,
            },
            "seo": {
                "score": 0.92,
            },
        },
    }

    async def fake_execute(command: list[str]) -> str:
        assert command == [
            "lighthouse",
            "https://example.com/",
            "--output=json",
            "--output-path=stdout",
            "--quiet",
            "--form-factor=mobile",
            "--only-categories=performance,seo",
        ]

        return json.dumps(report)

    monkeypatch.setattr(
        provider,
        "_execute",
        fake_execute,
    )

    result = await provider.analyze_performance(
        "https://example.com/",
    )

    assert result.performance_score == 87


@pytest.mark.asyncio
async def test_lighthouse_analyze_seo(monkeypatch) -> None:
    """Lighthouse SEO score is mapped correctly."""

    provider = LighthouseProvider()

    report = {
        "categories": {
            "performance": {
                "score": 0.87,
            },
            "seo": {
                "score": 0.92,
            },
        },
    }

    async def fake_execute(command: list[str]) -> str:
        return json.dumps(report)

    monkeypatch.setattr(
        provider,
        "_execute",
        fake_execute,
    )

    result = await provider.analyze_seo(
        "https://example.com/",
    )

    assert result.seo_score == 92


@pytest.mark.asyncio
async def test_lighthouse_handles_missing_performance_score(
    monkeypatch,
) -> None:
    """Missing Lighthouse performance score becomes None."""

    provider = LighthouseProvider()

    report = {
        "categories": {
            "seo": {
                "score": 0.92,
            },
        },
    }

    async def fake_execute(command: list[str]) -> str:
        return json.dumps(report)

    monkeypatch.setattr(
        provider,
        "_execute",
        fake_execute,
    )

    result = await provider.analyze_performance(
        "https://example.com/",
    )

    assert result.performance_score is None


@pytest.mark.asyncio
async def test_lighthouse_handles_missing_seo_score(
    monkeypatch,
) -> None:
    """Missing Lighthouse SEO score becomes None."""

    provider = LighthouseProvider()

    report = {
        "categories": {
            "performance": {
                "score": 0.87,
            },
        },
    }

    async def fake_execute(command: list[str]) -> str:
        return json.dumps(report)

    monkeypatch.setattr(
        provider,
        "_execute",
        fake_execute,
    )

    result = await provider.analyze_seo(
        "https://example.com/",
    )

    assert result.seo_score is None


@pytest.mark.asyncio
async def test_lighthouse_rejects_invalid_json(
    monkeypatch,
) -> None:
    """Invalid Lighthouse output raises an error."""

    provider = LighthouseProvider()

    async def fake_execute(command: list[str]) -> str:
        return "not valid json"

    monkeypatch.setattr(
        provider,
        "_execute",
        fake_execute,
    )

    with pytest.raises(
        RuntimeError,
        match="Lighthouse returned invalid JSON",
    ):
        await provider.analyze_performance(
            "https://example.com/",
        )


@pytest.mark.asyncio
async def test_lighthouse_rejects_invalid_report(
    monkeypatch,
) -> None:
    """Non-object Lighthouse JSON raises an error."""

    provider = LighthouseProvider()

    async def fake_execute(command: list[str]) -> str:
        return json.dumps(["invalid", "report"])

    monkeypatch.setattr(
        provider,
        "_execute",
        fake_execute,
    )

    with pytest.raises(
        RuntimeError,
        match="Lighthouse returned an invalid report",
    ):
        await provider.analyze_performance(
            "https://example.com/",
        )


@pytest.mark.asyncio
async def test_lighthouse_execute_failure(
    monkeypatch,
) -> None:
    """Lighthouse execution failures propagate correctly."""

    provider = LighthouseProvider()

    async def fake_execute(command: list[str]) -> str:
        raise RuntimeError(
            "Lighthouse failed with exit code 1: Chrome unavailable"
        )

    monkeypatch.setattr(
        provider,
        "_execute",
        fake_execute,
    )

    with pytest.raises(
        RuntimeError,
        match="Chrome unavailable",
    ):
        await provider.analyze_performance(
            "https://example.com/",
        )

def test_lighthouse_score_is_converted_to_percentage() -> None:
    report = {
        "categories": {
            "performance": {
                "score": 0.876,
            },
        },
    }

    score = LighthouseProvider._score(
        report,
        "performance",
    )

    assert score == 88