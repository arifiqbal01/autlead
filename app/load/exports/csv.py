import csv
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persistence import Company, Source, SourceRecord

LEAD_EXPORT_FIELDS = [
    "company_name",
    "website",
    "domain",
    "phone",
    "city",
    "country",
    "address",
    "category",
    "source",
    "created_at",
]


class LeadExportRow(BaseModel):
    company_name: str
    website: str | None = None
    domain: str | None = None
    phone: str | None = None
    city: str | None = None
    country: str | None = None
    address: str | None = None
    category: str | None = None
    source: str | None = None
    created_at: datetime


async def export_leads_csv(session: AsyncSession, output_path: Path) -> int:
    rows = await fetch_lead_export_rows(session)
    write_lead_rows_csv(rows, output_path)
    return len(rows)


async def fetch_lead_export_rows(session: AsyncSession) -> list[LeadExportRow]:
    source_name = (
        select(Source.name)
        .join(SourceRecord, SourceRecord.source_id == Source.id)
        .where(SourceRecord.company_id == Company.id)
        .order_by(SourceRecord.collected_at.asc(), SourceRecord.id.asc())
        .limit(1)
        .scalar_subquery()
    )

    statement = select(
        Company.name,
        Company.website,
        Company.domain,
        Company.phone,
        Company.city,
        Company.country,
        Company.address,
        Company.category,
        source_name.label("source"),
        Company.created_at,
    ).order_by(Company.created_at.asc(), Company.id.asc())

    result = await session.execute(statement)
    return [
        LeadExportRow(
            company_name=row.name,
            website=row.website,
            domain=row.domain,
            phone=row.phone,
            city=row.city,
            country=row.country,
            address=row.address,
            category=row.category,
            source=row.source,
            created_at=row.created_at,
        )
        for row in result
    ]


def write_lead_rows_csv(rows: Iterable[LeadExportRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=LEAD_EXPORT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(_serialize_row(row))


def _serialize_row(row: LeadExportRow) -> dict[str, Any]:
    data = row.model_dump(mode="json")
    return {field: data[field] if data[field] is not None else "" for field in LEAD_EXPORT_FIELDS}
