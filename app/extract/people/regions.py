# app/extract/people/regions.py

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag


@dataclass(frozen=True, slots=True)
class PersonRegion:
    element: Tag
    score: int
    reasons: tuple[str, ...]


PERSON_CLASS_TERMS = frozenset(
    {
        "team",
        "team-member",
        "team_member",
        "teammember",
        "employee",
        "staff",
        "staff-member",
        "staff_member",
        "person",
        "person-card",
        "person_card",
        "people",
        "profile",
        "profile-card",
        "profile_card",
        "member",
        "leadership",
        "management",
        "medewerker",
        "medewerkers",
    }
)


NEGATIVE_CLASS_TERMS = frozenset(
    {
        "cookie",
        "consent",
        "privacy",
        "navigation",
        "breadcrumb",
        "footer",
        "sidebar",
        "menu",
        "popup",
        "modal",
        "header",
        "nav",
    }
)


LINKEDIN_HOST = "linkedin.com"


def find_person_regions(
    html: str,
    *,
    min_score: int = 6,
) -> list[PersonRegion]:
    """
    Identify DOM regions that are plausible person/team-member blocks.

    This is structural extraction only.

    It does not:

        - extract names
        - extract titles
        - crawl pages
        - resolve identities
        - score decision makers
        - persist data

    Typical downstream flow:

        HTML
          ↓
        find_person_regions()
          ↓
        PersonRegion[]
          ↓
        extract_person_cards()
    """

    if not html:
        return []

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    candidates: list[PersonRegion] = []

    for element in soup.find_all(
        (
            "article",
            "section",
            "li",
            "div",
        )
    ):
        if not isinstance(element, Tag):
            continue

        score, reasons = _score_region(
            element
        )

        if score < min_score:
            continue

        candidates.append(
            PersonRegion(
                element=element,
                score=score,
                reasons=tuple(reasons),
            )
        )

    return _remove_nested_regions(
        candidates
    )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _score_region(
    element: Tag,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    metadata_terms = _class_and_id_terms(
        element
    )

    # ---------------------------------------------------------
    # Positive structural evidence
    # ---------------------------------------------------------

    person_terms = (
        metadata_terms
        & PERSON_CLASS_TERMS
    )

    if person_terms:
        # Multiple relevant class/id signals are useful, but
        # avoid allowing huge containers to gain unlimited score.
        score += min(
            len(person_terms) * 5,
            10,
        )

        for term in sorted(person_terms):
            reasons.append(
                f"class:{term}"
            )

    # ---------------------------------------------------------
    # Negative structural evidence
    # ---------------------------------------------------------

    negative_terms = (
        metadata_terms
        & NEGATIVE_CLASS_TERMS
    )

    if negative_terms:
        score -= min(
            len(negative_terms) * 10,
            20,
        )

        for term in sorted(negative_terms):
            reasons.append(
                f"negative:{term}"
            )

    # ---------------------------------------------------------
    # LinkedIn personal profile
    # ---------------------------------------------------------

    if _has_linkedin_profile(
        element
    ):
        score += 6
        reasons.append(
            "linkedin-profile"
        )

    # ---------------------------------------------------------
    # Schema.org Person
    # ---------------------------------------------------------

    if _has_schema_person(
        element
    ):
        score += 10
        reasons.append(
            "schema-person"
        )

    # ---------------------------------------------------------
    # Heading
    # ---------------------------------------------------------

    heading_count = _heading_count(
        element
    )

    if heading_count == 1:
        score += 3
        reasons.append(
            "single-heading"
        )

    elif 2 <= heading_count <= 3:
        score += 1
        reasons.append(
            "few-headings"
        )

    elif heading_count > 6:
        # Large section/container rather than individual card.
        score -= 3
        reasons.append(
            "many-headings"
        )

    # ---------------------------------------------------------
    # Image evidence
    # ---------------------------------------------------------

    if _has_likely_person_image(
        element
    ):
        score += 2
        reasons.append(
            "person-image"
        )

    # ---------------------------------------------------------
    # Region size
    # ---------------------------------------------------------

    text = _clean_text(
        element
    )

    text_length = len(text)

    if 10 <= text_length <= 500:
        score += 2
        reasons.append(
            "reasonable-text-size"
        )

    elif text_length > 1500:
        # Strong indication that this is a parent section rather
        # than one person's card.
        score -= 5
        reasons.append(
            "oversized-region"
        )

    # ---------------------------------------------------------
    # Link density
    # ---------------------------------------------------------

    links = element.find_all(
        "a",
        href=True,
    )

    if len(links) > 20:
        score -= 4
        reasons.append(
            "high-link-density"
        )

    return score, reasons


# ---------------------------------------------------------------------------
# Structural signals
# ---------------------------------------------------------------------------


def _class_and_id_terms(
    element: Tag,
) -> set[str]:
    """
    Convert class/id metadata into normalized terms.

    This avoids loose substring matching.

    Example:

        class="team-member profile-card"

    becomes:

        {
            "team-member",
            "team",
            "member",
            "profile-card",
            "profile",
            "card",
        }

    while:

        class="steampunk"

    does not accidentally match:

        team
    """

    values: list[str] = []

    classes = element.get(
        "class",
        [],
    )

    if isinstance(classes, str):
        classes = [classes]

    values.extend(
        str(value)
        for value in classes
    )

    element_id = element.get(
        "id"
    )

    if isinstance(element_id, str):
        values.append(element_id)

    terms: set[str] = set()

    for value in values:
        normalized = (
            value
            .casefold()
            .strip()
        )

        if not normalized:
            continue

        terms.add(normalized)

        for token in re.split(
            r"[\s_\-]+",
            normalized,
        ):
            if token:
                terms.add(token)

    return terms


def _has_linkedin_profile(
    element: Tag,
) -> bool:
    for anchor in element.find_all(
        "a",
        href=True,
    ):
        href = anchor.get(
            "href"
        )

        if not isinstance(href, str):
            continue

        href_lower = href.casefold()

        if (
            LINKEDIN_HOST in href_lower
            and "/in/" in href_lower
        ):
            return True

    return False


def _has_schema_person(
    element: Tag,
) -> bool:
    """
    Detect Schema.org Person microdata within the region.
    """

    current: Tag | None = element

    itemtype = current.get(
        "itemtype"
    )

    if _itemtype_contains_person(
        itemtype
    ):
        return True

    nested = element.find(
        attrs={
            "itemtype": True,
        }
    )

    if isinstance(nested, Tag):
        return _itemtype_contains_person(
            nested.get("itemtype")
        )

    return False


def _itemtype_contains_person(
    value,
) -> bool:
    if value is None:
        return False

    values = (
        [value]
        if isinstance(value, str)
        else list(value)
    )

    return any(
        "schema.org/person"
        in str(item).casefold()
        for item in values
    )


def _has_likely_person_image(
    element: Tag,
) -> bool:
    """
    Use image metadata only as weak supporting evidence.

    An image alone never establishes that a region represents a person.
    """

    for image in element.find_all(
        "img"
    ):
        alt = image.get(
            "alt"
        )

        if not isinstance(alt, str):
            continue

        alt = " ".join(
            alt.split()
        )

        if not alt:
            continue

        # Avoid some obvious non-person imagery.
        alt_lower = alt.casefold()

        if any(
            term in alt_lower
            for term in (
                "logo",
                "icon",
                "banner",
                "background",
                "product",
            )
        ):
            continue

        return True

    return False


def _heading_count(
    element: Tag,
) -> int:
    return len(
        element.find_all(
            (
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
            )
        )
    )


def _clean_text(
    element: Tag,
) -> str:
    return " ".join(
        element.stripped_strings
    )


# ---------------------------------------------------------------------------
# Region pruning
# ---------------------------------------------------------------------------


def _remove_nested_regions(
    regions: list[PersonRegion],
) -> list[PersonRegion]:
    """
    Prefer the smallest strong person region.

    Team pages often produce structures like:

        section.team
            div.team-grid
                div.team-member
                    h3
                    p
                    linkedin

    All three containers may score positively.

    We want:

        div.team-member

    rather than:

        section.team
    """

    # Deepest elements first.
    ordered = sorted(
        regions,
        key=lambda region: (
            _element_depth(
                region.element
            ),
            region.score,
        ),
        reverse=True,
    )

    selected: list[PersonRegion] = []

    for region in ordered:
        element = region.element

        # If one of the already-selected deeper regions lives
        # inside this element, this element is likely its parent
        # container and should normally be discarded.
        contains_selected_region = any(
            element
            in existing.element.parents
            for existing in selected
        )

        if contains_selected_region:
            continue

        # Avoid exact duplicates defensively.
        if any(
            existing.element is element
            for existing in selected
        ):
            continue

        selected.append(
            region
        )

    # Highest-confidence regions first for downstream extraction.
    return sorted(
        selected,
        key=lambda region: (
            -region.score,
            _element_depth(
                region.element
            ),
        ),
    )


def _element_depth(
    element: Tag,
) -> int:
    return sum(
        1
        for _ in element.parents
    )


__all__ = [
    "PersonRegion",
    "find_person_regions",
]