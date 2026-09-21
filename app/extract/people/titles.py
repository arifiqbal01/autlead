# app/extract/people/titles.py

from __future__ import annotations

import re
from collections.abc import Iterable

from .words import normalize_language


# ---------------------------------------------------------------------------
# Title boundaries
# ---------------------------------------------------------------------------
#
# Do not use a loose \b for short titles such as:
#
#     CEO
#     CTO
#     CMO
#     COO
#     CFO
#     VP
#     Dr
#
# Otherwise a title can be detected inside another word.
#
# Example:
#
#     Cookie
#
# must NOT produce:
#
#     COO
#
# These boundaries also account for accented Unicode letters.
# ---------------------------------------------------------------------------

_TITLE_START = r"(?<![\wÀ-ÖØ-öø-ÿ])"
_TITLE_END = r"(?![\wÀ-ÖØ-öø-ÿ])"


# ---------------------------------------------------------------------------
# English titles
# ---------------------------------------------------------------------------

TITLE_RE = re.compile(
    rf"""
    {_TITLE_START}
    (
        Managing\s+Director
        | General\s+Manager
        | Commercial\s+Director
        | Operations?\s+Director
        | Technical\s+Director
        | Managing\s+Partner
        | Vice\s+President

        | Head\s+of\s+\w+(?:\s+\w+){{0,3}}
        | Lead(?:\s+\w+){{0,3}}

        | Co[- ]Founder
        | Founder
        | Owner
        | Director
        | Manager
        | Partner
        | President
        | VP

        | Consultant
        | Specialist
        | Developer
        | Designer
        | Engineer
        | Architect
        | Lawyer
        | Solicitor
        | Accountant
        | Researcher
        | Scientist
        | Principal

        | Professor
        | Prof\.?
        | Doctor
        | Dr\.?

        | CEO
        | CTO
        | CMO
        | COO
        | CFO
    )
    {_TITLE_END}
    """,
    re.IGNORECASE | re.UNICODE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Dutch titles
# ---------------------------------------------------------------------------

DUTCH_TITLE_RE = re.compile(
    rf"""
    {_TITLE_START}
    (
        Algemeen\s+Directeur
        | Commercieel\s+Directeur
        | Operationeel\s+Directeur
        | Technisch\s+Directeur
        | Beherend\s+Vennoot
        | Managing\s+Partner

        | Praktijkeigenaar
        | Praktijkhouder
        | Praktijkmanager
        | Vestigingsmanager
        | Bedrijfsleider
        | Projectmanager
        | Accountmanager
        | Teamleider
        | Teamlead

        | Mede[- ]?oprichter
        | Mede[- ]?eigenaar

        | Bestuurder
        | Bestuurslid

        | Directeur
        | Eigenaar
        | Ondernemer
        | Oprichter
        | Vennoot
        | Partner
        | Manager

        | Consultant
        | Specialist
        | Onderzoeker
        | Wetenschapper

        | Hoofd(?:\s+van)?(?:\s+\w+){{0,3}}

        | Dhr\.?
        | Mevr\.?
        | Mw\.?
        | Drs\.?
        | Ir\.?
        | Ing\.?
        | Prof\.?
        | Professor

        | CEO
        | CTO
        | CMO
        | COO
        | CFO
    )
    {_TITLE_END}
    """,
    re.IGNORECASE | re.UNICODE | re.VERBOSE,
)


def find_titles(
    text: str,
    *,
    language: str | None = None,
) -> Iterable[re.Match[str]]:
    """
    Find English and Dutch person titles.

    Dutch websites commonly mix Dutch and English business terminology,
    so both vocabularies are searched regardless of the selected language.

    Titles are returned in document order.
    """

    normalize_language(language)

    matches = list(
        TITLE_RE.finditer(text),
    )

    matches.extend(
        DUTCH_TITLE_RE.finditer(text),
    )

    return sorted(
        matches,
        key=lambda match: (
            match.start(),
            -len(match.group(0)),
        ),
    )


def extract_nearby_title(
    text: str,
    *,
    language: str | None = None,
) -> str | None:
    """
    Return the first recognized title from a local text fragment.
    """

    matches = list(
        find_titles(
            text,
            language=language,
        ),
    )

    if not matches:
        return None

    return matches[0].group(0).strip()


def contains_professional_title(
    text: str,
    *,
    language: str | None = None,
) -> bool:
    """
    Return whether the text contains at least one recognized
    professional/person title.
    """

    return any(
        find_titles(
            text,
            language=language,
        )
    )


__all__ = [
    "DUTCH_TITLE_RE",
    "TITLE_RE",
    "extract_nearby_title",
    "find_titles",
    "contains_professional_title",
]