from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persistence.website_performance import WebsitePerformance
from app.models.schemas.performance import WebsitePerformanceResult
from app.models.schemas.seo import WebsiteSeoResult


async def load_website_performance(
    session: AsyncSession,
    performance: WebsitePerformanceResult,
    *,
    company_id: int,
    provider_name: str,
    source_id: int | None = None,
    seo: WebsiteSeoResult | None = None,
    observed_at: datetime | None = None,
) -> WebsitePerformance:
    """
    Persist a website performance observation.

    Performance and SEO results produced by the same website analysis
    are stored together as one historical WebsitePerformance record.
    """

    if observed_at is None:
        observed_at = datetime.now().astimezone()

    website_performance = WebsitePerformance(
        company_id=company_id,
        source_id=source_id,
        provider_name=provider_name,
        performance_score=performance.performance_score,
        first_contentful_paint_ms=performance.first_contentful_paint_ms,
        largest_contentful_paint_ms=performance.largest_contentful_paint_ms,
        cumulative_layout_shift=performance.cumulative_layout_shift,
        total_blocking_time_ms=performance.total_blocking_time_ms,
        speed_index_ms=performance.speed_index_ms,
        seo_score=seo.seo_score if seo is not None else None,
        observed_at=observed_at,
    )

    session.add(website_performance)
    await session.flush()

    return website_performance


async def get_latest_website_performance(
    session: AsyncSession,
    *,
    company_id: int,
) -> WebsitePerformance | None:
    """
    Return the most recently observed website performance for a company.
    """

    from sqlalchemy import select

    result = await session.scalars(
        select(WebsitePerformance)
        .where(
            WebsitePerformance.company_id == company_id,
        )
        .order_by(
            WebsitePerformance.observed_at.desc(),
        )
        .limit(1),
    )

    return result.first()