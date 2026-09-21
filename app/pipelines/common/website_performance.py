from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.load.postgres import load_website_performance
from app.providers.performance.protocol import (
    WebsitePerformanceProvider,
    WebsiteSeoProvider,
)


logger = get_logger(__name__)


class WebsitePerformancePipelineResult(BaseModel):
    analyzed: int
    failed: int
    stored: int


async def run_website_performance_pipeline(
    *,
    performance_provider: WebsitePerformanceProvider,
    seo_provider: WebsiteSeoProvider,
    websites: list[tuple[int, str]],
    session: AsyncSession,
    source_id: int | None = None,
) -> WebsitePerformancePipelineResult:
    analyzed = 0
    failed = 0
    stored = 0

    logger.info(
        "performance_pipeline_started",
        websites=len(websites),
        performance_provider=performance_provider.provider_name,
        seo_provider=seo_provider.provider_name,
    )

    for index, (company_id, website) in enumerate(
        websites,
        start=1,
    ):
        logger.info(
            "performance_analysis_started",
            company_id=company_id,
            website=website,
            progress=f"{index}/{len(websites)}",
        )

        try:
            # -----------------------------------------------------
            # Performance
            # -----------------------------------------------------

            performance = (
                await performance_provider.analyze_performance(
                    website,
                )
            )

            logger.info(
                "performance_analysis_completed",
                company_id=company_id,
                website=website,
                provider=performance_provider.provider_name,
                progress=f"{index}/{len(websites)}",
            )

            # -----------------------------------------------------
            # SEO
            # -----------------------------------------------------

            logger.info(
                "seo_analysis_started",
                company_id=company_id,
                website=website,
                provider=seo_provider.provider_name,
            )

            seo = await seo_provider.analyze_seo(
                website,
            )

            logger.info(
                "seo_analysis_completed",
                company_id=company_id,
                website=website,
                provider=seo_provider.provider_name,
            )

            # -----------------------------------------------------
            # Persistence
            # -----------------------------------------------------

            await load_website_performance(
                session,
                performance,
                company_id=company_id,
                provider_name=performance_provider.provider_name,
                source_id=source_id,
                seo=seo,
            )

            await session.commit()

            analyzed += 1
            stored += 1

            logger.info(
                "performance_result_stored",
                company_id=company_id,
                website=website,
                progress=f"{index}/{len(websites)}",
            )

        except Exception as exc:
            failed += 1

            await session.rollback()

            logger.error(
                "performance_analysis_failed",
                company_id=company_id,
                website=website,
                error_type=type(exc).__name__,
                error=str(exc),
                progress=f"{index}/{len(websites)}",
            )

            continue

    result = WebsitePerformancePipelineResult(
        analyzed=analyzed,
        failed=failed,
        stored=stored,
    )

    logger.info(
        "performance_pipeline_completed",
        websites=len(websites),
        analyzed=result.analyzed,
        failed=result.failed,
        stored=result.stored,
    )

    return result