# app/pipelines/enrichment/technology_detection.py

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.load.postgres.technology_observation import (
    load_technology_observation,
)
from app.providers.technology.protocol import (
    WebsiteTechnologyDetectionProvider,
)


logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TechnologyDetectionResult:
    detected: int
    stored: int


async def analyze_technology(
    *,
    session: AsyncSession,
    provider: WebsiteTechnologyDetectionProvider,
    company_id: int,
    company_name: str,
    website: str,
    source_id: int | None = None,
    timeout: int = 30,
) -> TechnologyDetectionResult:
    """
    Detect and persist website technologies for one company.

    Flow:

        company website
            ↓
        technology detection provider
            ↓
        detected technologies
            ↓
        technology observation persistence

    Transaction ownership belongs to the caller.
    """

    logger.info(
        "technology_detection_started",
        company_id=company_id,
        company_name=company_name,
        website=website,
        provider=provider.provider_name,
        timeout=timeout,
    )

    technologies = await provider.detect(
        website,
        timeout=timeout,
    )

    detected = len(technologies)

    logger.info(
        "technology_detection_completed",
        company_id=company_id,
        company_name=company_name,
        website=website,
        provider=provider.provider_name,
        detected=detected,
    )

    stored = 0

    for technology in technologies:
        await load_technology_observation(
            session,
            technology,
            company_id=company_id,
            provider_name=provider.provider_name,
            source_id=source_id,
        )

        stored += 1

    logger.info(
        "technology_observations_stored",
        company_id=company_id,
        company_name=company_name,
        website=website,
        provider=provider.provider_name,
        stored=stored,
    )

    return TechnologyDetectionResult(
        detected=detected,
        stored=stored,
    )