from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.load.postgres import load_business_record
from app.models.schemas import DiscoveryQuery
from app.providers.discovery import BusinessDiscoveryProvider
from app.transform.normalization import normalize_business_record


logger = get_logger(__name__)


class DiscoveredCompany(BaseModel):
    company_id: int
    name: str
    website: str | None
    domain: str | None


class BusinessDiscoveryPipelineResult(BaseModel):
    found: int
    new: int
    duplicates: int
    stored: int
    companies: list[DiscoveredCompany]


async def run_business_discovery_pipeline(
    *,
    provider: BusinessDiscoveryProvider,
    query: DiscoveryQuery,
    session: AsyncSession,
) -> BusinessDiscoveryPipelineResult:
    # =========================================================
    # Discovery
    # =========================================================

    logger.info(
        "discovery_started",
        query=query.query,
        location=query.location,
        limit=query.limit,
        provider=provider.__class__.__name__,
    )

    records = await provider.discover(query)

    logger.info(
        "discovery_completed",
        query=query.query,
        location=query.location,
        found=len(records),
    )

    new_count = 0
    duplicate_count = 0
    companies: list[DiscoveredCompany] = []

    # =========================================================
    # Persistence
    # =========================================================

    logger.info(
        "discovery_persistence_started",
        records=len(records),
    )

    async with session.begin():
        for record in records:
            candidate = normalize_business_record(record)

            company, created = await load_business_record(
                session,
                record,
                candidate,
            )

            if created:
                new_count += 1
            else:
                duplicate_count += 1

            companies.append(
                DiscoveredCompany(
                    company_id=company.id,
                    name=company.name,
                    website=(
                        str(company.website)
                        if company.website
                        else None
                    ),
                    domain=(
                        str(company.domain)
                        if company.domain
                        else None
                    ),
                )
            )

    # =========================================================
    # Pipeline result
    # =========================================================

    result = BusinessDiscoveryPipelineResult(
        found=len(records),
        new=new_count,
        duplicates=duplicate_count,
        stored=len(companies),
        companies=companies,
    )

    logger.info(
        "discovery_pipeline_completed",
        query=query.query,
        location=query.location,
        found=result.found,
        new=result.new,
        duplicates=result.duplicates,
        stored=result.stored,
        companies_with_websites=sum(
            1
            for company in result.companies
            if company.website
        ),
    )

    return result