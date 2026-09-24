# app/pipelines/enrichment/website_performance.py

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.load.postgres import load_website_performance
from app.providers.performance.protocol import (
    WebsitePerformanceProvider,
    WebsiteSeoProvider,
)


logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class WebsitePerformanceResult:
    analyzed: bool
    stored: bool


async def analyze_website_performance(
    *,
    session: AsyncSession,
    performance_provider: WebsitePerformanceProvider,
    seo_provider: WebsiteSeoProvider,
    company_id: int,
    company_name: str,
    website: str,
    source_id: int | None = None,
) -> WebsitePerformanceResult:
    """
    Analyze and persist website performance and SEO data for one company.

    Flow:

        company website
            ↓
        performance analysis
            ↓
        SEO analysis
            ↓
        website performance persistence

    Transaction ownership belongs to the caller.
    """

    logger.info(
        "website_performance_started",
        company_id=company_id,
        company_name=company_name,
        website=website,
        performance_provider=performance_provider.provider_name,
        seo_provider=seo_provider.provider_name,
    )

    # ---------------------------------------------------------
    # Performance
    # ---------------------------------------------------------

    logger.info(
        "performance_analysis_started",
        company_id=company_id,
        company_name=company_name,
        website=website,
        provider=performance_provider.provider_name,
    )

    performance = await performance_provider.analyze_performance(
        website,
    )

    logger.info(
        "performance_analysis_completed",
        company_id=company_id,
        company_name=company_name,
        website=website,
        provider=performance_provider.provider_name,
    )

    # ---------------------------------------------------------
    # SEO
    # ---------------------------------------------------------

    logger.info(
        "seo_analysis_started",
        company_id=company_id,
        company_name=company_name,
        website=website,
        provider=seo_provider.provider_name,
    )

    seo = await seo_provider.analyze_seo(
        website,
    )

    logger.info(
        "seo_analysis_completed",
        company_id=company_id,
        company_name=company_name,
        website=website,
        provider=seo_provider.provider_name,
    )

    # ---------------------------------------------------------
    # Persistence
    # ---------------------------------------------------------

    await load_website_performance(
        session,
        performance,
        company_id=company_id,
        provider_name=performance_provider.provider_name,
        source_id=source_id,
        seo=seo,
    )

    logger.info(
        "website_performance_stored",
        company_id=company_id,
        company_name=company_name,
        website=website,
        performance_provider=performance_provider.provider_name,
        seo_provider=seo_provider.provider_name,
    )

    return WebsitePerformanceResult(
        analyzed=True,
        stored=True,
    )