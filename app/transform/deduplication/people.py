from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.models.schemas.people import PersonCandidate
from app.transform.normalization.person import (
    normalize_linkedin_url,
    normalize_person_name,
)


class PersonDeduplicationMatch(BaseModel):
    field: Literal[
        "linkedin",
        "name",
    ]
    value: str


def person_deduplication_matches(
    candidate: PersonCandidate,
    *,
    language: str = "nl",
) -> list[PersonDeduplicationMatch]:
    matches: list[PersonDeduplicationMatch] = []

    linkedin = (
        normalize_linkedin_url(
            str(candidate.linkedin_url)
        )
        if candidate.linkedin_url
        else None
    )

    if linkedin:
        matches.append(
            PersonDeduplicationMatch(
                field="linkedin",
                value=linkedin.casefold(),
            )
        )

    normalized_name = normalize_person_name(
        candidate.name,
        language=language,
    ).casefold()

    if normalized_name:
        matches.append(
            PersonDeduplicationMatch(
                field="name",
                value=normalized_name,
            )
        )

    return matches


__all__ = [
    "PersonDeduplicationMatch",
    "person_deduplication_matches",
]