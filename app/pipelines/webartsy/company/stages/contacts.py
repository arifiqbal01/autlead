# app/pipelines/enrichment/stages/contacts.py

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.pipelines.common.contacts import (
    ContactAnalysisResult,
    analyze_contacts,
)


logger = get_logger(__name__)


async def run_contacts_stage(
    *,
    session: AsyncSession,
    company_id: int,
    company_name: str,
    pages: list,
    provider_name: str,
    phone_region: str | None = None,
    source_id: int | None = None,
) -> ContactAnalysisResult:
    """
    Run WebArtsy contact extraction and persistence for one company.

    Pipeline:

        crawled business pages
            ↓
        common contact extraction
            ↓
        deterministic normalization + deduplication
            ↓
        contact observation persistence

    This stage owns WebArtsy-specific input preparation and logging.

    Contact extraction, normalization, deduplication, and persistence
    are delegated to the common contacts pipeline.

    Transaction ownership belongs to the caller.
    """

    logger.info(
        "webartsy_contacts_started",
        company_id=company_id,
        company_name=company_name,
        pages=len(pages),
        provider=provider_name,
    )

    result = await analyze_contacts(
        session=session,
        company_id=company_id,
        pages=pages,
        provider_name=provider_name,
        phone_region=phone_region,
        source_id=source_id,
    )

    logger.info(
        "webartsy_contacts_completed",
        company_id=company_id,
        company_name=company_name,
        pages=len(pages),
        extracted=result.extracted_count,
        normalized=result.normalized_count,
        discarded=result.discarded_count,
        persisted=result.persisted_count,
    )

    return result