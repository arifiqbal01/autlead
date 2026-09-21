# app/extract/people/names.py

from __future__ import annotations

from collections.abc import Iterable

from app.models.schemas.people import PersonCandidate

from .patterns import NAME_RE
from .titles import find_titles
from .words import (
    combined_person_titles,
    combined_sentence_words,
    combined_website_words,
    name_particles,
)


TITLE_NAME_WINDOW = 60
NAME_TITLE_WINDOW = 80


def extract_title_name_candidates(
    *,
    text: str,
    source_url: str,
    language: str,
) -> Iterable[PersonCandidate]:
    """
    Extract explicit title/name combinations.

    Examples:

        Dr. John Smith
        Directeur Jan de Vries
        CEO John Smith
        Eigenaar Jan de Vries
        John Smith, Managing Director

    This is one of the stronger text-based extraction paths.
    """

    if not text:
        return

    for title_match in find_titles(
        text,
        language=language,
    ):
        title = title_match.group(0).strip()

        # -----------------------------------------------------
        # Title before name
        # -----------------------------------------------------

        right = text[
            title_match.end():
            min(
                len(text),
                title_match.end()
                + TITLE_NAME_WINDOW,
            )
        ]

        name = extract_name_after(
            right
        )

        if name:
            yield PersonCandidate(
                name=name,
                title=title,
                linkedin_url=None,
                source_url=source_url,
            )
            continue

        # -----------------------------------------------------
        # Name before title
        # -----------------------------------------------------

        left = text[
            max(
                0,
                title_match.start()
                - TITLE_NAME_WINDOW,
            ):
            title_match.start()
        ]

        name = extract_name_before(
            left
        )

        if name:
            yield PersonCandidate(
                name=name,
                title=title,
                linkedin_url=None,
                source_url=source_url,
            )


def extract_name_title_candidates(
    *,
    text: str,
    source_url: str,
    language: str,
) -> Iterable[PersonCandidate]:
    """
    Extract names with a nearby professional title.

    This is lower-confidence than an explicit title/name sequence.

    The nearest title in the local context is preferred.
    """

    if not text:
        return

    for match in NAME_RE.finditer(
        text
    ):
        name = clean_name_candidate(
            match.group("name"),
        )

        if not name:
            continue

        context_start = max(
            0,
            match.start()
            - NAME_TITLE_WINDOW,
        )

        context_end = min(
            len(text),
            match.end()
            + NAME_TITLE_WINDOW,
        )

        context = text[
            context_start:
            context_end
        ]

        name_start_in_context = (
            match.start()
            - context_start
        )

        name_end_in_context = (
            match.end()
            - context_start
        )

        title = _nearest_title(
            context,
            name_start=name_start_in_context,
            name_end=name_end_in_context,
            language=language,
        )

        if not title:
            continue

        yield PersonCandidate(
            name=name,
            title=title,
            linkedin_url=None,
            source_url=source_url,
        )


def extract_name_after(
    text: str,
) -> str | None:
    """
    Extract a name immediately following a title.
    """

    text = text.lstrip(
        " \t\r\n-–—|,:;/()",
    )

    match = NAME_RE.match(
        text
    )

    if not match:
        return None

    return clean_name_candidate(
        match.group("name"),
    )


def extract_name_before(
    text: str,
) -> str | None:
    """
    Extract a name immediately before a title.
    """

    text = text.rstrip(
        " \t\r\n-–—|,:;/()",
    )

    matches = list(
        NAME_RE.finditer(text),
    )

    if not matches:
        return None

    match = matches[-1]

    trailing = text[
        match.end():
    ]

    if trailing.strip(
        " \t\r\n-–—|,:;/()",
    ):
        return None

    return clean_name_candidate(
        match.group("name"),
    )


