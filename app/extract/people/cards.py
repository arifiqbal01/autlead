from __future__ import annotations

from dataclasses import dataclass

from bs4 import Tag

from .names import (
    extract_name_title_candidates,
    extract_title_name_candidates,
)
from .titles import contains_professional_title


@dataclass(frozen=True, slots=True)
class PersonCard:
    name: str
    title: str | None = None
    linkedin_url: str | None = None
    source_url: str | None = None
    evidence: tuple[str, ...] = ()


HEADING_TAGS = (
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
)

TITLE_TAGS = (
    "p",
    "span",
    "div",
    "small",
    "strong",
    "em",
)


def _clean_text(
    element: Tag,
) -> str:
    return " ".join(
        element.stripped_strings
    )


def _extract_heading(
    element: Tag,
) -> Tag | None:
    heading = element.find(
        HEADING_TAGS,
    )

    return (
        heading
        if isinstance(heading, Tag)
        else None
    )


def _extract_heading_text(
    element: Tag,
) -> str | None:
    heading = _extract_heading(
        element
    )

    if heading is None:
        return None

    text = _clean_text(
        heading
    )

    return text or None


def _extract_linkedin_url(
    element: Tag,
) -> str | None:
    for anchor in element.find_all(
        "a",
        href=True,
    ):
        href = anchor.get(
            "href"
        )

        if not isinstance(
            href,
            str,
        ):
            continue

        href = href.strip()

        if (
            "linkedin.com/in/"
            in href.casefold()
        ):
            return href

    return None


def _candidate_name_from_heading(
    element: Tag,
    *,
    source_url: str | None,
    language: str,
) -> tuple[str, str | None] | None:
    heading_text = _extract_heading_text(
        element
    )

    if not heading_text:
        return None

    candidates = []

    candidates.extend(
        extract_name_title_candidates(
            text=heading_text,
            source_url=source_url or "",
            language=language,
        )
    )

    candidates.extend(
        extract_title_name_candidates(
            text=heading_text,
            source_url=source_url or "",
            language=language,
        )
    )

    if not candidates:
        return None

    candidate = candidates[0]

    return (
        candidate.name,
        candidate.title,
    )


def _extract_card_title(
    element: Tag,
    *,
    name: str,
    language: str,
) -> str | None:
    """
    Extract a likely professional title from within the same
    person region.

    Only text recognized as a professional title is accepted.
    """

    heading = _extract_heading(
        element
    )

    for candidate in element.find_all(
        TITLE_TAGS,
    ):
        if (
            heading is not None
            and candidate is heading
        ):
            continue

        text = _clean_text(
            candidate
        )

        if not text:
            continue

        if (
            text.casefold()
            == name.casefold()
        ):
            continue

        if len(text) > 160:
            continue

        if not contains_professional_title(
            text=text,
            language=language,
        ):
            continue

        return text

    return None


def extract_person_cards(
    regions: list[Tag],
    *,
    source_url: str | None = None,
    language: str = "en",
) -> list[PersonCard]:
    """
    Extract people from previously identified person-like DOM regions.

    Regions should already be scoped by ``find_person_regions()``.

    Extraction remains conservative:

        - requires a credible name from the region heading
        - only accepts recognized professional titles
        - only attaches LinkedIn URLs found inside the same region
    """

    results: list[PersonCard] = []

    seen: set[
        tuple[
            str,
            str | None,
        ]
    ] = set()

    for region in regions:
        extracted = _candidate_name_from_heading(
            region,
            source_url=source_url,
            language=language,
        )

        if extracted is None:
            continue

        name, title = extracted

        if title is None:
            title = _extract_card_title(
                region,
                name=name,
                language=language,
            )

        linkedin_url = _extract_linkedin_url(
            region
        )

        identity = (
            name.casefold().strip(),
            (
                linkedin_url
                .casefold()
                .strip()
                if linkedin_url
                else None
            ),
        )

        if identity in seen:
            continue

        seen.add(identity)

        evidence = [
            "person-region",
            "heading",
        ]

        if title:
            evidence.append(
                "professional-title"
            )

        if linkedin_url:
            evidence.append(
                "linkedin"
            )

        results.append(
            PersonCard(
                name=name,
                title=title,
                linkedin_url=linkedin_url,
                source_url=source_url,
                evidence=tuple(
                    evidence
                ),
            )
        )

    return results


__all__ = [
    "PersonCard",
    "extract_person_cards",
]