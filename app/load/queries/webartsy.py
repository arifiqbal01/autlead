# app/queries/webartsy.py

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persistence.company import Company


@dataclass(frozen=True, slots=True)
class StoredCompany:
    company_id: int
    name: str
    website: str | None
    domain: str | None
    country: str | None
    city: str | None
    address: str | None
    category: str | None


async def get_saved_companies(
    *,
    session: AsyncSession,
    country: str | None = None,
    city: str | None = None,
    category: str | None = None,
    limit: int | None = None,
) -> list[StoredCompany]:
    """
    Read companies already persisted in PostgreSQL.

    This function:

        - does NOT call discovery providers
        - does NOT crawl websites
        - does NOT run PageSpeed
        - does NOT run technology detection
        - does NOT modify the database
    """

    statement = (
        select(Company)
        .order_by(Company.id)
    )

    if country:
        statement = statement.where(
            Company.country == country
        )

    if city:
        statement = statement.where(
            Company.city == city
        )

    if category:
        statement = statement.where(
            Company.category == category
        )

    if limit is not None:
        statement = statement.limit(limit)

    companies = list(
        (
            await session.scalars(
                statement
            )
        ).all()
    )

    return [
        StoredCompany(
            company_id=company.id,
            name=company.name,
            website=company.website,
            domain=company.domain,
            country=company.country,
            city=company.city,
            address=company.address,
            category=company.category,
        )
        for company in companies
    ]