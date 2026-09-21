from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.load.postgres.technology_observation import (
    load_technology_observation,
)
from app.models.persistence.company import Company
from app.models.persistence.source import Source
from app.models.persistence.technology_observation import (
    TechnologyObservation,
)
from app.models.schemas.technology import DetectedTechnology


@pytest.fixture
async def source(
    session: AsyncSession,
) -> Source:
    source = Source(
        name="Technology Detection",
        source_type="technology_detection",
    )

    session.add(source)
    await session.flush()

    return source


@pytest.fixture
def technology() -> DetectedTechnology:
    return DetectedTechnology(
        name="WordPress",
        version="6.8.2",
        confidence=95,
        categories=["CMS"],
        groups=["Content Management Systems"],
    )


@pytest.fixture
def observed_at() -> datetime:
    return datetime(
        2026,
        8,
        17,
        11,
        0,
        tzinfo=UTC,
    )


@pytest.mark.asyncio
async def test_load_technology_observation(
    session: AsyncSession,
    company: Company,
    source: Source,
    technology: DetectedTechnology,
    observed_at: datetime,
) -> None:
    observation = await load_technology_observation(
        session=session,
        technology=technology,
        company_id=company.id,
        provider_name="wappalyzer",
        source_id=source.id,
        observed_at=observed_at,
    )

    assert observation.id is not None
    assert observation.company_id == company.id
    assert observation.source_id == source.id
    assert observation.provider_name == "wappalyzer"

    assert observation.name == "WordPress"
    assert observation.version == "6.8.2"
    assert observation.confidence == 95
    assert observation.categories == ["CMS"]
    assert observation.groups == [
        "Content Management Systems",
    ]

    assert observation.observed_at == observed_at


@pytest.mark.asyncio
async def test_load_technology_observation_persists_record(
    session: AsyncSession,
    company: Company,
    source: Source,
    technology: DetectedTechnology,
    observed_at: datetime,
) -> None:
    observation = await load_technology_observation(
        session=session,
        technology=technology,
        company_id=company.id,
        provider_name="wappalyzer",
        source_id=source.id,
        observed_at=observed_at,
    )

    statement = select(TechnologyObservation).where(
        TechnologyObservation.id == observation.id,
    )

    persisted = await session.scalar(statement)

    assert persisted is not None
    assert persisted.company_id == company.id
    assert persisted.source_id == source.id
    assert persisted.name == "WordPress"
    assert persisted.version == "6.8.2"
    assert persisted.confidence == 95
    assert persisted.categories == ["CMS"]
    assert persisted.groups == [
        "Content Management Systems",
    ]


@pytest.mark.asyncio
async def test_load_technology_observation_allows_missing_version(
    session: AsyncSession,
    company: Company,
    source: Source,
    observed_at: datetime,
) -> None:
    technology = DetectedTechnology(
        name="Cloudflare",
        version=None,
        confidence=90,
        categories=["CDN"],
        groups=["Web Infrastructure"],
    )

    observation = await load_technology_observation(
        session=session,
        technology=technology,
        company_id=company.id,
        provider_name="wappalyzer",
        source_id=source.id,
        observed_at=observed_at,
    )

    assert observation.id is not None
    assert observation.name == "Cloudflare"
    assert observation.version is None
    assert observation.confidence == 90


@pytest.mark.asyncio
async def test_load_technology_observation_allows_empty_categories_and_groups(
    session: AsyncSession,
    company: Company,
    source: Source,
    observed_at: datetime,
) -> None:
    technology = DetectedTechnology(
        name="Custom Technology",
        version=None,
        confidence=75,
        categories=[],
        groups=[],
    )

    observation = await load_technology_observation(
        session=session,
        technology=technology,
        company_id=company.id,
        provider_name="wappalyzer",
        source_id=source.id,
        observed_at=observed_at,
    )

    assert observation.id is not None
    assert observation.name == "Custom Technology"
    assert observation.version is None
    assert observation.confidence == 75
    assert observation.categories == []
    assert observation.groups == []


@pytest.mark.asyncio
async def test_load_technology_observation_allows_multiple_observations(
    session: AsyncSession,
    company: Company,
    source: Source,
    observed_at: datetime,
) -> None:
    wordpress = DetectedTechnology(
        name="WordPress",
        version="6.8.2",
        confidence=95,
        categories=["CMS"],
        groups=["Content Management Systems"],
    )

    woocommerce = DetectedTechnology(
        name="WooCommerce",
        version="9.9.0",
        confidence=92,
        categories=["Ecommerce"],
        groups=["Ecommerce"],
    )

    first = await load_technology_observation(
        session=session,
        technology=wordpress,
        company_id=company.id,
        provider_name="wappalyzer",
        source_id=source.id,
        observed_at=observed_at,
    )

    second = await load_technology_observation(
        session=session,
        technology=woocommerce,
        company_id=company.id,
        provider_name="wappalyzer",
        source_id=source.id,
        observed_at=observed_at,
    )

    assert first.id != second.id

    statement = select(TechnologyObservation).where(
        TechnologyObservation.company_id == company.id,
    )

    observations = list(
        (await session.scalars(statement)).all(),
    )

    assert len(observations) == 2
    assert {observation.name for observation in observations} == {
        "WordPress",
        "WooCommerce",
    }