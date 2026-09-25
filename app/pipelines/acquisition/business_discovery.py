from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.load.postgres.companies import load_business_record
from app.models.schemas import DiscoveryQuery
from app.providers.discovery.protocol import (
    BusinessDiscoveryProvider,
)
from app.transform.normalization.business import (
    normalize_business_record,
)


logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class BusinessDiscoveryResult:
    found: int
    new: int
    duplicates: int
    stored: int


async def run_business_discovery(
    *,
    session: AsyncSession,
    provider: BusinessDiscoveryProvider,
    query: DiscoveryQuery,
) -> BusinessDiscoveryResult:
    """
    Discover businesses and persist acquisition data.

    Responsibilities:
        - provider discovery
        - normalization
        - deduplication
        - company persistence
        - source/source-record persistence

    Transaction ownership belongs to the caller.
    """

    logger.info(
        "business_discovery_started",
        provider=provider.provider_name,
        query=query.query,
        location=query.location,
        limit=query.limit,
    )

    records = await provider.discover(query)

    found = len(records)
    new = 0
    duplicates = 0
    stored = 0

    for record in records:
        candidate = normalize_business_record(
            record,
        )

        _, created = await load_business_record(
            session=session,
            record=record,
            candidate=candidate,
        )

        if created:
            new += 1
        else:
            duplicates += 1

        stored += 1

    result = BusinessDiscoveryResult(
        found=found,
        new=new,
        duplicates=duplicates,
        stored=stored,
    )

    logger.info(
        "business_discovery_completed",
        provider=provider.provider_name,
        query=query.query,
        location=query.location,
        limit=query.limit,
        found=result.found,
        new=result.new,
        duplicates=result.duplicates,
        stored=result.stored,
    )

    return result