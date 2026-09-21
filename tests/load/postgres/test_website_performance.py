from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.load.postgres.website_performance import (
    get_latest_website_performance,
    load_website_performance,
)
from app.models.persistence.company import Company
from app.models.persistence.website_performance import WebsitePerformance
from app.models.schemas.performance import WebsitePerformanceResult
from app.models.schemas.seo import WebsiteSeoResult
from app.models.persistence.source import Source

@pytest.fixture
async def source(
    session: AsyncSession,
) -> Source:
    source = Source(
        name="Website Analysis",
        source_type="website_analysis",
    )

    session.add(source)
    await session.flush()

    return source


@pytest.fixture
async def company(
    session: AsyncSession,
) -> Company:
    company = Company(
        name="Example Company",
        normalized_name="example company",
        website="https://example.com/",
        domain="example.com",
        country="Pakistan",
        city="Lahore",
        category="Software company",
    )

    session.add(company)
    await session.flush()

    return company


@pytest.fixture
def performance_result() -> WebsitePerformanceResult:
    return WebsitePerformanceResult(
        performance_score=42,
        first_contentful_paint_ms=1800.5,
        largest_contentful_paint_ms=4200.25,
        cumulative_layout_shift=0.18,
        total_blocking_time_ms=650.0,
        speed_index_ms=3900.75,
    )


@pytest.fixture
def seo_result() -> WebsiteSeoResult:
    return WebsiteSeoResult(
        seo_score=61,
    )


@pytest.fixture
def observed_at() -> datetime:
    return datetime(2026, 8, 17, 10, 30, tzinfo=UTC)


@pytest.mark.asyncio
async def test_load_website_performance(
    session: AsyncSession,
    company: Company,
    performance_result: WebsitePerformanceResult,
    seo_result: WebsiteSeoResult,
    observed_at: datetime,
) -> None:
    performance = await load_website_performance(
        session=session,
        performance=performance_result,
        company_id=company.id,
        provider_name="lighthouse",
        seo=seo_result,
        observed_at=observed_at,
    )

    assert performance.id is not None
    assert performance.company_id == company.id
    assert performance.provider_name == "lighthouse"

    assert performance.performance_score == 42
    assert performance.first_contentful_paint_ms == 1800.5
    assert performance.largest_contentful_paint_ms == 4200.25
    assert performance.cumulative_layout_shift == 0.18
    assert performance.total_blocking_time_ms == 650.0
    assert performance.speed_index_ms == 3900.75

    assert performance.seo_score == 61
    assert performance.observed_at == observed_at


@pytest.mark.asyncio
async def test_load_website_performance_persists_record(
    session: AsyncSession,
    company: Company,
    performance_result: WebsitePerformanceResult,
    seo_result: WebsiteSeoResult,
    observed_at: datetime,
) -> None:
    performance = await load_website_performance(
        session=session,
        performance=performance_result,
        company_id=company.id,
        provider_name="lighthouse",
        seo=seo_result,
        observed_at=observed_at,
    )

    statement = select(WebsitePerformance).where(
        WebsitePerformance.id == performance.id,
    )

    persisted = await session.scalar(statement)

    assert persisted is not None
    assert persisted.company_id == company.id
    assert persisted.performance_score == 42
    assert persisted.seo_score == 61


@pytest.mark.asyncio
async def test_load_website_performance_without_seo(
    session: AsyncSession,
    company: Company,
    performance_result: WebsitePerformanceResult,
    observed_at: datetime,
) -> None:
    performance = await load_website_performance(
        session=session,
        performance=performance_result,
        company_id=company.id,
        provider_name="lighthouse",
        observed_at=observed_at,
    )

    assert performance.id is not None
    assert performance.performance_score == 42
    assert performance.seo_score is None


@pytest.mark.asyncio
async def test_load_website_performance_allows_empty_metrics(
    session: AsyncSession,
    company: Company,
    observed_at: datetime,
) -> None:
    performance_result = WebsitePerformanceResult()

    performance = await load_website_performance(
        session=session,
        performance=performance_result,
        company_id=company.id,
        provider_name="lighthouse",
        observed_at=observed_at,
    )

    assert performance.id is not None
    assert performance.performance_score is None
    assert performance.first_contentful_paint_ms is None
    assert performance.largest_contentful_paint_ms is None
    assert performance.cumulative_layout_shift is None
    assert performance.total_blocking_time_ms is None
    assert performance.speed_index_ms is None
    assert performance.seo_score is None


@pytest.mark.asyncio
async def test_load_website_performance_preserves_source(
    session: AsyncSession,
    company: Company,
    source: Source,
    performance_result: WebsitePerformanceResult,
    seo_result: WebsiteSeoResult,
    observed_at: datetime,
) -> None:
    performance = await load_website_performance(
        session=session,
        performance=performance_result,
        company_id=company.id,
        provider_name="lighthouse",
        source_id=source.id,
        seo=seo_result,
        observed_at=observed_at,
    )

    assert performance.source_id == source.id


@pytest.mark.asyncio
async def test_get_latest_website_performance(
    session: AsyncSession,
    company: Company,
    performance_result: WebsitePerformanceResult,
) -> None:
    first_observed_at = datetime(2026, 8, 15, 10, 30, tzinfo=UTC)
    second_observed_at = datetime(2026, 8, 17, 10, 30, tzinfo=UTC)

    first = await load_website_performance(
        session=session,
        performance=performance_result,
        company_id=company.id,
        provider_name="lighthouse",
        observed_at=first_observed_at,
    )

    second_result = WebsitePerformanceResult(
        performance_score=78,
    )

    second = await load_website_performance(
        session=session,
        performance=second_result,
        company_id=company.id,
        provider_name="lighthouse",
        observed_at=second_observed_at,
    )

    latest = await get_latest_website_performance(
        session=session,
        company_id=company.id,
    )

    assert first.id != second.id
    assert latest is not None
    assert latest.id == second.id
    assert latest.performance_score == 78
    assert latest.observed_at == second_observed_at