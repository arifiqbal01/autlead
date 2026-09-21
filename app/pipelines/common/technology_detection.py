from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.load.postgres.technology_observation import (
    load_technology_observation,
)
from app.providers.technology.protocol import (
    WebsiteTechnologyDetectionProvider,
)


logger = get_logger(__name__)


class WebsiteTechnologyPipelineResult(BaseModel):
    detected: int
    failed: int
    stored: int


async def _process_website(
    *,
    provider: WebsiteTechnologyDetectionProvider,
    company_id: int,
    website: str,
    session: AsyncSession,
    source_id: int | None = None,
    timeout: int = 30,
    progress: str,
) -> tuple[int, int, bool]:
    logger.info(
        "technology_detection_started",
        company_id=company_id,
        website=website,
        progress=progress,
    )

    try:
        technologies = await provider.detect(
            website,
            timeout=timeout,
        )

        technology_count = len(technologies)

        logger.info(
            "technology_detection_completed",
            company_id=company_id,
            website=website,
            detected=technology_count,
            progress=progress,
        )

        company_stored = 0

        async with session.begin():
            for technology in technologies:
                await load_technology_observation(
                    session,
                    technology,
                    company_id=company_id,
                    provider_name=provider.provider_name,
                    source_id=source_id,
                )

                company_stored += 1

        logger.info(
            "technology_observations_stored",
            company_id=company_id,
            website=website,
            stored=company_stored,
        )

        return technology_count, company_stored, False

    except Exception as exc:
        await session.rollback()

        logger.error(
            "technology_detection_failed",
            company_id=company_id,
            website=website,
            error_type=type(exc).__name__,
            error=str(exc),
            progress=progress,
        )

        return 0, 0, True


async def run_website_technology_pipeline(
    *,
    provider: WebsiteTechnologyDetectionProvider,
    websites: list[tuple[int, str]],
    session: AsyncSession,
    source_id: int | None = None,
    timeout: int = 30,
) -> WebsiteTechnologyPipelineResult:
    detected = 0
    failed = 0
    stored = 0

    logger.info(
        "technology_pipeline_started",
        provider=provider.provider_name,
        websites=len(websites),
        timeout=timeout,
    )

    total_websites = len(websites)

    for index, (company_id, website) in enumerate(
        websites,
        start=1,
    ):
        company_detected, company_stored, company_failed = (
            await _process_website(
                provider=provider,
                company_id=company_id,
                website=website,
                session=session,
                source_id=source_id,
                timeout=timeout,
                progress=f"{index}/{total_websites}",
            )
        )

        detected += company_detected
        stored += company_stored

        if company_failed:
            failed += 1

    result = WebsiteTechnologyPipelineResult(
        detected=detected,
        failed=failed,
        stored=stored,
    )

    logger.info(
        "technology_pipeline_completed",
        provider=provider.provider_name,
        websites=len(websites),
        detected=result.detected,
        failed=result.failed,
        stored=result.stored,
    )

    return result