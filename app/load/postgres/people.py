from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persistence.person import Person
from app.models.persistence.person_observation import PersonObservation


async def load_person(
    session: AsyncSession,
    *,
    company_id: int,
    name: str,
    normalized_name: str,
    title: str | None = None,
    linkedin_url: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> Person:
    """
    Persist a canonical person for a company.

    The person represents the current canonical identity. Historical
    discovery and decision-maker assessments are stored separately as
    PersonObservation records.
    """

    person = Person(
        company_id=company_id,
        name=name,
        normalized_name=normalized_name,
        title=title,
        linkedin_url=linkedin_url,
        email=email,
        phone=phone,
    )

    session.add(person)
    await session.flush()

    return person


async def load_person_observation(
    session: AsyncSession,
    *,
    person_id: int,
    company_id: int,
    provider_name: str,
    name: str,
    title: str | None = None,
    linkedin_url: str | None = None,
    source_url: str | None = None,
    source_id: int | None = None,
    decision_maker_score: int | None = None,
    decision_maker_role_group: str | None = None,
    decision_maker_confidence: str | None = None,
    decision_maker_reasons: str | None = None,
    observed_at: datetime | None = None,
) -> PersonObservation:
    """
    Persist a historical person observation.

    Decision-maker score, role group, confidence, and reasons are
    stored as observations because they are derived results that may
    change as scoring rules evolve.
    """

    if observed_at is None:
        observed_at = datetime.now().astimezone()

    observation = PersonObservation(
        person_id=person_id,
        company_id=company_id,
        source_id=source_id,
        provider_name=provider_name,
        source_url=source_url,
        name=name,
        title=title,
        linkedin_url=linkedin_url,
        decision_maker_score=decision_maker_score,
        decision_maker_role_group=decision_maker_role_group,
        decision_maker_confidence=decision_maker_confidence,
        decision_maker_reasons=decision_maker_reasons,
        observed_at=observed_at,
    )

    session.add(observation)
    await session.flush()

    return observation