from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.persistence.person import Person
from app.models.persistence.person_observation import (
    PersonObservation,
)
from app.pipelines.common.person_email import (
    PersonEmailAnalysisResult,
    PersonEmailTarget,
    analyze_person_emails,
)
from app.providers.email.verification import (
    EmailVerificationProvider,
)


logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Persisted person target
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PersistedPerson:
    person_id: int
    name: str
    email: str | None
    title: str | None
    linkedin_url: str | None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_person_email_stage(
    *,
    session: AsyncSession,
    provider: EmailVerificationProvider,
    company_id: int,
    company_name: str,
    company_domain: str,
    source_id: int | None = None,
    person_limit: int | None = None,
) -> PersonEmailAnalysisResult:
    """
    Verify or derive email addresses for persisted people.

    Flow:

        persisted person
            ↓
        existing email?
            ├── yes → verify existing email
            └── no  → generate deterministic candidates from
                      person name + company domain
            ↓
        verification
            ↓
        qualification
            ↓
        persistence

    Email verification applies independently of decision-maker
    classification.
    """

    people = await _load_people(
        session,
        company_id=company_id,
        limit=person_limit,
    )

    targets = [
        PersonEmailTarget(
            person_id=person.person_id,
            company_id=company_id,
            person_name=person.name,
            company_domain=company_domain,
            email=person.email,
            source_urls=(
                (person.linkedin_url,)
                if person.linkedin_url
                else ()
            ),
        )
        for person in people
    ]

    logger.info(
        "webartsy_person_email_targets_selected",
        company_id=company_id,
        company_name=company_name,
        company_domain=company_domain,
        targets=len(targets),
    )

    return await analyze_person_emails(
        session=session,
        provider=provider,
        targets=targets,
        source_id=source_id,
    )


# ---------------------------------------------------------------------------
# Persisted people loading
# ---------------------------------------------------------------------------


async def _load_people(
    session: AsyncSession,
    *,
    company_id: int,
    limit: int | None = None,
) -> list[PersistedPerson]:
    """
    Load all persisted people for a company.

    People without an existing email must also be included because
    the common pipeline can generate deterministic candidates from
    their name and the company domain.
    """

    statement = (
        select(
            Person,
            PersonObservation,
        )
        .outerjoin(
            PersonObservation,
            PersonObservation.person_id == Person.id,
        )
        .where(
            Person.company_id == company_id,
        )
        .order_by(
            Person.id.asc(),
            PersonObservation.observed_at.desc(),
        )
    )

    rows = (
        await session.execute(
            statement
        )
    ).all()

    people: list[PersistedPerson] = []
    seen_person_ids: set[int] = set()

    for person, observation in rows:
        if person.id in seen_person_ids:
            continue

        seen_person_ids.add(
            person.id
        )

        name = (
            person.name.strip()
            if person.name
            else ""
        )

        if not name:
            logger.debug(
                "webartsy_person_email_person_skipped",
                company_id=company_id,
                person_id=person.id,
                reason="missing_name",
            )
            continue

        email = (
            person.email.strip()
            if person.email
            else None
        )

        if email == "":
            email = None

        title = (
            observation.title
            if observation
            and observation.title
            else person.title
        )

        linkedin_url = (
            observation.linkedin_url
            if observation
            and observation.linkedin_url
            else person.linkedin_url
        )

        people.append(
            PersistedPerson(
                person_id=person.id,
                name=name,
                email=email,
                title=title,
                linkedin_url=linkedin_url,
            )
        )

        if (
            limit is not None
            and len(people) >= limit
        ):
            break

    logger.info(
        "webartsy_people_for_email_verification_loaded",
        company_id=company_id,
        people=len(people),
        with_email=sum(
            1
            for person in people
            if person.email
        ),
        without_email=sum(
            1
            for person in people
            if not person.email
        ),
    )

    return people