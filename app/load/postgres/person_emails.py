# app/load/postgres/person_emails.py

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persistence.person_email_observation import (
    PersonEmailObservation,
)


async def load_person_email_observation(
    session: AsyncSession,
    *,
    person_id: int,
    company_id: int,
    provider_name: str,
    email: str,
    normalized_email: str,
    source_id: int | None = None,
    confidence: float | None = None,
    verification_method: str | None = None,
    verification_result: str | None = None,
    pattern_inferred: str | None = None,
    source_urls: str | None = None,
    found_public_emails: str | None = None,
    observed_at: datetime | None = None,
) -> PersonEmailObservation:
    """
    Persist a historical person-outreach discovery observation.

    Email discovery results are stored as observations because they
    may come from multiple providers and confidence or verification
    evidence may change over time.
    """

    if observed_at is None:
        observed_at = datetime.now().astimezone()

    observation = PersonEmailObservation(
        person_id=person_id,
        company_id=company_id,
        source_id=source_id,
        provider_name=provider_name,
        email=email,
        normalized_email=normalized_email,
        confidence=confidence,
        verification_method=verification_method,
        verification_result=verification_result,
        pattern_inferred=pattern_inferred,
        source_urls=source_urls,
        found_public_emails=found_public_emails,
        observed_at=observed_at,
    )

    session.add(observation)
    await session.flush()

    return observation