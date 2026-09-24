# app/pipelines/enrichment/stages/technology.py

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.pipelines.common.technology_detection import (
    WebsiteTechnologyPipelineResult,
    run_website_technology_pipeline,
)
from app.providers.technology.protocol import (
    WebsiteTechnologyDetectionProvider,
)


logger = get_logger(__name__)


async def run_technology_stage(
    *,
    session: AsyncSession,
    provider: WebsiteTechnologyDetectionProvider,
    company_id: int,
    company_name: str,
    website: str,
    source_id: int | None = None,
    timeout: int = 30,
) -> WebsiteTechnologyPipelineResult:
    """
    Run WebArtsy technology detection for one company.

    Pipeline:

        company website
            ↓
        common technology-detection pipeline
            ↓
        technology observations persistence

    This stage owns WebArtsy-specific input preparation and logging.

    Technology detection and persistence are delegated to the common
    technology pipeline.

    Transaction ownership belongs to the caller.
    """

    websites = [
        (
            company_id,
            website,
        )
    ]

    logger.info(
        "webartsy_technology_started",
        company_id=company_id,
        company_name=company_name,
        website=website,
    )

    result = await run_website_technology_pipeline(
        provider=provider,
        websites=websites,
        session=session,
        source_id=source_id,
        timeout=timeout,
    )

    logger.info(
        "webartsy_technology_completed",
        company_id=company_id,
        company_name=company_name,
        website=website,
        detected=result.detected,
        failed=result.failed,
        stored=result.stored,
    )

    return result