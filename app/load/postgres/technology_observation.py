from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persistence.technology_observation import TechnologyObservation
from app.models.schemas.technology import DetectedTechnology


async def load_technology_observation(
    session: AsyncSession,
    technology: DetectedTechnology,
    *,
    company_id: int,
    provider_name: str,
    source_id: int | None = None,
    observed_at: datetime | None = None,
) -> TechnologyObservation:
    """
    Persist a detected technology observation for a company.

    Each detection is stored as a historical observation so that
    technology changes over time can be retained.
    """

    if observed_at is None:
        observed_at = datetime.now().astimezone()

    observation = TechnologyObservation(
        company_id=company_id,
        source_id=source_id,
        provider_name=provider_name,
        name=technology.name,
        version=technology.version,
        confidence=technology.confidence,
        categories=technology.categories,
        groups=technology.groups,
        observed_at=observed_at,
    )

    session.add(observation)
    await session.flush()

    return observation