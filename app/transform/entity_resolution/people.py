# app/transform/entity_resolution/people.py

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from urllib.parse import urlparse

from app.models.schemas.people import PersonCandidate
from app.transform.normalization.person import (
    normalize_linkedin_url,
    normalize_person_name,
)


AUTO_MERGE_THRESHOLD = 0.92
POSSIBLE_MATCH_THRESHOLD = 0.75


@dataclass(frozen=True, slots=True)
class PersonMatch:
    """
    Relationship between two person candidates.

    Relations:

        same
        possible
        different
    """

    left: PersonCandidate
    right: PersonCandidate
    score: float
    relation: str


@dataclass(frozen=True, slots=True)
class ResolvedPerson:
    """
    Canonical person plus all source candidates that contributed
    to the resolved identity.
    """

    person: PersonCandidate
    sources: tuple[PersonCandidate, ...]


def compare_people(
    left: PersonCandidate,
    right: PersonCandidate,
    *,
    language: str = "nl",
) -> PersonMatch:
    """
    Compare two normalized/extracted people conservatively.

    Resolution priority:

        1. Same LinkedIn profile
        2. Conflicting LinkedIn profiles
        3. Exact normalized name
        4. Strong fuzzy name + supporting evidence
        5. Possible fuzzy match
        6. Different

    Fuzzy similarity by itself never auto-merges.
    """

    left_linkedin = _linkedin_key(
        left
    )

    right_linkedin = _linkedin_key(
        right
    )

    # ---------------------------------------------------------
    # Strongest identity evidence: LinkedIn
    # ---------------------------------------------------------

    if (
        left_linkedin
        and right_linkedin
        and left_linkedin == right_linkedin
    ):
        return PersonMatch(
            left=left,
            right=right,
            score=1.0,
            relation="same",
        )

    if (
        left_linkedin
        and right_linkedin
        and left_linkedin != right_linkedin
    ):
        return PersonMatch(
            left=left,
            right=right,
            score=0.0,
            relation="different",
        )

    # ---------------------------------------------------------
    # Canonical names
    # ---------------------------------------------------------

    left_name = _name_key(
        left,
        language=language,
    )

    right_name = _name_key(
        right,
        language=language,
    )

    if not left_name or not right_name:
        return PersonMatch(
            left=left,
            right=right,
            score=0.0,
            relation="different",
        )

    if left_name == right_name:
        return PersonMatch(
            left=left,
            right=right,
            score=1.0,
            relation="same",
        )

    # ---------------------------------------------------------
    # Fuzzy similarity
    # ---------------------------------------------------------

    name_score = SequenceMatcher(
        None,
        left_name,
        right_name,
    ).ratio()

    if name_score >= AUTO_MERGE_THRESHOLD:
        if _has_supporting_identity_evidence(
            left,
            right,
        ):
            return PersonMatch(
                left=left,
                right=right,
                score=name_score,
                relation="same",
            )

        return PersonMatch(
            left=left,
            right=right,
            score=name_score,
            relation="possible",
        )

    if name_score >= POSSIBLE_MATCH_THRESHOLD:
        return PersonMatch(
            left=left,
            right=right,
            score=name_score,
            relation="possible",
        )

    return PersonMatch(
        left=left,
        right=right,
        score=name_score,
        relation="different",
    )


def resolve_people(
    people: list[PersonCandidate],
    *,
    language: str = "nl",
) -> list[ResolvedPerson]:
    """
    Resolve duplicate person candidates conservatively.

    Automatically merges:

        - matching LinkedIn profiles
        - exact normalized names
        - very strong fuzzy matches only with supporting evidence

    Possible fuzzy matches are kept separate.
    """

    resolved: list[ResolvedPerson] = []

    for person in people:
        matched_index: int | None = None

        for index, existing in enumerate(
            resolved
        ):
            match = compare_people(
                person,
                existing.person,
                language=language,
            )

            if match.relation == "same":
                matched_index = index
                break

        if matched_index is None:
            resolved.append(
                ResolvedPerson(
                    person=person,
                    sources=(person,),
                )
            )
            continue

        existing = resolved[
            matched_index
        ]

        canonical = _choose_canonical_person(
            existing.person,
            person,
        )

        resolved[
            matched_index
        ] = ResolvedPerson(
            person=canonical,
            sources=(
                *existing.sources,
                person,
            ),
        )

    return resolved


