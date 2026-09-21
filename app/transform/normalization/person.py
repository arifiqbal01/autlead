# app/transform/normalization/person.py

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

from app.models.schemas.people import PersonCandidate

from .person_words import (
    combined_name_particles,
    combined_name_prefixes,
    normalize_combined_title,
    normalize_language,
    name_particles,
    title_mapping,
)


_WHITESPACE_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def normalize_person(
    candidate: PersonCandidate,
    *,
    language: str = "nl",
) -> PersonCandidate:
    """
    Deterministically normalize an extracted person candidate.

    This layer only canonicalizes already-extracted values.

    It does NOT:

        - perform NER
        - discover people
        - crawl websites
        - verify identities
        - resolve entities
        - score decision makers
        - attach contact information
        - persist data
    """

    language = normalize_language(language)

    return PersonCandidate(
        name=normalize_person_name(
            candidate.name,
            language=language,
        ),
        title=normalize_person_title(
            candidate.title,
            language=language,
        ),
        linkedin_url=(
            normalize_linkedin_url(
                str(candidate.linkedin_url),
            )
            if candidate.linkedin_url
            else None
        ),
        source_url=candidate.source_url,
    )


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------


def normalize_person_name(
    value: str,
    *,
    language: str = "nl",
) -> str:
    """
    Normalize a person's name while preserving Dutch and
    international surname particles.

    Examples:

        JOHN SMITH
            -> John Smith

        JAN VAN DER BERG
            -> Jan van der Berg

        MARIA DE VRIES
            -> Maria de Vries

        PETER O'CONNOR
            -> Peter O'Connor

        ANNE-MARIE JANSEN
            -> Anne-Marie Jansen
    """

    language = normalize_language(language)

    value = _clean_text(value)

    if not value:
        return ""

    words = value.split(" ")

    particles = {
        item.casefold()
        for item in name_particles(language)
    }

    # Dutch websites frequently mix Dutch and English naming/title
    # conventions, so keep combined vocabulary available.
    particles.update(
        item.casefold()
        for item in combined_name_particles()
    )

    normalized: list[str] = []

    index = 0

    while index < len(words):
        matched_particle = _match_particle(
            words=words,
            index=index,
            particles=particles,
        )

        if matched_particle is not None:
            particle, length = matched_particle

            normalized.append(
                _normalize_particle(particle)
            )

            index += length
            continue

        normalized.append(
            _normalize_name_word(
                words[index]
            )
        )

        index += 1

    return " ".join(
        part
        for part in normalized
        if part
    )


def normalized_person_name_key(
    value: str,
    *,
    language: str = "nl",
) -> str:
    """
    Return a deterministic normalized name key.

    Useful for exact deduplication and downstream entity resolution.

    This is NOT fuzzy matching.
    """

    return normalize_person_name(
        value,
        language=language,
    ).casefold()


def _match_particle(
    *,
    words: list[str],
    index: int,
    particles: set[str],
) -> tuple[str, int] | None:
    """
    Match the longest configured surname particle.

    Examples:

        van der
        van de
        van den
        de
        van
    """

    remaining = len(words) - index

    # Longest match first.
    max_length = min(
        3,
        remaining,
    )

    for length in range(
        max_length,
        0,
        -1,
    ):
        candidate = " ".join(
            words[index:index + length]
        ).casefold()

        if candidate in particles:
            return candidate, length

    return None


def _normalize_particle(
    value: str,
) -> str:
    """Keep configured surname particles lowercase."""

    return " ".join(
        part.casefold()
        for part in value.split()
    )


def _normalize_name_word(
    value: str,
) -> str:
    """
    Normalize one name component.

    Handles:

        prefixes
        hyphenated names
        straight apostrophes
        curly apostrophes
    """

    value = value.strip()

    if not value:
        return ""

    normalized_prefix = _normalize_prefix(
        value
    )

    if normalized_prefix:
        return normalized_prefix

    # Normalize curly apostrophe variants before processing.
    value = (
        value
        .replace("‘", "'")
        .replace("’", "'")
        .replace("ʼ", "'")
    )

    if "-" in value:
        return "-".join(
            _capitalize_name_component(part)
            for part in value.split("-")
        )

    if "'" in value:
        return "'".join(
            _capitalize_name_component(part)
            for part in value.split("'")
        )

    return _capitalize_name_component(
        value
    )


