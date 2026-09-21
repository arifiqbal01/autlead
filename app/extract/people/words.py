# app/extract/people/words.py

from __future__ import annotations

from app.transform.normalization.person_words import (
    COMBINED_DECISION_MAKER_ROLES,
    DECISION_MAKER_ROLES,
    LANGUAGE_ALIASES,
    NAME_CREDENTIALS,
    NAME_PARTICLES,
    NAME_PREFIXES,
    PERSON_TITLES,
    SENTENCE_WORDS,
    SUPPORTED_LANGUAGES,
    WEBSITE_WORDS,
)


# ---------------------------------------------------------------------------
# Language
# ---------------------------------------------------------------------------


def normalize_language(
    language: str | None,
) -> str:
    """
    Return the canonical language code.

    Unknown languages fall back to English.
    """

    if not language:
        return "en"

    value = language.strip().casefold()

    return LANGUAGE_ALIASES.get(
        value,
        "en",
    )


# ---------------------------------------------------------------------------
# Person titles
# ---------------------------------------------------------------------------


def person_titles(
    language: str | None = None,
) -> frozenset[str]:
    """
    Return person titles for a specific language.
    """

    language = normalize_language(
        language
    )

    return PERSON_TITLES[
        language
    ]


def combined_person_titles() -> frozenset[str]:
    """
    Return person titles across all supported languages.

    Useful for website extraction because websites may mix
    Dutch and English terminology.
    """

    return frozenset(
        title
        for titles in PERSON_TITLES.values()
        for title in titles
    )


# ---------------------------------------------------------------------------
# Decision-maker roles
# ---------------------------------------------------------------------------


def decision_maker_roles(
    language: str | None = None,
) -> frozenset[str]:
    """
    Return decision-maker roles for a specific language.
    """

    language = normalize_language(
        language
    )

    return DECISION_MAKER_ROLES[
        language
    ]


def combined_decision_maker_roles() -> frozenset[str]:
    """
    Return decision-maker roles across supported languages.
    """

    return COMBINED_DECISION_MAKER_ROLES


# ---------------------------------------------------------------------------
# Name particles
# ---------------------------------------------------------------------------


def name_particles(
    language: str | None = None,
) -> frozenset[str]:
    """
    Return surname particles for a specific language.

    Examples:

        van
        van der
        de
        den
        der
    """

    language = normalize_language(
        language
    )

    return NAME_PARTICLES[
        language
    ]


def combined_name_particles() -> frozenset[str]:
    """
    Return surname particles across supported languages.
    """

    return frozenset(
        particle
        for particles in NAME_PARTICLES.values()
        for particle in particles
    )


# ---------------------------------------------------------------------------
# Name prefixes
# ---------------------------------------------------------------------------


def name_prefixes(
    language: str | None = None,
) -> frozenset[str]:
    """
    Return name prefixes for a specific language.
    """

    language = normalize_language(
        language
    )

    return NAME_PREFIXES[
        language
    ]


def combined_name_prefixes() -> frozenset[str]:
    """
    Return name prefixes across supported languages.
    """

    return frozenset(
        prefix
        for prefixes in NAME_PREFIXES.values()
        for prefix in prefixes
    )


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------


def name_credentials() -> frozenset[str]:
    """
    Return configured academic/professional credentials.

    Credentials are not considered part of a person's canonical name.
    """

    return NAME_CREDENTIALS


# ---------------------------------------------------------------------------
# Website / UI vocabulary
# ---------------------------------------------------------------------------


def website_words(
    language: str | None = None,
) -> frozenset[str]:
    """
    Return website/UI vocabulary for a specific language.

    Used to reject obvious navigation, marketing, and interface
    fragments that resemble names.
    """

    language = normalize_language(
        language
    )

    return WEBSITE_WORDS[
        language
    ]


def combined_website_words() -> frozenset[str]:
    """
    Return website/UI vocabulary across supported languages.
    """

    return frozenset(
        word
        for words in WEBSITE_WORDS.values()
        for word in words
    )


# ---------------------------------------------------------------------------
# Sentence vocabulary
# ---------------------------------------------------------------------------


def sentence_words(
    language: str | None = None,
) -> frozenset[str]:
    """
    Return common sentence vocabulary for a specific language.

    Used during extraction-level false-positive filtering.
    """

    language = normalize_language(
        language
    )

    return SENTENCE_WORDS[
        language
    ]


def combined_sentence_words() -> frozenset[str]:
    """
    Return sentence vocabulary across supported languages.
    """

    return frozenset(
        word
        for words in SENTENCE_WORDS.values()
        for word in words
    )


# ---------------------------------------------------------------------------
# Language metadata
# ---------------------------------------------------------------------------


def supported_languages() -> frozenset[str]:
    """
    Return supported canonical languages.
    """

    return SUPPORTED_LANGUAGES


__all__ = [
    "combined_decision_maker_roles",
    "combined_name_particles",
    "combined_name_prefixes",
    "combined_person_titles",
    "combined_sentence_words",
    "combined_website_words",
    "decision_maker_roles",
    "name_credentials",
    "name_particles",
    "name_prefixes",
    "normalize_language",
    "person_titles",
    "sentence_words",
    "supported_languages",
    "website_words",
]