def _choose_canonical_person(
    left: PersonCandidate,
    right: PersonCandidate,
) -> PersonCandidate:
    """
    Select the richer representation of the same resolved person.
    """

    linkedin_url = (
        left.linkedin_url
        or right.linkedin_url
    )

    title = _choose_title(
        left.title,
        right.title,
    )

    name = max(
        (
            left.name,
            right.name,
        ),
        key=_name_quality,
    )

    source_url = (
        left.source_url
        or right.source_url
    )

    return PersonCandidate(
        name=name,
        title=title,
        linkedin_url=linkedin_url,
        source_url=source_url,
    )


def _choose_title(
    left: str | None,
    right: str | None,
) -> str | None:
    if not left:
        return right

    if not right:
        return left

    return max(
        (
            left,
            right,
        ),
        key=lambda value: (
            len(value.split()),
            len(value),
        ),
    )


def _has_supporting_identity_evidence(
    left: PersonCandidate,
    right: PersonCandidate,
) -> bool:
    """
    Require additional evidence before fuzzy auto-merge.

    Supporting evidence:

        - same source page
        - same source domain
        - one candidate has LinkedIn while the other does not
        - compatible professional titles
    """

    left_source = _source_key(
        left
    )

    right_source = _source_key(
        right
    )

    if (
        left_source
        and right_source
        and left_source == right_source
    ):
        return True

    left_domain = _source_domain(
        left
    )

    right_domain = _source_domain(
        right
    )

    if (
        left_domain
        and right_domain
        and left_domain == right_domain
    ):
        return True

    left_linkedin = _linkedin_key(
        left
    )

    right_linkedin = _linkedin_key(
        right
    )

    if bool(left_linkedin) != bool(
        right_linkedin
    ):
        return True

    if _titles_compatible(
        left.title,
        right.title,
    ):
        return True

    return False


def _titles_compatible(
    left: str | None,
    right: str | None,
) -> bool:
    """
    Treat equal or strongly overlapping titles as supporting evidence.
    """

    if not left or not right:
        return False

    left_key = " ".join(
        left.casefold().split()
    )

    right_key = " ".join(
        right.casefold().split()
    )

    if left_key == right_key:
        return True

    return (
        left_key in right_key
        or right_key in left_key
    )


def _linkedin_key(
    person: PersonCandidate,
) -> str | None:
    if not person.linkedin_url:
        return None

    normalized = normalize_linkedin_url(
        str(person.linkedin_url)
    )

    if normalized is None:
        return None

    return normalized.casefold()


def _source_key(
    person: PersonCandidate,
) -> str | None:
    if not person.source_url:
        return None

    value = str(
        person.source_url
    ).strip()

    if not value:
        return None

    parsed = urlparse(
        value
    )

    if not parsed.hostname:
        return value.casefold().rstrip("/")

    hostname = (
        parsed.hostname
        .casefold()
        .removeprefix("www.")
    )

    path = (
        parsed.path
        .rstrip("/")
        .casefold()
    )

    return f"{hostname}{path}"


def _source_domain(
    person: PersonCandidate,
) -> str | None:
    if not person.source_url:
        return None

    parsed = urlparse(
        str(person.source_url)
    )

    hostname = (
        parsed.hostname or ""
    ).casefold().removeprefix(
        "www."
    )

    return hostname or None


def _name_key(
    person: PersonCandidate,
    *,
    language: str,
) -> str:
    return normalize_person_name(
        person.name,
        language=language,
    ).casefold()


def _name_quality(
    value: str,
) -> tuple[int, int]:
    words = value.split()

    return (
        len(words),
        len(value),
    )


__all__ = [
    "AUTO_MERGE_THRESHOLD",
    "POSSIBLE_MATCH_THRESHOLD",
    "PersonMatch",
    "ResolvedPerson",
    "compare_people",
    "resolve_people",
]