def _normalize_prefix(
    value: str,
) -> str | None:
    """
    Normalize a known personal/name prefix.
    """

    normalized = value.strip().casefold()

    if not normalized:
        return None

    canonical = {
        "dr": "Dr.",
        "dr.": "Dr.",
        "mr": "Mr.",
        "mr.": "Mr.",
        "mrs": "Mrs.",
        "mrs.": "Mrs.",
        "ms": "Ms.",
        "ms.": "Ms.",
        "miss": "Miss",
        "prof": "Prof.",
        "prof.": "Prof.",
        "dhr": "Dhr.",
        "dhr.": "Dhr.",
        "mevr": "Mevr.",
        "mevr.": "Mevr.",
        "mw": "Mw.",
        "mw.": "Mw.",
        "drs": "Drs.",
        "drs.": "Drs.",
        "ir": "Ir.",
        "ir.": "Ir.",
        "ing": "Ing.",
        "ing.": "Ing.",
    }

    configured_prefixes = {
        prefix.casefold()
        for prefix in combined_name_prefixes()
    }

    if normalized not in configured_prefixes:
        return None

    return canonical.get(
        normalized,
        value,
    )


def _capitalize_name_component(
    value: str,
) -> str:
    """
    Conservatively normalize one name component.
    """

    value = value.strip()

    if not value:
        return ""

    return (
        value[:1].upper()
        + value[1:].lower()
    )


# ---------------------------------------------------------------------------
# Title normalization
# ---------------------------------------------------------------------------


def normalize_person_title(
    value: str | None,
    *,
    language: str = "nl",
) -> str | None:
    """
    Normalize a professional title.

    Dutch is the primary language, while English business titles
    remain supported because Dutch websites frequently mix both.

    Unknown titles are cleaned and preserved.
    """

    if value is None:
        return None

    language = normalize_language(language)

    value = _clean_text(value)

    if not value:
        return None

    value = value.strip(
        " -|,:;/"
    )

    if not value:
        return None

    # First try combined Dutch + English vocabulary.
    normalized = normalize_combined_title(
        value
    )

    if normalized:
        return normalized

    # Then language-specific mapping.
    normalized = title_mapping(
        language
    ).get(
        value.casefold()
    )

    if normalized:
        return normalized

    # Preserve unknown titles rather than destroying information.
    return " ".join(
        _capitalize_name_component(part)
        for part in value.split()
    )


# ---------------------------------------------------------------------------
# LinkedIn normalization
# ---------------------------------------------------------------------------


def normalize_linkedin_url(
    value: str,
) -> str | None:
    """
    Normalize a LinkedIn person-profile URL.

    Only LinkedIn /in/ profiles are accepted.

    Query parameters and fragments are discarded.
    """

    value = value.strip()

    if not value:
        return None

    # Extraction may occasionally provide linkedin.com/in/foo
    # without a scheme.
    if "://" not in value:
        value = f"https://{value}"

    parsed = urlparse(
        value
    )

    if parsed.scheme.lower() not in {
        "http",
        "https",
    }:
        return None

    hostname = (
        parsed.hostname or ""
    ).casefold()

    hostname = hostname.removeprefix(
        "www."
    )

    if hostname != "linkedin.com":
        return None

    path = parsed.path.rstrip("/")

    if not path.casefold().startswith(
        "/in/"
    ):
        return None

    profile_slug = path[4:].strip("/")

    if not profile_slug:
        return None

    # /in/person/foo must not be treated as a profile.
    if "/" in profile_slug:
        return None

    return (
        "https://www.linkedin.com/in/"
        f"{profile_slug}"
    )


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def person_identity(
    candidate: PersonCandidate,
    *,
    language: str = "nl",
) -> tuple[str, str]:
    """
    Return a deterministic identity key.

    LinkedIn is preferred because it is stronger identity evidence.

    Otherwise use the normalized person's name.

    This is exact identity/deduplication only. It is not fuzzy entity
    resolution.
    """

    linkedin_url = (
        normalize_linkedin_url(
            str(candidate.linkedin_url)
        )
        if candidate.linkedin_url
        else None
    )

    if linkedin_url:
        return (
            "linkedin",
            linkedin_url.casefold(),
        )

    return (
        "name",
        normalized_person_name_key(
            candidate.name,
            language=language,
        ),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_text(
    value: str,
) -> str:
    """
    Unicode-normalize text, collapse whitespace and trim it.
    """

    value = unicodedata.normalize(
        "NFKC",
        value,
    )

    return _WHITESPACE_RE.sub(
        " ",
        value,
    ).strip()


__all__ = [
    "normalize_linkedin_url",
    "normalize_person",
    "normalize_person_name",
    "normalize_person_title",
    "normalized_person_name_key",
    "person_identity",
]