from __future__ import annotations

import pytest
from pydantic import HttpUrl

from app.models.schemas.people import PersonCandidate
from app.transform.normalization.person import (
    normalize_linkedin_url,
    normalize_person,
    normalize_person_name,
    normalize_person_title,
    person_identity,
)


# ---------------------------------------------------------------------------
# Person name normalization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "language", "expected"),
    [
        (
            "  JOHN   SMITH  ",
            "en",
            "John Smith",
        ),
        (
            "JOHN SMITH",
            "en",
            "John Smith",
        ),
        (
            "Dr. JOHN SMITH",
            "en",
            "Dr. John Smith",
        ),
        (
            "ANNE-MARIE JANSEN",
            "en",
            "Anne-Marie Jansen",
        ),
        (
            "PETER O'CONNOR",
            "en",
            "Peter O'Connor",
        ),
        # Dutch surname particles.
        (
            "JAN VAN DER BERG",
            "nl",
            "Jan van der Berg",
        ),
        (
            "MARIA DE VRIES",
            "nl",
            "Maria de Vries",
        ),
        (
            "PIETER VAN DEN BROEK",
            "nl",
            "Pieter van den Broek",
        ),
        (
            "ANNE VAN DE VEEN",
            "nl",
            "Anne van de Veen",
        ),
        (
            "JAN TER HORST",
            "nl",
            "Jan ter Horst",
        ),
        (
            "PETER VAN 'T HOF",
            "nl",
            "Peter van 't Hof",
        ),
    ],
)
def test_normalize_person_name(
    value: str,
    language: str,
    expected: str,
) -> None:
    assert (
        normalize_person_name(
            value,
            language=language,
        )
        == expected
    )


# ---------------------------------------------------------------------------
# Person title normalization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "language", "expected"),
    [
        ("dr", "en", "Dr."),
        ("DR.", "en", "Dr."),
        ("doctor", "en", "Doctor"),
        ("dentist", "en", "Dentist"),
        ("founder", "en", "Founder"),
        ("co founder", "en", "Co-Founder"),
        ("ceo", "en", "CEO"),
        ("CEO", "en", "CEO"),
        ("dhr", "nl", "Dhr."),
        ("mevr.", "nl", "Mevr."),
        ("drs", "nl", "Drs."),
        ("prof.", "nl", "Prof."),
        ("ir.", "nl", "Ir."),
        ("ing", "nl", "Ing."),
        ("tandarts", "nl", "Tandarts"),
        ("kaakchirurg", "nl", "Kaakchirurg"),
        ("orthodontist", "nl", "Orthodontist"),
        ("directeur", "nl", "Directeur"),
        ("eigenaar", "nl", "Eigenaar"),
        ("oprichter", "nl", "Oprichter"),
        ("mede-oprichter", "nl", "Medeoprichter"),
        ("ceo", "nl", "CEO"),
    ],
)
def test_normalize_person_title(
    value: str,
    language: str,
    expected: str,
) -> None:
    assert (
        normalize_person_title(
            value,
            language=language,
        )
        == expected
    )


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "   ",
    ],
)
def test_normalize_person_title_empty(
    value: str | None,
) -> None:
    assert normalize_person_title(value) is None


def test_unknown_title_is_preserved() -> None:
    assert (
        normalize_person_title(
            "Head of Marketing",
            language="en",
        )
        == "Head Of Marketing"
    )


# ---------------------------------------------------------------------------
# LinkedIn URL normalization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "https://www.linkedin.com/in/john-smith/",
            "https://www.linkedin.com/in/john-smith",
        ),
        (
            "https://linkedin.com/in/john-smith/?trk=profile",
            "https://www.linkedin.com/in/john-smith",
        ),
        (
            "https://WWW.LINKEDIN.COM/in/john-smith#about",
            "https://www.linkedin.com/in/john-smith",
        ),
    ],
)
def test_normalize_linkedin_url(
    value: str,
    expected: str,
) -> None:
    assert normalize_linkedin_url(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not-a-url",
        "https://example.com/in/john-smith",
        "https://www.linkedin.com/company/acme",
        "https://www.linkedin.com/",
        "ftp://www.linkedin.com/in/john-smith",
    ],
)
def test_reject_invalid_linkedin_url(
    value: str,
) -> None:
    assert normalize_linkedin_url(value) is None


# ---------------------------------------------------------------------------
# Full person normalization
# ---------------------------------------------------------------------------


def test_normalize_person_english() -> None:
    candidate = PersonCandidate(
        name="  JOHN   SMITH ",
        title="dr",
        linkedin_url=HttpUrl(
            "https://www.linkedin.com/in/john-smith/?trk=profile"
        ),
        source_url=HttpUrl(
            "https://example.com/team"
        ),
    )

    result = normalize_person(
        candidate,
        language="en",
    )

    assert result.name == "John Smith"
    assert result.title == "Dr."
    assert str(result.linkedin_url) == (
        "https://www.linkedin.com/in/john-smith"
    )
    assert str(result.source_url) == (
        "https://example.com/team"
    )


def test_normalize_person_dutch() -> None:
    candidate = PersonCandidate(
        name="  JAN VAN DER BERG ",
        title="TANDARTS",
        linkedin_url=HttpUrl(
            "https://linkedin.com/in/jan-van-der-berg/"
        ),
        source_url=HttpUrl(
            "https://example.nl/team"
        ),
    )

    result = normalize_person(
        candidate,
        language="nl",
    )

    assert result.name == "Jan van der Berg"
    assert result.title == "Tandarts"
    assert str(result.linkedin_url) == (
        "https://www.linkedin.com/in/jan-van-der-berg"
    )


# ---------------------------------------------------------------------------
# Person identity
# ---------------------------------------------------------------------------


def test_person_identity_prefers_linkedin() -> None:
    candidate = PersonCandidate(
        name="John Smith",
        title="Dentist",
        linkedin_url=HttpUrl(
            "https://www.linkedin.com/in/john-smith/"
        ),
        source_url=HttpUrl(
            "https://example.com/team"
        ),
    )

    assert person_identity(candidate) == (
        "linkedin",
        "https://www.linkedin.com/in/john-smith",
    )


def test_person_identity_falls_back_to_normalized_name() -> None:
    candidate = PersonCandidate(
        name="  JAN   VAN DER   BERG ",
        title="Tandarts",
        source_url=HttpUrl(
            "https://example.nl/team"
        ),
    )

    assert person_identity(
        candidate,
        language="nl",
    ) == (
        "name",
        "jan van der berg",
    )


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_person_normalization_is_deterministic() -> None:
    candidate = PersonCandidate(
        name="JAN VAN DER BERG",
        title="tandarts",
        linkedin_url=HttpUrl(
            "https://linkedin.com/in/jan-van-der-berg/?trk=profile"
        ),
        source_url=HttpUrl(
            "https://example.nl/team"
        ),
    )

    first = normalize_person(
        candidate,
        language="nl",
    )

    second = normalize_person(
        candidate,
        language="nl",
    )

    assert first == second