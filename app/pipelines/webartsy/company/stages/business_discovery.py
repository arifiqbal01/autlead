# app/pipelines/webartsy/company/stages/business_discovery.py

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.schemas.discovery import DiscoveryQuery
from app.pipelines.common.business_discovery import (
    BusinessDiscoveryPipelineResult,
    run_business_discovery_pipeline,
)
from app.providers.discovery.protocol import (
    BusinessDiscoveryProvider,
)


logger = get_logger(__name__)


async def run_business_discovery_stage(
    *,
    session: AsyncSession,
    provider: BusinessDiscoveryProvider,
    query: DiscoveryQuery,
) -> BusinessDiscoveryPipelineResult:
    """
    Run WebArtsy business discovery.

    DiscoveryQuery owns:
        - query
        - location
        - limit

    The common pipeline owns:
        provider discovery
        normalization
        deduplication
        company persistence

    Transaction ownership belongs to the caller.
    """

    logger.info(
        "webartsy_business_discovery_started",
        query=query.query,
        location=query.location,
        limit=query.limit,
    )

    result = await run_business_discovery_pipeline(
        provider=provider,
        query=query,
        session=session,
    )

    logger.info(
        "webartsy_business_discovery_completed",
        query=query.query,
        location=query.location,
        limit=query.limit,
        found=result.found,
        new=result.new,
        duplicates=result.duplicates,
        stored=result.stored,
    )

    return result