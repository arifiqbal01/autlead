from typing import cast

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persistence import Company, Source, SourceRecord
from app.models.schemas import BusinessRecord, CompanyCandidate
from app.transform.deduplication import CompanyDeduplicationMatch, company_deduplication_matches


async def load_business_record(
    session: AsyncSession,
    record: BusinessRecord,
    candidate: CompanyCandidate,
) -> tuple[Company, bool]:
    company = await _find_existing_company(session, candidate)
    created = company is None

    if company is None:
        company = Company(
            name=candidate.name,
            normalized_name=candidate.normalized_name,
            website=candidate.website,
            domain=candidate.domain,
            phone=candidate.phone,
            country=candidate.country,
            city=candidate.city,
            address=candidate.address,
            category=candidate.category,
        )
        session.add(company)
        await session.flush()
    else:
        _fill_missing_company_values(company, candidate)

    source = await _get_or_create_source(session, record)
    await _record_source_provenance(session, record, source, company)

    return company, created


async def _find_existing_company(
    session: AsyncSession,
    candidate: CompanyCandidate,
) -> Company | None:
    for match in company_deduplication_matches(candidate):
        company = await _find_company_by_match(session, candidate, match)
        if company is not None:
            return company

    return None


async def _find_company_by_match(
    session: AsyncSession,
    candidate: CompanyCandidate,
    match: CompanyDeduplicationMatch,
) -> Company | None:
    if match.field == "domain":
        statement = select(Company).where(Company.domain == match.value)
    elif match.field == "phone":
        statement = select(Company).where(Company.phone == match.value)
    else:
        conditions = [Company.normalized_name == candidate.normalized_name]
        if candidate.city is not None:
            conditions.append(Company.city == candidate.city)
        if candidate.country is not None:
            conditions.append(Company.country == candidate.country)
        if candidate.address is not None:
            conditions.append(Company.address == candidate.address)

        statement = select(Company).where(and_(*conditions))

    return cast(Company | None, await session.scalar(statement))


def _fill_missing_company_values(company: Company, candidate: CompanyCandidate) -> None:
    for field_name in (
        "website",
        "domain",
        "phone",
        "country",
        "city",
        "address",
        "category",
    ):
        current_value = getattr(company, field_name)
        new_value = getattr(candidate, field_name)
        if current_value is None and new_value is not None:
            setattr(company, field_name, new_value)


async def _get_or_create_source(session: AsyncSession, record: BusinessRecord) -> Source:
    source = await session.scalar(select(Source).where(Source.name == record.source_name))
    if source is not None:
        return source

    source = Source(
        name=record.source_name,
        source_type=record.source_type,
    )
    session.add(source)
    await session.flush()
    return source


async def _record_source_provenance(
    session: AsyncSession,
    record: BusinessRecord,
    source: Source,
    company: Company,
) -> None:
    source_record = await _find_source_record(session, source, record)
    if source_record is None:
        source_record = SourceRecord(
            source_id=source.id,
            company_id=company.id,
            provider_name=record.provider_name,
            external_id=record.external_id,
            raw_data=record.raw_data,
            collected_at=record.collected_at,
        )
        session.add(source_record)
        return

    source_record.company_id = company.id
    source_record.raw_data = record.raw_data
    source_record.collected_at = record.collected_at


async def _find_source_record(
    session: AsyncSession,
    source: Source,
    record: BusinessRecord,
) -> SourceRecord | None:
    if record.external_id is None:
        return None

    return cast(
        SourceRecord | None,
        await session.scalar(
            select(SourceRecord).where(
                SourceRecord.source_id == source.id,
                SourceRecord.external_id == record.external_id,
            )
        ),
    )
