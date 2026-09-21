# app/extract/people/candidates.py

from __future__ import annotations

import re

from app.models.schemas.people import PersonCandidate


def _normalize_name_key(
    name: str,
) -> str:
    """
    Create a deterministic exact-name key for extraction-level
    deduplication.
    """

    return re.sub(
        r"\s+",
        " ",
        name,
    ).strip().casefold()


def _normalize_linkedin_key(
    linkedin_url: object | None,
) -> str | None:
    """
    Create a deterministic LinkedIn key for extraction-level
    deduplication.
    """

    if not linkedin_url:
        return None

    return (
        str(linkedin_url)
        .strip()
        .rstrip("/")
        .casefold()
    )


def append_candidate(
    *,
    candidates: list[PersonCandidate],
    seen: set[tuple[str, str | None]],
    candidate: PersonCandidate,
) -> None:
    """
    Add a person candidate with lightweight extraction-level
    deduplication.

    Identity rules:

        1. Matching LinkedIn profile = same extracted person.
        2. Otherwise, exact normalized name = same extracted person.
        3. Prefer the more complete candidate.

    This intentionally does not perform:

        - fuzzy name matching
        - cross-company entity resolution
        - identity verification
        - decision-maker scoring
        - decision-maker selection

    More sophisticated identity resolution belongs downstream.
    """

    if not candidate.source_url:
        return

    name_key = _normalize_name_key(
        candidate.name,
    )

    if not name_key:
        return

    linkedin_key = _normalize_linkedin_key(
        candidate.linkedin_url,
    )

    # ---------------------------------------------------------
    # Find an existing exact extraction-level match
    # ---------------------------------------------------------

    existing_index = _find_existing_candidate(
        candidates=candidates,
        name_key=name_key,
        linkedin_key=linkedin_key,
    )

    if existing_index is not None:
        existing = candidates[
            existing_index
        ]

        if _candidate_completeness(
            candidate
        ) > _candidate_completeness(
            existing
        ):
            candidates[
                existing_index
            ] = candidate

        _register_seen_identity(
            seen=seen,
            name_key=name_key,
            linkedin_key=linkedin_key,
        )

        return

    # ---------------------------------------------------------
    # New candidate
    # ---------------------------------------------------------

    candidates.append(
        candidate
    )

    _register_seen_identity(
        seen=seen,
        name_key=name_key,
        linkedin_key=linkedin_key,
    )


def _find_existing_candidate(
    *,
    candidates: list[PersonCandidate],
    name_key: str,
    linkedin_key: str | None,
) -> int | None:
    """
    Find an existing candidate representing the same extracted person.

    LinkedIn is the strongest deterministic signal.

    When LinkedIn is absent, exact normalized name is used as the
    extraction-level fallback.
    """

    # ---------------------------------------------------------
    # Strongest identity: LinkedIn profile
    # ---------------------------------------------------------

    if linkedin_key is not None:
        for index, existing in enumerate(
            candidates
        ):
            existing_linkedin = (
                _normalize_linkedin_key(
                    existing.linkedin_url
                )
            )

            if (
                existing_linkedin
                == linkedin_key
            ):
                return index

    # ---------------------------------------------------------
    # Exact-name fallback
    # ---------------------------------------------------------

    for index, existing in enumerate(
        candidates
    ):
        existing_name = (
            _normalize_name_key(
                existing.name
            )
        )

        if existing_name == name_key:
            return index

    return None


def _candidate_completeness(
    candidate: PersonCandidate,
) -> int:
    """
    Score candidate completeness only for deciding which duplicate
    extraction record to retain.

    This is not lead scoring or decision-maker scoring.
    """

    score = 0

    if candidate.name:
        score += 1

    if candidate.title:
        score += 2

    if candidate.linkedin_url:
        score += 4

    if candidate.source_url:
        score += 1

    return score


def _register_seen_identity(
    *,
    seen: set[tuple[str, str | None]],
    name_key: str,
    linkedin_key: str | None,
) -> None:
    """
    Preserve the existing ``seen`` interface for callers.

    The candidate list remains the authoritative source for duplicate
    comparison because a person may first be found without LinkedIn and
    later found again with stronger LinkedIn evidence.
    """

    seen.add(
        (
            name_key,
            linkedin_key,
        )
    )


__all__ = [
    "append_candidate",
]