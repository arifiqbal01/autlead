from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.schemas.technology import DetectedTechnology
from app.pipelines.common import technology_detection


def make_session() -> SimpleNamespace:
    transaction = MagicMock()

    transaction.__aenter__ = AsyncMock(
        return_value=transaction,
    )
    transaction.__aexit__ = AsyncMock(
        return_value=None,
    )

    return SimpleNamespace(
        begin=MagicMock(return_value=transaction),
    )


def make_technology(
    *,
    name: str = "WordPress",
    version: str | None = "6.8.2",
    confidence: int = 100,
    categories: list[str] | None = None,
    groups: list[str] | None = None,
) -> DetectedTechnology:
    return DetectedTechnology(
        name=name,
        version=version,
        confidence=confidence,
        categories=categories or ["CMS"],
        groups=groups or ["CMS"],
    )


@pytest.mark.asyncio
async def test_detects_and_persists_technologies(
    monkeypatch,
):
    session = make_session()

    provider = SimpleNamespace(
        provider_name="wappalyzer",
        detect=AsyncMock(
            return_value=[
                make_technology(
                    name="WordPress",
                    version="6.8.2",
                ),
                make_technology(
                    name="WooCommerce",
                    version="9.9.0",
                    categories=["Ecommerce"],
                    groups=["Ecommerce"],
                ),
            ],
        ),
    )

    load_observation = AsyncMock()

    monkeypatch.setattr(
        technology_detection,
        "load_technology_observation",
        load_observation,
    )

    result = await technology_detection.run_website_technology_pipeline(
        provider=provider,
        websites=[
            (1, "https://example.com"),
        ],
        session=session,
        source_id=10,
        timeout=45,
    )

    assert result.detected == 2
    assert result.failed == 0
    assert result.stored == 2

    provider.detect.assert_awaited_once_with(
        "https://example.com",
        timeout=45,
    )

    assert load_observation.await_count == 2

    first_call = load_observation.await_args_list[0]

    assert first_call.args[0] is session
    assert first_call.args[1].name == "WordPress"
    assert first_call.kwargs == {
        "company_id": 1,
        "provider_name": "wappalyzer",
        "source_id": 10,
    }

    second_call = load_observation.await_args_list[1]

    assert second_call.args[0] is session
    assert second_call.args[1].name == "WooCommerce"
    assert second_call.kwargs == {
        "company_id": 1,
        "provider_name": "wappalyzer",
        "source_id": 10,
    }


@pytest.mark.asyncio
async def test_no_technologies_detected(
    monkeypatch,
):
    session = make_session()

    provider = SimpleNamespace(
        provider_name="wappalyzer",
        detect=AsyncMock(return_value=[]),
    )

    load_observation = AsyncMock()

    monkeypatch.setattr(
        technology_detection,
        "load_technology_observation",
        load_observation,
    )

    result = await technology_detection.run_website_technology_pipeline(
        provider=provider,
        websites=[
            (1, "https://example.com"),
        ],
        session=session,
    )

    assert result.detected == 0
    assert result.failed == 0
    assert result.stored == 0

    provider.detect.assert_awaited_once_with(
        "https://example.com",
        timeout=30,
    )

    load_observation.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_failure_isolated_per_website(
    monkeypatch,
):
    session = make_session()

    provider = SimpleNamespace(
        provider_name="wappalyzer",
        detect=AsyncMock(
            side_effect=[
                RuntimeError("Wappalyzer unavailable"),
                [
                    make_technology(
                        name="Cloudflare",
                        version=None,
                        categories=["CDN"],
                        groups=["Servers"],
                    ),
                ],
            ],
        ),
    )

    load_observation = AsyncMock()

    monkeypatch.setattr(
        technology_detection,
        "load_technology_observation",
        load_observation,
    )

    result = await technology_detection.run_website_technology_pipeline(
        provider=provider,
        websites=[
            (1, "https://failed.example"),
            (2, "https://success.example"),
        ],
        session=session,
    )

    assert result.detected == 1
    assert result.failed == 1
    assert result.stored == 1

    assert provider.detect.await_count == 2

    provider.detect.assert_any_await(
        "https://failed.example",
        timeout=30,
    )

    provider.detect.assert_any_await(
        "https://success.example",
        timeout=30,
    )

    load_observation.assert_awaited_once()

    call = load_observation.await_args

    assert call.args[0] is session
    assert call.args[1].name == "Cloudflare"
    assert call.kwargs == {
        "company_id": 2,
        "provider_name": "wappalyzer",
        "source_id": None,
    }


@pytest.mark.asyncio
async def test_persistence_failure_isolated_per_website(
    monkeypatch,
):
    session = make_session()

    provider = SimpleNamespace(
        provider_name="wappalyzer",
        detect=AsyncMock(
            side_effect=[
                [
                    make_technology(
                        name="WordPress",
                    ),
                ],
                [
                    make_technology(
                        name="Shopify",
                        categories=["Ecommerce"],
                        groups=["Ecommerce"],
                    ),
                ],
            ],
        ),
    )

    load_observation = AsyncMock(
        side_effect=[
            RuntimeError("database unavailable"),
            None,
        ],
    )

    monkeypatch.setattr(
        technology_detection,
        "load_technology_observation",
        load_observation,
    )

    result = await technology_detection.run_website_technology_pipeline(
        provider=provider,
        websites=[
            (1, "https://first.example"),
            (2, "https://second.example"),
        ],
        session=session,
    )

    assert result.detected == 2
    assert result.failed == 1
    assert result.stored == 1

    assert provider.detect.await_count == 2
    assert load_observation.await_count == 2

    first_call = load_observation.await_args_list[0]

    assert first_call.args[1].name == "WordPress"
    assert first_call.kwargs["company_id"] == 1

    second_call = load_observation.await_args_list[1]

    assert second_call.args[1].name == "Shopify"
    assert second_call.kwargs["company_id"] == 2