from __future__ import annotations

from app.core.database.session import SessionFactory
from app.core.logging import get_logger
from app.pipelines.acquisition.business_discovery import (
    BusinessDiscoveryResult,
    run_business_discovery,
)
from app.pipelines.acquisition.models import (
    DiscoveryQuery,
)
from app.providers.discovery.protocol import (
    BusinessDiscoveryProvider,
)


logger = get_logger(__name__)


async def run_acquisition_pipeline(
    *,
    provider: BusinessDiscoveryProvider,
    query: DiscoveryQuery,
) -> BusinessDiscoveryResult:
    """
    Run one acquisition flow.

    Acquisition ends after discovered businesses
    have been persisted.

    No enrichment or outreach is performed here.
    """

    logger.info(
        "acquisition_started",
        provider=provider.provider_name,
        query=query.query,
        location=query.location,
        limit=query.limit,
    )

    async with SessionFactory() as session:
        try:
            result = await run_business_discovery(
                session=session,
                provider=provider,
                query=query,
            )

            await session.commit()

        except Exception:
            await session.rollback()

            logger.exception(
                "acquisition_failed",
                provider=provider.provider_name,
                query=query.query,
                location=query.location,
            )

            raise

    logger.info(
        "acquisition_completed",
        provider=provider.provider_name,
        query=query.query,
        location=query.location,
        found=result.found,
        new=result.new,
        duplicates=result.duplicates,
        stored=result.stored,
    )

    return result