def extract_best_name(
    text: str,
) -> str | None:
    """
    Select the strongest plausible name from a short text fragment.

    Preference is given to ordinary two- or three-part human names.
    """

    candidates: list[str] = []

    for match in NAME_RE.finditer(
        text
    ):
        name = clean_name_candidate(
            match.group("name"),
        )

        if name:
            candidates.append(
                name
            )

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda value: (
            abs(
                len(value.split())
                - 2
            ),
            len(value),
        ),
    )


def clean_name_candidate(
    value: str,
) -> str | None:
    """
    Reject or clean obvious non-person strings.

    This is extraction filtering only.

    It does not:

        - normalize canonical names
        - resolve identities
        - verify people
        - score people
        - determine decision-maker status
    """

    value = " ".join(
        value.split()
    )

    if not value:
        return None

    words = value.split()

    if not 2 <= len(words) <= 6:
        return None

    # ---------------------------------------------------------
    # Remove trailing title leakage
    # ---------------------------------------------------------

    words = _trim_trailing_title_words(
        words
    )

    if not 2 <= len(words) <= 4:
        return None

    normalized = [
        _comparison_word(word)
        for word in words
    ]

    if any(
        not word
        for word in normalized
    ):
        return None

    sentence_words = (
        combined_sentence_words()
    )

    website_words = (
        combined_website_words()
    )

    # ---------------------------------------------------------
    # Sentence fragments
    # ---------------------------------------------------------

    if any(
        word in sentence_words
        for word in normalized
    ):
        return None

    # ---------------------------------------------------------
    # Website/UI vocabulary
    # ---------------------------------------------------------

    if any(
        word in website_words
        for word in normalized
    ):
        return None

    # ---------------------------------------------------------
    # Placeholder names
    # ---------------------------------------------------------

    placeholders = {
        "voornaam",
        "achternaam",
        "voornaam achternaam",
        "firstname",
        "lastname",
        "first name",
        "last name",
        "john doe",
        "jane doe",
    }

    normalized_value = " ".join(
        normalized
    )

    if normalized_value in placeholders:
        return None

    # ---------------------------------------------------------
    # Obvious technical / UI phrases
    # ---------------------------------------------------------

    rejected_phrases = {
        "accessibility statement",
        "privacy policy",
        "cookie policy",
        "terms conditions",
        "terms service",
        "google partner",
        "meta business",
        "cloudways partner",
        "read more",
        "learn more",
        "contact us",
        "about us",
        "our team",
    }

    if normalized_value in rejected_phrases:
        return None

    # ---------------------------------------------------------
    # Role-only strings
    # ---------------------------------------------------------

    role_words = _role_words()

    non_particle_words = [
        word
        for word in normalized
        if word
        not in _particle_tokens()
    ]

    if len(non_particle_words) < 2:
        return None

    if all(
        word in role_words
        for word in non_particle_words
    ):
        return None

    # ---------------------------------------------------------
    # Organization-like combinations
    # ---------------------------------------------------------

    organization_words = {
        "clinic",
        "clinics",
        "dental",
        "tandarts",
        "centrum",
        "center",
        "group",
        "groep",
        "company",
        "bedrijf",
        "bedrijven",
        "agency",
        "bureau",
        "studio",
        "bv",
        "b.v",
        "b.v.",
        "amsterdam",
        "rotterdam",
        "utrecht",
        "bilthoven",
        "amersfoort",
        "lahore",
    }

    organization_hits = sum(
        word in organization_words
        for word in normalized
    )

    if organization_hits >= 2:
        return None

    # ---------------------------------------------------------
    # Obvious location/address combinations
    # ---------------------------------------------------------

    location_words = {
        "straat",
        "street",
        "laan",
        "road",
        "weg",
        "plein",
        "square",
        "avenue",
        "boulevard",
        "maliebaan",
        "utrecht",
        "amsterdam",
        "rotterdam",
        "bilthoven",
        "amersfoort",
        "lahore",
    }

    if sum(
        word in location_words
        for word in normalized
    ) >= 2:
        return None

    # ---------------------------------------------------------
    # Reject punctuation-heavy/non-name strings
    # ---------------------------------------------------------

    if any(
        character in value
        for character in (
            "@",
            "/",
            "\\",
            "=",
            "<",
            ">",
        )
    ):
        return None

    return " ".join(
        words
    )


