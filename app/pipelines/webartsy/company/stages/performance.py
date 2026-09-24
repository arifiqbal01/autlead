# app/pipelines/enrichment/stages/performance.py

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.pipelines.common.website_performance import (
    WebsitePerformancePipelineResult,
    run_website_performance_pipeline,
)
from app.providers.performance.protocol import (
    WebsitePerformanceProvider,
    WebsiteSeoProvider,
)


logger = get_logger(__name__)


async def run_performance_stage(
    *,
    session: AsyncSession,
    performance_provider: WebsitePerformanceProvider,
    seo_provider: WebsiteSeoProvider,
    company_id: int,
    company_name: str,
    website: str,
    source_id: int | None = None,
) -> WebsitePerformancePipelineResult:
    """
    Run WebArtsy performance and SEO analysis for one company.

    Pipeline:

        company website
            ↓
        common performance + SEO pipeline
            ↓
        performance/SEO persistence

    This stage owns WebArtsy-specific input preparation and logging.

    Performance analysis, SEO analysis, and persistence are delegated
    to the common website-performance pipeline.

    Transaction ownership belongs to the caller.
    """

    websites = [
        (
            company_id,
            website,
        )
    ]

    logger.info(
        "webartsy_performance_started",
        company_id=company_id,
        company_name=company_name,
        website=website,
    )

    result = await run_website_performance_pipeline(
        performance_provider=(
            performance_provider
        ),
        seo_provider=seo_provider,
        websites=websites,
        session=session,
        source_id=source_id,
    )

    logger.info(
        "webartsy_performance_completed",
        company_id=company_id,
        company_name=company_name,
        website=website,
        analyzed=result.analyzed,
        failed=result.failed,
        stored=result.stored,
    )

    return result