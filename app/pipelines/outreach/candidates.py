from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persistence.email_message import (
    EmailMessage,
)
from app.models.persistence.person_email_observation import (
    PersonEmailObservation,
)


@dataclass(frozen=True)
class EmailCandidate:
    person_id: int
    company_id: int
    email: str
    verification_result: str
    confidence: float


async def get_email_candidates(
    session: AsyncSession,
    *,
    limit: int,
    minimum_confidence: float = 0.70,
    allowed_verification_results: set[str] | None = None,
    skip_previously_sent: bool = True,
) -> list[EmailCandidate]:
    """
    Return outreach candidates eligible for further send-policy
    evaluation.

    This function performs coarse database filtering only.
    It does not send emails or make final outreach decisions.
    """

    if limit < 1:
        return []

    if allowed_verification_results is None:
        allowed_verification_results = {
            "deliverable",
        }

    if not allowed_verification_results:
        return []

    statement = (
        select(PersonEmailObservation)
        .where(
            PersonEmailObservation.verification_result.in_(
                allowed_verification_results
            ),
            PersonEmailObservation.confidence.is_not(None),
            PersonEmailObservation.confidence
            >= minimum_confidence,
        )
        .order_by(
            PersonEmailObservation.confidence.desc(),
            PersonEmailObservation.id.asc(),
        )
        .limit(limit)
    )

    if skip_previously_sent:
        already_sent = exists().where(
            EmailMessage.to_email
            == PersonEmailObservation.normalized_email
        )

        statement = statement.where(
            ~already_sent
        )

    result = await session.scalars(statement)

    observations = result.all()

    candidates: list[EmailCandidate] = []

    for observation in observations:
        if observation.confidence is None:
            continue

        candidates.append(
            EmailCandidate(
                person_id=observation.person_id,
                company_id=observation.company_id,
                email=observation.normalized_email,
                verification_result=(
                    observation.verification_result
                ),
                confidence=float(
                    observation.confidence
                ),
            )
        )

    return candidates