def _nearest_title(
    text: str,
    *,
    name_start: int,
    name_end: int,
    language: str,
) -> str | None:
    """
    Return the professional title closest to the name.

    This reduces false associations where multiple people or roles occur
    inside the same text window.
    """

    matches = list(
        find_titles(
            text,
            language=language,
        )
    )

    if not matches:
        return None

    def distance(
        match,
    ) -> int:
        if match.end() <= name_start:
            return (
                name_start
                - match.end()
            )

        if match.start() >= name_end:
            return (
                match.start()
                - name_end
            )

        return 0

    closest = min(
        matches,
        key=lambda match: (
            distance(match),
            -len(match.group(0)),
        ),
    )

    # Keep proximity conservative.
    if distance(closest) > 50:
        return None

    return closest.group(0).strip()


def _trim_trailing_title_words(
    words: list[str],
) -> list[str]:
    """
    Remove trailing professional-title leakage.

    Examples:

        Jana Stickelbruck Vestigingsmanager
            -> Jana Stickelbruck

        Maarten Vaartjes Tandarts
            -> Maarten Vaartjes

        John Smith Managing Director
            -> John Smith
    """

    title_words = _title_tokens()

    cleaned = list(
        words
    )

    while len(cleaned) > 2:
        last_word = _comparison_word(
            cleaned[-1],
        )

        if (
            last_word
            not in title_words
        ):
            break

        cleaned.pop()

    return cleaned


def _title_tokens() -> set[str]:
    """
    Return configured English and Dutch title tokens.
    """

    tokens: set[str] = set()

    for title in combined_person_titles():
        for part in title.split():
            normalized = _comparison_word(
                part
            )

            if normalized:
                tokens.add(
                    normalized
                )

    return tokens


def _role_words() -> set[str]:
    """
    Return professional role/title words that by themselves do not
    constitute a human name.
    """

    return {
        "ceo",
        "cto",
        "cfo",
        "cmo",
        "coo",
        "vp",
        "founder",
        "cofounder",
        "co-founder",
        "owner",
        "director",
        "manager",
        "partner",
        "president",
        "head",
        "lead",
        "principal",
        "eigenaar",
        "directeur",
        "oprichter",
        "medeoprichter",
        "mede-oprichter",
        "vennoot",
        "bestuurder",
        "praktijkeigenaar",
        "praktijkhouder",
        "praktijkmanager",
        "vestigingsmanager",
        "bedrijfsleider",
        "projectmanager",
        "accountmanager",
        "teamleider",
        "teamlead",
        "consultant",
        "specialist",
        "onderzoeker",
        "wetenschapper",
        "tandarts",
        "arts",
        "doctor",
        "dr",
        "engineer",
        "architect",
        "lawyer",
        "accountant",
        "designer",
        "developer",
        "researcher",
        "scientist",
    }


def _particle_tokens() -> set[str]:
    """
    Return configured English and Dutch surname particles.
    """

    particles: set[str] = set()

    for values in (
        name_particles("en"),
        name_particles("nl"),
    ):
        for value in values:
            particles.update(
                value.casefold().split(),
            )

    return particles


def _comparison_word(
    value: str,
) -> str:
    """
    Normalize a word only for extraction-level comparison/filtering.
    """

    return value.strip(
        ".,:;!?()[]{}\"“”‘’",
    ).casefold()


__all__ = [
    "clean_name_candidate",
    "extract_best_name",
    "extract_name_after",
    "extract_name_before",
    "extract_name_title_candidates",
    "extract_title_name_candidates",
]