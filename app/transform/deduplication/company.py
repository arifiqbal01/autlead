from typing import Literal

from pydantic import BaseModel

from app.models.schemas import CompanyCandidate


class CompanyDeduplicationMatch(BaseModel):
    field: Literal["domain", "phone", "name_location"]
    value: str


def company_deduplication_matches(candidate: CompanyCandidate) -> list[CompanyDeduplicationMatch]:
    matches: list[CompanyDeduplicationMatch] = []

    if candidate.domain is not None:
        matches.append(CompanyDeduplicationMatch(field="domain", value=candidate.domain))

    if candidate.phone is not None:
        matches.append(CompanyDeduplicationMatch(field="phone", value=candidate.phone))

    name_location = _name_location_key(candidate)
    if name_location is not None:
        matches.append(CompanyDeduplicationMatch(field="name_location", value=name_location))

    return matches


def _name_location_key(candidate: CompanyCandidate) -> str | None:
    location_parts = [
        part for part in (candidate.city, candidate.country, candidate.address) if part is not None
    ]
    if not location_parts:
        return None

    return "|".join([candidate.normalized_name, *location_parts])
