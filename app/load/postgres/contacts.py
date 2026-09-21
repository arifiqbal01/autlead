from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persistence.contact_observation import ContactObservation
from app.models.schemas.contacts import ContactEvidence


async def load_contact_observation(
    session: AsyncSession,
    *,
    company_id: int,
    provider_name: str,
    kind: str,
    value: str,
    normalized_value: str,
    source_url: str | None = None,
    source_id: int | None = None,
    observed_at: datetime | None = None,
) -> ContactObservation:
    """
    Persist a contact observation for a company.

    Contact observations are stored as historical facts so that contact
    information and its provenance can be retained over time.
    """

    if observed_at is None:
        observed_at = datetime.now().astimezone()

    observation = ContactObservation(
        company_id=company_id,
        source_id=source_id,
        provider_name=provider_name,
        kind=kind,
        value=value,
        normalized_value=normalized_value,
        source_url=source_url,
        observed_at=observed_at,
    )

    session.add(observation)
    await session.flush()

    return observation