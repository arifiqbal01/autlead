from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.persistence.company import Company
from app.models.persistence.source import (
    Source,
    SourceRecord,
)
from app.pipelines.acquisition.models import (
    BusinessRecord,
    DiscoveryQuery,
)
from app.providers.discovery.protocol import (
    BusinessDiscoveryProvider,
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
        business = BusinessRecord.model_validate(
            record,
        )

        source = await _get_or_create_source(
            session=session,
            record=business,
        )

        existing_company = await _find_existing_company(
            session=session,
            record=business,
        )

        if existing_company is not None:
            duplicates += 1

            await _persist_source_record(
                session=session,
                source=source,
                company=existing_company,
                record=business,
            )

            stored += 1
            continue

        company = Company(
            name=business.name,
            website=business.website,
            domain=business.domain,
            phone=business.phone,
            country=business.country,
            city=business.city,
            address=business.address,
            category=business.category,
        )

        session.add(company)
        await session.flush()

        await _persist_source_record(
            session=session,
            source=source,
            company=company,
            record=business,
        )

        new += 1
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


async def _get_or_create_source(
    *,
    session: AsyncSession,
    record: BusinessRecord,
) -> Source:
    result = await session.execute(
        select(Source).where(
            Source.name == record.source_name,
        )
    )

    source = result.scalar_one_or_none()

    if source is not None:
        return source

    source = Source(
        name=record.source_name,
        source_type=record.source_type,
    )

    session.add(source)
    await session.flush()

    return source


async def _find_existing_company(
    *,
    session: AsyncSession,
    record: BusinessRecord,
) -> Company | None:
    if record.domain:
        result = await session.execute(
            select(Company).where(
                Company.domain == record.domain,
            )
        )

        company = result.scalar_one_or_none()

        if company is not None:
            return company

    if record.website:
        result = await session.execute(
            select(Company).where(
                Company.website == record.website,
            )
        )

        company = result.scalar_one_or_none()

        if company is not None:
            return company

    return None


async def _persist_source_record(
    *,
    session: AsyncSession,
    source: Source,
    company: Company,
    record: BusinessRecord,
) -> None:
    if record.external_id:
        result = await session.execute(
            select(SourceRecord).where(
                SourceRecord.source_id == source.id,
                SourceRecord.external_id == record.external_id,
            )
        )

        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.company_id = company.id
            existing.provider_name = record.provider_name
            existing.raw_data = record.raw_data
            existing.collected_at = record.collected_at
            return

    session.add(
        SourceRecord(
            source_id=source.id,
            company_id=company.id,
            provider_name=record.provider_name,
            external_id=record.external_id,
            raw_data=record.raw_data,
            collected_at=record.collected_at,
        )
    )

    # Temporary compatibility alias.
    # Remove after the WebArtsy pipeline is migrated to enrichment.
    BusinessDiscoveryPipelineResult = BusinessDiscoveryResult