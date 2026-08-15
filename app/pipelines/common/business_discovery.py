from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.load.postgres import load_business_record
from app.models.schemas import DiscoveryQuery
from app.providers.discovery import BusinessDiscoveryProvider
from app.transform.normalization import normalize_business_record


class BusinessDiscoveryPipelineResult(BaseModel):
    found: int
    new: int
    duplicates: int
    stored: int


async def run_business_discovery_pipeline(
    *,
    provider: BusinessDiscoveryProvider,
    query: DiscoveryQuery,
    session: AsyncSession,
) -> BusinessDiscoveryPipelineResult:
    records = await provider.discover(query)
    new_count = 0
    duplicate_count = 0

    async with session.begin():
        for record in records:
            candidate = normalize_business_record(record)
            _company, created = await load_business_record(session, record, candidate)
            if created:
                new_count += 1
            else:
                duplicate_count += 1

    return BusinessDiscoveryPipelineResult(
        found=len(records),
        new=new_count,
        duplicates=duplicate_count,
        stored=len(records),
    )
